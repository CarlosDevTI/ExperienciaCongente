import csv
from io import BytesIO

from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth import logout
from django.core.paginator import Paginator
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from analytics.services import (
    EXPORT_BASE_HEADERS,
    build_chart_payload,
    build_dashboard_summary,
    get_export_question_headers,
    get_filter_options,
    get_filtered_submissions,
    submission_to_export_row,
)
from surveys.models import SurveySubmission


@staff_member_required
def index(request):
    submissions = get_filtered_submissions(request.GET)
    summary = build_dashboard_summary(submissions)
    context = {
        'summary': summary,
        'filters': request.GET,
        'filter_options': get_filter_options(),
        'chart_data': build_chart_payload(summary),
    }
    return render(request, 'dashboard/index.html', context)


@staff_member_required
def responses_list(request):
    submissions = get_filtered_submissions(request.GET)
    paginator = Paginator(submissions, 20)
    page_obj = paginator.get_page(request.GET.get('page'))
    context = {
        'page_obj': page_obj,
        'filters': request.GET,
        'filter_options': get_filter_options(),
    }
    return render(request, 'dashboard/responses_list.html', context)


@staff_member_required
def response_detail(request, submission_id):
    submission = get_object_or_404(
        SurveySubmission.objects.select_related('survey', 'area', 'qr_entry_point').prefetch_related(
            'answers__question', 'answers__selected_option', 'answers__selected_options'
        ),
        pk=submission_id,
    )
    answers = submission.answers.all().order_by('question__order')
    return render(request, 'dashboard/response_detail.html', {'submission': submission, 'answers': answers})


@staff_member_required
def export_csv(request):
    submissions = list(get_filtered_submissions(request.GET))
    question_headers = get_export_question_headers(submissions)
    headers = EXPORT_BASE_HEADERS + question_headers
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="congente_responses.csv"'
    writer = csv.DictWriter(response, fieldnames=headers)
    writer.writeheader()
    for submission in submissions:
        writer.writerow(submission_to_export_row(submission))
    return response


@staff_member_required
def export_excel(request):
    try:
        from openpyxl import Workbook
    except ImportError:
        return HttpResponse('openpyxl no esta instalado.', status=503)

    submissions = list(get_filtered_submissions(request.GET))
    question_headers = get_export_question_headers(submissions)
    headers = EXPORT_BASE_HEADERS + question_headers
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = 'Responses'
    sheet.append(headers)
    for submission in submissions:
        row = submission_to_export_row(submission)
        sheet.append([row.get(column, '') for column in headers])

    output = BytesIO()
    workbook.save(output)
    output.seek(0)

    response = HttpResponse(
        output.getvalue(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )
    response['Content-Disposition'] = 'attachment; filename="congente_responses.xlsx"'
    return response


@require_POST
def logout_view(request):
    logout(request)
    login_url = reverse('admin:login')
    return redirect(f'{login_url}?next={reverse("dashboard:index")}')
