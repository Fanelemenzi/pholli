"""
URL configuration for simple_surveys app.

Provides URL patterns for:
- Main pages using public templates
- Direct survey entry points
- Survey forms by category
- AJAX endpoints for saving responses
- Survey processing and results
- Error handling for session issues
- Admin management interfaces for benefit levels and ranges
- Response migration handling for existing users
"""

from django.urls import path
from . import views
from .admin_views import (
    BenefitLevelManagementView, AnnualLimitRangeManagementView,
    get_benefit_choice_details, validate_choice_configuration,
    SurveyAnalyticsDashboardView, BenefitLevelAnalyticsView,
    RangeSelectionAnalyticsView, CompletionAnalyticsView,
    export_analytics_data, get_analytics_summary
)
from .migration_views import (
    ResponseMigrationView, check_migration_status, migrate_responses_ajax,
    get_migration_notification
)

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
    
    # Feature-based survey functionality
    path('feature-survey/<str:category>/', views.FeatureSurveyView.as_view(), name='feature_survey'),
    path('feature-survey/<str:category>/results/', views.FeatureResultsView.as_view(), name='feature_results'),
    
    # Response migration functionality
    path('migrate/<str:category>/', ResponseMigrationView.as_view(), name='migrate_responses'),
    path('ajax/migration-status/<str:category>/', check_migration_status, name='migration_status'),
    path('ajax/migration-notification/<str:category>/', get_migration_notification, name='migration_notification'),
    path('ajax/migrate/<str:category>/', migrate_responses_ajax, name='migrate_responses_ajax'),
    
    # AJAX endpoints
    path('ajax/save-response/', views.save_response_ajax, name='save_response'),
    path('ajax/survey-status/<str:category>/', views.survey_status_ajax, name='survey_status'),
    path('ajax/policy-benefits/<int:policy_id>/', views.policy_benefits_ajax, name='policy_benefits'),
    
    # Admin management interfaces
    path('admin/benefit-levels/', BenefitLevelManagementView.as_view(), name='admin_benefit_levels'),
    path('admin/annual-limits/', AnnualLimitRangeManagementView.as_view(), name='admin_annual_limits'),
    
    # Analytics dashboard
    path('admin/analytics/', SurveyAnalyticsDashboardView.as_view(), name='admin_analytics_dashboard'),
    path('admin/analytics/benefit-levels/', BenefitLevelAnalyticsView.as_view(), name='admin_benefit_analytics'),
    path('admin/analytics/ranges/', RangeSelectionAnalyticsView.as_view(), name='admin_range_analytics'),
    path('admin/analytics/completion/', CompletionAnalyticsView.as_view(), name='admin_completion_analytics'),
    
    # Admin API endpoints
    path('admin/api/choice-details/<str:choice_type>/<str:choice_value>/', 
         get_benefit_choice_details, name='admin_choice_details'),
    path('admin/api/validate-choices/', validate_choice_configuration, name='admin_validate_choices'),
    path('admin/api/export-analytics/', export_analytics_data, name='admin_export_analytics'),
    path('admin/api/analytics-summary/', get_analytics_summary, name='admin_analytics_summary'),
    
    # Error handling
    path('session-expired/', views.session_expired_view, name='session_expired'),
    path('session-error/', views.session_error_view, name='session_error'),
]