from django.contrib import admin


class AuditAdminMixin(admin.ModelAdmin):
    def save_model(self, request, obj, form, change):
        if hasattr(obj, 'updated_by'):
            obj.updated_by = request.user
        if hasattr(obj, 'created_by') and not obj.created_by_id:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

