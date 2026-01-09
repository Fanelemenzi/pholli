from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.translation import gettext_lazy as _
from policies.models import BasePolicy


class HealthPolicy(BasePolicy):
    """
    Model for Health Insurance policies.
    Extends BasePolicy with health-specific fields.
    """
    
    class CoverageLevel(models.TextChoices):
        BASIC = 'BASIC', _('Basic')
        STANDARD = 'STANDARD', _('Standard')
        COMPREHENSIVE = 'COMPREHENSIVE', _('Comprehensive')
        PREMIUM = 'PREMIUM', _('Premium')
    
    # Coverage Details
    coverage_level = models.CharField(
        max_length=20,
        choices=CoverageLevel.choices,
        default=CoverageLevel.STANDARD,
        help_text=_("Level of health coverage")
    )
    
    hospital_network_type = models.CharField(
        max_length=50,
        help_text=_("Type of hospital network (e.g., Private, Public, Both)")
    )
    
    includes_hospital_cover = models.BooleanField(
        default=True,
        help_text=_("Whether policy includes hospital/inpatient coverage")
    )
    
    includes_outpatient_cover = models.BooleanField(
        default=False,
        help_text=_("Whether policy includes outpatient/day-to-day coverage")
    )
    
    includes_dental_cover = models.BooleanField(
        default=False,
        help_text=_("Whether policy includes dental coverage")
    )
    
    includes_optical_cover = models.BooleanField(
        default=False,
        help_text=_("Whether policy includes optical/vision coverage")
    )
    
    includes_maternity_cover = models.BooleanField(
        default=False,
        help_text=_("Whether policy includes maternity coverage")
    )
    
    # Medical Benefits
    gp_visits_per_year = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text=_("Number of GP visits covered per year (null for unlimited)")
    )
    
    specialist_visits_per_year = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text=_("Number of specialist visits covered per year")
    )
    
    chronic_medication_covered = models.BooleanField(
        default=False,
        help_text=_("Whether chronic medication is covered")
    )
    
    chronic_conditions_limit = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text=_("Number of chronic conditions covered")
    )
    
    # Hospital Benefits
    hospital_days_per_year = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text=_("Number of hospital days covered per year (null for unlimited)")
    )
    
    private_hospital_room = models.BooleanField(
        default=False,
        help_text=_("Whether private hospital room is included")
    )
    
    icu_cover_days = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text=_("Number of ICU days covered per year")
    )
    
    # Emergency Services
    ambulance_cover = models.BooleanField(
        default=True,
        help_text=_("Whether ambulance services are covered")
    )
    
    emergency_room_cover = models.BooleanField(
        default=True,
        help_text=_("Whether emergency room visits are covered")
    )
    
    # Preventive Care
    annual_checkup_covered = models.BooleanField(
        default=False,
        help_text=_("Whether annual health checkup is covered")
    )
    
    vaccinations_covered = models.BooleanField(
        default=False,
        help_text=_("Whether vaccinations are covered")
    )
    
    screening_tests_covered = models.BooleanField(
        default=False,
        help_text=_("Whether screening tests are covered")
    )
    
    # Prescription Coverage
    prescription_drug_coverage = models.BooleanField(
        default=True,
        help_text=_("Whether prescription drugs are covered")
    )
    
    prescription_annual_limit = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        help_text=_("Annual limit for prescription drugs")
    )
    
    # Co-payments and Deductibles
    copay_gp_visit = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=0.00,
        validators=[MinValueValidator(0)],
        help_text=_("Co-payment amount for GP visits")
    )
    
    copay_specialist = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=0.00,
        validators=[MinValueValidator(0)],
        help_text=_("Co-payment amount for specialist visits")
    )
    
    annual_deductible = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00,
        validators=[MinValueValidator(0)],
        help_text=_("Annual deductible amount")
    )
    
    out_of_pocket_maximum = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        help_text=_("Maximum out-of-pocket expenses per year")
    )
    
    # Additional Benefits
    mental_health_cover = models.BooleanField(
        default=False,
        help_text=_("Whether mental health services are covered")
    )
    
    physiotherapy_sessions = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text=_("Number of physiotherapy sessions covered per year")
    )
    
    alternative_medicine_cover = models.BooleanField(
        default=False,
        help_text=_("Whether alternative medicine is covered")
    )
    
    home_nursing_care = models.BooleanField(
        default=False,
        help_text=_("Whether home nursing care is covered")
    )
    
    class Meta:
        verbose_name = _("Health Policy")
        verbose_name_plural = _("Health Policies")
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Health: {self.name} - {self.organization.name}"


class HealthPolicyBenefit(models.Model):
    """
    Model for specific health benefits included in a policy.
    Allows for detailed breakdown of covered services.
    """
    
    class BenefitType(models.TextChoices):
        HOSPITAL = 'HOSPITAL', _('Hospital Services')
        OUTPATIENT = 'OUTPATIENT', _('Outpatient Services')
        SPECIALIST = 'SPECIALIST', _('Specialist Services')
        DENTAL = 'DENTAL', _('Dental Services')
        OPTICAL = 'OPTICAL', _('Optical Services')
        MATERNITY = 'MATERNITY', _('Maternity Services')
        MENTAL_HEALTH = 'MENTAL_HEALTH', _('Mental Health')
        PREVENTIVE = 'PREVENTIVE', _('Preventive Care')
        EMERGENCY = 'EMERGENCY', _('Emergency Services')
        OTHER = 'OTHER', _('Other Services')
    
    health_policy = models.ForeignKey(
        HealthPolicy,
        on_delete=models.CASCADE,
        related_name='health_benefits'
    )
    
    benefit_type = models.CharField(
        max_length=20,
        choices=BenefitType.choices,
        help_text=_("Type of health benefit")
    )
    
    benefit_name = models.CharField(
        max_length=255,
        help_text=_("Name of the benefit")
    )
    
    description = models.TextField(
        help_text=_("Detailed description of the benefit")
    )
    
    coverage_limit = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        help_text=_("Coverage limit for this benefit (null for unlimited)")
    )
    
    frequency_limit = models.CharField(
        max_length=100,
        blank=True,
        help_text=_("Frequency limit (e.g., 'per year', 'per visit', 'lifetime')")
    )
    
    copay_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0.00,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text=_("Co-payment percentage for this benefit")
    )
    
    requires_pre_authorization = models.BooleanField(
        default=False,
        help_text=_("Whether this benefit requires pre-authorization")
    )
    
    is_active = models.BooleanField(
        default=True,
        help_text=_("Whether this benefit is currently active")
    )
    
    display_order = models.PositiveIntegerField(
        default=0,
        help_text=_("Order in which to display this benefit")
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['health_policy', 'benefit_type', 'display_order']
        verbose_name = _("Health Policy Benefit")
        verbose_name_plural = _("Health Policy Benefits")
        indexes = [
            models.Index(fields=['health_policy', 'benefit_type']),
        ]
    
    def __str__(self):
        return f"{self.benefit_name} - {self.health_policy.name}"


class HospitalNetwork(models.Model):
    """
    Model for hospitals in the network of a health policy.
    Tracks which hospitals accept which policies.
    """
    
    class HospitalType(models.TextChoices):
        PUBLIC = 'PUBLIC', _('Public Hospital')
        PRIVATE = 'PRIVATE', _('Private Hospital')
        CLINIC = 'CLINIC', _('Clinic')
        SPECIALIST_CENTER = 'SPECIALIST', _('Specialist Center')
        DAY_CLINIC = 'DAY_CLINIC', _('Day Clinic')
    
    health_policy = models.ForeignKey(
        HealthPolicy,
        on_delete=models.CASCADE,
        related_name='hospital_networks'
    )
    
    hospital_name = models.CharField(
        max_length=255,
        help_text=_("Name of the hospital/medical facility")
    )
    
    hospital_type = models.CharField(
        max_length=20,
        choices=HospitalType.choices,
        help_text=_("Type of medical facility")
    )
    
    address = models.TextField(
        help_text=_("Full address of the facility")
    )
    
    city = models.CharField(
        max_length=100,
        help_text=_("City")
    )
    
    state_province = models.CharField(
        max_length=100,
        help_text=_("State or Province")
    )
    
    phone = models.CharField(
        max_length=20,
        help_text=_("Contact phone number")
    )
    
    emergency_services = models.BooleanField(
        default=False,
        help_text=_("Whether facility has emergency services")
    )
    
    specialties = models.JSONField(
        default=list,
        blank=True,
        help_text=_("List of medical specialties available")
    )
    
    is_preferred_provider = models.BooleanField(
        default=False,
        help_text=_("Whether this is a preferred provider (lower copays)")
    )
    
    latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
        help_text=_("Latitude for mapping")
    )
    
    longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
        help_text=_("Longitude for mapping")
    )
    
    is_active = models.BooleanField(
        default=True,
        help_text=_("Whether facility is currently in network")
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['city', 'hospital_name']
        verbose_name = _("Hospital Network")
        verbose_name_plural = _("Hospital Networks")
        indexes = [
            models.Index(fields=['health_policy', 'city']),
            models.Index(fields=['hospital_type']),
        ]
    
    def __str__(self):
        return f"{self.hospital_name} - {self.city}"


class ChronicConditionCoverage(models.Model):
    """
    Model for tracking chronic conditions covered by health policies.
    """
    health_policy = models.ForeignKey(
        HealthPolicy,
        on_delete=models.CASCADE,
        related_name='chronic_conditions'
    )
    
    condition_name = models.CharField(
        max_length=255,
        help_text=_("Name of the chronic condition")
    )
    
    description = models.TextField(
        blank=True,
        help_text=_("Description of coverage for this condition")
    )
    
    medication_covered = models.BooleanField(
        default=True,
        help_text=_("Whether medication for this condition is covered")
    )
    
    annual_limit = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        help_text=_("Annual coverage limit for this condition")
    )
    
    specialist_visits_included = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text=_("Number of specialist visits included per year")
    )
    
    requires_management_program = models.BooleanField(
        default=False,
        help_text=_("Whether patient must enroll in disease management program")
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['health_policy', 'condition_name']
        verbose_name = _("Chronic Condition Coverage")
        verbose_name_plural = _("Chronic Condition Coverage")
        indexes = [
            models.Index(fields=['health_policy']),
        ]
    
    def __str__(self):
        return f"{self.condition_name} - {self.health_policy.name}"