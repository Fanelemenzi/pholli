from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
from datetime import timedelta
import json


# Benefit Level Configuration Constants

HOSPITAL_BENEFIT_CHOICES = [
    ('no_cover', 'No hospital cover', 'I do not need cover for hospital admission'),
    ('basic', 'Basic hospital care', 'Covers admission and standard hospital treatment'),
    ('moderate', 'Moderate hospital care', 'Covers admission, procedures, and specialist treatment'),
    ('extensive', 'Extensive hospital care', 'Covers most hospital needs, including major procedures'),
    ('comprehensive', 'Comprehensive hospital care', 'Covers all hospital-related treatment and services'),
]

OUT_HOSPITAL_BENEFIT_CHOICES = [
    ('no_cover', 'No out-of-hospital cover', 'No cover for day-to-day medical care'),
    ('basic_visits', 'Basic clinic visits', 'Covers GP/clinic visits only'),
    ('routine_care', 'Routine medical care', 'Covers GP visits and basic medication'),
    ('extended_care', 'Extended medical care', 'Covers GP visits, specialists, and diagnostics'),
    ('comprehensive_care', 'Comprehensive day-to-day care', 'Covers most medical needs outside hospital, including chronic care'),
]

ANNUAL_LIMIT_FAMILY_RANGES = [
    ('10k-50k', 'R10,000 - R50,000', 'Basic family coverage for routine medical needs'),
    ('50k-100k', 'R50,001 - R100,000', 'Standard family coverage for most medical situations'),
    ('100k-250k', 'R100,001 - R250,000', 'Enhanced family coverage including specialist care'),
    ('250k-500k', 'R250,001 - R500,000', 'Comprehensive family coverage for major medical needs'),
    ('500k-1m', 'R500,001 - R1,000,000', 'Premium family coverage for extensive medical care'),
    ('1m-2m', 'R1,000,001 - R2,000,000', 'High-end family coverage for complex medical needs'),
    ('2m-5m', 'R2,000,001 - R5,000,000', 'Luxury family coverage for all medical scenarios'),
    ('5m-plus', 'R5,000,001+', 'Unlimited family coverage preferred'),
    ('not_sure', 'Not sure / Need guidance', 'Help me choose based on my situation'),
]

ANNUAL_LIMIT_MEMBER_RANGES = [
    ('10k-25k', 'R10,000 - R25,000', 'Basic individual coverage for routine care'),
    ('25k-50k', 'R25,001 - R50,000', 'Standard individual coverage for most needs'),
    ('50k-100k', 'R50,001 - R100,000', 'Enhanced individual coverage including specialists'),
    ('100k-200k', 'R100,001 - R200,000', 'Comprehensive individual coverage for major needs'),
    ('200k-500k', 'R200,001 - R500,000', 'Premium individual coverage for extensive care'),
    ('500k-1m', 'R500,001 - R1,000,000', 'High-end individual coverage for complex needs'),
    ('1m-2m', 'R1,000,001 - R2,000,000', 'Luxury individual coverage for all scenarios'),
    ('2m-plus', 'R2,000,001+', 'Unlimited individual coverage preferred'),
    ('not_sure', 'Not sure / Need guidance', 'Help me choose based on my situation'),
]


class SimpleSurveyQuestionManager(models.Manager):
    """Manager for SimpleSurveyQuestion with common queries"""
    
    def for_category(self, category):
        """Get all questions for a specific category ordered by display_order"""
        return self.filter(category=category).order_by('display_order')
    
    def required_questions(self, category):
        """Get all required questions for a category"""
        return self.filter(category=category, is_required=True).order_by('display_order')


class SimpleSurveyQuestion(models.Model):
    """Simplified survey question model for health and funeral insurance"""
    
    CATEGORY_CHOICES = [
        ('health', 'Health Insurance'),
        ('funeral', 'Funeral Insurance'),
    ]
    
    INPUT_TYPE_CHOICES = [
        ('text', 'Text Input'),
        ('number', 'Number Input'),
        ('select', 'Dropdown Select'),
        ('radio', 'Radio Buttons'),
        ('checkbox', 'Checkboxes'),
    ]
    
    category = models.CharField(
        max_length=20, 
        choices=CATEGORY_CHOICES,
        help_text="Insurance category this question belongs to"
    )
    question_text = models.TextField(
        help_text="The question text displayed to users"
    )
    field_name = models.CharField(
        max_length=50,
        help_text="Field name that maps to quotation criteria"
    )
    input_type = models.CharField(
        max_length=20,
        choices=INPUT_TYPE_CHOICES,
        help_text="Type of input control to display"
    )
    choices = models.JSONField(
        default=list,
        blank=True,
        help_text="Available choices for select, radio, or checkbox inputs"
    )
    is_required = models.BooleanField(
        default=True,
        help_text="Whether this question must be answered"
    )
    display_order = models.PositiveIntegerField(
        help_text="Order in which questions are displayed"
    )
    validation_rules = models.JSONField(
        default=dict,
        blank=True,
        help_text="Simple validation rules (min, max, pattern, etc.)"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    objects = SimpleSurveyQuestionManager()
    
    class Meta:
        ordering = ['category', 'display_order']
        unique_together = ['category', 'field_name']
        indexes = [
            models.Index(fields=['category', 'display_order']),
            models.Index(fields=['category', 'is_required']),
        ]
    
    def __str__(self):
        return f"{self.get_category_display()} - {self.question_text[:50]}"
    
    def get_choices_list(self):
        """Return choices as a list, handling both list and dict formats"""
        if isinstance(self.choices, list):
            return self.choices
        elif isinstance(self.choices, dict):
            return list(self.choices.items())
        return []
    
    def validate_response(self, response_value):
        """Simple validation based on input type and rules"""
        errors = []
        
        # Required field validation
        if self.is_required and (response_value is None or response_value == ''):
            errors.append("This field is required")
            return errors
        
        # Skip further validation if field is empty and not required
        if not response_value and not self.is_required:
            return errors
        
        # Type-specific validation
        if self.input_type == 'number':
            try:
                num_value = float(response_value)
                if 'min' in self.validation_rules and num_value < self.validation_rules['min']:
                    errors.append(f"Value must be at least {self.validation_rules['min']}")
                if 'max' in self.validation_rules and num_value > self.validation_rules['max']:
                    errors.append(f"Value must be at most {self.validation_rules['max']}")
            except (ValueError, TypeError):
                errors.append("Please enter a valid number")
        
        elif self.input_type in ['select', 'radio']:
            valid_choices = [choice[0] if isinstance(choice, (list, tuple)) else choice 
                           for choice in self.get_choices_list()]
            if response_value not in valid_choices:
                errors.append("Please select a valid option")
        
        elif self.input_type == 'checkbox':
            if not isinstance(response_value, list):
                # Try to convert string to list
                if isinstance(response_value, str):
                    response_value = [item.strip() for item in response_value.split(',') if item.strip()]
                else:
                    errors.append("Invalid checkbox response format")
                    return errors
            
            valid_choices = [choice[0] if isinstance(choice, (list, tuple)) else choice 
                           for choice in self.get_choices_list()]
            for value in response_value:
                if value not in valid_choices:
                    errors.append(f"Invalid choice: {value}")
                    break  # Only report first invalid choice
        
        elif self.input_type == 'text':
            if 'max_length' in self.validation_rules and len(str(response_value)) > self.validation_rules['max_length']:
                errors.append(f"Text must be no more than {self.validation_rules['max_length']} characters")
        
        return errors


class SimpleSurveyResponseManager(models.Manager):
    """Manager for SimpleSurveyResponse with common queries"""
    
    def for_session(self, session_key):
        """Get all responses for a session"""
        return self.filter(session_key=session_key).select_related('question')
    
    def for_session_category(self, session_key, category):
        """Get responses for a specific session and category"""
        return self.filter(
            session_key=session_key,
            category=category
        ).select_related('question')
    
    def completed_sessions(self, category):
        """Get session keys that have completed all required questions"""
        required_count = SimpleSurveyQuestion.objects.filter(
            category=category, 
            is_required=True
        ).count()
        
        return self.filter(category=category).values('session_key').annotate(
            response_count=models.Count('id')
        ).filter(response_count__gte=required_count).values_list('session_key', flat=True)


class SimpleSurveyResponse(models.Model):
    """User response to a survey question"""
    
    session_key = models.CharField(
        max_length=100,
        help_text="Session identifier for anonymous users"
    )
    category = models.CharField(
        max_length=20,
        choices=SimpleSurveyQuestion.CATEGORY_CHOICES,
        help_text="Insurance category for this response"
    )
    question = models.ForeignKey(
        SimpleSurveyQuestion,
        on_delete=models.CASCADE,
        help_text="The question being answered"
    )
    response_value = models.JSONField(
        help_text="The user's response (can be string, number, list, etc.)"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    objects = SimpleSurveyResponseManager()
    
    class Meta:
        unique_together = ['session_key', 'question']
        indexes = [
            models.Index(fields=['session_key']),
            models.Index(fields=['session_key', 'category']),
            models.Index(fields=['category', 'created_at']),
        ]
    
    def __str__(self):
        return f"Response {self.session_key[:8]} - {self.question.field_name}"
    
    def get_display_value(self):
        """Get a human-readable display value for the response"""
        if self.question.input_type == 'checkbox' and isinstance(self.response_value, list):
            return ', '.join(str(v) for v in self.response_value)
        return str(self.response_value)


class QuotationSessionManager(models.Manager):
    """Manager for QuotationSession with common queries"""
    
    def active_sessions(self):
        """Get all non-expired sessions"""
        return self.filter(expires_at__gt=timezone.now())
    
    def expired_sessions(self):
        """Get all expired sessions for cleanup"""
        return self.filter(expires_at__lte=timezone.now())
    
    def create_session(self, session_key, category):
        """Create a new quotation session with 24-hour expiry"""
        expires_at = timezone.now() + timedelta(hours=24)
        return self.create(
            session_key=session_key,
            category=category,
            expires_at=expires_at
        )
    
    def completed_sessions(self, category=None):
        """Get completed sessions, optionally filtered by category"""
        queryset = self.filter(is_completed=True)
        if category:
            queryset = queryset.filter(category=category)
        return queryset


class QuotationSession(models.Model):
    """Session tracking for survey completion and quotation generation"""
    
    session_key = models.CharField(
        max_length=100,
        help_text="Session identifier (not unique, allows multiple categories per Django session)"
    )
    category = models.CharField(
        max_length=20,
        choices=SimpleSurveyQuestion.CATEGORY_CHOICES,
        help_text="Insurance category for this session"
    )
    user_criteria = models.JSONField(
        default=dict,
        help_text="Processed criteria from survey responses for quotation matching"
    )
    is_completed = models.BooleanField(
        default=False,
        help_text="Whether the survey has been completed and quotations generated"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(
        help_text="Session expiry time (24 hours from creation)"
    )
    
    objects = QuotationSessionManager()
    
    class Meta:
        unique_together = ['session_key', 'category']
        indexes = [
            models.Index(fields=['session_key']),
            models.Index(fields=['category', 'is_completed']),
            models.Index(fields=['expires_at']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"Session {self.session_key[:8]} - {self.get_category_display()}"
    
    def is_expired(self):
        """Check if the session has expired"""
        return timezone.now() > self.expires_at
    
    def extend_expiry(self, hours=24):
        """Extend session expiry by specified hours"""
        self.expires_at = timezone.now() + timedelta(hours=hours)
        self.save(update_fields=['expires_at'])
    
    def update_criteria(self, criteria_dict):
        """Update user criteria from survey responses"""
        self.user_criteria.update(criteria_dict)
        self.save(update_fields=['user_criteria'])
    
    def mark_completed(self):
        """Mark session as completed"""
        self.is_completed = True
        self.save(update_fields=['is_completed'])
    
    def get_response_count(self):
        """Get the number of responses for this session"""
        return SimpleSurveyResponse.objects.filter(
            session_key=self.session_key,
            category=self.category
        ).count()
    
    def get_completion_percentage(self):
        """Calculate completion percentage based on required questions"""
        total_required = SimpleSurveyQuestion.objects.filter(
            category=self.category,
            is_required=True
        ).count()
        
        if total_required == 0:
            return 100
        
        completed = SimpleSurveyResponse.objects.filter(
            session_key=self.session_key,
            category=self.category,
            question__is_required=True
        ).count()
        
        return int((completed / total_required) * 100)


class SimpleSurvey(models.Model):
    """
    Simplified survey focusing only on policy features and contact info.
    Based on features from Docs/features.md for health and funeral policies.
    """
    
    class InsuranceType(models.TextChoices):
        HEALTH = 'HEALTH', 'Health Policies'
        FUNERAL = 'FUNERAL', 'Funeral Policies'
    
    # Contact Information (for survey only)
    first_name = models.CharField(
        max_length=100,
        help_text="First name of the survey respondent"
    )
    last_name = models.CharField(
        max_length=100,
        help_text="Last name of the survey respondent"
    )
    date_of_birth = models.DateField(
        help_text="Date of birth of the survey respondent"
    )
    email = models.EmailField(
        blank=True,
        help_text="Email address (optional)"
    )
    phone = models.CharField(
        max_length=20,
        blank=True,
        help_text="Phone number (optional)"
    )
    
    # Insurance type selection
    insurance_type = models.CharField(
        max_length=20,
        choices=InsuranceType.choices,
        help_text="Type of insurance being surveyed"
    )
    
    # Health Policy Preferences (from Docs/features.md)
    preferred_annual_limit = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Preferred overall annual limit per member per family"
    )
    preferred_annual_limit_per_family = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Preferred annual limit per family (replaces per member limit)"
    )
    household_income = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Monthly household income"
    )
    wants_ambulance_coverage = models.BooleanField(
        null=True,
        blank=True,
        help_text="Do you want ambulance coverage?"
    )
    needs_chronic_medication = models.BooleanField(
        null=True,
        blank=True,
        help_text="Do you need chronic medication coverage?"
    )
    
    # New benefit level fields (replacing boolean fields)
    in_hospital_benefit_level = models.CharField(
        max_length=50,
        choices=[(choice[0], choice[1]) for choice in HOSPITAL_BENEFIT_CHOICES],
        null=True,
        blank=True,
        help_text="Level of in-hospital coverage needed"
    )
    
    out_hospital_benefit_level = models.CharField(
        max_length=50,
        choices=[(choice[0], choice[1]) for choice in OUT_HOSPITAL_BENEFIT_CHOICES],
        null=True,
        blank=True,
        help_text="Level of out-of-hospital coverage needed"
    )
    
    # New range fields for annual limits
    annual_limit_family_range = models.CharField(
        max_length=50,
        choices=[(choice[0], choice[1]) for choice in ANNUAL_LIMIT_FAMILY_RANGES],
        null=True,
        blank=True,
        help_text="Preferred annual limit range per family"
    )
    
    annual_limit_member_range = models.CharField(
        max_length=50,
        choices=[(choice[0], choice[1]) for choice in ANNUAL_LIMIT_MEMBER_RANGES],
        null=True,
        blank=True,
        help_text="Preferred annual limit range per member"
    )
    
    # Funeral Policy Preferences (from Docs/features.md)
    preferred_cover_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Preferred cover amount for funeral policy"
    )
    marital_status = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        help_text="Marital status"
    )
    gender = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        help_text="Gender"
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Simple Survey"
        verbose_name_plural = "Simple Surveys"
        indexes = [
            models.Index(fields=['insurance_type', 'created_at']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.first_name} {self.last_name} - {self.get_insurance_type_display()}"
    
    def clean(self):
        """Validate survey responses based on insurance type."""
        super().clean()
        errors = {}
        
        # Validate health policy fields
        if self.insurance_type == self.InsuranceType.HEALTH:
            if self.household_income is None:
                errors['household_income'] = 'Household income is required for health policies'
            elif self.household_income <= 0:
                errors['household_income'] = 'Household income must be greater than 0'
                
            if self.wants_ambulance_coverage is None:
                errors['wants_ambulance_coverage'] = 'Ambulance coverage preference is required for health policies'
                
            if self.in_hospital_benefit_level is None:
                errors['in_hospital_benefit_level'] = 'In-hospital benefit level is required for health policies'
            else:
                # Validate that the selected benefit level is a valid choice
                valid_choices = [choice[0] for choice in HOSPITAL_BENEFIT_CHOICES]
                if self.in_hospital_benefit_level not in valid_choices:
                    errors['in_hospital_benefit_level'] = 'Please select a valid in-hospital benefit level'
                
            if self.out_hospital_benefit_level is None:
                errors['out_hospital_benefit_level'] = 'Out-of-hospital benefit level is required for health policies'
            else:
                # Validate that the selected benefit level is a valid choice
                valid_choices = [choice[0] for choice in OUT_HOSPITAL_BENEFIT_CHOICES]
                if self.out_hospital_benefit_level not in valid_choices:
                    errors['out_hospital_benefit_level'] = 'Please select a valid out-of-hospital benefit level'
                
            if self.annual_limit_family_range is None:
                errors['annual_limit_family_range'] = 'Annual limit family range is required for health policies'
            else:
                # Validate that the selected range is a valid choice
                valid_choices = [choice[0] for choice in ANNUAL_LIMIT_FAMILY_RANGES]
                if self.annual_limit_family_range not in valid_choices:
                    errors['annual_limit_family_range'] = 'Please select a valid annual limit family range'
                
            if self.annual_limit_member_range is None:
                errors['annual_limit_member_range'] = 'Annual limit member range is required for health policies'
            else:
                # Validate that the selected range is a valid choice
                valid_choices = [choice[0] for choice in ANNUAL_LIMIT_MEMBER_RANGES]
                if self.annual_limit_member_range not in valid_choices:
                    errors['annual_limit_member_range'] = 'Please select a valid annual limit member range'
                
            if self.needs_chronic_medication is None:
                errors['needs_chronic_medication'] = 'Chronic medication preference is required for health policies'
        
        # Validate funeral policy fields
        elif self.insurance_type == self.InsuranceType.FUNERAL:
            if self.preferred_cover_amount is None:
                errors['preferred_cover_amount'] = 'Cover amount preference is required for funeral policies'
            elif self.preferred_cover_amount <= 0:
                errors['preferred_cover_amount'] = 'Cover amount must be greater than 0'
                
            if not self.marital_status:
                errors['marital_status'] = 'Marital status is required for funeral policies'
                
            if not self.gender:
                errors['gender'] = 'Gender is required for funeral policies'
        
        if errors:
            raise ValidationError(errors)
    
    def get_preferences_dict(self):
        """Get user preferences as dictionary for matching."""
        if self.insurance_type == self.InsuranceType.HEALTH:
            return {
                'annual_limit_per_family': self.preferred_annual_limit_per_family,
                'annual_limit_family_range': self.annual_limit_family_range,
                'annual_limit_member_range': self.annual_limit_member_range,
                'monthly_household_income': self.household_income,
                'ambulance_coverage': self.wants_ambulance_coverage,
                'in_hospital_benefit_level': self.in_hospital_benefit_level,
                'out_hospital_benefit_level': self.out_hospital_benefit_level,
                'chronic_medication_availability': self.needs_chronic_medication,
            }
        elif self.insurance_type == self.InsuranceType.FUNERAL:
            return {
                'cover_amount': self.preferred_cover_amount,
                'marital_status_requirement': self.marital_status,
                'gender_requirement': self.gender,
            }
        return {}
    
    def is_complete(self):
        """Check if all required fields for the insurance type are filled."""
        try:
            self.clean()
            return True
        except ValidationError:
            return False
    
    def get_missing_fields(self):
        """Get list of missing required fields for the insurance type."""
        missing_fields = []
        
        # Common required fields
        if not self.first_name:
            missing_fields.append('first_name')
        if not self.last_name:
            missing_fields.append('last_name')
        if not self.date_of_birth:
            missing_fields.append('date_of_birth')
        if not self.insurance_type:
            missing_fields.append('insurance_type')
        
        # Health policy required fields
        if self.insurance_type == self.InsuranceType.HEALTH:
            if self.household_income is None:
                missing_fields.append('household_income')
            if self.wants_ambulance_coverage is None:
                missing_fields.append('wants_ambulance_coverage')
            if self.in_hospital_benefit_level is None:
                missing_fields.append('in_hospital_benefit_level')
            if self.out_hospital_benefit_level is None:
                missing_fields.append('out_hospital_benefit_level')
            if self.annual_limit_family_range is None:
                missing_fields.append('annual_limit_family_range')
            if self.annual_limit_member_range is None:
                missing_fields.append('annual_limit_member_range')
            if self.needs_chronic_medication is None:
                missing_fields.append('needs_chronic_medication')
        
        # Funeral policy required fields
        elif self.insurance_type == self.InsuranceType.FUNERAL:
            if self.preferred_cover_amount is None:
                missing_fields.append('preferred_cover_amount')
            if not self.marital_status:
                missing_fields.append('marital_status')
            if not self.gender:
                missing_fields.append('gender')
        
        return missing_fields