from django.urls import path

from . import views

app_name = 'surveys'

urlpatterns = [
    path('encuesta/<slug:area_slug>/<str:token>/', views.landing, name='landing'),
    path('encuesta/<slug:area_slug>/<str:token>/iniciar/', views.start, name='start'),
    path('encuesta/<slug:area_slug>/<str:token>/paso/<int:step>/', views.step, name='step'),
    path('encuesta/<slug:area_slug>/<str:token>/gracias/', views.thank_you, name='thank_you'),
]

