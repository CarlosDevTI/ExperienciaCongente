from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView


def superuser_admin_permission(request):
    return request.user.is_active and request.user.is_superuser


admin.site.has_permission = superuser_admin_permission

urlpatterns = [
    path('', RedirectView.as_view(pattern_name='dashboard:index', permanent=False)),
    path('admin/', admin.site.urls),
    path('', include('surveys.urls')),
    path('dashboard/', include('dashboard.urls')),
]
