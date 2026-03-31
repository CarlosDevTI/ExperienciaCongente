import ipaddress
import uuid

from django.conf import settings
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.html import strip_tags

from .models import Answer, AreaQuestion, ChoiceOption, QrEntryPoint, SubmissionEvent, SurveySubmission


RATING_LABELS = {
    1: 'Muy mala',
    2: 'Mala',
    3: 'Regular',
    4: 'Buena',
    5: 'Excelente',
}


def is_htmx_request(request):
    return request.headers.get('HX-Request') == 'true'


def get_client_ip(request):
    forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    if forwarded:
        return forwarded.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


def anonymize_ip(raw_ip):
    if not raw_ip:
        return None
    try:
        parsed = ipaddress.ip_address(raw_ip)
    except ValueError:
        return None

    if parsed.version == 4:
        network = ipaddress.ip_network(f'{parsed}/24', strict=False)
        return str(network.network_address)

    network = ipaddress.ip_network(f'{parsed}/64', strict=False)
    return str(network.network_address)


def sanitize_text(value):
    return ' '.join(strip_tags(value or '').split())


def get_session_uuid(request):
    cookie_name = settings.SURVEY_SESSION_COOKIE
    raw = request.COOKIES.get(cookie_name)
    try:
        return uuid.UUID(str(raw)), False
    except (ValueError, TypeError, AttributeError):
        return uuid.uuid4(), True


def set_session_cookie(response, session_uuid):
    response.set_cookie(
        settings.SURVEY_SESSION_COOKIE,
        str(session_uuid),
        max_age=settings.SURVEY_SESSION_COOKIE_AGE,
        samesite='Lax',
        secure=settings.SESSION_COOKIE_SECURE,
    )
    return response


def get_qr_entry_point(area_slug, token):
    qr_entry = get_object_or_404(
        QrEntryPoint.objects.select_related('survey', 'area'),
        public_token=token,
        is_active=True,
        survey__is_active=True,
        area__is_active=True,
    )
    if qr_entry.area.slug != area_slug:
        raise Http404('QR no válido para esta área.')
    return qr_entry


def get_area_questions(qr_entry):
    return list(
        AreaQuestion.objects.filter(
            survey=qr_entry.survey,
            area=qr_entry.area,
            is_visible=True,
            question__is_active=True,
        )
        .select_related('question')
        .prefetch_related('question__options')
        .order_by('order', 'id')
    )


def log_event(event_type, submission=None, qr_entry_point=None, metadata=None):
    SubmissionEvent.objects.create(
        submission=submission,
        qr_entry_point=qr_entry_point,
        event_type=event_type,
        metadata=metadata or {},
    )


def get_submission_for_request(request, qr_entry):
    session_uuid, is_new = get_session_uuid(request)
    submission = (
        SurveySubmission.objects.filter(qr_entry_point=qr_entry, session_uuid=session_uuid)
        .select_related('survey', 'area', 'qr_entry_point')
        .prefetch_related('answers__selected_options', 'answers__selected_option')
        .order_by('-created_at')
        .first()
    )
    return submission, session_uuid, is_new


def get_or_create_submission(request, qr_entry):
    submission, session_uuid, is_new = get_submission_for_request(request, qr_entry)
    blocked = False
    if submission and submission.status == SurveySubmission.Status.COMPLETED and not qr_entry.allow_multiple_submissions:
        blocked = True
        log_event(
            SubmissionEvent.EventType.BLOCKED_DUPLICATE,
            submission=submission,
            qr_entry_point=qr_entry,
            metadata={'session_uuid': str(session_uuid)},
        )
        return submission, session_uuid, is_new, blocked, False

    created = False
    if not submission or submission.status == SurveySubmission.Status.COMPLETED:
        submission = SurveySubmission.objects.create(
            survey=qr_entry.survey,
            area=qr_entry.area,
            qr_entry_point=qr_entry,
            session_uuid=session_uuid,
            ip_address=anonymize_ip(get_client_ip(request)),
            user_agent=request.META.get('HTTP_USER_AGENT', '')[:512],
        )
        created = True
        log_event(SubmissionEvent.EventType.OPENED, submission=submission, qr_entry_point=qr_entry)
    return submission, session_uuid, is_new, blocked, created


def get_existing_answer(submission, question):
    return submission.answers.filter(question=question).first()


def save_answer(submission, area_question, cleaned_data):
    question = area_question.question
    answer, _ = Answer.objects.get_or_create(submission=submission, question=question)
    answer.rating_value = None
    answer.boolean_value = None
    answer.selected_option = None
    answer.text_value = ''
    answer.save()
    answer.selected_options.clear()

    response = cleaned_data.get('response')
    other_text = sanitize_text(cleaned_data.get('other_text', ''))

    if question.question_type == question.QuestionType.RATING:
        answer.rating_value = int(response)
    elif question.question_type == question.QuestionType.YES_NO:
        answer.boolean_value = response == 'yes'
    elif question.question_type == question.QuestionType.SINGLE_CHOICE:
        selected = question.options.filter(value=response).first()
        answer.selected_option = selected
        if question.code == 'q8' and selected:
            submission.preferred_channel = selected.label
            submission.save(update_fields=['preferred_channel', 'updated_at'])
    elif question.question_type == question.QuestionType.MULTIPLE_CHOICE:
        selected = list(question.options.filter(value__in=response))
        answer.save()
        if selected:
            answer.selected_options.set(selected)
        answer.text_value = other_text
    else:
        answer.text_value = sanitize_text(response)

    if question.question_type != question.QuestionType.MULTIPLE_CHOICE:
        answer.text_value = answer.text_value or other_text
    answer.save()

    if question.code == 'q8' and not answer.selected_option:
        submission.preferred_channel = ''
        submission.save(update_fields=['preferred_channel', 'updated_at'])

    log_event(
        SubmissionEvent.EventType.STEP_SAVED,
        submission=submission,
        qr_entry_point=submission.qr_entry_point,
        metadata={'question_code': question.code},
    )
    return answer


def complete_submission(submission):
    submission.status = SurveySubmission.Status.COMPLETED
    submission.completed_at = timezone.now()
    submission.save(update_fields=['status', 'completed_at', 'updated_at'])
    log_event(
        SubmissionEvent.EventType.SUBMITTED,
        submission=submission,
        qr_entry_point=submission.qr_entry_point,
        metadata={'completed_at': submission.completed_at.isoformat()},
    )
    return submission


def serialize_answer(answer):
    if answer.rating_value is not None:
        return RATING_LABELS.get(answer.rating_value, str(answer.rating_value))
    if answer.boolean_value is not None:
        return 'Sí' if answer.boolean_value else 'No'
    if answer.selected_option_id:
        return answer.selected_option.label
    selected = list(answer.selected_options.values_list('label', flat=True))
    if selected:
        if answer.text_value:
            selected.append(answer.text_value)
        return ', '.join(selected)
    return answer.text_value


def get_choice_map(question):
    return {option.value: option for option in question.options.all()}

