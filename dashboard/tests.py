from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from surveys.models import Answer, Area, ChoiceOption, QrEntryPoint, Question, Survey, SurveySubmission


User = get_user_model()


class DashboardViewTests(TestCase):
    def setUp(self):
        self.superuser = User.objects.create_user(
            username='admin',
            password='secret',
            is_staff=True,
            is_superuser=True,
        )
        self.staff_user = User.objects.create_user(
            username='analyst',
            password='secret',
            is_staff=True,
            is_superuser=False,
        )
        self.client = Client()
        self.client.login(username='admin', password='secret')

        survey = Survey.objects.create(name='Survey', slug='survey')
        area = Area.objects.create(name='Caja', slug='caja')
        q1 = Question.objects.create(code='q1', text='Califica', question_type='rating', order=1)
        q8 = Question.objects.create(code='q8', text='Canal', question_type='single_choice', order=2)
        q10 = Question.objects.create(code='q10', text='Comentario', question_type='text', order=3)
        email = ChoiceOption.objects.create(question=q8, label='Email', value='email', order=1)
        qr_entry = QrEntryPoint.objects.create(survey=survey, area=area, name='Caja')

        submission = SurveySubmission.objects.create(
            survey=survey,
            area=area,
            qr_entry_point=qr_entry,
            status=SurveySubmission.Status.COMPLETED,
            preferred_channel='Email',
            completed_at=timezone.now(),
        )
        Answer.objects.create(submission=submission, question=q1, rating_value=5)
        Answer.objects.create(submission=submission, question=q8, selected_option=email)
        Answer.objects.create(submission=submission, question=q10, text_value='Excelente servicio')
        self.submission = submission

    def test_dashboard_requires_staff(self):
        anonymous = Client()
        response = anonymous.get(reverse('dashboard:index'))
        self.assertEqual(response.status_code, 302)

    def test_dashboard_index_loads(self):
        response = self.client.get(reverse('dashboard:index'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Panel de satisfaccion')
        self.assertContains(response, 'Resumen')
        self.assertContains(response, 'Respuestas')
        self.assertContains(response, 'Administracion')
        self.assertContains(response, 'Pregunta 1')
        self.assertContains(response, 'Desarrollado por Equipo Ingenieria TI')
        self.assertContains(response, 'Cerrar sesion')

    def test_dashboard_hides_admin_link_for_non_superuser(self):
        client = Client()
        client.login(username='analyst', password='secret')
        response = client.get(reverse('dashboard:index'))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'Administracion')

    def test_admin_is_not_accessible_for_non_superuser(self):
        client = Client()
        client.login(username='analyst', password='secret')
        response = client.get('/admin/')
        self.assertNotEqual(response.status_code, 200)

    def test_response_detail_hides_token_and_uses_business_question_labels(self):
        response = self.client.get(reverse('dashboard:response_detail', args=[self.submission.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Tipo de encuesta')
        self.assertContains(response, 'Pregunta 1')
        self.assertNotContains(response, 'Token QR')
        self.assertNotContains(response, self.submission.qr_entry_point.public_token)

    def test_csv_export_contains_business_headers(self):
        response = self.client.get(reverse('dashboard:export_csv'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('text/csv', response['Content-Type'])
        content = response.content.decode('utf-8')
        self.assertIn('Tipo de encuesta', content)
        self.assertIn('Pregunta 1', content)
        self.assertIn('Punto / Origen', content)
        self.assertNotIn('qr_token', content)
        self.assertNotIn('submission_id', content)
        self.assertIn('Email', content)

    def test_logout_view_closes_session(self):
        response = self.client.post(reverse('dashboard:logout'))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('admin:login'), response.url)
        follow_up = self.client.get(reverse('dashboard:index'))
        self.assertEqual(follow_up.status_code, 302)