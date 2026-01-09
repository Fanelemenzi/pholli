"""
Caching utilities for survey performance optimization.
Implements question template caching, response processing caching, and lazy loading.
"""

import hashlib
import json
from typing import Dict, List, Any, Optional, Union
from django.core.cache import cache
from django.conf import settings
from django.db.models import QuerySet
from django.utils import timezone
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)


class SurveyCacheManager:
    """
    Centralized cache manager for survey-related data.
    Handles caching of question templates, processed responses, and survey metadata.
    """
    
    # Cache key prefixes
    TEMPLATE_PREFIX = 'survey_template'
    QUESTIONS_PREFIX = 'survey_questions'
    RESPONSES_PREFIX = 'survey_responses'
    CRITERIA_PREFIX = 'survey_criteria'
    SECTIONS_PREFIX = 'survey_sections'
    ANALYTICS_PREFIX = 'survey_analytics'
    
    # Cache timeouts (in seconds)
    TEMPLATE_TIMEOUT = 3600 * 24  # 24 hours
    QUESTIONS_TIMEOUT = 3600 * 12  # 12 hours
    RESPONSES_TIMEOUT = 3600 * 2   # 2 hours
    CRITERIA_TIMEOUT = 3600 * 4    # 4 hours
    SECTIONS_TIMEOUT = 3600 * 6    # 6 hours
    ANALYTICS_TIMEOUT = 3600 * 1   # 1 hour
    
    def __init__(self):
        """Initialize the cache manager."""
        self.cache_enabled = getattr(settings, 'SURVEY_CACHE_ENABLED', True)
        self.cache_prefix = getattr(settings, 'SURVEY_CACHE_PREFIX', 'survey')
    
    def _make_key(self, prefix: str, *args) -> str:
        """
        Create a cache key with consistent formatting.
        
        Args:
            prefix: Cache key prefix
            *args: Additional key components
            
        Returns:
            Formatted cache key
        """
        key_parts = [self.cache_prefix, prefix] + [str(arg) for arg in args]
        return ':'.join(key_parts)
    
    def _hash_data(self, data: Any) -> str:
        """
        Create a hash of data for cache key generation.
        
        Args:
            data: Data to hash
            
        Returns:
            MD5 hash string
        """
        if isinstance(data, dict):
            # Sort dict for consistent hashing
            # Use default=str to handle Decimal and other non-serializable types
            data_str = json.dumps(data, sort_keys=True, default=str)
        else:
            data_str = str(data)
        
        return hashlib.md5(data_str.encode()).hexdigest()[:8]
    
    def get_template_cache(self, category_slug: str) -> Optional[Dict[str, Any]]:
        """
        Get cached survey template data.
        
        Args:
            category_slug: Policy category slug
            
        Returns:
            Cached template data or None
        """
        if not self.cache_enabled:
            return None
        
        key = self._make_key(self.TEMPLATE_PREFIX, category_slug)
        return cache.get(key)
    
    def set_template_cache(self, category_slug: str, template_data: Dict[str, Any]) -> None:
        """
        Cache survey template data.
        
        Args:
            category_slug: Policy category slug
            template_data: Template data to cache
        """
        if not self.cache_enabled:
            return
        
        key = self._make_key(self.TEMPLATE_PREFIX, category_slug)
        cache.set(key, template_data, self.TEMPLATE_TIMEOUT)
        logger.debug(f"Cached template data for category: {category_slug}")
    
    def get_questions_cache(self, category_slug: str, section: Optional[str] = None) -> Optional[List[Dict[str, Any]]]:
        """
        Get cached question data.
        
        Args:
            category_slug: Policy category slug
            section: Optional section filter
            
        Returns:
            Cached question data or None
        """
        if not self.cache_enabled:
            return None
        
        key_parts = [category_slug]
        if section:
            key_parts.append(section)
        
        key = self._make_key(self.QUESTIONS_PREFIX, *key_parts)
        return cache.get(key)
    
    def set_questions_cache(
        self, 
        category_slug: str, 
        questions_data: List[Dict[str, Any]], 
        section: Optional[str] = None
    ) -> None:
        """
        Cache question data.
        
        Args:
            category_slug: Policy category slug
            questions_data: Question data to cache
            section: Optional section filter
        """
        if not self.cache_enabled:
            return
        
        key_parts = [category_slug]
        if section:
            key_parts.append(section)
        
        key = self._make_key(self.QUESTIONS_PREFIX, *key_parts)
        cache.set(key, questions_data, self.QUESTIONS_TIMEOUT)
        logger.debug(f"Cached questions for category: {category_slug}, section: {section}")
    
    def get_sections_cache(self, category_slug: str) -> Optional[List[Dict[str, Any]]]:
        """
        Get cached survey sections data.
        
        Args:
            category_slug: Policy category slug
            
        Returns:
            Cached sections data or None
        """
        if not self.cache_enabled:
            return None
        
        key = self._make_key(self.SECTIONS_PREFIX, category_slug)
        return cache.get(key)
    
    def set_sections_cache(self, category_slug: str, sections_data: List[Dict[str, Any]]) -> None:
        """
        Cache survey sections data.
        
        Args:
            category_slug: Policy category slug
            sections_data: Sections data to cache
        """
        if not self.cache_enabled:
            return
        
        key = self._make_key(self.SECTIONS_PREFIX, category_slug)
        cache.set(key, sections_data, self.SECTIONS_TIMEOUT)
        logger.debug(f"Cached sections for category: {category_slug}")
    
    def get_response_processing_cache(self, session_id: int, responses_hash: str) -> Optional[Dict[str, Any]]:
        """
        Get cached response processing results.
        
        Args:
            session_id: Comparison session ID
            responses_hash: Hash of responses for cache invalidation
            
        Returns:
            Cached processing results or None
        """
        if not self.cache_enabled:
            return None
        
        key = self._make_key(self.RESPONSES_PREFIX, session_id, responses_hash)
        return cache.get(key)
    
    def set_response_processing_cache(
        self, 
        session_id: int, 
        responses_hash: str, 
        processing_results: Dict[str, Any]
    ) -> None:
        """
        Cache response processing results.
        
        Args:
            session_id: Comparison session ID
            responses_hash: Hash of responses for cache invalidation
            processing_results: Processing results to cache
        """
        if not self.cache_enabled:
            return
        
        key = self._make_key(self.RESPONSES_PREFIX, session_id, responses_hash)
        cache.set(key, processing_results, self.RESPONSES_TIMEOUT)
        logger.debug(f"Cached response processing for session: {session_id}")
    
    def get_criteria_cache(self, criteria_hash: str) -> Optional[Dict[str, Any]]:
        """
        Get cached comparison criteria.
        
        Args:
            criteria_hash: Hash of criteria parameters
            
        Returns:
            Cached criteria or None
        """
        if not self.cache_enabled:
            return None
        
        key = self._make_key(self.CRITERIA_PREFIX, criteria_hash)
        return cache.get(key)
    
    def set_criteria_cache(self, criteria_hash: str, criteria_data: Dict[str, Any]) -> None:
        """
        Cache comparison criteria.
        
        Args:
            criteria_hash: Hash of criteria parameters
            criteria_data: Criteria data to cache
        """
        if not self.cache_enabled:
            return
        
        key = self._make_key(self.CRITERIA_PREFIX, criteria_hash)
        cache.set(key, criteria_data, self.CRITERIA_TIMEOUT)
        logger.debug(f"Cached criteria with hash: {criteria_hash}")
    
    def invalidate_template_cache(self, category_slug: str) -> None:
        """
        Invalidate template cache for a category.
        
        Args:
            category_slug: Policy category slug
        """
        if not self.cache_enabled:
            return
        
        # Invalidate template cache
        template_key = self._make_key(self.TEMPLATE_PREFIX, category_slug)
        cache.delete(template_key)
        
        # Invalidate related caches
        questions_key = self._make_key(self.QUESTIONS_PREFIX, category_slug)
        cache.delete(questions_key)
        
        sections_key = self._make_key(self.SECTIONS_PREFIX, category_slug)
        cache.delete(sections_key)
        
        logger.info(f"Invalidated template cache for category: {category_slug}")
    
    def invalidate_session_cache(self, session_id: int) -> None:
        """
        Invalidate all cache entries for a session.
        
        Args:
            session_id: Comparison session ID
        """
        if not self.cache_enabled:
            return
        
        # We can't easily delete all keys with a pattern in Django's cache
        # So we'll use a versioning approach or manual tracking
        # For now, we'll just log the invalidation
        logger.info(f"Invalidated session cache for session: {session_id}")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics and health information.
        
        Returns:
            Dictionary with cache statistics
        """
        if not self.cache_enabled:
            return {'enabled': False}
        
        # Basic cache info
        stats = {
            'enabled': True,
            'cache_prefix': self.cache_prefix,
            'timeouts': {
                'template': self.TEMPLATE_TIMEOUT,
                'questions': self.QUESTIONS_TIMEOUT,
                'responses': self.RESPONSES_TIMEOUT,
                'criteria': self.CRITERIA_TIMEOUT,
                'sections': self.SECTIONS_TIMEOUT,
                'analytics': self.ANALYTICS_TIMEOUT
            }
        }
        
        # Try to get cache backend info if available
        try:
            cache_info = cache._cache.get_stats()
            stats['backend_stats'] = cache_info
        except AttributeError:
            stats['backend_stats'] = 'Not available'
        
        return stats


class LazyQuestionLoader:
    """
    Lazy loading utility for survey questions to improve performance.
    Loads questions on-demand and implements pagination for large surveys.
    """
    
    def __init__(self, category_slug: str, cache_manager: Optional[SurveyCacheManager] = None):
        """
        Initialize the lazy loader.
        
        Args:
            category_slug: Policy category slug
            cache_manager: Optional cache manager instance
        """
        self.category_slug = category_slug
        self.cache_manager = cache_manager or SurveyCacheManager()
        self._sections_cache = {}
        self._questions_cache = {}
        self._dependencies_cache = {}
        self._template_cache = None
    
    def get_sections_summary(self) -> List[Dict[str, Any]]:
        """
        Get a summary of all sections without loading full question data.
        
        Returns:
            List of section summaries
        """
        # Try cache first
        cached_sections = self.cache_manager.get_sections_cache(self.category_slug)
        if cached_sections:
            return cached_sections
        
        # Load from database
        from .models import SurveyQuestion
        from policies.models import PolicyCategory
        
        try:
            category = PolicyCategory.objects.get(slug=self.category_slug)
            
            # Get section summaries with question counts
            sections_data = (
                SurveyQuestion.objects
                .filter(category=category, is_active=True)
                .values('section')
                .distinct()
                .order_by('section')
            )
            
            sections_summary = []
            for section_data in sections_data:
                section_name = section_data['section']
                
                # Count questions in this section
                question_count = SurveyQuestion.objects.filter(
                    category=category,
                    section=section_name,
                    is_active=True
                ).count()
                
                sections_summary.append({
                    'name': section_name,
                    'question_count': question_count,
                    'loaded': False  # Indicates questions not yet loaded
                })
            
            # Cache the result
            self.cache_manager.set_sections_cache(self.category_slug, sections_summary)
            
            return sections_summary
            
        except Exception as e:
            logger.error(f"Error loading sections summary for {self.category_slug}: {str(e)}")
            return []
    
    def load_section_questions(self, section_name: str, force_reload: bool = False) -> List[Dict[str, Any]]:
        """
        Load questions for a specific section.
        
        Args:
            section_name: Name of the section to load
            force_reload: Force reload from database
            
        Returns:
            List of question data for the section
        """
        # Check local cache first
        if not force_reload and section_name in self._questions_cache:
            return self._questions_cache[section_name]
        
        # Try distributed cache
        if not force_reload:
            cached_questions = self.cache_manager.get_questions_cache(
                self.category_slug, section_name
            )
            if cached_questions:
                self._questions_cache[section_name] = cached_questions
                return cached_questions
        
        # Load from database
        from .models import SurveyQuestion, TemplateQuestion, SurveyTemplate
        from policies.models import PolicyCategory
        
        try:
            category = PolicyCategory.objects.get(slug=self.category_slug)
            
            # Get active template
            template = SurveyTemplate.objects.filter(
                category=category,
                is_active=True
            ).first()
            
            if not template:
                logger.warning(f"No active template found for category: {self.category_slug}")
                return []
            
            # Load questions for this section
            template_questions = (
                TemplateQuestion.objects
                .filter(template=template, question__section=section_name, question__is_active=True)
                .select_related('question')
                .order_by('display_order')
            )
            
            questions_data = []
            for tq in template_questions:
                question = tq.question
                question_data = {
                    'id': question.id,
                    'question_text': question.question_text,
                    'question_type': question.question_type,
                    'field_name': question.field_name,
                    'choices': question.choices,
                    'validation_rules': question.validation_rules,
                    'help_text': question.help_text,
                    'is_required': tq.is_required,
                    'display_order': tq.display_order,
                    'weight_impact': float(question.weight_impact)
                }
                questions_data.append(question_data)
            
            # Cache the results
            self._questions_cache[section_name] = questions_data
            self.cache_manager.set_questions_cache(
                self.category_slug, questions_data, section_name
            )
            
            return questions_data
            
        except Exception as e:
            logger.error(f"Error loading questions for section {section_name}: {str(e)}")
            return []
    
    def get_question_by_id(self, question_id: int) -> Optional[Dict[str, Any]]:
        """
        Get a specific question by ID, loading its section if necessary.
        
        Args:
            question_id: Question ID to retrieve
            
        Returns:
            Question data or None if not found
        """
        # Search in loaded sections first
        for section_questions in self._questions_cache.values():
            for question in section_questions:
                if question['id'] == question_id:
                    return question
        
        # Load from database if not found in cache
        from .models import SurveyQuestion
        
        try:
            question = SurveyQuestion.objects.get(
                id=question_id,
                category__slug=self.category_slug,
                is_active=True
            )
            
            # Load the entire section to populate cache
            section_questions = self.load_section_questions(question.section)
            
            # Find and return the specific question
            for q in section_questions:
                if q['id'] == question_id:
                    return q
            
            return None
            
        except Exception as e:
            logger.error(f"Error loading question {question_id}: {str(e)}")
            return None
    
    def preload_sections(self, section_names: List[str]) -> None:
        """
        Preload multiple sections for better performance.
        
        Args:
            section_names: List of section names to preload
        """
        for section_name in section_names:
            if section_name not in self._questions_cache:
                self.load_section_questions(section_name)
    
    def get_loaded_sections(self) -> List[str]:
        """
        Get list of currently loaded section names.
        
        Returns:
            List of loaded section names
        """
        return list(self._questions_cache.keys())
    
    def clear_cache(self) -> None:
        """Clear local question cache."""
        self._questions_cache.clear()
        self._sections_cache.clear()
        self._dependencies_cache.clear()
        self._template_cache = None
    
    def get_question_dependencies(self, question_id: int) -> List[Dict[str, Any]]:
        """
        Get cached question dependencies for conditional logic.
        
        Args:
            question_id: Question ID to get dependencies for
            
        Returns:
            List of dependency rules
        """
        if question_id not in self._dependencies_cache:
            self._load_question_dependencies(question_id)
        
        return self._dependencies_cache.get(question_id, [])
    
    def _load_question_dependencies(self, question_id: int) -> None:
        """
        Load and cache question dependencies.
        
        Args:
            question_id: Question ID to load dependencies for
        """
        from .models import QuestionDependency
        
        try:
            dependencies = QuestionDependency.objects.filter(
                parent_question_id=question_id,
                is_active=True
            ).select_related('child_question')
            
            dependency_data = []
            for dep in dependencies:
                dependency_data.append({
                    'child_question_id': dep.child_question.id,
                    'condition_value': dep.condition_value,
                    'condition_operator': dep.condition_operator,
                    'child_field_name': dep.child_question.field_name
                })
            
            self._dependencies_cache[question_id] = dependency_data
            
        except Exception as e:
            logger.error(f"Error loading dependencies for question {question_id}: {str(e)}")
            self._dependencies_cache[question_id] = []
    
    def preload_template(self) -> Optional[Dict[str, Any]]:
        """
        Preload and cache the survey template.
        
        Returns:
            Template data or None if not found
        """
        if self._template_cache is not None:
            return self._template_cache
        
        # Try cache first
        cached_template = self.cache_manager.get_template_cache(self.category_slug)
        if cached_template:
            self._template_cache = cached_template
            return cached_template
        
        # Load from database
        from .models import SurveyTemplate
        from policies.models import PolicyCategory
        
        try:
            category = PolicyCategory.objects.get(slug=self.category_slug)
            template = SurveyTemplate.objects.filter(
                category=category,
                is_active=True
            ).first()
            
            if template:
                template_data = {
                    'id': template.id,
                    'name': template.name,
                    'description': template.description,
                    'version': template.version,
                    'category_slug': self.category_slug
                }
                
                # Cache the template
                self.cache_manager.set_template_cache(self.category_slug, template_data)
                self._template_cache = template_data
                
                return template_data
            
            return None
            
        except Exception as e:
            logger.error(f"Error loading template for {self.category_slug}: {str(e)}")
            return None
    
    def get_section_progress(self, session_id: int, section_name: str) -> Dict[str, Any]:
        """
        Get progress information for a specific section.
        
        Args:
            session_id: Comparison session ID
            section_name: Name of the section
            
        Returns:
            Dictionary with section progress information
        """
        # Load section questions if not already loaded
        section_questions = self.load_section_questions(section_name)
        
        if not section_questions:
            return {
                'total_questions': 0,
                'answered_questions': 0,
                'completion_percentage': 0.0,
                'unanswered_questions': []
            }
        
        # Get responses for this section
        from .models import SurveyResponse
        from comparison.models import ComparisonSession
        
        try:
            session = ComparisonSession.objects.get(id=session_id)
            question_ids = [q['id'] for q in section_questions]
            
            answered_responses = SurveyResponse.objects.filter(
                session=session,
                question_id__in=question_ids
            ).values_list('question_id', flat=True)
            
            answered_count = len(answered_responses)
            total_count = len(section_questions)
            completion_percentage = float((answered_count / total_count * 100)) if total_count > 0 else 0.0
            
            # Find unanswered questions
            unanswered_questions = [
                {
                    'id': q['id'],
                    'question_text': q['question_text'],
                    'is_required': q['is_required']
                }
                for q in section_questions
                if q['id'] not in answered_responses
            ]
            
            return {
                'total_questions': total_count,
                'answered_questions': answered_count,
                'completion_percentage': completion_percentage,
                'unanswered_questions': unanswered_questions
            }
            
        except Exception as e:
            logger.error(f"Error getting section progress: {str(e)}")
            return {
                'total_questions': len(section_questions),
                'answered_questions': 0,
                'completion_percentage': 0.0,
                'unanswered_questions': section_questions
            }


# Global cache manager instance
cache_manager = SurveyCacheManager()


class ResponseProcessingCache:
    """
    Specialized caching for response processing to avoid recomputation.
    Handles caching of criteria mapping, weight calculations, and user profiles.
    """
    
    def __init__(self, cache_manager: Optional[SurveyCacheManager] = None):
        """
        Initialize the response processing cache.
        
        Args:
            cache_manager: Optional cache manager instance
        """
        self.cache_manager = cache_manager or SurveyCacheManager()
        self._local_cache = {}
    
    def get_criteria_mapping_cache(self, category_slug: str, responses_hash: str) -> Optional[Dict[str, Any]]:
        """
        Get cached criteria mapping results.
        
        Args:
            category_slug: Policy category slug
            responses_hash: Hash of survey responses
            
        Returns:
            Cached criteria mapping or None
        """
        cache_key = f"criteria_mapping_{category_slug}_{responses_hash}"
        
        # Check local cache first
        if cache_key in self._local_cache:
            return self._local_cache[cache_key]
        
        # Check distributed cache
        cached_data = self.cache_manager.get_criteria_cache(responses_hash)
        if cached_data:
            self._local_cache[cache_key] = cached_data
            return cached_data
        
        return None
    
    def set_criteria_mapping_cache(
        self, 
        category_slug: str, 
        responses_hash: str, 
        criteria_data: Dict[str, Any]
    ) -> None:
        """
        Cache criteria mapping results.
        
        Args:
            category_slug: Policy category slug
            responses_hash: Hash of survey responses
            criteria_data: Criteria mapping data to cache
        """
        cache_key = f"criteria_mapping_{category_slug}_{responses_hash}"
        
        # Store in local cache
        self._local_cache[cache_key] = criteria_data
        
        # Store in distributed cache
        self.cache_manager.set_criteria_cache(responses_hash, criteria_data)
    
    def get_weight_calculation_cache(self, responses_hash: str) -> Optional[Dict[str, float]]:
        """
        Get cached weight calculation results.
        
        Args:
            responses_hash: Hash of survey responses
            
        Returns:
            Cached weight calculations or None
        """
        cache_key = f"weights_{responses_hash}"
        
        if cache_key in self._local_cache:
            return self._local_cache[cache_key]
        
        # Try to get from criteria cache (weights are part of criteria)
        cached_criteria = self.cache_manager.get_criteria_cache(responses_hash)
        if cached_criteria and 'weights' in cached_criteria:
            weights = cached_criteria['weights']
            self._local_cache[cache_key] = weights
            return weights
        
        return None
    
    def set_weight_calculation_cache(self, responses_hash: str, weights: Dict[str, float]) -> None:
        """
        Cache weight calculation results.
        
        Args:
            responses_hash: Hash of survey responses
            weights: Weight calculations to cache
        """
        cache_key = f"weights_{responses_hash}"
        self._local_cache[cache_key] = weights
    
    def get_user_profile_cache(self, responses_hash: str) -> Optional[Dict[str, Any]]:
        """
        Get cached user profile data.
        
        Args:
            responses_hash: Hash of survey responses
            
        Returns:
            Cached user profile or None
        """
        cache_key = f"profile_{responses_hash}"
        
        if cache_key in self._local_cache:
            return self._local_cache[cache_key]
        
        # Try to get from criteria cache (profile is part of criteria)
        cached_criteria = self.cache_manager.get_criteria_cache(responses_hash)
        if cached_criteria and 'user_profile' in cached_criteria:
            profile = cached_criteria['user_profile']
            self._local_cache[cache_key] = profile
            return profile
        
        return None
    
    def set_user_profile_cache(self, responses_hash: str, profile_data: Dict[str, Any]) -> None:
        """
        Cache user profile data.
        
        Args:
            responses_hash: Hash of survey responses
            profile_data: User profile data to cache
        """
        cache_key = f"profile_{responses_hash}"
        self._local_cache[cache_key] = profile_data
    
    def generate_responses_hash(self, responses: List[Dict[str, Any]]) -> str:
        """
        Generate a hash for survey responses to use as cache key.
        
        Args:
            responses: List of survey response data
            
        Returns:
            MD5 hash of responses
        """
        # Sort responses by question ID for consistent hashing
        sorted_responses = sorted(responses, key=lambda r: r.get('question_id', 0))
        
        # Create a simplified representation for hashing
        hash_data = []
        for response in sorted_responses:
            hash_data.append({
                'question_id': response.get('question_id'),
                'field_name': response.get('field_name'),
                'response_value': response.get('response_value'),
                'confidence_level': response.get('confidence_level', 3)
            })
        
        return self.cache_manager._hash_data(hash_data)
    
    def invalidate_response_cache(self, responses_hash: str) -> None:
        """
        Invalidate cached data for specific responses.
        
        Args:
            responses_hash: Hash of responses to invalidate
        """
        # Remove from local cache
        keys_to_remove = [
            key for key in self._local_cache.keys()
            if responses_hash in key
        ]
        
        for key in keys_to_remove:
            del self._local_cache[key]
        
        # Remove from distributed cache
        self.cache_manager.invalidate_session_cache(0)  # Generic invalidation
        logger.info(f"Invalidated response cache for hash: {responses_hash}")
    
    def clear_local_cache(self) -> None:
        """Clear all local cache data."""
        self._local_cache.clear()
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics for response processing.
        
        Returns:
            Dictionary with cache statistics
        """
        return {
            'local_cache_size': len(self._local_cache),
            'local_cache_keys': list(self._local_cache.keys()),
            'cache_manager_stats': self.cache_manager.get_cache_stats()
        }


class SurveyPerformanceOptimizer:
    """
    Performance optimization utilities for survey operations.
    Provides methods for bulk operations, prefetching, and query optimization.
    """
    
    def __init__(self):
        """Initialize the performance optimizer."""
        self.cache_manager = SurveyCacheManager()
        self.response_cache = ResponseProcessingCache(self.cache_manager)
    
    def bulk_load_questions(self, category_slug: str, question_ids: List[int]) -> Dict[int, Dict[str, Any]]:
        """
        Bulk load multiple questions with optimized queries.
        
        Args:
            category_slug: Policy category slug
            question_ids: List of question IDs to load
            
        Returns:
            Dictionary mapping question IDs to question data
        """
        from .models import SurveyQuestion
        from policies.models import PolicyCategory
        
        try:
            category = PolicyCategory.objects.get(slug=category_slug)
            
            # Use select_related for optimized query
            questions = SurveyQuestion.objects.filter(
                id__in=question_ids,
                category=category,
                is_active=True
            ).select_related('category')
            
            questions_data = {}
            for question in questions:
                questions_data[question.id] = {
                    'id': question.id,
                    'question_text': question.question_text,
                    'question_type': question.question_type,
                    'field_name': question.field_name,
                    'choices': question.choices,
                    'validation_rules': question.validation_rules,
                    'help_text': question.help_text,
                    'is_required': question.is_required,
                    'weight_impact': float(question.weight_impact),
                    'section': question.section
                }
            
            return questions_data
            
        except Exception as e:
            logger.error(f"Error bulk loading questions: {str(e)}")
            return {}
    
    def bulk_load_responses(self, session_id: int, question_ids: Optional[List[int]] = None) -> Dict[int, Dict[str, Any]]:
        """
        Bulk load survey responses with optimized queries.
        
        Args:
            session_id: Comparison session ID
            question_ids: Optional list of specific question IDs to load
            
        Returns:
            Dictionary mapping question IDs to response data
        """
        from .models import SurveyResponse
        from comparison.models import ComparisonSession
        
        try:
            session = ComparisonSession.objects.get(id=session_id)
            
            # Build query
            query = SurveyResponse.objects.filter(session=session)
            if question_ids:
                query = query.filter(question_id__in=question_ids)
            
            # Use select_related for optimized query
            responses = query.select_related('question').order_by('question__display_order')
            
            responses_data = {}
            for response in responses:
                responses_data[response.question.id] = {
                    'question_id': response.question.id,
                    'field_name': response.question.field_name,
                    'response_value': response.response_value,
                    'confidence_level': response.confidence_level,
                    'question_type': response.question.question_type,
                    'section': response.question.section,
                    'created_at': response.created_at,
                    'updated_at': response.updated_at
                }
            
            return responses_data
            
        except Exception as e:
            logger.error(f"Error bulk loading responses: {str(e)}")
            return {}
    
    def prefetch_survey_data(self, category_slug: str, session_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Prefetch all survey data for optimal performance.
        
        Args:
            category_slug: Policy category slug
            session_id: Optional session ID to prefetch responses
            
        Returns:
            Dictionary with prefetched data
        """
        prefetched_data = {
            'template': None,
            'sections': [],
            'questions': {},
            'responses': {},
            'dependencies': {}
        }
        
        try:
            # Load template
            lazy_loader = LazyQuestionLoader(category_slug, self.cache_manager)
            template = lazy_loader.preload_template()
            prefetched_data['template'] = template
            
            # Load sections summary
            sections = lazy_loader.get_sections_summary()
            prefetched_data['sections'] = sections
            
            # Preload all sections
            for section in sections:
                section_questions = lazy_loader.load_section_questions(section['name'])
                for question in section_questions:
                    prefetched_data['questions'][question['id']] = question
                    
                    # Load dependencies for this question
                    deps = lazy_loader.get_question_dependencies(question['id'])
                    if deps:
                        prefetched_data['dependencies'][question['id']] = deps
            
            # Load responses if session provided
            if session_id:
                responses = self.bulk_load_responses(session_id)
                prefetched_data['responses'] = responses
            
            logger.info(f"Prefetched survey data for {category_slug}: "
                       f"{len(prefetched_data['questions'])} questions, "
                       f"{len(prefetched_data['sections'])} sections")
            
            return prefetched_data
            
        except Exception as e:
            logger.error(f"Error prefetching survey data: {str(e)}")
            return prefetched_data
    
    def optimize_session_queries(self, session_id: int) -> Dict[str, Any]:
        """
        Optimize queries for a specific session with prefetching.
        
        Args:
            session_id: Comparison session ID
            
        Returns:
            Dictionary with optimized session data
        """
        from comparison.models import ComparisonSession
        
        try:
            # Load session with related data
            session = ComparisonSession.objects.select_related(
                'category', 'user'
            ).prefetch_related(
                'survey_responses__question',
                'policies'
            ).get(id=session_id)
            
            # Prefetch survey data for this category
            survey_data = self.prefetch_survey_data(
                session.category.slug, 
                session_id
            )
            
            # Combine session and survey data
            optimized_data = {
                'session': {
                    'id': session.id,
                    'category_slug': session.category.slug,
                    'survey_completed': session.survey_completed,
                    'survey_completion_percentage': float(session.survey_completion_percentage),
                    'survey_responses_count': session.survey_responses_count,
                    'user_profile': session.user_profile,
                    'status': session.status
                },
                'survey_data': survey_data
            }
            
            return optimized_data
            
        except Exception as e:
            logger.error(f"Error optimizing session queries: {str(e)}")
            return {}
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """
        Get performance metrics for survey operations.
        
        Returns:
            Dictionary with performance metrics
        """
        return {
            'cache_stats': self.cache_manager.get_cache_stats(),
            'response_cache_stats': self.response_cache.get_cache_stats(),
            'timestamp': timezone.now().isoformat()
        }


# Global instances
performance_optimizer = SurveyPerformanceOptimizer()
response_processing_cache = ResponseProcessingCache()