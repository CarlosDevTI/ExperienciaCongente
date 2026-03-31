from django.http import Http404, HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.cache import never_cache

from .forms import QuestionResponseForm
from .services import (
    complete_submission,
    get_area_questions,
    get_existing_answer,
    get_or_create_submission,
    get_qr_entry_point,
    get_submission_for_request,
    is_htmx_request,
    save_answer,
    set_session_cookie,
)


MOBILE_USER_AGENT_TOKENS = ('android', 'iphone', 'ipad', 'ipod', 'mobile')


def is_mobile_request(request):
    user_agent = request.META.get('HTTP_USER_AGENT', '').lower()
    return any(token in user_agent for token in MOBILE_USER_AGENT_TOKENS)


@never_cache
def landing(request, area_slug, token):
    qr_entry = get_qr_entry_point(area_slug, token)
    submission, session_uuid, is_new_cookie = get_submission_for_request(request, qr_entry)
    already_submitted = bool(
        submission
        and submission.status == submission.Status.COMPLETED
        and not qr_entry.allow_multiple_submissions
    )

    if is_mobile_request(request):
        if already_submitted:
            response = redirect(f"{reverse('surveys:thank_you', kwargs={'area_slug': area_slug, 'token': token})}?repeat=1")
        else:
            submission, session_uuid, is_new_cookie, blocked, _ = get_or_create_submission(request, qr_entry)
            if blocked:
                response = redirect(f"{reverse('surveys:thank_you', kwargs={'area_slug': area_slug, 'token': token})}?repeat=1")
            else:
                response = redirect('surveys:step', area_slug=area_slug, token=token, step=1)

        if is_new_cookie:
            set_session_cookie(response, session_uuid)
        return response

    context = {
        'qr_entry': qr_entry,
        'survey': qr_entry.survey,
        'area': qr_entry.area,
        'already_submitted': already_submitted,
    }
    return render(request, 'surveys/landing.html', context)


@never_cache
def start(request, area_slug, token):
    if request.method != 'POST':
        return redirect('surveys:landing', area_slug=area_slug, token=token)

    qr_entry = get_qr_entry_point(area_slug, token)
    submission, session_uuid, is_new_cookie, blocked, _ = get_or_create_submission(request, qr_entry)
    response = redirect(
        'surveys:thank_you' if blocked else 'surveys:step',
        area_slug=area_slug,
        token=token,
        step=1,
    ) if not blocked else redirect(f"{reverse('surveys:thank_you', kwargs={'area_slug': area_slug, 'token': token})}?repeat=1")

    if is_new_cookie:
        set_session_cookie(response, session_uuid)
    return response


def _build_step_context(qr_entry, submission, questions, step, form):
    total_steps = len(questions)
    current = questions[step - 1]
    return {
        'qr_entry': qr_entry,
        'survey': qr_entry.survey,
        'area': qr_entry.area,
        'submission': submission,
        'area_question': current,
        'question': current.question,
        'form': form,
        'step': step,
        'total_steps': total_steps,
        'progress_percent': int((step / total_steps) * 100),
        'previous_step': step - 1 if step > 1 else None,
        'next_step': step + 1 if step < total_steps else None,
        'rating_labels': [
            {'value': value, 'label': label}
            for value, label in ((1, 'Muy mala'), (2, 'Mala'), (3, 'Regular'), (4, 'Buena'), (5, 'Excelente'))
        ],
    }


def _render_step(request, context, *, full_page=False, response=None):
    template_name = 'surveys/step_page.html' if full_page else 'surveys/partials/question_step.html'
    rendered = render(request, template_name, context)
    if response is None:
        return rendered
    response.content = rendered.content
    return response


@never_cache
def step(request, area_slug, token, step):
    qr_entry = get_qr_entry_point(area_slug, token)
    submission, session_uuid, is_new_cookie = get_submission_for_request(request, qr_entry)
    if not submission:
        return redirect('surveys:landing', area_slug=area_slug, token=token)

    questions = get_area_questions(qr_entry)
    if not questions:
        raise Http404('No hay preguntas configuradas para esta area.')
    if step < 1 or step > len(questions):
        raise Http404('Paso no valido.')

    area_question = questions[step - 1]
    existing_answer = get_existing_answer(submission, area_question.question)

    if request.method == 'POST':
        form = QuestionResponseForm(area_question, request.POST, existing_answer=existing_answer)
        if form.is_valid():
            save_answer(submission, area_question, form.cleaned_data)
            if step >= len(questions):
                complete_submission(submission)
                if is_htmx_request(request):
                    response = HttpResponse(status=204)
                    response['HX-Redirect'] = reverse('surveys:thank_you', kwargs={'area_slug': area_slug, 'token': token})
                else:
                    response = redirect('surveys:thank_you', area_slug=area_slug, token=token)
            else:
                next_step = step + 1
                if is_htmx_request(request):
                    next_area_question = questions[next_step - 1]
                    next_existing = get_existing_answer(submission, next_area_question.question)
                    next_form = QuestionResponseForm(next_area_question, existing_answer=next_existing)
                    context = _build_step_context(qr_entry, submission, questions, next_step, next_form)
                    response = _render_step(request, context, full_page=False)
                else:
                    response = redirect('surveys:step', area_slug=area_slug, token=token, step=next_step)
        else:
            context = _build_step_context(qr_entry, submission, questions, step, form)
            response = _render_step(request, context, full_page=not is_htmx_request(request))
    else:
        form = QuestionResponseForm(area_question, existing_answer=existing_answer)
        context = _build_step_context(qr_entry, submission, questions, step, form)
        response = _render_step(request, context, full_page=True)

    if is_new_cookie:
        set_session_cookie(response, session_uuid)
    return response


@never_cache
def thank_you(request, area_slug, token):
    qr_entry = get_qr_entry_point(area_slug, token)
    submission, _, _ = get_submission_for_request(request, qr_entry)
    context = {
        'qr_entry': qr_entry,
        'survey': qr_entry.survey,
        'area': qr_entry.area,
        'submission': submission,
        'repeat_submission': request.GET.get('repeat') == '1',
    }
    return render(request, 'surveys/thank_you.html', context)