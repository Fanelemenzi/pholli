"""
URL configuration for simple_surveys app.

Provides URL patterns for:
- Main pages using public templates
- Direct survey entry points
- Survey forms by category
- AJAX endpoints for saving responses
- Survey processing and results
- Error handling for session issues
"""

from django.urls import path
from . import views

app_name = 'simple_surveys'

urlpatterns = [
    # Main pages using public templates
    path('', views.home, name='home'),
    path('health/', views.health_page, name='health'),
    path('funerals/', views.funerals_page, name='funerals'),
    
    # Direct survey entry points (matches template URLs)
    path('direct/<str:category_slug>/', views.direct_survey, name='direct_survey'),
    
    # Survey functionality
    path('survey/<str:category>/', views.SurveyView.as_view(), name='survey'),
    path('survey/<str:category>/process/', views.ProcessSurveyView.as_view(), name='process'),
    path('survey/<str:category>/results/', views.SurveyResultsView.as_view(), name='results'),
    
    # AJAX endpoints
    path('ajax/save-response/', views.save_response_ajax, name='save_response'),
    path('ajax/survey-status/<str:category>/', views.survey_status_ajax, name='survey_status'),
    
    # Error handling
    path('session-expired/', views.session_expired_view, name='session_expired'),
    path('session-error/', views.session_error_view, name='session_error'),
]