"""
Survey analytics collection and processing functionality.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from django.db import models, transaction
from django.db.models import Count, Avg, Q, F
from django.utils import timezone
from django.core.cache import cache
from .models import (
    SurveyQuestion, SurveyResponse, SurveyAnalytics, 
    ComparisonSession, SurveyTemplate
)

logger = logging.getLogger(__name__)


class SurveyAnalyticsCollector:
    """
    Collects and processes survey analytics data.
    """
    
    def __init__(self):
        self.cache_timeout = 3600  # 1 hour cache
    
    def collect_question_analytics(self, question_id: int) -> Dict[str, Any]:
        """
        Collect comprehensive analytics for a specific question.
        """
        try:
            question = SurveyQuestion.objects.get(id=question_id)
            responses = SurveyResponse.objects.filter(question=question)
            
            # Basic metrics
            total_responses = responses.count()
            if total_responses == 0:
                return self._empty_analytics()
            
            # Calculate completion rate
            # Get all sessions that reached this question
            sessions_with_question = ComparisonSession.objects.filter(
                survey_responses__question=question
            ).distinct()
            
            # Get all sessions for this category
            total_sessions = ComparisonSession.objects.filter(
                category=question.category
            ).count()
            
            completion_rate = float((sessions_with_question.count() / max(total_sessions, 1)) * 100)
            
            # Calculate skip rate
            sessions_that_skipped = total_sessions - sessions_with_question.count()
            skip_rate = float((sessions_that_skipped / max(total_sessions, 1)) * 100)
            
            # Response distribution
            response_distribution = self._calculate_response_distribution(responses, question)
            
            # Most common response
            most_common_response = self._get_most_common_response(responses, question)
            
            # Average confidence level
            avg_confidence = responses.aggregate(
                avg_confidence=Avg('confidence_level')
            )['avg_confidence'] or 0
            
            return {
                'question_id': question_id,
                'total_responses': total_responses,
                'completion_rate': round(completion_rate, 2),
                'skip_rate': round(skip_rate, 2),
                'response_distribution': response_distribution,
                'most_common_response': most_common_response,
                'average_confidence': float(round(avg_confidence, 2)),
                'last_updated': timezone.now().isoformat()
            }
            
        except SurveyQuestion.DoesNotExist:
            logger.error(f"Question with id {question_id} not found")
            return self._empty_analytics()
        except Exception as e:
            logger.error(f"Error collecting analytics for question {question_id}: {str(e)}")
            return self._empty_analytics()
    
    def collect_template_analytics(self, template_id: int) -> Dict[str, Any]:
        """
        Collect analytics for an entire survey template.
        """
        try:
            template = SurveyTemplate.objects.get(id=template_id)
            questions = SurveyQuestion.objects.filter(
                category=template.category,
                is_active=True
            )
            
            # Overall completion metrics
            total_sessions = ComparisonSession.objects.filter(
                category=template.category
            ).count()
            
            completed_sessions = ComparisonSession.objects.filter(
                category=template.category,
                survey_completed=True
            ).count()
            
            overall_completion_rate = (completed_sessions / max(total_sessions, 1)) * 100
            
            # Average completion percentage
            avg_completion_percentage = ComparisonSession.objects.filter(
                category=template.category
            ).aggregate(
                avg_completion=Avg('survey_completion_percentage')
            )['avg_completion'] or 0
            
            # Question-level analytics
            question_analytics = []
            for question in questions:
                question_data = self.collect_question_analytics(question.id)
                question_analytics.append(question_data)
            
            # Drop-off analysis
            drop_off_points = self._analyze_drop_off_points(template)
            
            return {
                'template_id': template_id,
                'template_name': template.name,
                'category': template.category.name,
                'total_sessions': total_sessions,
                'completed_sessions': completed_sessions,
                'overall_completion_rate': round(overall_completion_rate, 2),
                'average_completion_percentage': round(avg_completion_percentage, 2),
                'question_analytics': question_analytics,
                'drop_off_points': drop_off_points,
                'last_updated': timezone.now().isoformat()
            }
            
        except SurveyTemplate.DoesNotExist:
            logger.error(f"Template with id {template_id} not found")
            return {}
        except Exception as e:
            logger.error(f"Error collecting template analytics for {template_id}: {str(e)}")
            return {}
    
    def update_analytics_cache(self, question_id: int) -> None:
        """
        Update cached analytics for a question.
        """
        cache_key = f"question_analytics_{question_id}"
        analytics_data = self.collect_question_analytics(question_id)
        cache.set(cache_key, analytics_data, self.cache_timeout)
    
    def get_cached_analytics(self, question_id: int) -> Optional[Dict[str, Any]]:
        """
        Get cached analytics for a question.
        """
        cache_key = f"question_analytics_{question_id}"
        return cache.get(cache_key)
    
    def bulk_update_analytics(self, question_ids: List[int] = None) -> Dict[str, int]:
        """
        Bulk update analytics for multiple questions.
        """
        if question_ids is None:
            questions = SurveyQuestion.objects.filter(is_active=True)
            question_ids = list(questions.values_list('id', flat=True))
        
        updated_count = 0
        error_count = 0
        
        for question_id in question_ids:
            try:
                analytics_data = self.collect_question_analytics(question_id)
                
                # Update or create SurveyAnalytics record
                analytics, created = SurveyAnalytics.objects.get_or_create(
                    question_id=question_id,
                    defaults={
                        'total_responses': analytics_data['total_responses'],
                        'completion_rate': analytics_data['completion_rate'],
                        'skip_rate': analytics_data['skip_rate'],
                        'most_common_response': analytics_data['most_common_response'],
                        'response_distribution': analytics_data['response_distribution']
                    }
                )
                
                if not created:
                    analytics.total_responses = analytics_data['total_responses']
                    analytics.completion_rate = analytics_data['completion_rate']
                    analytics.skip_rate = analytics_data['skip_rate']
                    analytics.most_common_response = analytics_data['most_common_response']
                    analytics.response_distribution = analytics_data['response_distribution']
                    analytics.save()
                
                # Update cache
                self.update_analytics_cache(question_id)
                updated_count += 1
                
            except Exception as e:
                logger.error(f"Error updating analytics for question {question_id}: {str(e)}")
                error_count += 1
        
        return {
            'updated': updated_count,
            'errors': error_count,
            'total': len(question_ids)
        }
    
    def _calculate_response_distribution(self, responses, question) -> Dict[str, Any]:
        """
        Calculate response distribution based on question type.
        """
        if question.question_type in ['CHOICE', 'MULTI_CHOICE']:
            # For choice questions, count each option
            distribution = {}
            for response in responses:
                value = response.response_value
                if isinstance(value, list):
                    # Multi-choice
                    for choice in value:
                        distribution[str(choice)] = distribution.get(str(choice), 0) + 1
                else:
                    # Single choice
                    distribution[str(value)] = distribution.get(str(value), 0) + 1
            return distribution
        
        elif question.question_type == 'BOOLEAN':
            # For boolean questions
            true_count = responses.filter(response_value=True).count()
            false_count = responses.filter(response_value=False).count()
            return {'true': true_count, 'false': false_count}
        
        elif question.question_type in ['NUMBER', 'RANGE']:
            # For numeric questions, create ranges
            values = [r.response_value for r in responses if isinstance(r.response_value, (int, float))]
            if not values:
                return {}
            
            min_val, max_val = min(values), max(values)
            range_size = (max_val - min_val) / 5 if max_val > min_val else 1
            
            distribution = {}
            for i in range(5):
                range_start = min_val + (i * range_size)
                range_end = min_val + ((i + 1) * range_size)
                range_key = f"{range_start:.1f}-{range_end:.1f}"
                count = sum(1 for v in values if range_start <= v < range_end)
                distribution[range_key] = count
            
            return distribution
        
        else:
            # For text questions, just return count
            return {'total_responses': len(responses)}
    
    def _get_most_common_response(self, responses, question) -> Any:
        """
        Get the most common response for a question.
        """
        if question.question_type in ['CHOICE', 'BOOLEAN']:
            # For single-value responses
            response_counts = {}
            for response in responses:
                value = str(response.response_value)
                response_counts[value] = response_counts.get(value, 0) + 1
            
            if response_counts:
                return max(response_counts.items(), key=lambda x: x[1])[0]
        
        elif question.question_type == 'MULTI_CHOICE':
            # For multi-choice, find most common individual choice
            choice_counts = {}
            for response in responses:
                if isinstance(response.response_value, list):
                    for choice in response.response_value:
                        choice_counts[str(choice)] = choice_counts.get(str(choice), 0) + 1
            
            if choice_counts:
                return max(choice_counts.items(), key=lambda x: x[1])[0]
        
        elif question.question_type in ['NUMBER', 'RANGE']:
            # For numeric, return average
            values = [r.response_value for r in responses if isinstance(r.response_value, (int, float))]
            if values:
                return float(sum(values) / len(values))
        
        return None
    
    def _analyze_drop_off_points(self, template) -> List[Dict[str, Any]]:
        """
        Analyze where users typically drop off in the survey.
        """
        questions = SurveyQuestion.objects.filter(
            category=template.category,
            is_active=True
        ).order_by('display_order')
        
        drop_off_points = []
        
        for i, question in enumerate(questions):
            # Count sessions that reached this question
            sessions_reached = ComparisonSession.objects.filter(
                survey_responses__question=question
            ).distinct().count()
            
            # Count sessions that reached the next question (if exists)
            next_question = questions[i + 1] if i + 1 < len(questions) else None
            sessions_continued = 0
            
            if next_question:
                sessions_continued = ComparisonSession.objects.filter(
                    survey_responses__question=next_question
                ).distinct().count()
            
            drop_off_rate = 0
            if sessions_reached > 0:
                drop_off_rate = float(((sessions_reached - sessions_continued) / sessions_reached) * 100)
            
            drop_off_points.append({
                'question_id': question.id,
                'question_text': question.question_text[:50] + '...',
                'sessions_reached': sessions_reached,
                'sessions_continued': sessions_continued,
                'drop_off_rate': round(drop_off_rate, 2)
            })
        
        return drop_off_points
    
    def _empty_analytics(self) -> Dict[str, Any]:
        """
        Return empty analytics structure.
        """
        return {
            'total_responses': 0,
            'completion_rate': 0.0,
            'skip_rate': 0.0,
            'response_distribution': {},
            'most_common_response': None,
            'average_confidence': 0.0,
            'last_updated': timezone.now().isoformat()
        }


class ResponseTimeTracker:
    """
    Tracks response times for survey questions.
    """
    
    @staticmethod
    def start_question_timer(session_id: str, question_id: int) -> None:
        """
        Start timing for a question.
        """
        cache_key = f"question_timer_{session_id}_{question_id}"
        cache.set(cache_key, timezone.now().timestamp(), 3600)  # 1 hour timeout
    
    @staticmethod
    def end_question_timer(session_id: str, question_id: int) -> Optional[float]:
        """
        End timing for a question and return duration in seconds.
        """
        cache_key = f"question_timer_{session_id}_{question_id}"
        start_time = cache.get(cache_key)
        
        if start_time:
            duration = timezone.now().timestamp() - start_time
            cache.delete(cache_key)
            return duration
        
        return None
    
    @staticmethod
    def record_response_time(question_id: int, duration_seconds: float) -> None:
        """
        Record response time for analytics.
        """
        # Store in cache for batch processing
        cache_key = f"response_times_{question_id}"
        times = cache.get(cache_key, [])
        times.append(duration_seconds)
        cache.set(cache_key, times, 3600)
    
    @staticmethod
    def process_response_times() -> None:
        """
        Process cached response times and update analytics.
        """
        # This would be called by a periodic task
        # Implementation would batch process response times
        pass


class AnalyticsReportGenerator:
    """
    Generates analytics reports for admin dashboard.
    """
    
    def __init__(self):
        self.collector = SurveyAnalyticsCollector()
    
    def generate_category_report(self, category_slug: str) -> Dict[str, Any]:
        """
        Generate comprehensive analytics report for a category.
        """
        from policies.models import PolicyCategory
        
        try:
            category = PolicyCategory.objects.get(slug=category_slug)
            templates = SurveyTemplate.objects.filter(category=category, is_active=True)
            
            report = {
                'category': category.name,
                'category_slug': category_slug,
                'templates': [],
                'summary': {
                    'total_sessions': 0,
                    'completed_sessions': 0,
                    'overall_completion_rate': 0.0,
                    'total_questions': 0,
                    'avg_question_completion_rate': 0.0
                },
                'generated_at': timezone.now().isoformat()
            }
            
            total_sessions = 0
            completed_sessions = 0
            total_questions = 0
            total_completion_rate = 0.0
            
            for template in templates:
                template_analytics = self.collector.collect_template_analytics(template.id)
                report['templates'].append(template_analytics)
                
                total_sessions += template_analytics.get('total_sessions', 0)
                completed_sessions += template_analytics.get('completed_sessions', 0)
                total_questions += len(template_analytics.get('question_analytics', []))
                
                # Sum completion rates for averaging
                for q_analytics in template_analytics.get('question_analytics', []):
                    total_completion_rate += q_analytics.get('completion_rate', 0)
            
            # Calculate summary statistics
            report['summary']['total_sessions'] = total_sessions
            report['summary']['completed_sessions'] = completed_sessions
            report['summary']['overall_completion_rate'] = (
                (completed_sessions / max(total_sessions, 1)) * 100
            )
            report['summary']['total_questions'] = total_questions
            report['summary']['avg_question_completion_rate'] = (
                total_completion_rate / max(total_questions, 1)
            )
            
            return report
            
        except PolicyCategory.DoesNotExist:
            logger.error(f"Category {category_slug} not found")
            return {}
        except Exception as e:
            logger.error(f"Error generating category report for {category_slug}: {str(e)}")
            return {}
    
    def generate_performance_report(self, days: int = 30) -> Dict[str, Any]:
        """
        Generate performance report for the last N days.
        """
        end_date = timezone.now()
        start_date = end_date - timedelta(days=days)
        
        # Get sessions in date range
        sessions = ComparisonSession.objects.filter(
            created_at__gte=start_date,
            created_at__lte=end_date
        )
        
        # Calculate metrics
        total_sessions = sessions.count()
        completed_sessions = sessions.filter(survey_completed=True).count()
        
        # Daily breakdown
        daily_stats = []
        for i in range(days):
            day_start = start_date + timedelta(days=i)
            day_end = day_start + timedelta(days=1)
            
            day_sessions = sessions.filter(
                created_at__gte=day_start,
                created_at__lt=day_end
            )
            
            daily_stats.append({
                'date': day_start.date().isoformat(),
                'total_sessions': day_sessions.count(),
                'completed_sessions': day_sessions.filter(survey_completed=True).count(),
                'avg_completion_percentage': day_sessions.aggregate(
                    avg=Avg('survey_completion_percentage')
                )['avg'] or 0
            })
        
        return {
            'period': f"{start_date.date()} to {end_date.date()}",
            'summary': {
                'total_sessions': total_sessions,
                'completed_sessions': completed_sessions,
                'completion_rate': (completed_sessions / max(total_sessions, 1)) * 100,
                'avg_completion_percentage': sessions.aggregate(
                    avg=Avg('survey_completion_percentage')
                )['avg'] or 0
            },
            'daily_stats': daily_stats,
            'generated_at': timezone.now().isoformat()
        }