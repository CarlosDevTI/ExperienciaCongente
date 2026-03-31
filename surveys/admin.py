from django.contrib import admin

from core.admin import AuditAdminMixin

from .models import (
    Answer,
    Area,
    AreaQuestion,
    ChoiceOption,
    QrEntryPoint,
    Question,
    SubmissionEvent,
    Survey,
    SurveySubmission,
)


class ChoiceOptionInline(admin.TabularInline):
    model = ChoiceOption
    extra = 0


@admin.register(Survey)
class SurveyAdmin(AuditAdminMixin):
    list_display = ('name', 'slug', 'is_active', 'updated_at')
    search_fields = ('name', 'slug')
    list_filter = ('is_active',)


@admin.register(Area)
class AreaAdmin(AuditAdminMixin):
    list_display = ('name', 'slug', 'is_active', 'updated_at')
    search_fields = ('name', 'slug')
    list_filter = ('is_active',)


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ('code', 'question_type', 'order', 'is_required_default', 'is_active')
    list_filter = ('question_type', 'is_active')
    search_fields = ('code', 'text')
    ordering = ('order',)
    inlines = [ChoiceOptionInline]


@admin.register(AreaQuestion)
class AreaQuestionAdmin(admin.ModelAdmin):
    list_display = ('survey', 'area', 'question', 'order', 'is_required', 'is_visible')
    list_filter = ('survey', 'area', 'is_required', 'is_visible')
    search_fields = ('survey__name', 'area__name', 'question__code', 'question__text')
    ordering = ('survey', 'area', 'order')


@admin.register(QrEntryPoint)
class QrEntryPointAdmin(AuditAdminMixin):
    list_display = ('name', 'survey', 'area', 'public_token', 'allow_multiple_submissions', 'is_active')
    list_filter = ('survey', 'area', 'allow_multiple_submissions', 'is_active')
    search_fields = ('name', 'public_token', 'area__name')
    readonly_fields = ('public_token',)


class AnswerInline(admin.StackedInline):
    model = Answer
    extra = 0
    readonly_fields = ('question', 'rating_value', 'boolean_value', 'selected_option', 'text_value', 'created_at', 'updated_at')
    can_delete = False


@admin.register(SurveySubmission)
class SurveySubmissionAdmin(admin.ModelAdmin):
    list_display = ('public_id', 'survey', 'area', 'status', 'preferred_channel', 'created_at', 'completed_at')
    list_filter = ('survey', 'area', 'status', 'preferred_channel')
    search_fields = ('public_id', 'preferred_channel', 'user_agent', 'qr_entry_point__public_token')
    readonly_fields = ('public_id', 'session_uuid', 'survey', 'area', 'qr_entry_point', 'status', 'ip_address', 'user_agent', 'preferred_channel', 'created_at', 'updated_at', 'completed_at')
    inlines = [AnswerInline]

    def has_add_permission(self, request):
        return False


@admin.register(Answer)
class AnswerAdmin(admin.ModelAdmin):
    list_display = ('submission', 'question', 'display_value', 'updated_at')
    search_fields = ('submission__public_id', 'question__code', 'text_value')
    readonly_fields = ('submission', 'question', 'rating_value', 'boolean_value', 'selected_option', 'text_value', 'created_at', 'updated_at')


@admin.register(SubmissionEvent)
class SubmissionEventAdmin(admin.ModelAdmin):
    list_display = ('event_type', 'submission', 'qr_entry_point', 'created_at')
    list_filter = ('event_type', 'created_at')
    readonly_fields = ('event_type', 'submission', 'qr_entry_point', 'metadata', 'created_at', 'updated_at')
    search_fields = ('submission__public_id', 'qr_entry_point__public_token')

