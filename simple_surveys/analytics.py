"""
Analytics and reporting functionality for SimpleSurvey system.
Tracks benefit level selections, range patterns, and completion rates.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from django.db import models
from django.db.models import Count, Avg, Q, F
from django.utils import timezone
from django.core.cache import cache
from collections import defaultdict, Counter

from .models import (
    SimpleSurveyQuestion, SimpleSurveyResponse, QuotationSession,
    HOSPITAL_BENEFIT_CHOICES, OUT_HOSPITAL_BENEFIT_CHOICES,
    ANNUAL_LIMIT_FAMILY_RANGES, ANNUAL_LIMIT_MEMBER_RANGES
)

logger = logging.getLogger(__name__)


class SimpleSurveyAnalytics:
    """
    Analytics collector for SimpleSurvey system focusing on benefit levels and ranges.
    """
    
    def __init__(self):
        self.cache_timeout = 3600  # 1 hour cache
    
    def get_benefit_level_analytics(self, category: str, days: int = 30) -> Dict[str, Any]:
        """
        Analyze benefit level selection patterns for in-hospital and out-of-hospital benefits.
        
        Args:
            category: 'health' or 'funeral'
            days: Number of days to analyze (default 30)
            
        Returns:
            Dict containing benefit level analytics
        """
        end_date = timezone.now()
        start_date = end_date - timedelta(days=days)
        
        # Get responses for benefit level questions
        hospital_responses = SimpleSurveyResponse.objects.filter(
            category=category,
            question__field_name='in_hospital_benefit_level',
            created_at__gte=start_date,
            created_at__lte=end_date
        ).values_list('response_value', flat=True)
        
        out_hospital_responses = SimpleSurveyResponse.objects.filter(
            category=category,
            question__field_name='out_hospital_benefit_level',
            created_at__gte=start_date,
            created_at__lte=end_date
        ).values_list('response_value', flat=True)
        
        # Count selections for each benefit level
        hospital_counts = Counter(hospital_responses)
        out_hospital_counts = Counter(out_hospital_responses)
        
        # Get choice labels for display
        hospital_choices_dict = {choice[0]: choice[1] for choice in HOSPITAL_BENEFIT_CHOICES}
        out_hospital_choices_dict = {choice[0]: choice[1] for choice in OUT_HOSPITAL_BENEFIT_CHOICES}
        
        # Calculate percentages
        total_hospital = sum(hospital_counts.values())
        total_out_hospital = sum(out_hospital_counts.values())
        
        hospital_distribution = {}
        for choice_value, count in hospital_counts.items():
            percentage = (count / total_hospital * 100) if total_hospital > 0 else 0
            hospital_distribution[choice_value] = {
                'count': count,
                'percentage': round(percentage, 2),
                'label': hospital_choices_dict.get(choice_value, choice_value)
            }
        
        out_hospital_distribution = {}
        for choice_value, count in out_hospital_counts.items():
            percentage = (count / total_out_hospital * 100) if total_out_hospital > 0 else 0
            out_hospital_distribution[choice_value] = {
                'count': count,
                'percentage': round(percentage, 2),
                'label': out_hospital_choices_dict.get(choice_value, choice_value)
            }
        
        return {
            'category': category,
            'period_days': days,
            'period_start': start_date.date().isoformat(),
            'period_end': end_date.date().isoformat(),
            'hospital_benefits': {
                'total_responses': total_hospital,
                'distribution': hospital_distribution,
                'most_popular': max(hospital_counts.items(), key=lambda x: x[1])[0] if hospital_counts else None
            },
            'out_hospital_benefits': {
                'total_responses': total_out_hospital,
                'distribution': out_hospital_distribution,
                'most_popular': max(out_hospital_counts.items(), key=lambda x: x[1])[0] if out_hospital_counts else None
            },
            'generated_at': timezone.now().isoformat()
        }
    
    def get_range_selection_analytics(self, category: str, days: int = 30) -> Dict[str, Any]:
        """
        Analyze annual limit range selection patterns.
        
        Args:
            category: 'health' or 'funeral'
            days: Number of days to analyze (default 30)
            
        Returns:
            Dict containing range selection analytics
        """
        end_date = timezone.now()
        start_date = end_date - timedelta(days=days)
        
        # Get responses for range questions
        family_responses = SimpleSurveyResponse.objects.filter(
            category=category,
            question__field_name='annual_limit_family_range',
            created_at__gte=start_date,
            created_at__lte=end_date
        ).values_list('response_value', flat=True)
        
        member_responses = SimpleSurveyResponse.objects.filter(
            category=category,
            question__field_name='annual_limit_member_range',
            created_at__gte=start_date,
            created_at__lte=end_date
        ).values_list('response_value', flat=True)
        
        # Count selections for each range
        family_counts = Counter(family_responses)
        member_counts = Counter(member_responses)
        
        # Get choice labels for display
        family_choices_dict = {choice[0]: choice[1] for choice in ANNUAL_LIMIT_FAMILY_RANGES}
        member_choices_dict = {choice[0]: choice[1] for choice in ANNUAL_LIMIT_MEMBER_RANGES}
        
        # Calculate percentages and analyze patterns
        total_family = sum(family_counts.values())
        total_member = sum(member_counts.values())
        
        family_distribution = {}
        for choice_value, count in family_counts.items():
            percentage = (count / total_family * 100) if total_family > 0 else 0
            family_distribution[choice_value] = {
                'count': count,
                'percentage': round(percentage, 2),
                'label': family_choices_dict.get(choice_value, choice_value)
            }
        
        member_distribution = {}
        for choice_value, count in member_counts.items():
            percentage = (count / total_member * 100) if total_member > 0 else 0
            member_distribution[choice_value] = {
                'count': count,
                'percentage': round(percentage, 2),
                'label': member_choices_dict.get(choice_value, choice_value)
            }
        
        # Analyze guidance requests
        family_guidance_requests = family_counts.get('not_sure', 0)
        member_guidance_requests = member_counts.get('not_sure', 0)
        
        family_guidance_rate = (family_guidance_requests / total_family * 100) if total_family > 0 else 0
        member_guidance_rate = (member_guidance_requests / total_member * 100) if total_member > 0 else 0
        
        return {
            'category': category,
            'period_days': days,
            'period_start': start_date.date().isoformat(),
            'period_end': end_date.date().isoformat(),
            'family_ranges': {
                'total_responses': total_family,
                'distribution': family_distribution,
                'most_popular': max(family_counts.items(), key=lambda x: x[1])[0] if family_counts else None,
                'guidance_requests': family_guidance_requests,
                'guidance_rate': round(family_guidance_rate, 2)
            },
            'member_ranges': {
                'total_responses': total_member,
                'distribution': member_distribution,
                'most_popular': max(member_counts.items(), key=lambda x: x[1])[0] if member_counts else None,
                'guidance_requests': member_guidance_requests,
                'guidance_rate': round(member_guidance_rate, 2)
            },
            'generated_at': timezone.now().isoformat()
        }
    
    def get_completion_analytics(self, category: str, days: int = 30) -> Dict[str, Any]:
        """
        Analyze survey completion rates with new question structure.
        
        Args:
            category: 'health' or 'funeral'
            days: Number of days to analyze (default 30)
            
        Returns:
            Dict containing completion analytics
        """
        end_date = timezone.now()
        start_date = end_date - timedelta(days=days)
        
        # Get all sessions in the period
        sessions = QuotationSession.objects.filter(
            category=category,
            created_at__gte=start_date,
            created_at__lte=end_date
        )
        
        total_sessions = sessions.count()
        completed_sessions = sessions.filter(is_completed=True).count()
        
        # Calculate completion rate
        overall_completion_rate = (completed_sessions / total_sessions * 100) if total_sessions > 0 else 0
        
        # Analyze completion by question type (exclude medical aid questions)
        question_completion = {}
        questions = SimpleSurveyQuestion.objects.filter(
            category=category, 
            is_required=True
        ).exclude(
            field_name__in=['currently_on_medical_aid', 'medical_aid_status']
        )
        
        for question in questions:
            responses_count = SimpleSurveyResponse.objects.filter(
                category=category,
                question=question,
                created_at__gte=start_date,
                created_at__lte=end_date
            ).count()
            
            completion_rate = (responses_count / total_sessions * 100) if total_sessions > 0 else 0
            
            question_completion[question.field_name] = {
                'question_text': question.question_text[:50] + '...',
                'responses': responses_count,
                'completion_rate': round(completion_rate, 2),
                'input_type': question.input_type
            }
        
        # Analyze drop-off points
        drop_off_analysis = self._analyze_drop_off_points(category, start_date, end_date)
        
        # Daily completion trends
        daily_trends = []
        for i in range(days):
            day_start = start_date + timedelta(days=i)
            day_end = day_start + timedelta(days=1)
            
            day_sessions = sessions.filter(
                created_at__gte=day_start,
                created_at__lt=day_end
            )
            
            day_total = day_sessions.count()
            day_completed = day_sessions.filter(is_completed=True).count()
            day_completion_rate = (day_completed / day_total * 100) if day_total > 0 else 0
            
            daily_trends.append({
                'date': day_start.date().isoformat(),
                'total_sessions': day_total,
                'completed_sessions': day_completed,
                'completion_rate': round(day_completion_rate, 2)
            })
        
        return {
            'category': category,
            'period_days': days,
            'period_start': start_date.date().isoformat(),
            'period_end': end_date.date().isoformat(),
            'summary': {
                'total_sessions': total_sessions,
                'completed_sessions': completed_sessions,
                'completion_rate': round(overall_completion_rate, 2)
            },
            'question_completion': question_completion,
            'drop_off_analysis': drop_off_analysis,
            'daily_trends': daily_trends,
            'generated_at': timezone.now().isoformat()
        }
    
    def get_comprehensive_report(self, category: str, days: int = 30) -> Dict[str, Any]:
        """
        Generate comprehensive analytics report combining all metrics.
        
        Args:
            category: 'health' or 'funeral'
            days: Number of days to analyze (default 30)
            
        Returns:
            Dict containing comprehensive analytics report
        """
        benefit_analytics = self.get_benefit_level_analytics(category, days)
        range_analytics = self.get_range_selection_analytics(category, days)
        completion_analytics = self.get_completion_analytics(category, days)
        
        # Calculate key insights
        insights = self._generate_insights(benefit_analytics, range_analytics, completion_analytics)
        
        return {
            'category': category,
            'period_days': days,
            'period_start': completion_analytics['period_start'],
            'period_end': completion_analytics['period_end'],
            'benefit_levels': benefit_analytics,
            'range_selections': range_analytics,
            'completion_metrics': completion_analytics,
            'insights': insights,
            'generated_at': timezone.now().isoformat()
        }
    
    def _analyze_drop_off_points(self, category: str, start_date: datetime, end_date: datetime) -> List[Dict[str, Any]]:
        """
        Analyze where users typically drop off in the survey.
        """
        questions = SimpleSurveyQuestion.objects.filter(
            category=category,
            is_required=True
        ).exclude(
            field_name__in=['currently_on_medical_aid', 'medical_aid_status']
        ).order_by('display_order')
        
        drop_off_points = []
        
        for i, question in enumerate(questions):
            # Count sessions that reached this question
            sessions_reached = SimpleSurveyResponse.objects.filter(
                category=category,
                question=question,
                created_at__gte=start_date,
                created_at__lte=end_date
            ).values('session_key').distinct().count()
            
            # Count sessions that reached the next question (if exists)
            next_question = questions[i + 1] if i + 1 < len(questions) else None
            sessions_continued = 0
            
            if next_question:
                sessions_continued = SimpleSurveyResponse.objects.filter(
                    category=category,
                    question=next_question,
                    created_at__gte=start_date,
                    created_at__lte=end_date
                ).values('session_key').distinct().count()
            
            drop_off_rate = 0
            if sessions_reached > 0:
                drop_off_rate = ((sessions_reached - sessions_continued) / sessions_reached) * 100
            
            drop_off_points.append({
                'question_field': question.field_name,
                'question_text': question.question_text[:50] + '...',
                'sessions_reached': sessions_reached,
                'sessions_continued': sessions_continued,
                'drop_off_rate': round(drop_off_rate, 2),
                'input_type': question.input_type
            })
        
        return drop_off_points
    
    def _generate_insights(self, benefit_analytics: Dict, range_analytics: Dict, completion_analytics: Dict) -> List[str]:
        """
        Generate key insights from analytics data.
        """
        insights = []
        
        # Benefit level insights
        hospital_data = benefit_analytics['hospital_benefits']
        if hospital_data['most_popular']:
            hospital_choice = next(
                (choice[1] for choice in HOSPITAL_BENEFIT_CHOICES if choice[0] == hospital_data['most_popular']),
                hospital_data['most_popular']
            )
            insights.append(f"Most popular in-hospital benefit level: {hospital_choice}")
        
        out_hospital_data = benefit_analytics['out_hospital_benefits']
        if out_hospital_data['most_popular']:
            out_hospital_choice = next(
                (choice[1] for choice in OUT_HOSPITAL_BENEFIT_CHOICES if choice[0] == out_hospital_data['most_popular']),
                out_hospital_data['most_popular']
            )
            insights.append(f"Most popular out-of-hospital benefit level: {out_hospital_choice}")
        
        # Range selection insights
        family_data = range_analytics['family_ranges']
        if family_data['guidance_rate'] > 20:
            insights.append(f"High guidance request rate for family ranges: {family_data['guidance_rate']}%")
        
        member_data = range_analytics['member_ranges']
        if member_data['guidance_rate'] > 20:
            insights.append(f"High guidance request rate for member ranges: {member_data['guidance_rate']}%")
        
        # Completion insights
        completion_rate = completion_analytics['summary']['completion_rate']
        if completion_rate < 70:
            insights.append(f"Low completion rate detected: {completion_rate}% - consider survey optimization")
        elif completion_rate > 85:
            insights.append(f"Excellent completion rate: {completion_rate}%")
        
        # Drop-off insights
        drop_offs = completion_analytics['drop_off_analysis']
        high_drop_off = [d for d in drop_offs if d['drop_off_rate'] > 30]
        if high_drop_off:
            question_field = high_drop_off[0]['question_field']
            rate = high_drop_off[0]['drop_off_rate']
            insights.append(f"High drop-off at {question_field}: {rate}% - review question design")
        
        return insights
    
    def get_cached_analytics(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """
        Get cached analytics data.
        """
        return cache.get(cache_key)
    
    def set_cached_analytics(self, cache_key: str, data: Dict[str, Any]) -> None:
        """
        Cache analytics data.
        """
        cache.set(cache_key, data, self.cache_timeout)


class AnalyticsDashboard:
    """
    Dashboard interface for analytics data.
    """
    
    def __init__(self):
        self.analytics = SimpleSurveyAnalytics()
    
    def get_dashboard_data(self, category: str = None, days: int = 30) -> Dict[str, Any]:
        """
        Get dashboard data for admin interface.
        
        Args:
            category: Optional category filter ('health' or 'funeral')
            days: Number of days to analyze
            
        Returns:
            Dict containing dashboard data
        """
        categories = [category] if category else ['health', 'funeral']
        dashboard_data = {
            'period_days': days,
            'categories': {},
            'summary': {
                'total_sessions': 0,
                'total_completed': 0,
                'overall_completion_rate': 0,
                'total_benefit_responses': 0,
                'total_range_responses': 0
            },
            'generated_at': timezone.now().isoformat()
        }
        
        total_sessions = 0
        total_completed = 0
        total_benefit_responses = 0
        total_range_responses = 0
        
        for cat in categories:
            cache_key = f"dashboard_analytics_{cat}_{days}"
            cached_data = self.analytics.get_cached_analytics(cache_key)
            
            if cached_data:
                cat_data = cached_data
            else:
                cat_data = self.analytics.get_comprehensive_report(cat, days)
                self.analytics.set_cached_analytics(cache_key, cat_data)
            
            dashboard_data['categories'][cat] = cat_data
            
            # Aggregate summary data
            completion_data = cat_data['completion_metrics']['summary']
            total_sessions += completion_data['total_sessions']
            total_completed += completion_data['completed_sessions']
            
            benefit_data = cat_data['benefit_levels']
            total_benefit_responses += benefit_data['hospital_benefits']['total_responses']
            total_benefit_responses += benefit_data['out_hospital_benefits']['total_responses']
            
            range_data = cat_data['range_selections']
            total_range_responses += range_data['family_ranges']['total_responses']
            total_range_responses += range_data['member_ranges']['total_responses']
        
        # Calculate overall metrics
        dashboard_data['summary']['total_sessions'] = total_sessions
        dashboard_data['summary']['total_completed'] = total_completed
        dashboard_data['summary']['overall_completion_rate'] = (
            (total_completed / total_sessions * 100) if total_sessions > 0 else 0
        )
        dashboard_data['summary']['total_benefit_responses'] = total_benefit_responses
        dashboard_data['summary']['total_range_responses'] = total_range_responses
        
        return dashboard_data
    
    def export_analytics_data(self, category: str, days: int = 30, format: str = 'json') -> Dict[str, Any]:
        """
        Export analytics data for external analysis.
        
        Args:
            category: 'health' or 'funeral'
            days: Number of days to analyze
            format: Export format ('json' only for now)
            
        Returns:
            Dict containing exportable analytics data
        """
        if format != 'json':
            raise ValueError("Only JSON format is currently supported")
        
        comprehensive_data = self.analytics.get_comprehensive_report(category, days)
        
        # Add metadata for export
        export_data = {
            'export_metadata': {
                'exported_at': timezone.now().isoformat(),
                'export_format': format,
                'data_version': '1.0',
                'category': category,
                'period_days': days
            },
            'analytics_data': comprehensive_data
        }
        
        return export_data