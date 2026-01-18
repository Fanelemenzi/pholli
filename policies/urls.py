from django.urls import path
from . import views

app_name = 'policies'

urlpatterns = [
    # Policy listing views
    path('', views.PolicyListView.as_view(), name='policy_list'),
    path('health/', views.HealthPolicyListView.as_view(), name='health_policy_list'),
    path('funeral/', views.FuneralPolicyListView.as_view(), name='funeral_policy_list'),
    
    # Policy detail view
    path('<int:pk>/', views.PolicyDetailView.as_view(), name='policy_detail'),
    
    # Feature-based filtering
    path('health/filter/', views.HealthPolicyFilterView.as_view(), name='health_policy_filter'),
    path('funeral/filter/', views.FuneralPolicyFilterView.as_view(), name='funeral_policy_filter'),
]