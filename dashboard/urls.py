from django.urls import path

from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.index, name='index'),
    path('respuestas/', views.responses_list, name='responses_list'),
    path('respuestas/<int:submission_id>/', views.response_detail, name='response_detail'),
    path('export/responses.csv', views.export_csv, name='export_csv'),
    path('export/responses.xlsx', views.export_excel, name='export_excel'),
    path('logout/', views.logout_view, name='logout'),
]