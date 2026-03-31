from django.core.management.base import BaseCommand

from surveys.models import Area, AreaQuestion, ChoiceOption, QrEntryPoint, Question, Survey


QUESTION_BANK = [
    ('q1', 'Califica tu experiencia como asociado Congente', 'rating'),
    ('q2', 'Califica el servicio recibido en caja', 'rating'),
    ('q3', 'Califica el servicio recibido en asesoria', 'rating'),
    ('q4', 'Califica tu experiencia en respuesta a peticiones, quejas, reclamos y sugerencias (PQRS)', 'rating'),
    ('q5', 'Califica nuestro portafolio de productos, servicios y convenios', 'rating'),
    ('q6', 'Califica tu experiencia con los beneficios de nuestra ticketera Congente', 'rating'),
    ('q7', 'Nos recomendarias con un familiar, amigo o conocido?', 'yes_no'),
    ('q8', 'Cual es su canal de preferencia?', 'single_choice'),
    ('q9', 'Que tipo de servicio, beneficio o convenio le gustaria encontrar?', 'multiple_choice'),
    ('q10', 'Como podemos mejorar?', 'text'),
]

AREAS = [
    {'name': 'Caja', 'slug': 'caja', 'questions': ['q1', 'q2', 'q7', 'q8', 'q9', 'q10']},
    {'name': 'Asesoria', 'slug': 'asesoria', 'questions': ['q1', 'q3', 'q7', 'q8', 'q9', 'q10']},
    {'name': 'Servicio al asociado', 'slug': 'servicio-asociado', 'questions': ['q4', 'q7', 'q8', 'q9', 'q10']},
    {'name': 'Servicio convenios', 'slug': 'servicio-convenios', 'questions': ['q5', 'q6', 'q7', 'q8', 'q9', 'q10']},
]

OPTIONS = {
    'q8': [
        ('whatsapp', 'WhatsApp', False),
        ('chatbot', 'ChatBot', False),
        ('sms', 'Mensaje de texto', False),
        ('email', 'Email', False),
        ('calls', 'Llamadas', False),
        ('social', 'Facebook / Instagram / YouTube', False),
        ('web', 'Pagina web', False),
        ('onsite', 'Presencial', False),
    ],
    'q9': [
        ('more-credit', 'Mas opciones de credito', False),
        ('training', 'Capacitaciones o talleres para asociados', False),
        ('family-benefits', 'Beneficios para familias o hijos', False),
        ('discounts', 'Descuentos en comercios o convenios nuevos', False),
        ('advisory', 'Asesoria financiera o educativa', False),
        ('other', 'Otro', True),
    ],
}


class Command(BaseCommand):
    help = 'Carga la configuracion inicial de la Encuesta de Satisfaccion Congente 2026 y deja un unico QR activo por area.'

    def handle(self, *args, **options):
        survey, _ = Survey.objects.get_or_create(
            slug='encuesta-satisfaccion-2026',
            defaults={
                'name': 'Encuesta de Satisfaccion 2026',
                'welcome_title': 'Calificador de atencion Congente',
                'welcome_text': 'Tu experiencia nos ayuda a mejorar cada canal de atencion.',
                'closing_title': 'Gracias por responder',
                'closing_text': 'Tu opinion se registra para seguimiento diario del area de servicio al asociado.',
                'is_active': True,
            },
        )

        questions = {}
        for order, (code, text, question_type) in enumerate(QUESTION_BANK, start=1):
            question, _ = Question.objects.update_or_create(
                code=code,
                defaults={
                    'text': text,
                    'question_type': question_type,
                    'order': order,
                    'is_required_default': True,
                    'is_active': True,
                },
            )
            questions[code] = question

        for code, choices in OPTIONS.items():
            question = questions[code]
            for order, (value, label, is_other_option) in enumerate(choices, start=1):
                ChoiceOption.objects.update_or_create(
                    question=question,
                    value=value,
                    defaults={
                        'label': label,
                        'order': order,
                        'is_other_option': is_other_option,
                    },
                )

        for area_data in AREAS:
            area, _ = Area.objects.update_or_create(
                slug=area_data['slug'],
                defaults={
                    'name': area_data['name'],
                    'description': f"Encuesta para {area_data['name'].lower()}",
                    'is_active': True,
                },
            )

            for order, code in enumerate(area_data['questions'], start=1):
                AreaQuestion.objects.update_or_create(
                    survey=survey,
                    area=area,
                    question=questions[code],
                    defaults={
                        'order': order,
                        'is_required': True,
                        'is_visible': True,
                    },
                )

            area_entries = list(QrEntryPoint.objects.filter(survey=survey, area=area).order_by('created_at', 'id'))
            if area_entries:
                canonical = area_entries[0]
                canonical.name = area.name
                canonical.allow_multiple_submissions = True
                canonical.is_active = True
                canonical.save(update_fields=['name', 'allow_multiple_submissions', 'is_active', 'updated_at'])
            else:
                canonical = QrEntryPoint.objects.create(
                    survey=survey,
                    area=area,
                    name=area.name,
                    allow_multiple_submissions=True,
                    is_active=True,
                )

            QrEntryPoint.objects.filter(survey=survey, area=area).exclude(pk=canonical.pk).update(is_active=False)

        self.stdout.write(self.style.SUCCESS('Seed Congente 2026 cargado correctamente.'))
        for qr_entry in QrEntryPoint.objects.filter(survey=survey, is_active=True).select_related('area').order_by('area__name'):
            self.stdout.write(f"/encuesta/{qr_entry.area.slug}/{qr_entry.public_token}/")
