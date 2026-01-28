from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.translation import gettext_lazy as _
from organizations.models import Organization
from .managers import BasePolicyManager


class PolicyCategory(models.Model):
    """
    Model representing main insurance categories (Health, Life, Funeral).
    Top level of the policy hierarchy.
    """
    name = models.CharField(
        max_length=100,
        unique=True,
        help_text=_("Category name (e.g., Health, Life, Funeral)")
    )
    
    slug = models.SlugField(
        max_length=100,
        unique=True,
        help_text=_("URL-friendly version of category name")
    )
    
    description = models.TextField(
        help_text=_("Brief description of this policy category")
    )
    
    icon = models.CharField(
        max_length=50,
        blank=True,
        help_text=_("Icon name or CSS class for UI display")
    )
    
    display_order = models.PositiveIntegerField(
        default=0,
        help_text=_("Order in which to display categories")
    )
    
    is_active = models.BooleanField(
        default=True,
        help_text=_("Whether this category is active")
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Custom manager
    objects = BasePolicyManager()
    
    class Meta:
        ordering = ['display_order', 'name']
        verbose_name = _("Policy Category")
        verbose_name_plural = _("Policy Categories")
        indexes = [
            models.Index(fields=['slug']),
            models.Index(fields=['is_active']),
        ]
    
    def __str__(self):
        return self.name


class PolicyType(models.Model):
    """
    Model representing policy types within a category.
    Examples: Comprehensive Health, Basic Life, Family Funeral.
    """
    category = models.ForeignKey(
        PolicyCategory,
        on_delete=models.CASCADE,
        related_name='policy_types'
    )
    
    name = models.CharField(
        max_length=100,
        help_text=_("Type name (e.g., Comprehensive, Basic, Premium)")
    )
    
    slug = models.SlugField(
        max_length=100,
        help_text=_("URL-friendly version of type name")
    )
    
    description = models.TextField(
        help_text=_("Brief description of this policy type")
    )
    
    display_order = models.PositiveIntegerField(
        default=0,
        help_text=_("Order in which to display types")
    )
    
    is_active = models.BooleanField(
        default=True,
        help_text=_("Whether this type is active")
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['category', 'display_order', 'name']
        verbose_name = _("Policy Type")
        verbose_name_plural = _("Policy Types")
        unique_together = ['category', 'slug']
        indexes = [
            models.Index(fields=['category', 'slug']),
            models.Index(fields=['is_active']),
        ]
    
    def __str__(self):
        return f"{self.category.name} - {self.name}"


class BasePolicy(models.Model):
    """
    Abstract base model for all policy types.
    Contains common fields shared across Health, Life, and Funeral policies.
    """
    
    class ApprovalStatus(models.TextChoices):
        DRAFT = 'DRAFT', _('Draft')
        PENDING = 'PENDING', _('Pending Approval')
        APPROVED = 'APPROVED', _('Approved')
        REJECTED = 'REJECTED', _('Rejected')
        ARCHIVED = 'ARCHIVED', _('Archived')
    
    # Relationships
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name='policies'
    )
    
    category = models.ForeignKey(
        PolicyCategory,
        on_delete=models.PROTECT,
        related_name='policies'
    )
    
    policy_type = models.ForeignKey(
        PolicyType,
        on_delete=models.PROTECT,
        related_name='policies'
    )
    
    # Basic Information
    name = models.CharField(
        max_length=255,
        help_text=_("Policy name/title")
    )
    
    policy_number = models.CharField(
        max_length=100,
        unique=True,
        help_text=_("Unique policy identifier")
    )
    
    description = models.TextField(
        help_text=_("Detailed policy description")
    )
    
    short_description = models.CharField(
        max_length=500,
        help_text=_("Brief summary for listings")
    )
    
    # Pricing
    base_premium = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        help_text=_("Base monthly premium amount")
    )
    
    currency = models.CharField(
        max_length=3,
        default='ZAR',
        help_text=_("Currency code (ISO 4217)")
    )
    
    # Coverage
    coverage_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        help_text=_("Maximum coverage/benefit amount")
    )
    
    # Terms and Conditions
    minimum_age = models.PositiveIntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(120)],
        help_text=_("Minimum age for eligibility")
    )
    
    maximum_age = models.PositiveIntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(120)],
        help_text=_("Maximum age for eligibility")
    )
    
    waiting_period_days = models.PositiveIntegerField(
        default=0,
        help_text=_("Waiting period in days before coverage starts")
    )
    
    terms_and_conditions = models.TextField(
        help_text=_("Full terms and conditions text")
    )
    
    # Status and Approval
    approval_status = models.CharField(
        max_length=20,
        choices=ApprovalStatus.choices,
        default=ApprovalStatus.DRAFT,
        help_text=_("Current approval status")
    )
    
    is_active = models.BooleanField(
        default=False,
        help_text=_("Whether policy is active and visible to users")
    )
    
    is_featured = models.BooleanField(
        default=False,
        help_text=_("Whether to feature this policy prominently")
    )
    
    approved_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_("Date and time when policy was approved")
    )
    
    approved_by = models.ForeignKey(
        'auth.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_policies'
    )
    
    # Additional Information
    brochure = models.FileField(
        upload_to='policies/brochures/',
        blank=True,
        null=True,
        help_text=_("Policy brochure PDF")
    )
    
    application_form = models.FileField(
        upload_to='policies/forms/',
        blank=True,
        null=True,
        help_text=_("Application form PDF")
    )
    
    tags = models.JSONField(
        default=list,
        blank=True,
        help_text=_("Tags for categorization and search")
    )
    
    custom_fields = models.JSONField(
        default=dict,
        blank=True,
        help_text=_("Custom fields specific to organization")
    )
    
    # Metadata
    views_count = models.PositiveIntegerField(
        default=0,
        help_text=_("Number of times policy has been viewed")
    )
    
    comparison_count = models.PositiveIntegerField(
        default=0,
        help_text=_("Number of times policy has been compared")
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = _("Base Policy")
        verbose_name_plural = _("Base Policies")
        indexes = [
            models.Index(fields=['organization', 'is_active']),
            models.Index(fields=['category', 'policy_type']),
            models.Index(fields=['approval_status']),
            models.Index(fields=['is_featured', 'is_active']),
            models.Index(fields=['policy_number']),
        ]
    
    def __str__(self):
        return f"{self.name} - {self.organization.name}"
    
    def get_policy_features(self):
        """Get the PolicyFeatures instance for this policy."""
        try:
            return self.policy_features
        except PolicyFeatures.DoesNotExist:
            return None
    
    def get_feature_value(self, feature_name):
        """Get the value of a specific feature."""
        policy_features = self.get_policy_features()
        if policy_features:
            return getattr(policy_features, feature_name, None)
        return None
    
    def get_all_features_dict(self):
        """Get all feature values as a dictionary."""
        policy_features = self.get_policy_features()
        if not policy_features:
            return {}
        
        features = {}
        if policy_features.insurance_type == 'HEALTH':
            features.update({
                'annual_limit_per_member': policy_features.annual_limit_per_member,
                'annual_limit_per_family': policy_features.annual_limit_per_family,
                'annual_limit_family_range': policy_features.annual_limit_family_range,
                'annual_limit_member_range': policy_features.annual_limit_member_range,
                'monthly_household_income': policy_features.monthly_household_income,
                'currently_on_medical_aid': policy_features.currently_on_medical_aid,
                'ambulance_coverage': policy_features.ambulance_coverage,
                'in_hospital_benefit': policy_features.in_hospital_benefit,
                'in_hospital_benefit_level': policy_features.in_hospital_benefit_level,
                'out_hospital_benefit': policy_features.out_hospital_benefit,
                'out_hospital_benefit_level': policy_features.out_hospital_benefit_level,
                'chronic_medication_availability': policy_features.chronic_medication_availability,
            })
        elif policy_features.insurance_type == 'FUNERAL':
            features.update({
                'cover_amount': policy_features.cover_amount,
                'marital_status_requirement': policy_features.marital_status_requirement,
                'gender_requirement': policy_features.gender_requirement,
            })
        
        return {k: v for k, v in features.items() if v is not None}
    
    def calculate_feature_compatibility(self, user_preferences):
        """Calculate compatibility score based on user preferences."""
        # This will be implemented by the FeatureMatchingEngine in a later task
        pass
    
    def is_approved(self):
        """Check if policy is approved."""
        return self.approval_status == self.ApprovalStatus.APPROVED
    
    def can_be_activated(self):
        """Check if policy can be activated."""
        return (
            self.is_approved() and
            self.organization.is_verified and
            self.organization.can_create_policy()
        )
    
    def increment_views(self):
        """Increment the view count."""
        self.views_count += 1
        self.save(update_fields=['views_count'])
    
    def increment_comparisons(self):
        """Increment the comparison count."""
        self.comparison_count += 1
        self.save(update_fields=['comparison_count'])


class PolicyFeatures(models.Model):
    """
    Core features model based on Docs/features.md for health and funeral policies.
    """
    
    class InsuranceType(models.TextChoices):
        HEALTH = 'HEALTH', _('Health Policies')
        FUNERAL = 'FUNERAL', _('Funeral Policies')
    
    # Import benefit choices from simple_surveys
    HOSPITAL_BENEFIT_CHOICES = [
        ('no_cover', _('No hospital cover')),
        ('basic', _('Basic hospital care')),
        ('moderate', _('Moderate hospital care')),
        ('extensive', _('Extensive hospital care')),
        ('comprehensive', _('Comprehensive hospital care')),
    ]

    OUT_HOSPITAL_BENEFIT_CHOICES = [
        ('no_cover', _('No out-of-hospital cover')),
        ('basic_visits', _('Basic clinic visits')),
        ('routine_care', _('Routine medical care')),
        ('extended_care', _('Extended medical care')),
        ('comprehensive_care', _('Comprehensive day-to-day care')),
    ]

    ANNUAL_LIMIT_FAMILY_RANGES = [
        ('10k-50k', _('R10,000 - R50,000')),
        ('50k-100k', _('R50,001 - R100,000')),
        ('100k-250k', _('R100,001 - R250,000')),
        ('250k-500k', _('R250,001 - R500,000')),
        ('500k-1m', _('R500,001 - R1,000,000')),
        ('1m-2m', _('R1,000,001 - R2,000,000')),
        ('2m-5m', _('R2,000,001 - R5,000,000')),
        ('5m-plus', _('R5,000,001+')),
        ('not_sure', _('Not sure / Need guidance')),
    ]

    ANNUAL_LIMIT_MEMBER_RANGES = [
        ('10k-25k', _('R10,000 - R25,000')),
        ('25k-50k', _('R25,001 - R50,000')),
        ('50k-100k', _('R50,001 - R100,000')),
        ('100k-200k', _('R100,001 - R200,000')),
        ('200k-500k', _('R200,001 - R500,000')),
        ('500k-1m', _('R500,001 - R1,000,000')),
        ('1m-2m', _('R1,000,001 - R2,000,000')),
        ('2m-plus', _('R2,000,001+')),
        ('not_sure', _('Not sure / Need guidance')),
    ]
    
    policy = models.OneToOneField(
        BasePolicy, 
        on_delete=models.CASCADE, 
        related_name='policy_features'
    )
    insurance_type = models.CharField(
        max_length=20, 
        choices=InsuranceType.choices,
        help_text=_("Type of insurance policy")
    )
    
    # Health Policy Features (from Docs/features.md)
    annual_limit_per_member = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        null=True, 
        blank=True,
        help_text=_("Overall annual limit per member per family")
    )
    annual_limit_per_family = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        null=True, 
        blank=True,
        help_text=_("Annual limit per family (replaces per member limit)")
    )
    
    # New range fields for annual limits
    annual_limit_family_range = models.CharField(
        max_length=50,
        choices=ANNUAL_LIMIT_FAMILY_RANGES,
        null=True,
        blank=True,
        help_text=_("Annual limit range per family for matching")
    )
    
    annual_limit_member_range = models.CharField(
        max_length=50,
        choices=ANNUAL_LIMIT_MEMBER_RANGES,
        null=True,
        blank=True,
        help_text=_("Annual limit range per member for matching")
    )
    
    monthly_household_income = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        null=True, 
        blank=True,
        help_text=_("Monthly household income requirement")
    )
    currently_on_medical_aid = models.BooleanField(
        null=True, 
        blank=True,
        help_text=_("Whether the applicant is currently on medical aid")
    )
    ambulance_coverage = models.BooleanField(
        null=True, 
        blank=True,
        help_text=_("Whether ambulance coverage is included")
    )
    
    # Updated benefit level fields (replacing boolean fields)
    in_hospital_benefit = models.BooleanField(
        null=True, 
        blank=True,
        help_text=_("With or without in-hospital benefit (legacy field)")
    )
    
    in_hospital_benefit_level = models.CharField(
        max_length=50,
        choices=HOSPITAL_BENEFIT_CHOICES,
        null=True,
        blank=True,
        help_text=_("Level of in-hospital coverage provided")
    )
    
    out_hospital_benefit = models.BooleanField(
        null=True, 
        blank=True,
        help_text=_("With or without out of hospital benefits (legacy field)")
    )
    
    out_hospital_benefit_level = models.CharField(
        max_length=50,
        choices=OUT_HOSPITAL_BENEFIT_CHOICES,
        null=True,
        blank=True,
        help_text=_("Level of out-of-hospital coverage provided")
    )
    
    chronic_medication_availability = models.BooleanField(
        null=True, 
        blank=True,
        help_text=_("Chronic medication availability")
    )
    
    # Funeral Policy Features (from Docs/features.md)
    cover_amount = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        null=True, 
        blank=True,
        help_text=_("Cover amount for funeral policy")
    )
    marital_status_requirement = models.CharField(
        max_length=50, 
        null=True, 
        blank=True,
        help_text=_("Marital status requirement")
    )
    gender_requirement = models.CharField(
        max_length=20, 
        null=True, 
        blank=True,
        help_text=_("Gender requirement")
    )
    monthly_net_income = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        null=True, 
        blank=True,
        help_text=_("Monthly net income requirement for funeral policy")
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _("Policy Features")
        verbose_name_plural = _("Policy Features")
        indexes = [
            models.Index(fields=['insurance_type']),
            models.Index(fields=['policy']),
        ]
    
    def __str__(self):
        return f"{self.policy.name} - {self.get_insurance_type_display()} Features"
    
    def get_all_features_dict(self):
        """Get all feature values as a dictionary."""
        features = {}
        if self.insurance_type == 'HEALTH':
            features.update({
                'annual_limit_per_member': self.annual_limit_per_member,
                'annual_limit_per_family': self.annual_limit_per_family,
                'annual_limit_family_range': self.annual_limit_family_range,
                'annual_limit_member_range': self.annual_limit_member_range,
                'monthly_household_income': self.monthly_household_income,
                'currently_on_medical_aid': self.currently_on_medical_aid,
                'ambulance_coverage': self.ambulance_coverage,
                'in_hospital_benefit': self.in_hospital_benefit,
                'in_hospital_benefit_level': self.in_hospital_benefit_level,
                'out_hospital_benefit': self.out_hospital_benefit,
                'out_hospital_benefit_level': self.out_hospital_benefit_level,
                'chronic_medication_availability': self.chronic_medication_availability,
            })
        elif self.insurance_type == 'FUNERAL':
            features.update({
                'cover_amount': self.cover_amount,
                'marital_status_requirement': self.marital_status_requirement,
                'gender_requirement': self.gender_requirement,
            })
        
        return {k: v for k, v in features.items() if v is not None}


class AdditionalFeatures(models.Model):
    """
    Additional features and benefits for policies (renamed from PolicyFeature).
    """
    policy = models.ForeignKey(
        BasePolicy,
        on_delete=models.CASCADE,
        related_name='additional_features'
    )
    
    title = models.CharField(
        max_length=255,
        help_text=_("Additional feature title")
    )
    
    description = models.TextField(
        help_text=_("Detailed additional feature description")
    )
    
    coverage_details = models.TextField(
        blank=True,
        help_text=_("Detailed coverage information and descriptions")
    )
    
    icon = models.CharField(
        max_length=50,
        blank=True,
        help_text=_("Icon name or CSS class")
    )
    
    is_highlighted = models.BooleanField(
        default=False,
        help_text=_("Whether to highlight this additional feature")
    )
    
    display_order = models.PositiveIntegerField(
        default=0,
        help_text=_("Order in which to display additional features")
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['policy', 'display_order', 'title']
        verbose_name = _("Additional Features")
        verbose_name_plural = _("Additional Features")
        indexes = [
            models.Index(fields=['policy', 'is_highlighted']),
        ]
    
    def __str__(self):
        return f"{self.title} - {self.policy.name}"


class PolicyEligibility(models.Model):
    """
    Model for policy eligibility criteria.
    Defines who can apply for the policy.
    """
    policy = models.ForeignKey(
        BasePolicy,
        on_delete=models.CASCADE,
        related_name='eligibility_criteria'
    )
    
    criterion = models.CharField(
        max_length=255,
        help_text=_("Eligibility criterion")
    )
    
    description = models.TextField(
        blank=True,
        help_text=_("Detailed description of this criterion")
    )
    
    is_mandatory = models.BooleanField(
        default=True,
        help_text=_("Whether this criterion is mandatory")
    )
    
    display_order = models.PositiveIntegerField(
        default=0,
        help_text=_("Order in which to display criteria")
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['policy', 'display_order', 'criterion']
        verbose_name = _("Policy Eligibility")
        verbose_name_plural = _("Policy Eligibility Criteria")
        indexes = [
            models.Index(fields=['policy', 'is_mandatory']),
        ]
    
    def __str__(self):
        return f"{self.criterion} - {self.policy.name}"


class PolicyExclusion(models.Model):
    """
    Model for policy exclusions.
    Defines what is not covered by the policy.
    """
    policy = models.ForeignKey(
        BasePolicy,
        on_delete=models.CASCADE,
        related_name='exclusions'
    )
    
    title = models.CharField(
        max_length=255,
        help_text=_("Exclusion title")
    )
    
    description = models.TextField(
        help_text=_("Detailed description of what is excluded")
    )
    
    display_order = models.PositiveIntegerField(
        default=0,
        help_text=_("Order in which to display exclusions")
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['policy', 'display_order', 'title']
        verbose_name = _("Policy Exclusion")
        verbose_name_plural = _("Policy Exclusions")
        indexes = [
            models.Index(fields=['policy']),
        ]
    
    def __str__(self):
        return f"{self.title} - {self.policy.name}"


class PolicyDocument(models.Model):
    """
    Model for policy-related documents.
    Stores additional documentation for policies.
    """
    
    class DocumentType(models.TextChoices):
        BROCHURE = 'BROCHURE', _('Brochure')
        TERMS = 'TERMS', _('Terms & Conditions')
        APPLICATION = 'APPLICATION', _('Application Form')
        CLAIM_FORM = 'CLAIM_FORM', _('Claim Form')
        GUIDE = 'GUIDE', _('User Guide')
        OTHER = 'OTHER', _('Other')
    
    policy = models.ForeignKey(
        BasePolicy,
        on_delete=models.CASCADE,
        related_name='documents'
    )
    
    document_type = models.CharField(
        max_length=20,
        choices=DocumentType.choices,
        help_text=_("Type of document")
    )
    
    title = models.CharField(
        max_length=255,
        help_text=_("Document title")
    )
    
    file = models.FileField(
        upload_to='policies/documents/',
        help_text=_("Document file")
    )
    
    description = models.TextField(
        blank=True,
        help_text=_("Brief description of the document")
    )
    
    is_public = models.BooleanField(
        default=True,
        help_text=_("Whether document is publicly accessible")
    )
    
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['policy', 'document_type', 'title']
        verbose_name = _("Policy Document")
        verbose_name_plural = _("Policy Documents")
        indexes = [
            models.Index(fields=['policy', 'document_type']),
            models.Index(fields=['is_public']),
        ]
    
    def __str__(self):
        return f"{self.title} - {self.policy.name}"


class PolicyPremiumCalculation(models.Model):
    """
    Model for storing premium calculation rules.
    Defines how premiums are calculated based on various factors.
    """
    policy = models.ForeignKey(
        BasePolicy,
        on_delete=models.CASCADE,
        related_name='premium_calculations'
    )
    
    factor_name = models.CharField(
        max_length=100,
        help_text=_("Factor affecting premium (e.g., age, gender, smoker)")
    )
    
    factor_value = models.CharField(
        max_length=100,
        help_text=_("Value of the factor (e.g., '18-25', 'male', 'yes')")
    )
    
    multiplier = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=1.00,
        help_text=_("Multiplier to apply to base premium")
    )
    
    additional_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00,
        help_text=_("Additional amount to add to premium")
    )
    
    description = models.TextField(
        blank=True,
        help_text=_("Description of this calculation rule")
    )
    
    is_active = models.BooleanField(
        default=True,
        help_text=_("Whether this rule is currently active")
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['policy', 'factor_name', 'factor_value']
        verbose_name = _("Policy Premium Calculation")
        verbose_name_plural = _("Policy Premium Calculations")
        unique_together = ['policy', 'factor_name', 'factor_value']
        indexes = [
            models.Index(fields=['policy', 'is_active']),
        ]
    
    def __str__(self):
        return f"{self.factor_name}={self.factor_value} - {self.policy.name}"
    
    def calculate_premium(self, base_premium):
        """Calculate the adjusted premium based on this rule."""
        return (base_premium * self.multiplier) + self.additional_amount


class Rewards(models.Model):
    """
    Model for managing rewards and incentives associated with policies.
    Tracks cashback, discounts, benefits, and other reward programs.
    """
    
    class RewardType(models.TextChoices):
        CASHBACK = 'CASHBACK', _('Cashback')
        DISCOUNT = 'DISCOUNT', _('Discount')
        BENEFIT = 'BENEFIT', _('Additional Benefit')
        POINTS = 'POINTS', _('Loyalty Points')
        OTHER = 'OTHER', _('Other')
    
    policy = models.ForeignKey(
        BasePolicy,
        on_delete=models.CASCADE,
        related_name='rewards',
        help_text=_("Policy this reward is associated with")
    )
    
    title = models.CharField(
        max_length=255,
        help_text=_("Reward title (e.g., 'Cashback Program', 'Loyalty Discount')")
    )
    
    description = models.TextField(
        help_text=_("Detailed description of the reward")
    )
    
    reward_type = models.CharField(
        max_length=50,
        choices=RewardType.choices,
        help_text=_("Type of reward offered")
    )
    
    value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        help_text=_("Monetary value of reward (if applicable)")
    )
    
    percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text=_("Percentage value of reward (if applicable)")
    )
    
    eligibility_criteria = models.TextField(
        blank=True,
        help_text=_("Criteria for earning this reward")
    )
    
    terms_and_conditions = models.TextField(
        blank=True,
        help_text=_("Terms and conditions for the reward")
    )
    
    is_active = models.BooleanField(
        default=True,
        help_text=_("Whether this reward is currently active")
    )
    
    display_order = models.PositiveIntegerField(
        default=0,
        help_text=_("Order for displaying rewards")
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['policy', 'display_order', 'title']
        verbose_name = _("Reward")
        verbose_name_plural = _("Rewards")
        indexes = [
            models.Index(fields=['policy', 'is_active']),
            models.Index(fields=['reward_type']),
            models.Index(fields=['display_order']),
        ]
    
    def __str__(self):
        return f"{self.title} - {self.policy.name}"
    
    def clean(self):
        """Validate that either value or percentage is provided for applicable reward types."""
        from django.core.exceptions import ValidationError
        
        # For cashback and discount rewards, require either value or percentage
        if self.reward_type in ['CASHBACK', 'DISCOUNT']:
            if not self.value and not self.percentage:
                raise ValidationError(
                    _("Cashback and discount rewards must have either a monetary value or percentage.")
                )
        
        # Ensure both value and percentage are not provided simultaneously
        if self.value and self.percentage:
            raise ValidationError(
                _("Please provide either a monetary value OR a percentage, not both.")
            )
    
    def get_display_value(self):
        """Get formatted display value for the reward."""
        if self.percentage:
            return f"{self.percentage}%"
        elif self.value:
            return f"R{self.value}"
        else:
            return "See terms"
    
    def is_monetary_reward(self):
        """Check if this is a monetary reward (has value or percentage)."""
        return bool(self.value or self.percentage)


class PolicyReview(models.Model):
    """
    Model for user reviews and ratings of policies.
    Allows users to rate and review policies they've experienced.
    """
    policy = models.ForeignKey(
        BasePolicy,
        on_delete=models.CASCADE,
        related_name='reviews'
    )
    
    user = models.ForeignKey(
        'auth.User',
        on_delete=models.CASCADE,
        related_name='policy_reviews'
    )
    
    rating = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text=_("Rating from 1 to 5 stars")
    )
    
    title = models.CharField(
        max_length=255,
        help_text=_("Review title")
    )
    
    comment = models.TextField(
        help_text=_("Review comment")
    )
    
    is_verified_purchase = models.BooleanField(
        default=False,
        help_text=_("Whether reviewer actually purchased this policy")
    )
    
    is_approved = models.BooleanField(
        default=False,
        help_text=_("Whether review has been approved for display")
    )
    
    helpful_count = models.PositiveIntegerField(
        default=0,
        help_text=_("Number of users who found this review helpful")
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = _("Policy Review")
        verbose_name_plural = _("Policy Reviews")
        unique_together = ['policy', 'user']
        indexes = [
            models.Index(fields=['policy', 'is_approved']),
            models.Index(fields=['rating']),
        ]
    
    def __str__(self):
        return f"{self.title} - {self.policy.name} ({self.rating}★)"