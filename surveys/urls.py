"""
Simplified URL configuration for surveys app.
"""

from django.urls import path
from django.shortcuts import redirect
from . import views

app_name = 'surveys'

urlpatterns = [
    # Default redirect to home page
    path('', lambda request: redirect('home'), name='surveys_home'),
    
    # Main survey flow
    path('<str:category_slug>/direct/', views.direct_survey_view, name='direct_survey'),
    path('<str:category_slug>/', views.survey_form_view, name='survey_form'),
    path('<str:category_slug>/complete/', views.survey_completion_view, name='survey_completion'),
    
    # Results and Progress
    path('results/', views.survey_results_view, name='survey_results'),
    path('progress/<str:session_key>/', views.survey_progress_view, name='survey_progress_view'),
]