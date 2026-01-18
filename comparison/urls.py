from django.urls import path
from . import views

app_name = 'comparison'

urlpatterns = [
    # Enhanced results display
    path('results/<str:session_key>/', views.enhanced_results_view, name='enhanced_results'),
    
    # Policy detail modal
    path('<str:session_key>/policy/<int:policy_id>/detail/', views.policy_detail_modal_view, name='policy_detail'),
    
    # Comparison matrix
    path('<str:session_key>/matrix/', views.comparison_matrix_view, name='comparison_matrix'),
    
    # AJAX endpoints
    path('<str:session_key>/update-criteria/', views.update_criteria_weights_ajax, name='update_criteria_weights'),
    
    # Feature-based comparison URLs
    path('feature-results/<int:survey_id>/', views.feature_comparison_results_view, name='feature_results'),
    path('feature-results/<int:survey_id>/detail/<int:result_id>/', views.feature_comparison_detail_view, name='feature_result_detail'),
    path('feature-results/<int:survey_id>/matrix/', views.feature_comparison_matrix_view, name='feature_matrix'),
    path('feature-results/<int:survey_id>/regenerate/', views.regenerate_comparison_results_ajax, name='regenerate_results'),
]