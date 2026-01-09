from django.db import models
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from policies.models import BasePolicy, PolicyCategory

User = get_user_model()


class ComparisonSession(models.Model):
    """
    Model for tracking user comparison sessions.
    Stores user preferences and selected policies for comparison.
    """
    
    class Status(models.TextChoices):
        ACTIVE = 'ACTIVE', _('Active')
        COMPLETED = 'COMPLETED', _('Completed')
        EXPIRED = 'EXPIRED', _('Expired')
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='comparison_sessions',
        null=True,
        blank=True,
        help_text=_("User who created this comparison (null for anonymous)")
    )
    
    session_key = models.CharField(
        max_length=100,
        unique=True,
        help_text=_("Unique session identifier for anonymous users")
    )
    
    category = models.ForeignKey(
        PolicyCategory,
        on_delete=models.CASCADE,
        related_name='comparisons',
        help_text=_("Policy category being compared")
    )
    
    policies = models.ManyToManyField(
        BasePolicy,
        related_name='comparisons',
        help_text=_("Policies included in this comparison")
    )
    
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
        help_text=_("Status of the comparison session")
    )
    
    # User Criteria/Preferences
    criteria = models.JSONField(
        default=dict,
        help_text=_("Comparison criteria and user preferences")
    )
    
    # Results
    best_match_policy = models.ForeignKey(
        BasePolicy,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='best_match_comparisons',
        help_text=_("Policy determined as best match")
    )
    
    match_scores = models.JSONField(
        default=dict,
        blank=True,
        help_text=_("Match scores for each policy")
    )
    
    # Survey-related fields
    survey_completed = models.BooleanField(
        default=False,
        help_text=_("Whether the survey has been completed")
    )
    
    survey_completion_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0.00,
        help_text=_("Percentage of survey completion")
    )
    
    survey_responses_count = models.PositiveIntegerField(
        default=0,
        help_text=_("Number of survey responses submitted")
    )
    
    user_profile = models.JSONField(
        default=dict,
        blank=True,
        help_text=_("Processed user profile from survey responses")
    )
    
    # Fallback mode fields
    fallback_mode = models.BooleanField(
        default=False,
        help_text=_("Whether this session is using fallback comparison")
    )
    
    fallback_type = models.CharField(
        max_length=50,
        blank=True,
        help_text=_("Type of fallback used (basic, enhanced_basic, partial_personalized, etc.)")
    )
    
    fallback_reason = models.TextField(
        blank=True,
        help_text=_("Reason why fallback was triggered")
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    expires_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_("When this session expires")
    )
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = _("Comparison Session")
        verbose_name_plural = _("Comparison Sessions")
        indexes = [
            models.Index(fields=['session_key']),
            models.Index(fields=['user', 'status']),
            models.Index(fields=['category', 'status']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        user_str = self.user.username if self.user else 'Anonymous'
        return f"Comparison by {user_str} - {self.category.name}"
    
    def update_survey_progress(self, responses_count=None, completion_percentage=None):
        """
        Update survey progress tracking fields.
        
        Args:
            responses_count (int, optional): Number of survey responses submitted
            completion_percentage (float, optional): Percentage of survey completion (0-100)
        """
        if responses_count is not None:
            self.survey_responses_count = responses_count
        
        if completion_percentage is not None:
            self.survey_completion_percentage = min(100.00, max(0.00, completion_percentage))
            # Mark survey as completed if 100%
            if self.survey_completion_percentage >= 100.00:
                self.survey_completed = True
        
        self.save(update_fields=['survey_responses_count', 'survey_completion_percentage', 'survey_completed', 'updated_at'])
    
    def mark_survey_completed(self, user_profile_data=None):
        """
        Mark the survey as completed and optionally update user profile.
        
        Args:
            user_profile_data (dict, optional): Processed user profile data from survey responses
        """
        self.survey_completed = True
        self.survey_completion_percentage = 100.00
        
        if user_profile_data:
            self.user_profile = user_profile_data
        
        self.save(update_fields=['survey_completed', 'survey_completion_percentage', 'user_profile', 'updated_at'])
    
    def reset_survey_data(self):
        """
        Reset all survey-related data for this session.
        Useful when user wants to restart the survey.
        """
        self.survey_completed = False
        self.survey_completion_percentage = 0.00
        self.survey_responses_count = 0
        self.user_profile = {}
        
        self.save(update_fields=['survey_completed', 'survey_completion_percentage', 'survey_responses_count', 'user_profile', 'updated_at'])
    
    def has_survey_data(self):
        """
        Check if this session has any survey data.
        
        Returns:
            bool: True if session has survey responses or profile data
        """
        return self.survey_responses_count > 0 or bool(self.user_profile)
    
    def get_survey_status(self):
        """
        Get a comprehensive survey status for this session.
        
        Returns:
            dict: Dictionary containing survey status information
        """
        return {
            'completed': self.survey_completed,
            'completion_percentage': float(self.survey_completion_percentage),
            'responses_count': self.survey_responses_count,
            'has_profile_data': bool(self.user_profile),
            'status': 'completed' if self.survey_completed else 'in_progress' if self.survey_responses_count > 0 else 'not_started'
        }
    
    def update_user_profile(self, profile_data):
        """
        Update the user profile data from survey responses.
        
        Args:
            profile_data (dict): Processed user profile data
        """
        if not isinstance(profile_data, dict):
            raise ValueError("Profile data must be a dictionary")
        
        self.user_profile.update(profile_data)
        self.save(update_fields=['user_profile', 'updated_at'])
    
    def get_survey_criteria_weights(self):
        """
        Extract criteria weights from user profile for comparison engine.
        
        Returns:
            dict: Criteria weights derived from survey responses
        """
        if not self.user_profile:
            return {}
        
        # Extract weights from user profile
        weights = {}
        
        # Get priority weights from user profile
        priorities = self.user_profile.get('priorities', {})
        for criterion, priority_level in priorities.items():
            # Convert priority level to weight (1-5 scale to 0-100 scale)
            if isinstance(priority_level, (int, float)):
                weights[criterion] = min(100, max(0, priority_level * 20))
        
        # Get confidence-based weights
        confidence_weights = self.user_profile.get('confidence_weights', {})
        weights.update(confidence_weights)
        
        return weights
    
    def is_survey_based_comparison(self):
        """
        Check if this comparison session is based on survey data.
        
        Returns:
            bool: True if comparison uses survey data
        """
        return self.survey_completed and bool(self.user_profile)


class ComparisonCriteria(models.Model):
    """
    Model for predefined comparison criteria templates.
    Helps users select common comparison factors.
    """
    category = models.ForeignKey(
        PolicyCategory,
        on_delete=models.CASCADE,
        related_name='criteria_templates',
        help_text=_("Policy category this criteria applies to")
    )
    
    name = models.CharField(
        max_length=255,
        help_text=_("Name of the criteria")
    )
    
    description = models.TextField(
        help_text=_("Description of what this criteria evaluates")
    )
    
    field_name = models.CharField(
        max_length=100,
        help_text=_("Model field name to compare")
    )
    
    weight = models.PositiveIntegerField(
        default=50,
        help_text=_("Default weight/importance (0-100)")
    )
    
    comparison_type = models.CharField(
        max_length=20,
        choices=[
            ('HIGHER_BETTER', _('Higher is Better')),
            ('LOWER_BETTER', _('Lower is Better')),
            ('EXACT_MATCH', _('Exact Match')),
            ('RANGE', _('Within Range')),
            ('BOOLEAN', _('Yes/No')),
        ],
        help_text=_("How to compare this criteria")
    )
    
    is_required = models.BooleanField(
        default=False,
        help_text=_("Whether this criteria must be met")
    )
    
    is_active = models.BooleanField(
        default=True,
        help_text=_("Whether this criteria is active")
    )
    
    display_order = models.PositiveIntegerField(
        default=0,
        help_text=_("Display order")
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['category', 'display_order', 'name']
        verbose_name = _("Comparison Criteria")
        verbose_name_plural = _("Comparison Criteria")
        unique_together = ['category', 'field_name']
        indexes = [
            models.Index(fields=['category', 'is_active']),
        ]
    
    def __str__(self):
        return f"{self.name} - {self.category.name}"


class ComparisonResult(models.Model):
    """
    Model for storing individual policy comparison results.
    Tracks how each policy scored against criteria.
    """
    session = models.ForeignKey(
        ComparisonSession,
        on_delete=models.CASCADE,
        related_name='results',
        help_text=_("Comparison session this result belongs to")
    )
    
    policy = models.ForeignKey(
        BasePolicy,
        on_delete=models.CASCADE,
        related_name='comparison_results',
        help_text=_("Policy being evaluated")
    )
    
    overall_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        help_text=_("Overall match score (0-100)")
    )
    
    criteria_scores = models.JSONField(
        default=dict,
        help_text=_("Scores for individual criteria")
    )
    
    rank = models.PositiveIntegerField(
        help_text=_("Rank among compared policies (1 = best)")
    )
    
    pros = models.JSONField(
        default=list,
        help_text=_("List of advantages for this policy")
    )
    
    cons = models.JSONField(
        default=list,
        help_text=_("List of disadvantages for this policy")
    )
    
    recommendation_reason = models.TextField(
        blank=True,
        help_text=_("Explanation of why this policy scored as it did")
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['session', 'rank']
        verbose_name = _("Comparison Result")
        verbose_name_plural = _("Comparison Results")
        unique_together = ['session', 'policy']
        indexes = [
            models.Index(fields=['session', 'rank']),
            models.Index(fields=['policy']),
        ]
    
    def __str__(self):
        return f"{self.policy.name} - Score: {self.overall_score} (Rank #{self.rank})"


class UserPreferenceProfile(models.Model):
    """
    Model for storing user preference profiles for reuse.
    Allows users to save their comparison criteria preferences.
    """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='preference_profiles',
        help_text=_("User who owns this profile")
    )
    
    name = models.CharField(
        max_length=255,
        help_text=_("Profile name")
    )
    
    category = models.ForeignKey(
        PolicyCategory,
        on_delete=models.CASCADE,
        related_name='user_profiles',
        help_text=_("Policy category this profile is for")
    )
    
    preferences = models.JSONField(
        default=dict,
        help_text=_("Saved preferences and criteria weights")
    )
    
    is_default = models.BooleanField(
        default=False,
        help_text=_("Whether this is the user's default profile for this category")
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['user', 'category', 'name']
        verbose_name = _("User Preference Profile")
        verbose_name_plural = _("User Preference Profiles")
        unique_together = ['user', 'category', 'name']
        indexes = [
            models.Index(fields=['user', 'category']),
        ]
    
    def __str__(self):
        return f"{self.name} - {self.user.username}"