from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from surveys.models import QrEntryPoint, Survey


class Command(BaseCommand):
    help = 'Lista los QR entry points activos con su token y URL publica.'

    def add_arguments(self, parser):
        parser.add_argument('--survey', default='encuesta-satisfaccion-2026')
        parser.add_argument('--base-url', default='', help='Host base para imprimir URL completa.')

    def handle(self, *args, **options):
        try:
            survey = Survey.objects.get(slug=options['survey'])
        except Survey.DoesNotExist as exc:
            raise CommandError('La encuesta indicada no existe.') from exc

        entries = QrEntryPoint.objects.filter(survey=survey, is_active=True).select_related('area').order_by('area__name')
        if not entries.exists():
            self.stdout.write('No hay entry points activos para esta encuesta.')
            return

        base_url = (options['base_url'] or settings.APP_BASE_URL).rstrip('/')
        for entry in entries:
            self.stdout.write(f"{entry.area.name}: {entry.public_token}")
            self.stdout.write(f"  {base_url}{entry.build_public_path()}")