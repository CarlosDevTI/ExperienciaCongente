from datetime import datetime, time

from django.db.models import Avg, Count, Q
from django.db.models.functions import TruncDate
from django.utils import timezone

from surveys.models import Answer, Area, QrEntryPoint, SurveySubmission
from surveys.services import serialize_answer


DATE_INPUT_FORMAT = '%Y-%m-%d'
EXPORT_BASE_HEADERS = [
    'Tipo de encuesta',
    'Area',
    'Punto / Origen',
    'Canal preferido',
    'Estado',
    'Fecha de respuesta',
    'Fecha de finalizacion',
]


def parse_date(value, *, end_of_day=False):
    if not value:
        return None
    parsed = datetime.strptime(value, DATE_INPUT_FORMAT).date()
    if end_of_day:
        return timezone.make_aware(datetime.combine(parsed, time.max))
    return timezone.make_aware(datetime.combine(parsed, time.min))


def get_filter_options():
    return {
        'areas': Area.objects.filter(is_active=True).order_by('name'),
        'qr_entries': QrEntryPoint.objects.filter(is_active=True).select_related('area').order_by('area__name', 'name'),
        'channels': (
            SurveySubmission.objects.exclude(preferred_channel='')
            .values_list('preferred_channel', flat=True)
            .distinct()
            .order_by('preferred_channel')
        ),
    }


def get_filtered_submissions(params):
    queryset = (
        SurveySubmission.objects.filter(status=SurveySubmission.Status.COMPLETED)
        .select_related('survey', 'area', 'qr_entry_point')
        .prefetch_related('answers__question', 'answers__selected_option', 'answers__selected_options')
    )

    area = params.get('area')
    channel = params.get('channel')
    qr_entry = params.get('qr')
    start_date = parse_date(params.get('start_date')) if params.get('start_date') else None
    end_date = parse_date(params.get('end_date'), end_of_day=True) if params.get('end_date') else None

    if area:
        queryset = queryset.filter(area__slug=area)
    if channel:
        queryset = queryset.filter(preferred_channel=channel)
    if qr_entry:
        queryset = queryset.filter(qr_entry_point_id=qr_entry)
    if start_date:
        queryset = queryset.filter(created_at__gte=start_date)
    if end_date:
        queryset = queryset.filter(created_at__lte=end_date)

    return queryset.order_by('-created_at')


def build_dashboard_summary(queryset):
    response_count = queryset.count()
    responses_by_area = list(queryset.values('area__name').annotate(total=Count('id')).order_by('-total'))

    rating_averages = [
        {
            **item,
            'question_label': question_label_from_code(item['question__code']),
        }
        for item in (
            Answer.objects.filter(submission__in=queryset, question__question_type='rating')
            .values('question__code', 'question__text')
            .annotate(average=Avg('rating_value'), total=Count('id'))
            .order_by('question__order')
        )
    ]

    channel_distribution = list(
        queryset.exclude(preferred_channel='')
        .values('preferred_channel')
        .annotate(total=Count('id'))
        .order_by('-total')
    )

    recommendation_total = Answer.objects.filter(submission__in=queryset, question__code='q7').count()
    recommendation_yes = Answer.objects.filter(
        submission__in=queryset,
        question__code='q7',
        boolean_value=True,
    ).count()
    recommendation_rate = round((recommendation_yes / recommendation_total) * 100, 1) if recommendation_total else 0

    comments = list(
        Answer.objects.filter(submission__in=queryset)
        .filter(Q(question__code='q10') | Q(text_value__gt=''))
        .exclude(text_value='')
        .select_related('submission', 'question', 'submission__area')
        .order_by('-created_at')[:25]
    )

    trends = list(
        queryset.annotate(day=TruncDate('created_at'))
        .values('day')
        .annotate(total=Count('id'))
        .order_by('day')
    )

    return {
        'response_count': response_count,
        'responses_by_area': responses_by_area,
        'rating_averages': rating_averages,
        'channel_distribution': channel_distribution,
        'recommendation_rate': recommendation_rate,
        'comments': comments,
        'trends': trends,
    }


def build_chart_payload(summary):
    return {
        'responsesByArea': {
            'labels': [item['area__name'] for item in summary['responses_by_area']],
            'values': [item['total'] for item in summary['responses_by_area']],
        },
        'channelDistribution': {
            'labels': [item['preferred_channel'] for item in summary['channel_distribution']],
            'values': [item['total'] for item in summary['channel_distribution']],
        },
        'trend': {
            'labels': [item['day'].strftime('%Y-%m-%d') for item in summary['trends']],
            'values': [item['total'] for item in summary['trends']],
        },
    }


def question_label_from_code(code):
    suffix = ''.join(character for character in str(code) if character.isdigit())
    if suffix:
        return f'Pregunta {suffix}'
    return str(code).replace('_', ' ').title()


def get_export_question_headers(submissions):
    seen = {}
    for submission in submissions:
        for answer in submission.answers.all():
            seen[answer.question_id] = answer.question
    questions = sorted(seen.values(), key=lambda question: (question.order, question.id))
    return [question.business_label for question in questions]


def submission_to_export_row(submission):
    row = {
        'Tipo de encuesta': submission.survey.name,
        'Area': submission.area.name,
        'Punto / Origen': submission.qr_entry_point.display_name,
        'Canal preferido': submission.preferred_channel or '-',
        'Estado': submission.get_status_display(),
        'Fecha de respuesta': timezone.localtime(submission.created_at).strftime('%Y-%m-%d %H:%M'),
        'Fecha de finalizacion': timezone.localtime(submission.completed_at).strftime('%Y-%m-%d %H:%M') if submission.completed_at else '',
    }
    for answer in submission.answers.all():
        row[answer.question.business_label] = serialize_answer(answer)
    return row
