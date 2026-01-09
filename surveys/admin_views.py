"""
Admin views for survey analytics and monitoring.
"""

import json
from datetime import datetime, timedelta
from django.shortcuts import render, get_object_or_404
from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse, HttpResponse
from django.db.models import Count, Avg, Q
from django.utils import timezone
from django.core.paginator import Paginator
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt

from .models import (
    SurveyQuestion, SurveyResponse, SurveyAnalytics, 
    SurveyTemplate, ComparisonSession
)
from .analytics import SurveyAnalyticsCollector, AnalyticsReportGenerator
from policies.models import PolicyCategory


@staff_member_required
def analytics_dashboard(request):
    """
    Main analytics dashboard for survey performance monitoring.
    """
    collector = SurveyAnalyticsCollector()
    report_generator = AnalyticsReportGenerator()
    
    # Get summary statistics
    total_questions = SurveyQuestion.objects.filter(is_active=True).count()
    total_responses = SurveyResponse.objects.count()
    total_sessions = ComparisonSession.objects.count()
    completed_sessions = ComparisonSession.objects.filter(survey_completed=True).count()
    
    # Get category statistics
    categories = PolicyCategory.objects.all()
    category_stats = []
    
    for category in categories:
        category_sessions = ComparisonSession.objects.filter(category=category)
        category_completed = category_sessions.filter(survey_completed=True)
        
        category_stats.append({
            'category': category,
            'total_sessions': category_sessions.count(),
            'completed_sessions': category_completed.count(),
            'completion_rate': float(
                (category_completed.count() / max(category_sessions.count(), 1)) * 100
            ),
            'avg_completion_percentage': float(category_sessions.aggregate(
                avg=Avg('survey_completion_percentage')
            )['avg'] or 0)
        })
    
    # Get recent performance (last 7 days)
    recent_performance = report_generator.generate_performance_report(days=7)
    
    # Get top performing and problematic questions
    top_questions = SurveyAnalytics.objects.select_related('question').order_by(
        '-completion_rate'
    )[:5]
    
    problematic_questions = SurveyAnalytics.objects.select_related('question').order_by(
        'completion_rate'
    )[:5]
    
    context = {
        'total_questions': total_questions,
        'total_responses': total_responses,
        'total_sessions': total_sessions,
        'completed_sessions': completed_sessions,
        'overall_completion_rate': float((completed_sessions / max(total_sessions, 1)) * 100),
        'category_stats': category_stats,
        'recent_performance': recent_performance,
        'top_questions': top_questions,
        'problematic_questions': problematic_questions,
    }
    
    return render(request, 'admin/surveys/analytics_dashboard.html', context)


@staff_member_required
def category_analytics(request, category_slug):
    """
    Detailed analytics for a specific category.
    """
    category = get_object_or_404(PolicyCategory, slug=category_slug)
    report_generator = AnalyticsReportGenerator()
    
    # Generate comprehensive category report
    report = report_generator.generate_category_report(category_slug)
    
    # Get questions for this category
    questions = SurveyQuestion.objects.filter(
        category=category,
        is_active=True
    ).select_related('analytics').order_by('section', 'display_order')
    
    # Paginate questions
    paginator = Paginator(questions, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'category': category,
        'report': report,
        'questions': page_obj,
        'page_obj': page_obj,
    }
    
    return render(request, 'admin/surveys/category_analytics.html', context)


@staff_member_required
def question_analytics(request, question_id):
    """
    Detailed analytics for a specific question.
    """
    question = get_object_or_404(SurveyQuestion, id=question_id)
    collector = SurveyAnalyticsCollector()
    
    # Get detailed analytics
    analytics_data = collector.collect_question_analytics(question_id)
    
    # Get recent responses for analysis
    recent_responses = SurveyResponse.objects.filter(
        question=question
    ).select_related('session').order_by('-created_at')[:50]
    
    # Get response trends (last 30 days)
    end_date = timezone.now()
    start_date = end_date - timedelta(days=30)
    
    daily_responses = []
    for i in range(30):
        day_start = start_date + timedelta(days=i)
        day_end = day_start + timedelta(days=1)
        
        day_count = SurveyResponse.objects.filter(
            question=question,
            created_at__gte=day_start,
            created_at__lt=day_end
        ).count()
        
        daily_responses.append({
            'date': day_start.date().isoformat(),
            'count': day_count
        })
    
    context = {
        'question': question,
        'analytics_data': analytics_data,
        'recent_responses': recent_responses,
        'daily_responses': daily_responses,
    }
    
    return render(request, 'admin/surveys/question_analytics.html', context)


@staff_member_required
@require_http_methods(["POST"])
def refresh_analytics(request):
    """
    Refresh analytics data for all questions.
    """
    collector = SurveyAnalyticsCollector()
    
    # Get question IDs to update
    question_ids = request.POST.getlist('question_ids')
    if not question_ids:
        # Update all active questions
        question_ids = list(
            SurveyQuestion.objects.filter(is_active=True).values_list('id', flat=True)
        )
    
    # Bulk update analytics
    result = collector.bulk_update_analytics([int(qid) for qid in question_ids])
    
    messages.success(
        request,
        f"Updated analytics for {result['updated']} questions. "
        f"{result['errors']} errors occurred."
    )
    
    return JsonResponse({
        'success': True,
        'updated': result['updated'],
        'errors': result['errors'],
        'total': result['total']
    })


@staff_member_required
def export_analytics(request):
    """
    Export analytics data as JSON or CSV.
    """
    format_type = request.GET.get('format', 'json')
    category_slug = request.GET.get('category')
    
    report_generator = AnalyticsReportGenerator()
    
    if category_slug:
        data = report_generator.generate_category_report(category_slug)
        filename = f"survey_analytics_{category_slug}"
    else:
        # Export all categories
        categories = PolicyCategory.objects.all()
        data = {
            'categories': [
                report_generator.generate_category_report(cat.slug)
                for cat in categories
            ],
            'generated_at': timezone.now().isoformat()
        }
        filename = "survey_analytics_all"
    
    if format_type == 'json':
        response = HttpResponse(
            json.dumps(data, indent=2, default=str),
            content_type='application/json'
        )
        response['Content-Disposition'] = f'attachment; filename="{filename}.json"'
        return response
    
    elif format_type == 'csv':
        import csv
        from io import StringIO
        
        output = StringIO()
        writer = csv.writer(output)
        
        # Write CSV headers and data
        if category_slug:
            # Single category CSV
            writer.writerow([
                'Question ID', 'Question Text', 'Section', 'Total Responses',
                'Completion Rate', 'Skip Rate', 'Most Common Response'
            ])
            
            for template in data.get('templates', []):
                for q_analytics in template.get('question_analytics', []):
                    writer.writerow([
                        q_analytics.get('question_id'),
                        q_analytics.get('question_text', '')[:100],
                        '',  # Section would need to be added to analytics
                        q_analytics.get('total_responses'),
                        q_analytics.get('completion_rate'),
                        q_analytics.get('skip_rate'),
                        q_analytics.get('most_common_response')
                    ])
        
        response = HttpResponse(output.getvalue(), content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{filename}.csv"'
        return response
    
    return JsonResponse({'error': 'Invalid format'}, status=400)


@staff_member_required
def performance_trends(request):
    """
    Show performance trends over time.
    """
    days = int(request.GET.get('days', 30))
    category_slug = request.GET.get('category')
    
    report_generator = AnalyticsReportGenerator()
    performance_data = report_generator.generate_performance_report(days=days)
    
    # Filter by category if specified
    if category_slug:
        category = get_object_or_404(PolicyCategory, slug=category_slug)
        # Filter performance data for specific category
        # This would require modifying the report generator to support category filtering
    
    context = {
        'performance_data': performance_data,
        'days': days,
        'category_slug': category_slug,
    }
    
    return render(request, 'admin/surveys/performance_trends.html', context)


@staff_member_required
def analytics_api(request):
    """
    API endpoint for real-time analytics data (for AJAX requests).
    """
    action = request.GET.get('action')
    
    if action == 'summary':
        # Return summary statistics
        total_sessions = ComparisonSession.objects.count()
        completed_sessions = ComparisonSession.objects.filter(survey_completed=True).count()
        
        return JsonResponse({
            'total_sessions': total_sessions,
            'completed_sessions': completed_sessions,
            'completion_rate': float((completed_sessions / max(total_sessions, 1)) * 100),
            'total_questions': SurveyQuestion.objects.filter(is_active=True).count(),
            'total_responses': SurveyResponse.objects.count(),
        })
    
    elif action == 'question_performance':
        question_id = request.GET.get('question_id')
        if question_id:
            collector = SurveyAnalyticsCollector()
            analytics_data = collector.collect_question_analytics(int(question_id))
            return JsonResponse(analytics_data)
    
    elif action == 'category_summary':
        category_slug = request.GET.get('category')
        if category_slug:
            report_generator = AnalyticsReportGenerator()
            report = report_generator.generate_category_report(category_slug)
            return JsonResponse(report.get('summary', {}))
    
    return JsonResponse({'error': 'Invalid action'}, status=400)


@staff_member_required
def question_management(request):
    """
    Question management interface with analytics integration.
    """
    category_slug = request.GET.get('category')
    section = request.GET.get('section')
    
    questions = SurveyQuestion.objects.select_related('analytics', 'category')
    
    if category_slug:
        questions = questions.filter(category__slug=category_slug)
    
    if section:
        questions = questions.filter(section=section)
    
    questions = questions.order_by('category', 'section', 'display_order')
    
    # Get sections for filter
    sections = SurveyQuestion.objects.values_list('section', flat=True).distinct()
    
    # Paginate
    paginator = Paginator(questions, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'questions': page_obj,
        'page_obj': page_obj,
        'categories': PolicyCategory.objects.all(),
        'sections': sections,
        'selected_category': category_slug,
        'selected_section': section,
    }
    
    return render(request, 'admin/surveys/question_management.html', context)


@staff_member_required
@csrf_exempt
@require_http_methods(["POST"])
def update_question_status(request):
    """
    Update question active status via AJAX.
    """
    question_id = request.POST.get('question_id')
    is_active = request.POST.get('is_active') == 'true'
    
    try:
        question = SurveyQuestion.objects.get(id=question_id)
        question.is_active = is_active
        question.save()
        
        return JsonResponse({
            'success': True,
            'message': f"Question {'activated' if is_active else 'deactivated'} successfully"
        })
    
    except SurveyQuestion.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Question not found'
        }, status=404)
    
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=500)