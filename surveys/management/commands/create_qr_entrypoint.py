from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from surveys.models import Area, QrEntryPoint, Survey


class Command(BaseCommand):
    help = 'Crea o actualiza el unico punto de acceso QR activo para una encuesta y area especificas.'

    def add_arguments(self, parser):
        parser.add_argument('survey_slug')
        parser.add_argument('area_slug')
        parser.add_argument('name', nargs='?', default='')
        parser.add_argument('--single-session', action='store_true', help='Permite una sola respuesta por sesion.')
        parser.add_argument('--rotate-token', action='store_true', help='Genera un token nuevo para ese QR.')
        parser.add_argument('--base-url', default='', help='Host base para imprimir la URL completa.')

    def handle(self, *args, **options):
        try:
            survey = Survey.objects.get(slug=options['survey_slug'])
            area = Area.objects.get(slug=options['area_slug'])
        except Survey.DoesNotExist as exc:
            raise CommandError('La encuesta indicada no existe.') from exc
        except Area.DoesNotExist as exc:
            raise CommandError('El area indicada no existe.') from exc

        entry_name = options['name'] or area.name
        existing_entries = list(QrEntryPoint.objects.filter(survey=survey, area=area).order_by('created_at', 'id'))

        if existing_entries:
            qr_entry = existing_entries[0]
            qr_entry.name = entry_name
            qr_entry.allow_multiple_submissions = not options['single_session']
            qr_entry.is_active = True
            if options['rotate_token']:
                qr_entry.rotate_token()
            qr_entry.save(update_fields=['name', 'allow_multiple_submissions', 'is_active', 'public_token', 'updated_at'])
            action = 'actualizado'
        else:
            qr_entry = QrEntryPoint.objects.create(
                survey=survey,
                area=area,
                name=entry_name,
                allow_multiple_submissions=not options['single_session'],
                is_active=True,
            )
            action = 'creado'

        QrEntryPoint.objects.filter(survey=survey, area=area).exclude(pk=qr_entry.pk).update(is_active=False)

        public_path = qr_entry.build_public_path()
        base_url = (options['base_url'] or settings.APP_BASE_URL).rstrip('/')
        full_url = f'{base_url}{public_path}' if base_url else public_path

        self.stdout.write(self.style.SUCCESS(f'QR {action} correctamente.'))
        self.stdout.write('Token: ' + qr_entry.public_token)
        self.stdout.write('URL: ' + full_url)