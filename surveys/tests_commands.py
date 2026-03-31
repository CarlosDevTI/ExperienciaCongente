import shutil
import sys
import tempfile
from io import StringIO
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from django.core.management import CommandError, call_command
from django.test import TestCase

from surveys.models import Area, QrEntryPoint, Survey


class FakeQrImage:
    def save(self, filepath):
        return None


class GenerateQrPngsCommandTests(TestCase):
    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp(dir=Path.cwd()))

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_fails_with_clear_message_when_no_active_surveys(self):
        with self.assertRaisesMessage(CommandError, 'No existen encuestas activas en la base de datos'):
            call_command('generate_qr_pngs', output_dir=str(self.temp_dir))

    def test_fails_with_available_surveys_when_multiple_active(self):
        Survey.objects.create(name='Encuesta A', slug='encuesta-a', is_active=True)
        Survey.objects.create(name='Encuesta B', slug='encuesta-b', is_active=True)

        with self.assertRaisesMessage(CommandError, 'Encuestas disponibles: encuesta-a, encuesta-b'):
            call_command('generate_qr_pngs', output_dir=str(self.temp_dir))

    def test_generates_pngs_for_specific_survey(self):
        survey = Survey.objects.create(name='Encuesta A', slug='encuesta-a', is_active=True)
        area = Area.objects.create(name='Caja', slug='caja', is_active=True)
        QrEntryPoint.objects.create(survey=survey, area=area, name='Caja', is_active=True)

        stdout = StringIO()
        fake_qrcode = SimpleNamespace(make=lambda *_args, **_kwargs: FakeQrImage())
        with patch.dict(sys.modules, {'qrcode': fake_qrcode}):
            call_command('generate_qr_pngs', survey='encuesta-a', output_dir=str(self.temp_dir), stdout=stdout)

        output = stdout.getvalue()
        self.assertIn('Encuesta: Encuesta A (encuesta-a)', output)
        self.assertIn('Se generaron 1 archivo(s) QR', output)
        self.assertIn('encuesta-a-caja-', output)