import re
import uuid

from django.db import models
from django.utils.text import slugify

from core.models import AuditModel, TimeStampedModel


class Survey(AuditModel):
    name = models.CharField(max_length=150)
    slug = models.SlugField(unique=True)
    welcome_title = models.CharField(max_length=150, default='Tu opinion nos ayuda a mejorar')
    welcome_text = models.TextField(default='Responde esta breve encuesta para calificar tu experiencia con Congente.')
    closing_title = models.CharField(max_length=150, default='Gracias por compartir tu experiencia')
    closing_text = models.TextField(default='Tus respuestas seran revisadas por el equipo de servicio al asociado.')
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class Area(AuditModel):
    name = models.CharField(max_length=120)
    slug = models.SlugField(unique=True)
    description = models.CharField(max_length=255, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Question(TimeStampedModel):
    class QuestionType(models.TextChoices):
        RATING = 'rating', 'Rating 1-5'
        YES_NO = 'yes_no', 'Si / No'
        SINGLE_CHOICE = 'single_choice', 'Seleccion unica'
        MULTIPLE_CHOICE = 'multiple_choice', 'Seleccion multiple'
        TEXT = 'text', 'Texto abierto'

    code = models.CharField(max_length=20, unique=True)
    text = models.TextField()
    question_type = models.CharField(max_length=20, choices=QuestionType.choices)
    help_text = models.CharField(max_length=255, blank=True)
    is_required_default = models.BooleanField(default=True)
    order = models.PositiveSmallIntegerField(default=1)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['order', 'id']

    def __str__(self):
        return f'{self.code}: {self.text[:70]}'

    @property
    def business_label(self):
        match = re.search(r'(\d+)$', self.code or '')
        if match:
            return f'Pregunta {match.group(1)}'
        return self.text[:40]


class ChoiceOption(TimeStampedModel):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='options')
    label = models.CharField(max_length=150)
    value = models.CharField(max_length=80)
    order = models.PositiveSmallIntegerField(default=1)
    is_other_option = models.BooleanField(default=False)

    class Meta:
        ordering = ['order', 'id']
        unique_together = [('question', 'value')]

    def __str__(self):
        return f'{self.question.code} - {self.label}'


class AreaQuestion(TimeStampedModel):
    survey = models.ForeignKey(Survey, on_delete=models.CASCADE, related_name='area_questions')
    area = models.ForeignKey(Area, on_delete=models.CASCADE, related_name='area_questions')
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='area_links')
    order = models.PositiveSmallIntegerField(default=1)
    is_required = models.BooleanField(default=True)
    is_visible = models.BooleanField(default=True)

    class Meta:
        ordering = ['order', 'id']
        unique_together = [('survey', 'area', 'question')]
        indexes = [
            models.Index(fields=['survey', 'area', 'order']),
            models.Index(fields=['question']),
        ]

    def __str__(self):
        return f'{self.survey.slug} / {self.area.slug} / {self.question.code}'


def qr_token():
    return str(uuid.uuid4())


class QrEntryPoint(AuditModel):
    survey = models.ForeignKey(Survey, on_delete=models.CASCADE, related_name='qr_entry_points')
    area = models.ForeignKey(Area, on_delete=models.CASCADE, related_name='qr_entry_points')
    name = models.CharField(max_length=150)
    public_token = models.CharField(max_length=80, unique=True, default=qr_token)
    allow_multiple_submissions = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['area__name', 'name']
        indexes = [
            models.Index(fields=['public_token']),
            models.Index(fields=['area', 'is_active']),
        ]

    def __str__(self):
        return f'{self.area.name} - {self.name}'

    @property
    def display_name(self):
        if self.name.strip().lower() == self.area.name.strip().lower():
            return 'Principal'
        return self.name

    def build_public_path(self):
        return f'/encuesta/{self.area.slug}/{self.public_token}/'

    def rotate_token(self):
        self.public_token = qr_token()
        return self.public_token


class SurveySubmission(TimeStampedModel):
    class Status(models.TextChoices):
        STARTED = 'started', 'Started'
        COMPLETED = 'completed', 'Completed'
        ABANDONED = 'abandoned', 'Abandoned'

    public_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    session_uuid = models.UUIDField(default=uuid.uuid4, db_index=True)
    survey = models.ForeignKey(Survey, on_delete=models.CASCADE, related_name='submissions')
    area = models.ForeignKey(Area, on_delete=models.CASCADE, related_name='submissions')
    qr_entry_point = models.ForeignKey(QrEntryPoint, on_delete=models.PROTECT, related_name='submissions')
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.STARTED)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    user_agent = models.CharField(max_length=512, blank=True)
    preferred_channel = models.CharField(max_length=150, blank=True)
    completed_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['area', 'created_at']),
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['session_uuid']),
            models.Index(fields=['qr_entry_point', 'created_at']),
        ]

    def __str__(self):
        return f'{self.area.name} - {self.public_id}'


class Answer(TimeStampedModel):
    submission = models.ForeignKey(SurveySubmission, on_delete=models.CASCADE, related_name='answers')
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='answers')
    rating_value = models.PositiveSmallIntegerField(blank=True, null=True)
    boolean_value = models.BooleanField(blank=True, null=True)
    selected_option = models.ForeignKey(
        ChoiceOption,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='single_answers',
    )
    selected_options = models.ManyToManyField(ChoiceOption, blank=True, related_name='multiple_answers')
    text_value = models.TextField(blank=True)

    class Meta:
        ordering = ['question__order', 'id']
        unique_together = [('submission', 'question')]
        indexes = [
            models.Index(fields=['question']),
            models.Index(fields=['submission', 'question']),
        ]

    def __str__(self):
        return f'{self.submission.public_id} - {self.question.code}'

    @property
    def display_value(self):
        if self.rating_value is not None:
            return str(self.rating_value)
        if self.boolean_value is not None:
            return 'Si' if self.boolean_value else 'No'
        if self.selected_option_id:
            return self.selected_option.label
        selected = list(self.selected_options.values_list('label', flat=True))
        if selected:
            if self.text_value:
                selected.append(self.text_value)
            return ', '.join(selected)
        return self.text_value


class SubmissionEvent(TimeStampedModel):
    class EventType(models.TextChoices):
        OPENED = 'opened', 'Opened'
        STEP_SAVED = 'step_saved', 'Step saved'
        SUBMITTED = 'submitted', 'Submitted'
        BLOCKED_DUPLICATE = 'blocked_duplicate', 'Blocked duplicate'

    submission = models.ForeignKey(
        SurveySubmission,
        on_delete=models.CASCADE,
        related_name='events',
        null=True,
        blank=True,
    )
    qr_entry_point = models.ForeignKey(
        QrEntryPoint,
        on_delete=models.CASCADE,
        related_name='events',
        null=True,
        blank=True,
    )
    event_type = models.CharField(max_length=30, choices=EventType.choices)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [models.Index(fields=['event_type', 'created_at'])]

    def __str__(self):
        return f'{self.event_type} @ {self.created_at:%Y-%m-%d %H:%M}'
