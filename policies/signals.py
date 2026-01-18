"""
Signal handlers for maintaining system integration and consistency.
"""

from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver
from django.core.cache import cache
from django.utils import timezone
import logging

from .models import BasePolicy, PolicyFeatures, AdditionalFeatures
from .integration import CrossModuleValidator, SystemIntegrationManager
from simple_surveys.models import SimpleSurvey, SimpleSurveyQuestion
from comparison.models import FeatureComparisonResult

logger = logging.getLogger(__name__)


@receiver(post_save, sender=PolicyFeatures)
def validate_policy_features_on_save(sender, instance, created, **kwargs):
    """
    Validate policy features when they are saved.
    Ensures consistency with feature definitions.
    """
    try:
        # Validate the policy features
        errors = CrossModuleValidator.validate_policy_features(instance.policy)
        
        if errors:
            logger.warning(
                f"Policy features validation issues for {instance.policy.name}: {errors}"
            )
            
            # Cache validation errors for admin interface
            cache_key = f"policy_validation_errors_{instance.policy.id}"
            cache.set(cache_key, errors, timeout=3600)  # 1 hour
        else:
            # Clear any cached validation errors
            cache_key = f"policy_validation_errors_{instance.policy.id}"
            cache.delete(cache_key)
            
            if created:
                logger.info(f"Policy features created and validated for {instance.policy.name}")
            else:
                logger.info(f"Policy features updated and validated for {instance.policy.name}")
    
    except Exception as e:
        logger.error(f"Error validating policy features for {instance.policy.name}: {str(e)}")


@receiver(post_save, sender=SimpleSurvey)
def validate_survey_on_save(sender, instance, created, **kwargs):
    """
    Validate survey completeness when it is saved.
    Ensures all required fields for the insurance type are present.
    """
    try:
        # Validate survey completeness
        errors = CrossModuleValidator.validate_survey_completeness(instance)
        
        if errors:
            logger.warning(
                f"Survey validation issues for survey {instance.id}: {errors}"
            )
            
            # Cache validation errors
            cache_key = f"survey_validation_errors_{instance.id}"
            cache.set(cache_key, errors, timeout=3600)  # 1 hour
        else:
            # Clear any cached validation errors
            cache_key = f"survey_validation_errors_{instance.id}"
            cache.delete(cache_key)
            
            if created:
                logger.info(f"Survey created and validated: {instance.id}")
            else:
                logger.info(f"Survey updated and validated: {instance.id}")
    
    except Exception as e:
        logger.error(f"Error validating survey {instance.id}: {str(e)}")


@receiver(post_save, sender=FeatureComparisonResult)
def validate_comparison_result_on_save(sender, instance, created, **kwargs):
    """
    Validate comparison results when they are saved.
    Ensures consistency between survey, policy, and comparison data.
    """
    try:
        # Validate comparison result consistency
        errors = CrossModuleValidator.validate_comparison_consistency(instance)
        
        if errors:
            logger.warning(
                f"Comparison result validation issues for result {instance.id}: {errors}"
            )
            
            # Cache validation errors
            cache_key = f"comparison_validation_errors_{instance.id}"
            cache.set(cache_key, errors, timeout=3600)  # 1 hour
        else:
            # Clear any cached validation errors
            cache_key = f"comparison_validation_errors_{instance.id}"
            cache.delete(cache_key)
            
            if created:
                logger.info(f"Comparison result created and validated: {instance.id}")
            else:
                logger.info(f"Comparison result updated and validated: {instance.id}")
    
    except Exception as e:
        logger.error(f"Error validating comparison result {instance.id}: {str(e)}")


@receiver(pre_save, sender=PolicyFeatures)
def ensure_insurance_type_consistency(sender, instance, **kwargs):
    """
    Ensure insurance type is consistent with policy category.
    """
    try:
        policy = instance.policy
        
        # Map policy categories to insurance types
        category_mapping = {
            'health': 'HEALTH',
            'funeral': 'FUNERAL',
            'life': 'FUNERAL',  # Life insurance often includes funeral benefits
        }
        
        if policy.category and policy.category.slug:
            expected_type = category_mapping.get(policy.category.slug.lower())
            
            if expected_type and instance.insurance_type != expected_type:
                logger.warning(
                    f"Insurance type mismatch for policy {policy.name}: "
                    f"category is {policy.category.slug}, but insurance_type is {instance.insurance_type}"
                )
                
                # Auto-correct if possible
                if not instance.pk:  # Only auto-correct on creation
                    instance.insurance_type = expected_type
                    logger.info(f"Auto-corrected insurance type to {expected_type} for policy {policy.name}")
    
    except Exception as e:
        logger.error(f"Error checking insurance type consistency: {str(e)}")


@receiver(post_delete, sender=PolicyFeatures)
def cleanup_related_data_on_policy_features_delete(sender, instance, **kwargs):
    """
    Clean up related data when policy features are deleted.
    """
    try:
        policy_id = instance.policy.id
        
        # Clear cached validation errors
        cache_key = f"policy_validation_errors_{policy_id}"
        cache.delete(cache_key)
        
        # Log the deletion
        logger.info(f"Policy features deleted for policy {instance.policy.name}")
        
        # Optionally, mark related comparison results as outdated
        FeatureComparisonResult.objects.filter(policy_id=policy_id).update(
            match_explanation="Policy features have been deleted - results may be outdated"
        )
    
    except Exception as e:
        logger.error(f"Error cleaning up after policy features deletion: {str(e)}")


@receiver(post_delete, sender=SimpleSurvey)
def cleanup_related_data_on_survey_delete(sender, instance, **kwargs):
    """
    Clean up related data when a survey is deleted.
    """
    try:
        survey_id = instance.id
        
        # Clear cached validation errors
        cache_key = f"survey_validation_errors_{survey_id}"
        cache.delete(cache_key)
        
        # Delete related comparison results
        deleted_count = FeatureComparisonResult.objects.filter(survey_id=survey_id).delete()[0]
        
        if deleted_count > 0:
            logger.info(f"Deleted {deleted_count} comparison results for survey {survey_id}")
        
        logger.info(f"Survey {survey_id} deleted and related data cleaned up")
    
    except Exception as e:
        logger.error(f"Error cleaning up after survey deletion: {str(e)}")


@receiver(post_save, sender=SimpleSurveyQuestion)
def invalidate_survey_cache_on_question_change(sender, instance, created, **kwargs):
    """
    Invalidate survey-related caches when survey questions change.
    """
    try:
        category = instance.category
        
        # Clear survey form cache for this category
        cache_key = f"survey_questions_{category}"
        cache.delete(cache_key)
        
        # Clear validation cache for surveys of this category
        cache_pattern = f"survey_validation_errors_*"
        # Note: Django cache doesn't support pattern deletion by default
        # This would need a custom cache backend or manual tracking
        
        if created:
            logger.info(f"Survey question created for {category}: {instance.question_text[:50]}")
        else:
            logger.info(f"Survey question updated for {category}: {instance.question_text[:50]}")
    
    except Exception as e:
        logger.error(f"Error handling survey question change: {str(e)}")


# System health monitoring signals
@receiver(post_save, sender=BasePolicy)
def monitor_system_health_on_policy_change(sender, instance, created, **kwargs):
    """
    Monitor system health when policies are created or updated.
    """
    try:
        # Update system health metrics
        cache_key = "system_health_last_check"
        cache.set(cache_key, timezone.now().isoformat(), timeout=86400)  # 24 hours
        
        # Increment policy change counter
        counter_key = "policy_changes_today"
        current_count = cache.get(counter_key, 0)
        cache.set(counter_key, current_count + 1, timeout=86400)  # 24 hours
        
        if created:
            logger.info(f"New policy created: {instance.name}")
        else:
            logger.info(f"Policy updated: {instance.name}")
    
    except Exception as e:
        logger.error(f"Error monitoring system health: {str(e)}")


def get_cached_validation_errors(model_type, object_id):
    """
    Helper function to get cached validation errors for an object.
    
    Args:
        model_type: 'policy', 'survey', or 'comparison'
        object_id: ID of the object
    
    Returns:
        List of validation errors or empty list
    """
    cache_key = f"{model_type}_validation_errors_{object_id}"
    return cache.get(cache_key, [])


def clear_all_validation_caches():
    """
    Helper function to clear all validation error caches.
    Useful after system-wide fixes or updates.
    """
    try:
        # This is a simplified approach - in production you might want
        # to track cache keys more systematically
        cache.clear()
        logger.info("All validation caches cleared")
    except Exception as e:
        logger.error(f"Error clearing validation caches: {str(e)}")


def get_system_health_metrics():
    """
    Get basic system health metrics from cache.
    
    Returns:
        Dictionary with health metrics
    """
    try:
        return {
            'last_check': cache.get('system_health_last_check'),
            'policy_changes_today': cache.get('policy_changes_today', 0),
            'cache_status': 'active'
        }
    except Exception as e:
        logger.error(f"Error getting system health metrics: {str(e)}")
        return {
            'cache_status': 'error',
            'error': str(e)
        }