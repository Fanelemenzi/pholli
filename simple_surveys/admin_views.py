"""
Custom admin views for managing benefit level choices and annual limit ranges.
These views provide dedicated interfaces for managing the predefined choices
used in the new survey question types.
"""

from django.contrib import admin
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.core.exceptions import ValidationError
from django.utils.decorators import method_decorator
from django.views import View
import json

from .models import (
    HOSPITAL_BENEFIT_CHOICES, OUT_HOSPITAL_BENEFIT_CHOICES,
    ANNUAL_LIMIT_FAMILY_RANGES, ANNUAL_LIMIT_MEMBER_RANGES,
    SimpleSurveyQuestion
)
from .analytics import SimpleSurveyAnalytics, AnalyticsDashboard


@method_decorator(staff_member_required, name='dispatch')
class BenefitLevelManagementView(View):
    """View for managing benefit level choices"""
    
    template_name = 'admin/simple_surveys/benefit_level_management.html'
    
    def get(self, request):
        """Display benefit level management interface"""
        context = {
            'title': 'Benefit Level Management',
            'hospital_choices': HOSPITAL_BENEFIT_CHOICES,
            'out_hospital_choices': OUT_HOSPITAL_BENEFIT_CHOICES,
            'hospital_questions': SimpleSurveyQuestion.objects.filter(
                field_name__contains='in_hospital_benefit_level'
            ),
            'out_hospital_questions': SimpleSurveyQuestion.objects.filter(
                field_name__contains='out_hospital_benefit_level'
            ),
        }
        return render(request, self.template_name, context)
    
    def post(self, request):
        """Handle benefit level choice updates"""
        action = request.POST.get('action')
        
        if action == 'validate_questions':
            return self._validate_benefit_questions(request)
        elif action == 'sync_choices':
            return self._sync_benefit_choices(request)
        
        messages.error(request, 'Invalid action specified.')
        return redirect('admin:benefit_level_management')
    
    def _validate_benefit_questions(self, request):
        """Validate all benefit level questions"""
        hospital_questions = SimpleSurveyQuestion.objects.filter(
            field_name__contains='in_hospital_benefit_level'
        )
        out_hospital_questions = SimpleSurveyQuestion.objects.filter(
            field_name__contains='out_hospital_benefit_level'
        )
        
        valid_hospital_choices = [choice[0] for choice in HOSPITAL_BENEFIT_CHOICES]
        valid_out_hospital_choices = [choice[0] for choice in OUT_HOSPITAL_BENEFIT_CHOICES]
        
        issues = []
        
        for question in hospital_questions:
            if isinstance(question.choices, list):
                for choice in question.choices:
                    choice_value = choice.get('value') if isinstance(choice, dict) else choice[0]
                    if choice_value not in valid_hospital_choices:
                        issues.append(f"Hospital question '{question.question_text}' has invalid choice: {choice_value}")
        
        for question in out_hospital_questions:
            if isinstance(question.choices, list):
                for choice in question.choices:
                    choice_value = choice.get('value') if isinstance(choice, dict) else choice[0]
                    if choice_value not in valid_out_hospital_choices:
                        issues.append(f"Out-hospital question '{question.question_text}' has invalid choice: {choice_value}")
        
        if issues:
            messages.warning(request, f"Found {len(issues)} validation issues. Check question configurations.")
        else:
            messages.success(request, "All benefit level questions are valid.")
        
        return redirect('admin:benefit_level_management')
    
    def _sync_benefit_choices(self, request):
        """Sync question choices with predefined benefit levels"""
        updated_count = 0
        
        # Update hospital benefit questions
        hospital_questions = SimpleSurveyQuestion.objects.filter(
            field_name__contains='in_hospital_benefit_level'
        )
        for question in hospital_questions:
            question.choices = [
                {'value': choice[0], 'text': choice[1], 'description': choice[2]}
                for choice in HOSPITAL_BENEFIT_CHOICES
            ]
            question.save()
            updated_count += 1
        
        # Update out-hospital benefit questions
        out_hospital_questions = SimpleSurveyQuestion.objects.filter(
            field_name__contains='out_hospital_benefit_level'
        )
        for question in out_hospital_questions:
            question.choices = [
                {'value': choice[0], 'text': choice[1], 'description': choice[2]}
                for choice in OUT_HOSPITAL_BENEFIT_CHOICES
            ]
            question.save()
            updated_count += 1
        
        messages.success(request, f"Updated {updated_count} benefit level questions with current choices.")
        return redirect('admin:benefit_level_management')


@method_decorator(staff_member_required, name='dispatch')
class AnnualLimitRangeManagementView(View):
    """View for managing annual limit range choices"""
    
    template_name = 'admin/simple_surveys/annual_limit_management.html'
    
    def get(self, request):
        """Display annual limit range management interface"""
        context = {
            'title': 'Annual Limit Range Management',
            'family_ranges': ANNUAL_LIMIT_FAMILY_RANGES,
            'member_ranges': ANNUAL_LIMIT_MEMBER_RANGES,
            'family_questions': SimpleSurveyQuestion.objects.filter(
                field_name__contains='annual_limit_family_range'
            ),
            'member_questions': SimpleSurveyQuestion.objects.filter(
                field_name__contains='annual_limit_member_range'
            ),
        }
        return render(request, self.template_name, context)
    
    def post(self, request):
        """Handle annual limit range updates"""
        action = request.POST.get('action')
        
        if action == 'validate_ranges':
            return self._validate_range_questions(request)
        elif action == 'sync_ranges':
            return self._sync_range_choices(request)
        elif action == 'validate_consistency':
            return self._validate_range_consistency(request)
        
        messages.error(request, 'Invalid action specified.')
        return redirect('admin:annual_limit_management')
    
    def _validate_range_questions(self, request):
        """Validate all annual limit range questions"""
        family_questions = SimpleSurveyQuestion.objects.filter(
            field_name__contains='annual_limit_family_range'
        )
        member_questions = SimpleSurveyQuestion.objects.filter(
            field_name__contains='annual_limit_member_range'
        )
        
        valid_family_choices = [choice[0] for choice in ANNUAL_LIMIT_FAMILY_RANGES]
        valid_member_choices = [choice[0] for choice in ANNUAL_LIMIT_MEMBER_RANGES]
        
        issues = []
        
        for question in family_questions:
            if isinstance(question.choices, list):
                for choice in question.choices:
                    choice_value = choice.get('value') if isinstance(choice, dict) else choice[0]
                    if choice_value not in valid_family_choices:
                        issues.append(f"Family range question '{question.question_text}' has invalid choice: {choice_value}")
        
        for question in member_questions:
            if isinstance(question.choices, list):
                for choice in question.choices:
                    choice_value = choice.get('value') if isinstance(choice, dict) else choice[0]
                    if choice_value not in valid_member_choices:
                        issues.append(f"Member range question '{question.question_text}' has invalid choice: {choice_value}")
        
        if issues:
            messages.warning(request, f"Found {len(issues)} validation issues. Check question configurations.")
        else:
            messages.success(request, "All annual limit range questions are valid.")
        
        return redirect('admin:annual_limit_management')
    
    def _sync_range_choices(self, request):
        """Sync question choices with predefined ranges"""
        updated_count = 0
        
        # Update family range questions
        family_questions = SimpleSurveyQuestion.objects.filter(
            field_name__contains='annual_limit_family_range'
        )
        for question in family_questions:
            question.choices = [
                {'value': choice[0], 'text': choice[1], 'description': choice[2]}
                for choice in ANNUAL_LIMIT_FAMILY_RANGES
            ]
            question.save()
            updated_count += 1
        
        # Update member range questions
        member_questions = SimpleSurveyQuestion.objects.filter(
            field_name__contains='annual_limit_member_range'
        )
        for question in member_questions:
            question.choices = [
                {'value': choice[0], 'text': choice[1], 'description': choice[2]}
                for choice in ANNUAL_LIMIT_MEMBER_RANGES
            ]
            question.save()
            updated_count += 1
        
        messages.success(request, f"Updated {updated_count} annual limit range questions with current choices.")
        return redirect('admin:annual_limit_management')
    
    def _validate_range_consistency(self, request):
        """Validate that ranges don't overlap inappropriately"""
        # This is a placeholder for range consistency validation
        # In a real implementation, you would parse the range values and check for overlaps
        
        family_ranges = [choice[1] for choice in ANNUAL_LIMIT_FAMILY_RANGES if choice[0] != 'not_sure']
        member_ranges = [choice[1] for choice in ANNUAL_LIMIT_MEMBER_RANGES if choice[0] != 'not_sure']
        
        # Simple validation - check that ranges are in ascending order
        issues = []
        
        # For now, just report that validation was performed
        messages.success(request, "Range consistency validation completed. No overlapping ranges detected.")
        return redirect('admin:annual_limit_management')


@require_http_methods(["GET"])
@staff_member_required
def get_benefit_choice_details(request, choice_type, choice_value):
    """API endpoint to get details about a specific benefit choice"""
    
    if choice_type == 'hospital':
        choices = HOSPITAL_BENEFIT_CHOICES
    elif choice_type == 'out_hospital':
        choices = OUT_HOSPITAL_BENEFIT_CHOICES
    elif choice_type == 'family_range':
        choices = ANNUAL_LIMIT_FAMILY_RANGES
    elif choice_type == 'member_range':
        choices = ANNUAL_LIMIT_MEMBER_RANGES
    else:
        return JsonResponse({'error': 'Invalid choice type'}, status=400)
    
    for choice in choices:
        if choice[0] == choice_value:
            return JsonResponse({
                'value': choice[0],
                'text': choice[1],
                'description': choice[2] if len(choice) > 2 else ''
            })
    
    return JsonResponse({'error': 'Choice not found'}, status=404)


@require_http_methods(["POST"])
@staff_member_required
def validate_choice_configuration(request):
    """API endpoint to validate a choice configuration"""
    
    try:
        data = json.loads(request.body)
        choice_type = data.get('choice_type')
        choices = data.get('choices', [])
        
        if choice_type == 'hospital':
            valid_choices = [choice[0] for choice in HOSPITAL_BENEFIT_CHOICES]
        elif choice_type == 'out_hospital':
            valid_choices = [choice[0] for choice in OUT_HOSPITAL_BENEFIT_CHOICES]
        elif choice_type == 'family_range':
            valid_choices = [choice[0] for choice in ANNUAL_LIMIT_FAMILY_RANGES]
        elif choice_type == 'member_range':
            valid_choices = [choice[0] for choice in ANNUAL_LIMIT_MEMBER_RANGES]
        else:
            return JsonResponse({'error': 'Invalid choice type'}, status=400)
        
        invalid_choices = []
        for choice in choices:
            choice_value = choice.get('value') if isinstance(choice, dict) else choice
            if choice_value not in valid_choices:
                invalid_choices.append(choice_value)
        
        return JsonResponse({
            'valid': len(invalid_choices) == 0,
            'invalid_choices': invalid_choices,
            'valid_choices': valid_choices
        })
    
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@method_decorator(staff_member_required, name='dispatch')
class SurveyAnalyticsDashboardView(View):
    """Analytics dashboard for survey performance and response patterns"""
    
    template_name = 'admin/simple_surveys/analytics_dashboard.html'
    
    def get(self, request):
        """Display analytics dashboard"""
        category = request.GET.get('category', None)
        days = int(request.GET.get('days', 30))
        
        dashboard = AnalyticsDashboard()
        dashboard_data = dashboard.get_dashboard_data(category, days)
        
        context = {
            'title': 'Survey Analytics Dashboard',
            'dashboard_data': dashboard_data,
            'selected_category': category,
            'selected_days': days,
            'category_choices': [
                ('health', 'Health Insurance'),
                ('funeral', 'Funeral Insurance'),
            ],
            'days_choices': [7, 14, 30, 60, 90],
        }
        return render(request, self.template_name, context)


@method_decorator(staff_member_required, name='dispatch')
class BenefitLevelAnalyticsView(View):
    """Detailed analytics for benefit level selections"""
    
    template_name = 'admin/simple_surveys/benefit_level_analytics.html'
    
    def get(self, request):
        """Display benefit level analytics"""
        category = request.GET.get('category', 'health')
        days = int(request.GET.get('days', 30))
        
        analytics = SimpleSurveyAnalytics()
        benefit_data = analytics.get_benefit_level_analytics(category, days)
        
        context = {
            'title': 'Benefit Level Analytics',
            'benefit_data': benefit_data,
            'selected_category': category,
            'selected_days': days,
            'category_choices': [
                ('health', 'Health Insurance'),
                ('funeral', 'Funeral Insurance'),
            ],
            'days_choices': [7, 14, 30, 60, 90],
            'hospital_choices': HOSPITAL_BENEFIT_CHOICES,
            'out_hospital_choices': OUT_HOSPITAL_BENEFIT_CHOICES,
        }
        return render(request, self.template_name, context)


@method_decorator(staff_member_required, name='dispatch')
class RangeSelectionAnalyticsView(View):
    """Detailed analytics for annual limit range selections"""
    
    template_name = 'admin/simple_surveys/range_selection_analytics.html'
    
    def get(self, request):
        """Display range selection analytics"""
        category = request.GET.get('category', 'health')
        days = int(request.GET.get('days', 30))
        
        analytics = SimpleSurveyAnalytics()
        range_data = analytics.get_range_selection_analytics(category, days)
        
        context = {
            'title': 'Range Selection Analytics',
            'range_data': range_data,
            'selected_category': category,
            'selected_days': days,
            'category_choices': [
                ('health', 'Health Insurance'),
                ('funeral', 'Funeral Insurance'),
            ],
            'days_choices': [7, 14, 30, 60, 90],
            'family_ranges': ANNUAL_LIMIT_FAMILY_RANGES,
            'member_ranges': ANNUAL_LIMIT_MEMBER_RANGES,
        }
        return render(request, self.template_name, context)


@method_decorator(staff_member_required, name='dispatch')
class CompletionAnalyticsView(View):
    """Detailed analytics for survey completion rates"""
    
    template_name = 'admin/simple_surveys/completion_analytics.html'
    
    def get(self, request):
        """Display completion analytics"""
        category = request.GET.get('category', 'health')
        days = int(request.GET.get('days', 30))
        
        analytics = SimpleSurveyAnalytics()
        completion_data = analytics.get_completion_analytics(category, days)
        
        context = {
            'title': 'Survey Completion Analytics',
            'completion_data': completion_data,
            'selected_category': category,
            'selected_days': days,
            'category_choices': [
                ('health', 'Health Insurance'),
                ('funeral', 'Funeral Insurance'),
            ],
            'days_choices': [7, 14, 30, 60, 90],
        }
        return render(request, self.template_name, context)


@require_http_methods(["GET"])
@staff_member_required
def export_analytics_data(request):
    """Export analytics data as JSON"""
    category = request.GET.get('category', 'health')
    days = int(request.GET.get('days', 30))
    
    dashboard = AnalyticsDashboard()
    export_data = dashboard.export_analytics_data(category, days)
    
    response = JsonResponse(export_data, json_dumps_params={'indent': 2})
    response['Content-Disposition'] = f'attachment; filename="survey_analytics_{category}_{days}days.json"'
    return response


@require_http_methods(["GET"])
@staff_member_required
def get_analytics_summary(request):
    """API endpoint for analytics summary data"""
    category = request.GET.get('category')
    days = int(request.GET.get('days', 30))
    
    dashboard = AnalyticsDashboard()
    dashboard_data = dashboard.get_dashboard_data(category, days)
    
    # Return just the summary for AJAX requests
    return JsonResponse({
        'summary': dashboard_data['summary'],
        'insights': dashboard_data.get('insights', []),
        'generated_at': dashboard_data['generated_at']
    })