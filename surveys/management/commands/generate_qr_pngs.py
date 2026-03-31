from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from surveys.models import QrEntryPoint, Survey


class Command(BaseCommand):
    help = 'Genera archivos PNG QR para los entry points activos de una o varias encuestas.'

    def add_arguments(self, parser):
        parser.add_argument('--survey', default='', help='Slug de una encuesta especifica.')
        parser.add_argument('--all-surveys', action='store_true', help='Genera QR para todas las encuestas activas.')
        parser.add_argument('--base-url', default='', help='Host base para las URLs de los QR.')
        parser.add_argument('--output-dir', default='media/qrcodes')

    def handle(self, *args, **options):
        survey_slug = (options.get('survey') or '').strip()
        include_all = options.get('all_surveys', False)
        surveys = self.resolve_surveys(survey_slug=survey_slug, include_all=include_all)

        try:
            import qrcode
        except ImportError as exc:
            raise CommandError('Falta la dependencia qrcode. Ejecuta: pip install -r requirements.txt') from exc

        base_url = (options['base_url'] or settings.APP_BASE_URL).rstrip('/')
        output_dir = Path(options['output_dir'])
        output_dir.mkdir(parents=True, exist_ok=True)

        generated = 0
        for survey in surveys:
            entries = QrEntryPoint.objects.filter(survey=survey, is_active=True).select_related('area').order_by('area__name')
            if not entries.exists():
                self.stdout.write(self.style.WARNING(
                    f'La encuesta "{survey.slug}" existe, pero no tiene entry points activos. '
                    'Crea los QR entry points o ejecuta el seed inicial.'
                ))
                continue

            self.stdout.write(self.style.SUCCESS(f'Encuesta: {survey.name} ({survey.slug})'))
            for entry in entries:
                public_url = f'{base_url}{entry.build_public_path()}'
                img = qrcode.make(public_url)
                filename = f'{survey.slug}-{entry.area.slug}-{entry.public_token}.png'
                filepath = output_dir / filename
                img.save(filepath)
                generated += 1
                self.stdout.write(f'  {entry.area.name}: {filepath} -> {public_url}')

        if not generated:
            raise CommandError(
                'No se genero ningun QR. Verifica que existan encuestas activas, areas y entry points activos. '
                'Si es una instalacion nueva, ejecuta: python manage.py seed_congente_survey'
            )

        self.stdout.write(self.style.SUCCESS(f'Se generaron {generated} archivo(s) QR en {output_dir}'))

    def resolve_surveys(self, *, survey_slug, include_all):
        active_surveys = list(Survey.objects.filter(is_active=True).order_by('name'))
        if not active_surveys:
            raise CommandError(
                'No existen encuestas activas en la base de datos. '
                'Primero crea una encuesta o ejecuta: python manage.py seed_congente_survey'
            )

        if include_all:
            return active_surveys

        if survey_slug:
            survey = Survey.objects.filter(slug=survey_slug).first()
            if survey:
                return [survey]
            available = ', '.join(s.slug for s in active_surveys)
            raise CommandError(
                f'La encuesta indicada no existe: "{survey_slug}". '
                f'Encuestas activas disponibles: {available}. '
                'Usa --survey=<slug> o --all-surveys.'
            )

        if len(active_surveys) == 1:
            return active_surveys

        available = ', '.join(s.slug for s in active_surveys)
        raise CommandError(
            'Hay varias encuestas activas y no se especifico cual usar. '
            f'Encuestas disponibles: {available}. '
            'Usa --survey=<slug> o --all-surveys.'
        )