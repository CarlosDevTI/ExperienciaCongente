from django.test import Client, TestCase
from django.urls import reverse

from surveys.models import Area, AreaQuestion, ChoiceOption, QrEntryPoint, Question, Survey, SurveySubmission


class SurveyFlowTests(TestCase):
    def setUp(self):
        self.survey = Survey.objects.create(name='Test Survey', slug='test-survey')
        self.area = Area.objects.create(name='Caja', slug='caja')
        self.q1 = Question.objects.create(code='q1', text='Califica tu experiencia', question_type='rating', order=1)
        self.q9 = Question.objects.create(code='q9', text='Que te gustaria encontrar?', question_type='multiple_choice', order=2)
        self.q10 = Question.objects.create(code='q10', text='Como podemos mejorar?', question_type='text', order=3)
        ChoiceOption.objects.create(question=self.q9, label='Mas credito', value='credit', order=1)
        ChoiceOption.objects.create(question=self.q9, label='Otro', value='other', order=2, is_other_option=True)

        AreaQuestion.objects.create(survey=self.survey, area=self.area, question=self.q1, order=1)
        AreaQuestion.objects.create(survey=self.survey, area=self.area, question=self.q9, order=2)
        AreaQuestion.objects.create(survey=self.survey, area=self.area, question=self.q10, order=3)

        self.qr_entry = QrEntryPoint.objects.create(
            survey=self.survey,
            area=self.area,
            name='Caja',
            allow_multiple_submissions=False,
        )
        self.client = Client()

    def test_token_is_generated_automatically(self):
        self.assertTrue(self.qr_entry.public_token)
        self.assertGreaterEqual(len(self.qr_entry.public_token), 20)

    def test_public_flow_completes_submission(self):
        landing_url = reverse('surveys:landing', args=[self.area.slug, self.qr_entry.public_token])
        start_url = reverse('surveys:start', args=[self.area.slug, self.qr_entry.public_token])

        response = self.client.get(landing_url)
        self.assertEqual(response.status_code, 200)

        response = self.client.post(start_url)
        self.assertRedirects(response, reverse('surveys:step', args=[self.area.slug, self.qr_entry.public_token, 1]))

        response = self.client.post(reverse('surveys:step', args=[self.area.slug, self.qr_entry.public_token, 1]), {'response': '5'})
        self.assertRedirects(response, reverse('surveys:step', args=[self.area.slug, self.qr_entry.public_token, 2]))

        response = self.client.post(reverse('surveys:step', args=[self.area.slug, self.qr_entry.public_token, 2]), {'response': ['credit']})
        self.assertRedirects(response, reverse('surveys:step', args=[self.area.slug, self.qr_entry.public_token, 3]))

        response = self.client.post(reverse('surveys:step', args=[self.area.slug, self.qr_entry.public_token, 3]), {'response': 'Atencion mas rapida'})
        self.assertRedirects(response, reverse('surveys:thank_you', args=[self.area.slug, self.qr_entry.public_token]))

        submission = SurveySubmission.objects.get(qr_entry_point=self.qr_entry)
        self.assertEqual(submission.status, SurveySubmission.Status.COMPLETED)
        self.assertEqual(submission.answers.count(), 3)

    def test_mobile_landing_redirects_directly_to_first_step(self):
        response = self.client.get(
            reverse('surveys:landing', args=[self.area.slug, self.qr_entry.public_token]),
            HTTP_USER_AGENT='Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 Mobile/15E148',
        )
        self.assertRedirects(response, reverse('surveys:step', args=[self.area.slug, self.qr_entry.public_token, 1]))

    def test_htmx_step_keeps_target_wrapper(self):
        self.client.post(reverse('surveys:start', args=[self.area.slug, self.qr_entry.public_token]))
        response = self.client.post(
            reverse('surveys:step', args=[self.area.slug, self.qr_entry.public_token, 1]),
            {'response': '5'},
            HTTP_HX_REQUEST='true',
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="survey-step"')
        self.assertContains(response, 'Que te gustaria encontrar?')

    def test_slug_mismatch_returns_404(self):
        response = self.client.get(reverse('surveys:landing', args=['asesoria', self.qr_entry.public_token]))
        self.assertEqual(response.status_code, 404)

    def test_other_option_requires_text(self):
        self.client.post(reverse('surveys:start', args=[self.area.slug, self.qr_entry.public_token]))
        self.client.post(reverse('surveys:step', args=[self.area.slug, self.qr_entry.public_token, 1]), {'response': '4'})

        response = self.client.post(
            reverse('surveys:step', args=[self.area.slug, self.qr_entry.public_token, 2]),
            {'response': ['other']},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Debes indicar')

    def test_duplicate_submission_redirects_to_thank_you(self):
        self.client.post(reverse('surveys:start', args=[self.area.slug, self.qr_entry.public_token]))
        self.client.post(reverse('surveys:step', args=[self.area.slug, self.qr_entry.public_token, 1]), {'response': '4'})
        self.client.post(reverse('surveys:step', args=[self.area.slug, self.qr_entry.public_token, 2]), {'response': ['credit']})
        self.client.post(reverse('surveys:step', args=[self.area.slug, self.qr_entry.public_token, 3]), {'response': 'Todo bien'})

        response = self.client.post(reverse('surveys:start', args=[self.area.slug, self.qr_entry.public_token]))
        self.assertRedirects(
            response,
            f"{reverse('surveys:thank_you', args=[self.area.slug, self.qr_entry.public_token])}?repeat=1",
            fetch_redirect_response=False,
        )