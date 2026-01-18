"""
Admin integration utilities for system consistency checks.
"""

from django.contrib import admin, messages
from django.shortcuts import render, redirect
from django.urls import path, reverse
from django.http import JsonResponse, HttpResponse
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.core.cache import cache
import json

from .integration import SystemIntegrationManager, CrossModuleValidator
from .signals import get_cached_validation_errors, get_system_health_metrics


class SystemIntegrationAdminMixin:
    """
    Mixin for admin classes to add system integration features.
    """
    
    def get_validation_errors_display(self, obj, model_type):
        """
        Get validation errors for display in admin.
        
        Args:
            obj: Model instance
            model_type: 'policy', 'survey', or 'comparison'
        
        Returns:
            HTML string with validation errors or success message
        """
        errors = get_cached_validation_errors(model_type, obj.id)
        
        if not errors:
            return format_html(
                '<span style="color: green;">{}</span>',
                '✓ Valid'
            )
        
        error_list = '<br>'.join([f'• {error}' for error in errors[:3]])
        if len(errors) > 3:
            error_list += f'<br>... and {len(errors) - 3} more'
        
        return format_html(
            '<span style="color: red;" title="{}">✗ {} issues</span>',
            error_list.replace('<br>', '\n'),
            len(errors)
        )
    
    def integration_status(self, obj):
        """
        Display integration status for an object.
        To be implemented by subclasses.
        """
        return "Not implemented"
    
    integration_status.short_description = "Integration Status"


def system_integration_admin_view(request):
    """
    Admin view for system integration status and controls.
    """
    if not request.user.is_staff:
        return redirect('admin:login')
    
    context = {
        'title': 'System Integration Status',
        'has_permission': True,
    }
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'check_system':
            results = SystemIntegrationManager.perform_full_system_check()
            context['check_results'] = results
            
            if results['overall_status'] == 'healthy':
                messages.success(request, 'System integration check passed!')
            elif results['overall_status'] == 'warning':
                messages.warning(request, 'System integration check found some issues.')
            else:
                messages.error(request, 'System integration check found critical issues.')
        
        elif action == 'synchronize_features':
            results = SystemIntegrationManager.synchronize_all_features()
            context['sync_results'] = results
            
            if results['overall_success']:
                messages.success(request, 'Feature synchronization completed successfully!')
            else:
                messages.error(request, 'Feature synchronization completed with errors.')
        
        elif action == 'clear_caches':
            cache.clear()
            messages.success(request, 'All caches cleared successfully!')
    
    # Get system health metrics
    context['health_metrics'] = get_system_health_metrics()
    
    return render(request, 'admin/policies/system_integration.html', context)


def system_integration_api_view(request):
    """
    API endpoint for system integration data.
    """
    if not request.user.is_staff:
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    action = request.GET.get('action', 'status')
    
    if action == 'status':
        results = SystemIntegrationManager.perform_full_system_check()
        return JsonResponse(results)
    
    elif action == 'health':
        metrics = get_system_health_metrics()
        return JsonResponse(metrics)
    
    elif action == 'validate_policy':
        policy_id = request.GET.get('policy_id')
        if not policy_id:
            return JsonResponse({'error': 'policy_id required'}, status=400)
        
        try:
            from .models import BasePolicy
            policy = BasePolicy.objects.get(id=policy_id)
            errors = CrossModuleValidator.validate_policy_features(policy)
            
            return JsonResponse({
                'policy_id': policy_id,
                'policy_name': policy.name,
                'valid': len(errors) == 0,
                'errors': errors
            })
        
        except BasePolicy.DoesNotExist:
            return JsonResponse({'error': 'Policy not found'}, status=404)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    elif action == 'validate_survey':
        survey_id = request.GET.get('survey_id')
        if not survey_id:
            return JsonResponse({'error': 'survey_id required'}, status=400)
        
        try:
            from simple_surveys.models import SimpleSurvey
            survey = SimpleSurvey.objects.get(id=survey_id)
            errors = CrossModuleValidator.validate_survey_completeness(survey)
            
            return JsonResponse({
                'survey_id': survey_id,
                'valid': len(errors) == 0,
                'errors': errors
            })
        
        except SimpleSurvey.DoesNotExist:
            return JsonResponse({'error': 'Survey not found'}, status=404)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    else:
        return JsonResponse({'error': 'Invalid action'}, status=400)


# URL patterns for admin integration
integration_urlpatterns = [
    path('system-integration/', system_integration_admin_view, name='system_integration'),
    path('system-integration/api/', system_integration_api_view, name='system_integration_api'),
]


def add_integration_urls(admin_site):
    """
    Add integration URLs to admin site.
    """
    admin_site.get_urls = lambda: integration_urlpatterns + admin_site.get_urls()


class IntegrationStatusFilter(admin.SimpleListFilter):
    """
    Admin filter for integration status.
    """
    title = 'Integration Status'
    parameter_name = 'integration_status'
    
    def lookups(self, request, model_admin):
        return (
            ('valid', 'Valid'),
            ('invalid', 'Has Issues'),
        )
    
    def queryset(self, request, queryset):
        if self.value() == 'valid':
            # This would need to be implemented based on cached validation results
            # For now, return all objects
            return queryset
        elif self.value() == 'invalid':
            # This would need to be implemented based on cached validation results
            # For now, return none
            return queryset.none()
        return queryset


def create_integration_admin_action(action_name, action_function, description):
    """
    Create an admin action for integration tasks.
    
    Args:
        action_name: Name of the action
        action_function: Function to execute
        description: Description for the admin interface
    
    Returns:
        Admin action function
    """
    def admin_action(modeladmin, request, queryset):
        try:
            results = []
            for obj in queryset:
                result = action_function(obj)
                results.append(result)
            
            success_count = sum(1 for r in results if r.get('success', False))
            total_count = len(results)
            
            if success_count == total_count:
                messages.success(
                    request,
                    f'{action_name} completed successfully for {success_count} items.'
                )
            else:
                messages.warning(
                    request,
                    f'{action_name} completed for {success_count}/{total_count} items.'
                )
        
        except Exception as e:
            messages.error(request, f'{action_name} failed: {str(e)}')
    
    admin_action.short_description = description
    admin_action.__name__ = f'{action_name.lower().replace(" ", "_")}_action'
    
    return admin_action


# Pre-defined admin actions
def validate_policy_features_action(policy):
    """Validate policy features for admin action."""
    errors = CrossModuleValidator.validate_policy_features(policy)
    return {
        'success': len(errors) == 0,
        'errors': errors
    }


def validate_survey_completeness_action(survey):
    """Validate survey completeness for admin action."""
    errors = CrossModuleValidator.validate_survey_completeness(survey)
    return {
        'success': len(errors) == 0,
        'errors': errors
    }


# Create the actual admin actions
validate_policies_action = create_integration_admin_action(
    'Validate Policy Features',
    validate_policy_features_action,
    'Validate selected policies for feature consistency'
)

validate_surveys_action = create_integration_admin_action(
    'Validate Survey Completeness',
    validate_survey_completeness_action,
    'Validate selected surveys for completeness'
)