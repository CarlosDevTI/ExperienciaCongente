from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from surveys.models import QrEntryPoint, Survey


class Command(BaseCommand):
    help = 'Genera archivos PNG QR para los entry points activos de una encuesta.'

    def add_arguments(self, parser):
        parser.add_argument('--survey', default='encuesta-satisfaccion-2026')
        parser.add_argument('--base-url', default='', help='Host base para las URLs de los QR.')
        parser.add_argument('--output-dir', default='media/qrcodes')

    def handle(self, *args, **options):
        try:
            import qrcode
        except ImportError as exc:
            raise CommandError('Falta la dependencia qrcode. Ejecuta: pip install -r requirements.txt') from exc

        try:
            survey = Survey.objects.get(slug=options['survey'])
        except Survey.DoesNotExist as exc:
            raise CommandError('La encuesta indicada no existe.') from exc

        base_url = (options['base_url'] or settings.APP_BASE_URL).rstrip('/')
        output_dir = Path(options['output_dir'])
        output_dir.mkdir(parents=True, exist_ok=True)

        entries = QrEntryPoint.objects.filter(survey=survey, is_active=True).select_related('area').order_by('area__name')
        if not entries.exists():
            self.stdout.write('No hay entry points activos para esta encuesta.')
            return

        for entry in entries:
            public_url = f'{base_url}{entry.build_public_path()}'
            img = qrcode.make(public_url)
            filename = f'{entry.area.slug}-{entry.public_token}.png'
            filepath = output_dir / filename
            img.save(filepath)
            self.stdout.write(f'{entry.area.name}: {filepath} -> {public_url}')