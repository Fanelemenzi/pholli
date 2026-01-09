from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from policies.models import PolicyCategory
from comparison.models import ComparisonSession

User = get_user_model()


class SurveyTemplate(models.Model):
    """
    Model for organizing survey questions by insurance category.
    Each template represents a complete survey for a specific policy category.
    """
    category = models.ForeignKey(
        PolicyCategory,
        on_delete=models.CASCADE,
        related_name='survey_templates',
        help_text=_("Policy category this template is for")
    )
    
    name = models.CharField(
        max_length=255,
        help_text=_("Template name")
    )
    
    description = models.TextField(
        help_text=_("Description of this survey template")
    )
    
    version = models.CharField(
        max_length=20,
        default='1.0',
        help_text=_("Template version for tracking changes")
    )
    
    is_active = models.BooleanField(
        default=True,
        help_text=_("Whether this template is currently active")
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['category', 'name']
        verbose_name = _("Survey Template")
        verbose_name_plural = _("Survey Templates")
        unique_together = ['category', 'name', 'version']
        indexes = [
            models.Index(fields=['category', 'is_active']),
        ]
    
    def __str__(self):
        return f"{self.name} v{self.version} - {self.category.name}"


class SurveyQuestion(models.Model):
    """
    Model for individual survey questions with flexible question types and validation rules.
    """
    
    class QuestionType(models.TextChoices):
        TEXT = 'TEXT', _('Text Input')
        NUMBER = 'NUMBER', _('Number Input')
        CHOICE = 'CHOICE', _('Single Choice')
        MULTI_CHOICE = 'MULTI_CHOICE', _('Multiple Choice')
        RANGE = 'RANGE', _('Range/Slider')
        BOOLEAN = 'BOOLEAN', _('Yes/No')
    
    category = models.ForeignKey(
        PolicyCategory,
        on_delete=models.CASCADE,
        related_name='survey_questions',
        help_text=_("Policy category this question belongs to")
    )
    
    section = models.CharField(
        max_length=100,
        help_text=_("Section name (e.g., 'Personal Info', 'Coverage Needs')")
    )
    
    question_text = models.TextField(
        help_text=_("The actual question text displayed to users")
    )
    
    question_type = models.CharField(
        max_length=20,
        choices=QuestionType.choices,
        help_text=_("Type of question input")
    )
    
    field_name = models.CharField(
        max_length=100,
        help_text=_("Field name that maps to comparison criteria")
    )
    
    choices = models.JSONField(
        default=list,
        blank=True,
        help_text=_("Available choices for choice-based questions")
    )
    
    validation_rules = models.JSONField(
        default=dict,
        blank=True,
        help_text=_("Validation rules (min/max values, required, etc.)")
    )
    
    weight_impact = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=1.00,
        help_text=_("How much this question affects comparison weighting")
    )
    
    help_text = models.TextField(
        blank=True,
        help_text=_("Additional help text or explanation for users")
    )
    
    is_required = models.BooleanField(
        default=True,
        help_text=_("Whether this question must be answered")
    )
    
    display_order = models.PositiveIntegerField(
        default=0,
        help_text=_("Order in which to display this question")
    )
    
    is_active = models.BooleanField(
        default=True,
        help_text=_("Whether this question is currently active")
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['category', 'section', 'display_order']
        verbose_name = _("Survey Question")
        verbose_name_plural = _("Survey Questions")
        unique_together = ['category', 'field_name']
        indexes = [
            models.Index(fields=['category', 'section', 'is_active']),
            models.Index(fields=['display_order']),
        ]
    
    def __str__(self):
        return f"{self.section}: {self.question_text[:50]}..."


class TemplateQuestion(models.Model):
    """
    Through model linking survey templates to questions.
    Allows questions to be reused across templates with different ordering.
    """
    template = models.ForeignKey(
        SurveyTemplate,
        on_delete=models.CASCADE,
        related_name='template_questions'
    )
    
    question = models.ForeignKey(
        SurveyQuestion,
        on_delete=models.CASCADE,
        related_name='template_questions'
    )
    
    display_order = models.PositiveIntegerField(
        default=0,
        help_text=_("Order of this question within the template")
    )
    
    is_required_override = models.BooleanField(
        null=True,
        blank=True,
        help_text=_("Override the question's default required setting")
    )
    
    class Meta:
        ordering = ['template', 'display_order']
        verbose_name = _("Template Question")
        verbose_name_plural = _("Template Questions")
        unique_together = ['template', 'question']
        indexes = [
            models.Index(fields=['template', 'display_order']),
        ]
    
    def __str__(self):
        return f"{self.template.name} - {self.question.question_text[:30]}..."
    
    @property
    def is_required(self):
        """Return whether this question is required, considering override."""
        if self.is_required_override is not None:
            return self.is_required_override
        return self.question.is_required


class SurveyResponse(models.Model):
    """
    Model to store user responses linked to comparison sessions.
    """
    session = models.ForeignKey(
        ComparisonSession,
        on_delete=models.CASCADE,
        related_name='survey_responses',
        help_text=_("Comparison session this response belongs to")
    )
    
    question = models.ForeignKey(
        SurveyQuestion,
        on_delete=models.CASCADE,
        related_name='responses',
        help_text=_("Question being answered")
    )
    
    response_value = models.JSONField(
        help_text=_("Flexible storage for different response types")
    )
    
    confidence_level = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        default=3,
        help_text=_("User's confidence in their answer (1-5)")
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['session', 'question__display_order']
        verbose_name = _("Survey Response")
        verbose_name_plural = _("Survey Responses")
        unique_together = ['session', 'question']
        indexes = [
            models.Index(fields=['session']),
            models.Index(fields=['question']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"Response to {self.question.question_text[:30]}... by {self.session}"


class QuestionDependency(models.Model):
    """
    Model for conditional question logic.
    Defines when child questions should be shown based on parent question responses.
    """
    
    class ConditionOperator(models.TextChoices):
        EQUALS = 'EQUALS', _('Equals')
        NOT_EQUALS = 'NOT_EQUALS', _('Not Equals')
        GREATER_THAN = 'GREATER_THAN', _('Greater Than')
        LESS_THAN = 'LESS_THAN', _('Less Than')
        CONTAINS = 'CONTAINS', _('Contains')
        IN_LIST = 'IN_LIST', _('In List')
    
    parent_question = models.ForeignKey(
        SurveyQuestion,
        on_delete=models.CASCADE,
        related_name='child_dependencies',
        help_text=_("Question that triggers the condition")
    )
    
    child_question = models.ForeignKey(
        SurveyQuestion,
        on_delete=models.CASCADE,
        related_name='parent_dependencies',
        help_text=_("Question that is shown/hidden based on condition")
    )
    
    condition_value = models.JSONField(
        help_text=_("Value that triggers the child question")
    )
    
    condition_operator = models.CharField(
        max_length=20,
        choices=ConditionOperator.choices,
        default=ConditionOperator.EQUALS,
        help_text=_("Operator to use for condition evaluation")
    )
    
    is_active = models.BooleanField(
        default=True,
        help_text=_("Whether this dependency rule is active")
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['parent_question', 'child_question']
        verbose_name = _("Question Dependency")
        verbose_name_plural = _("Question Dependencies")
        unique_together = ['parent_question', 'child_question']
        indexes = [
            models.Index(fields=['parent_question', 'is_active']),
            models.Index(fields=['child_question']),
        ]
    
    def __str__(self):
        return f"{self.parent_question.field_name} -> {self.child_question.field_name}"
    
    def evaluate_condition(self, parent_response_value):
        """
        Evaluate whether the condition is met based on parent response.
        Returns True if child question should be shown.
        """
        if not self.is_active:
            return False
        
        condition_value = self.condition_value
        operator = self.condition_operator
        
        if operator == self.ConditionOperator.EQUALS:
            return parent_response_value == condition_value
        elif operator == self.ConditionOperator.NOT_EQUALS:
            return parent_response_value != condition_value
        elif operator == self.ConditionOperator.GREATER_THAN:
            return parent_response_value > condition_value
        elif operator == self.ConditionOperator.LESS_THAN:
            return parent_response_value < condition_value
        elif operator == self.ConditionOperator.CONTAINS:
            return condition_value in parent_response_value
        elif operator == self.ConditionOperator.IN_LIST:
            return parent_response_value in condition_value
        
        return False


class SurveyAnalytics(models.Model):
    """
    Model to track survey performance and user behavior.
    """
    question = models.OneToOneField(
        SurveyQuestion,
        on_delete=models.CASCADE,
        related_name='analytics',
        help_text=_("Question these analytics are for")
    )
    
    total_responses = models.PositiveIntegerField(
        default=0,
        help_text=_("Total number of responses to this question")
    )
    
    completion_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0.00,
        help_text=_("Percentage of users who completed this question")
    )
    
    average_response_time = models.DurationField(
        null=True,
        blank=True,
        help_text=_("Average time users spend on this question")
    )
    
    skip_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0.00,
        help_text=_("Percentage of users who skipped this question")
    )
    
    most_common_response = models.JSONField(
        null=True,
        blank=True,
        help_text=_("Most frequently given response")
    )
    
    response_distribution = models.JSONField(
        default=dict,
        blank=True,
        help_text=_("Distribution of responses for analysis")
    )
    
    last_updated = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _("Survey Analytics")
        verbose_name_plural = _("Survey Analytics")
        indexes = [
            models.Index(fields=['question']),
            models.Index(fields=['completion_rate']),
            models.Index(fields=['last_updated']),
        ]
    
    def __str__(self):
        return f"Analytics for {self.question.question_text[:30]}..."
    
    def update_analytics(self):
        """
        Update analytics based on current response data.
        This method should be called periodically or after significant response changes.
        """
        responses = self.question.responses.all()
        total_responses = responses.count()
        
        if total_responses > 0:
            self.total_responses = total_responses
            # Additional analytics calculations would go here
            self.save()


class UserSurveyProfile(models.Model):
    """
    Extended user profile for survey-specific preferences and settings.
    """
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='survey_profile',
        help_text=_("User this profile belongs to")
    )
    
    # Profile preferences
    auto_save_responses = models.BooleanField(
        default=True,
        help_text=_("Automatically save survey responses as user progresses")
    )
    
    prefill_from_history = models.BooleanField(
        default=True,
        help_text=_("Pre-fill survey questions based on previous responses")
    )
    
    email_survey_reminders = models.BooleanField(
        default=False,
        help_text=_("Send email reminders for incomplete surveys")
    )
    
    data_retention_days = models.PositiveIntegerField(
        default=365,
        help_text=_("Number of days to retain survey data (0 = indefinite)")
    )
    
    # Profile metadata
    total_surveys_completed = models.PositiveIntegerField(
        default=0,
        help_text=_("Total number of surveys completed by user")
    )
    
    last_survey_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_("Date of last completed survey")
    )
    
    preferred_categories = models.ManyToManyField(
        PolicyCategory,
        blank=True,
        help_text=_("User's preferred insurance categories")
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _("User Survey Profile")
        verbose_name_plural = _("User Survey Profiles")
    
    def __str__(self):
        return f"Survey Profile for {self.user.username}"
    
    def update_survey_completion_stats(self):
        """Update survey completion statistics."""
        completed_sessions = ComparisonSession.objects.filter(
            user=self.user,
            survey_completed=True
        )
        
        self.total_surveys_completed = completed_sessions.count()
        
        latest_session = completed_sessions.order_by('-updated_at').first()
        if latest_session:
            self.last_survey_date = latest_session.updated_at
        
        self.save(update_fields=['total_surveys_completed', 'last_survey_date', 'updated_at'])


class SavedSurveyProfile(models.Model):
    """
    Model for saving complete survey response profiles for reuse.
    """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='saved_survey_profiles',
        help_text=_("User who owns this saved profile")
    )
    
    name = models.CharField(
        max_length=255,
        help_text=_("User-defined name for this profile")
    )
    
    category = models.ForeignKey(
        PolicyCategory,
        on_delete=models.CASCADE,
        related_name='saved_survey_profiles',
        help_text=_("Insurance category this profile is for")
    )
    
    description = models.TextField(
        blank=True,
        help_text=_("Optional description of this profile")
    )
    
    # Saved survey data
    survey_responses = models.JSONField(
        default=dict,
        help_text=_("Saved survey responses in structured format")
    )
    
    criteria_weights = models.JSONField(
        default=dict,
        help_text=_("Derived criteria weights from responses")
    )
    
    user_profile_data = models.JSONField(
        default=dict,
        help_text=_("Processed user profile data")
    )
    
    # Profile metadata
    is_default = models.BooleanField(
        default=False,
        help_text=_("Whether this is the default profile for this category")
    )
    
    usage_count = models.PositiveIntegerField(
        default=0,
        help_text=_("Number of times this profile has been used")
    )
    
    last_used = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_("When this profile was last used")
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _("Saved Survey Profile")
        verbose_name_plural = _("Saved Survey Profiles")
        unique_together = ['user', 'category', 'name']
        indexes = [
            models.Index(fields=['user', 'category']),
            models.Index(fields=['user', 'is_default']),
        ]
    
    def __str__(self):
        return f"{self.name} - {self.user.username} ({self.category.name})"
    
    def mark_used(self):
        """Mark this profile as used and update usage statistics."""
        self.usage_count += 1
        self.last_used = timezone.now()
        self.save(update_fields=['usage_count', 'last_used'])
    
    def set_as_default(self):
        """Set this profile as the default for its category."""
        # Remove default flag from other profiles in same category
        SavedSurveyProfile.objects.filter(
            user=self.user,
            category=self.category,
            is_default=True
        ).update(is_default=False)
        
        # Set this profile as default
        self.is_default = True
        self.save(update_fields=['is_default'])

class ABTestVariant(models.Model):
    """
    Model for A/B test variants.
    """
    
    class Status(models.TextChoices):
        DRAFT = 'DRAFT', 'Draft'
        ACTIVE = 'ACTIVE', 'Active'
        PAUSED = 'PAUSED', 'Paused'
        COMPLETED = 'COMPLETED', 'Completed'
    
    name = models.CharField(
        max_length=255,
        help_text="Name of the A/B test"
    )
    
    description = models.TextField(
        help_text="Description of what this test is measuring"
    )
    
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT
    )
    
    # Test configuration
    traffic_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=50.00,
        help_text="Percentage of traffic to include in this test (0-100)"
    )
    
    start_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When to start the test"
    )
    
    end_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When to end the test"
    )
    
    # Target metrics
    primary_metric = models.CharField(
        max_length=100,
        default='completion_rate',
        help_text="Primary metric to optimize (completion_rate, response_time, etc.)"
    )
    
    minimum_sample_size = models.PositiveIntegerField(
        default=100,
        help_text="Minimum number of participants needed for statistical significance"
    )
    
    # Test variants configuration
    variants_config = models.JSONField(
        default=dict,
        help_text="Configuration for different test variants"
    )
    
    # Results tracking
    participants_count = models.PositiveIntegerField(
        default=0,
        help_text="Total number of participants in this test"
    )
    
    results_data = models.JSONField(
        default=dict,
        help_text="Aggregated results data"
    )
    
    statistical_significance = models.DecimalField(
        max_digits=5,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="P-value for statistical significance"
    )
    
    winning_variant = models.CharField(
        max_length=100,
        blank=True,
        help_text="Winning variant (if test is completed)"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "A/B Test Variant"
        verbose_name_plural = "A/B Test Variants"
        indexes = [
            models.Index(fields=['status', 'start_date']),
            models.Index(fields=['primary_metric']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.status})"


class ABTestParticipant(models.Model):
    """
    Model to track A/B test participants.
    """
    test = models.ForeignKey(
        ABTestVariant,
        on_delete=models.CASCADE,
        related_name='participants'
    )
    
    session = models.ForeignKey(
        ComparisonSession,
        on_delete=models.CASCADE,
        related_name='ab_test_participations'
    )
    
    variant = models.CharField(
        max_length=100,
        help_text="Which variant this participant was assigned"
    )
    
    # Tracking data
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # Metrics
    completion_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True
    )
    
    response_time_seconds = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Total time spent on survey in seconds"
    )
    
    responses_count = models.PositiveIntegerField(
        default=0,
        help_text="Number of questions answered"
    )
    
    conversion_achieved = models.BooleanField(
        default=False,
        help_text="Whether the participant achieved the conversion goal"
    )
    
    class Meta:
        verbose_name = "A/B Test Participant"
        verbose_name_plural = "A/B Test Participants"
        unique_together = ['test', 'session']
        indexes = [
            models.Index(fields=['test', 'variant']),
            models.Index(fields=['started_at']),
        ]
    
    def __str__(self):
        return f"{self.test.name} - {self.variant} - {self.session}"