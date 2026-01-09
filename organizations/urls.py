from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('funerals/', views.funerals, name='funerals'),
    path('health/', views.health, name='health'),
    path('funeral-survey/', views.funeral_survey, name='funeral_survey'),
    path('health-survey/', views.health_survey, name='health_survey'),
]