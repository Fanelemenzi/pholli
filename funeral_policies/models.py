from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.translation import gettext_lazy as _
from policies.models import BasePolicy


class FuneralPolicy(BasePolicy):
    """
    Model for Funeral Insurance policies.
    Extends BasePolicy with funeral cover-specific fields.
    """
    
    class CoverType(models.TextChoices):
        INDIVIDUAL = 'INDIVIDUAL', _('Individual Only')
        FAMILY = 'FAMILY', _('Family Cover')
        EXTENDED_FAMILY = 'EXTENDED_FAMILY', _('Extended Family')
    
    class FuneralService(models.TextChoices):
        CASH_PAYOUT = 'CASH_PAYOUT', _('Cash Payout Only')
        MANAGED_SERVICE = 'MANAGED_SERVICE', _('Managed Funeral Service')
        HYBRID = 'HYBRID', _('Cash + Services')
    
    # Cover Type
    cover_type = models.CharField(
        max_length=20,
        choices=CoverType.choices,
        default=CoverType.INDIVIDUAL,
        help_text=_("Type of funeral cover")
    )
    
    service_type = models.CharField(
        max_length=20,
        choices=FuneralService.choices,
        default=FuneralService.CASH_PAYOUT,
        help_text=_("Type of funeral service provided")
    )
    
    # Main Member Coverage
    main_member_cover_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        help_text=_("Cover amount for main member")
    )
    
    # Spouse Coverage
    includes_spouse_cover = models.BooleanField(
        default=False,
        help_text=_("Whether spouse is covered")
    )
    
    spouse_cover_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        help_text=_("Cover amount for spouse")
    )
    
    spouse_same_cover = models.BooleanField(
        default=True,
        help_text=_("Whether spouse has same cover as main member")
    )
    
    # Children Coverage
    includes_children_cover = models.BooleanField(
        default=False,
        help_text=_("Whether children are covered")
    )
    
    number_of_children_covered = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text=_("Maximum number of children covered (null for unlimited)")
    )
    
    child_cover_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        help_text=_("Cover amount per child")
    )
    
    child_minimum_age = models.PositiveIntegerField(
        default=0,
        help_text=_("Minimum age for child coverage (usually 0 for stillborn)")
    )
    
    child_maximum_age = models.PositiveIntegerField(
        default=21,
        help_text=_("Maximum age for child coverage")
    )
    
    # Extended Family Coverage
    includes_parents_cover = models.BooleanField(
        default=False,
        help_text=_("Whether parents are covered")
    )
    
    number_of_parents_covered = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text=_("Number of parents covered (typically 2-4)")
    )
    
    parent_cover_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        help_text=_("Cover amount per parent")
    )
    
    includes_in_laws_cover = models.BooleanField(
        default=False,
        help_text=_("Whether parents-in-law are covered")
    )
    
    in_law_cover_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        help_text=_("Cover amount per parent-in-law")
    )
    
    includes_extended_family = models.BooleanField(
        default=False,
        help_text=_("Whether extended family members are covered")
    )
    
    extended_family_members = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text=_("Number of extended family members covered")
    )
    
    extended_family_cover_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        help_text=_("Cover amount per extended family member")
    )
    
    # Waiting Periods
    natural_death_waiting_period = models.PositiveIntegerField(
        default=6,
        help_text=_("Waiting period for natural death (months)")
    )
    
    accidental_death_waiting_period = models.PositiveIntegerField(
        default=0,
        help_text=_("Waiting period for accidental death (months)")
    )
    
    # Funeral Services (if managed service)
    includes_coffin = models.BooleanField(
        default=False,
        help_text=_("Whether coffin is provided")
    )
    
    includes_transport = models.BooleanField(
        default=False,
        help_text=_("Whether transport/hearse is provided")
    )
    
    includes_venue = models.BooleanField(
        default=False,
        help_text=_("Whether funeral venue is provided")
    )
    
    includes_catering = models.BooleanField(
        default=False,
        help_text=_("Whether catering is provided")
    )
    
    includes_tombstone = models.BooleanField(
        default=False,
        help_text=_("Whether tombstone/headstone is provided")
    )
    
    includes_flowers = models.BooleanField(
        default=False,
        help_text=_("Whether flowers are provided")
    )
    
    includes_memorial_service = models.BooleanField(
        default=False,
        help_text=_("Whether memorial service is included")
    )
    
    # Additional Benefits
    repatriation_covered = models.BooleanField(
        default=False,
        help_text=_("Whether repatriation to home country/area is covered")
    )
    
    repatriation_distance_km = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text=_("Maximum repatriation distance in kilometers")
    )
    
    grocery_benefit = models.BooleanField(
        default=False,
        help_text=_("Whether grocery/cash benefit is provided")
    )
    
    grocery_benefit_amount = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        help_text=_("Amount of grocery benefit")
    )
    
    mourning_clothes_benefit = models.BooleanField(
        default=False,
        help_text=_("Whether mourning clothes allowance is provided")
    )
    
    mourning_clothes_amount = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        help_text=_("Amount for mourning clothes")
    )
    
    night_vigil_cover = models.BooleanField(
        default=False,
        help_text=_("Whether night vigil expenses are covered")
    )
    
    night_vigil_amount = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        help_text=_("Amount for night vigil expenses")
    )
    
    # Documentation and Claims
    documents_required = models.TextField(
        blank=True,
        help_text=_("List of documents required for claims")
    )
    
    claim_payout_days = models.PositiveIntegerField(
        default=48,
        help_text=_("Number of hours for claim payout")
    )
    
    multiple_claims_per_year = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text=_("Maximum number of claims allowed per year (null for unlimited)")
    )
    
    # Premium Payment
    premium_increase_frequency = models.CharField(
        max_length=50,
        default='ANNUAL',
        help_text=_("Frequency of premium increases (e.g., 'ANNUAL', 'NEVER')")
    )
    
    premium_increase_method = models.CharField(
        max_length=100,
        blank=True,
        help_text=_("Method of premium increase (e.g., 'CPI-linked', 'Age-based')")
    )
    
    # Cover Increase
    automatic_cover_increase = models.BooleanField(
        default=False,
        help_text=_("Whether cover automatically increases")
    )
    
    cover_increase_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text=_("Annual cover increase rate (percentage)")
    )
    
    class Meta:
        verbose_name = _("Funeral Policy")
        verbose_name_plural = _("Funeral Policies")
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Funeral: {self.name} - {self.organization.name}"


class FamilyCoverageTier(models.Model):
    """
    Model for different family members covered under funeral policy.
    Tracks coverage levels for different family relationships.
    """
    
    class RelationshipType(models.TextChoices):
        MAIN_MEMBER = 'MAIN_MEMBER', _('Main Member')
        SPOUSE = 'SPOUSE', _('Spouse')
        CHILD = 'CHILD', _('Child')
        PARENT = 'PARENT', _('Parent')
        PARENT_IN_LAW = 'PARENT_IN_LAW', _('Parent-in-Law')
        SIBLING = 'SIBLING', _('Sibling')
        GRANDPARENT = 'GRANDPARENT', _('Grandparent')
        GRANDCHILD = 'GRANDCHILD', _('Grandchild')
        OTHER_RELATIVE = 'OTHER_RELATIVE', _('Other Relative')
    
    funeral_policy = models.ForeignKey(
        FuneralPolicy,
        on_delete=models.CASCADE,
        related_name='family_tiers'
    )
    
    relationship_type = models.CharField(
        max_length=20,
        choices=RelationshipType.choices,
        help_text=_("Type of family relationship")
    )
    
    cover_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        help_text=_("Cover amount for this relationship")
    )
    
    maximum_members = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text=_("Maximum number of members for this relationship (null for unlimited)")
    )
    
    minimum_age = models.PositiveIntegerField(
        default=0,
        help_text=_("Minimum age for this coverage")
    )
    
    maximum_age = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text=_("Maximum age for this coverage (null for unlimited)")
    )
    
    waiting_period_months = models.PositiveIntegerField(
        default=6,
        help_text=_("Waiting period for natural death (months)")
    )
    
    description = models.TextField(
        blank=True,
        help_text=_("Description of coverage for this relationship")
    )
    
    is_optional = models.BooleanField(
        default=False,
        help_text=_("Whether this coverage is optional")
    )
    
    additional_premium = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=0.00,
        validators=[MinValueValidator(0)],
        help_text=_("Additional monthly premium for this tier")
    )
    
    display_order = models.PositiveIntegerField(
        default=0,
        help_text=_("Display order")
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['funeral_policy', 'display_order', 'relationship_type']
        verbose_name = _("Family Coverage Tier")
        verbose_name_plural = _("Family Coverage Tiers")
        unique_together = ['funeral_policy', 'relationship_type']
        indexes = [
            models.Index(fields=['funeral_policy']),
        ]
    
    def __str__(self):
        return f"{self.get_relationship_type_display()} - {self.funeral_policy.name}"


class FuneralServiceProvider(models.Model):
    """
    Model for funeral service providers in the network.
    Tracks which funeral parlours service which policies.
    """
    funeral_policy = models.ForeignKey(
        FuneralPolicy,
        on_delete=models.CASCADE,
        related_name='service_providers'
    )
    
    provider_name = models.CharField(
        max_length=255,
        help_text=_("Name of funeral service provider")
    )
    
    address = models.TextField(
        help_text=_("Full address of provider")
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
    
    emergency_phone = models.CharField(
        max_length=20,
        blank=True,
        help_text=_("24/7 emergency contact number")
    )
    
    email = models.EmailField(
        blank=True,
        help_text=_("Contact email")
    )
    
    services_offered = models.JSONField(
        default=list,
        help_text=_("List of services offered by this provider")
    )
    
    coverage_areas = models.JSONField(
        default=list,
        help_text=_("List of areas/regions covered by this provider")
    )
    
    languages_spoken = models.JSONField(
        default=list,
        blank=True,
        help_text=_("Languages spoken by staff")
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
    
    operates_24_7 = models.BooleanField(
        default=True,
        help_text=_("Whether provider operates 24/7")
    )
    
    is_preferred_provider = models.BooleanField(
        default=False,
        help_text=_("Whether this is a preferred provider")
    )
    
    is_active = models.BooleanField(
        default=True,
        help_text=_("Whether provider is currently in network")
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['city', 'provider_name']
        verbose_name = _("Funeral Service Provider")
        verbose_name_plural = _("Funeral Service Providers")
        indexes = [
            models.Index(fields=['funeral_policy', 'city']),
        ]
    
    def __str__(self):
        return f"{self.provider_name} - {self.city}"


class FuneralPolicyBenefit(models.Model):
    """
    Model for additional benefits included in funeral policies.
    Tracks special benefits beyond basic cover.
    """
    
    class BenefitType(models.TextChoices):
        CASH = 'CASH', _('Cash Benefit')
        SERVICE = 'SERVICE', _('Funeral Service')
        REPATRIATION = 'REPATRIATION', _('Repatriation')
        GROCERY = 'GROCERY', _('Grocery Benefit')
        TRANSPORT = 'TRANSPORT', _('Transport')
        MEMORIAL = 'MEMORIAL', _('Memorial Service')
        COUNSELING = 'COUNSELING', _('Grief Counseling')
        LEGAL = 'LEGAL', _('Legal Assistance')
        OTHER = 'OTHER', _('Other Benefit')
    
    funeral_policy = models.ForeignKey(
        FuneralPolicy,
        on_delete=models.CASCADE,
        related_name='additional_benefits'
    )
    
    benefit_type = models.CharField(
        max_length=20,
        choices=BenefitType.choices,
        help_text=_("Type of benefit")
    )
    
    benefit_name = models.CharField(
        max_length=255,
        help_text=_("Name of the benefit")
    )
    
    description = models.TextField(
        help_text=_("Detailed description of the benefit")
    )
    
    benefit_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        help_text=_("Monetary value of benefit (if applicable)")
    )
    
    is_included = models.BooleanField(
        default=True,
        help_text=_("Whether benefit is included in base policy")
    )
    
    additional_premium = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=0.00,
        validators=[MinValueValidator(0)],
        help_text=_("Additional premium if optional")
    )
    
    waiting_period_months = models.PositiveIntegerField(
        default=0,
        help_text=_("Waiting period for this benefit (months)")
    )
    
    is_active = models.BooleanField(
        default=True,
        help_text=_("Whether benefit is currently active")
    )
    
    display_order = models.PositiveIntegerField(
        default=0,
        help_text=_("Display order")
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['funeral_policy', 'display_order', 'benefit_name']
        verbose_name = _("Funeral Policy Benefit")
        verbose_name_plural = _("Funeral Policy Benefits")
        indexes = [
            models.Index(fields=['funeral_policy', 'benefit_type']),
        ]
    
    def __str__(self):
        return f"{self.benefit_name} - {self.funeral_policy.name}"


class ClaimRequirement(models.Model):
    """
    Model for tracking claim requirements and documentation needed.
    """
    
    class DocumentType(models.TextChoices):
        DEATH_CERTIFICATE = 'DEATH_CERT', _('Death Certificate')
        ID_DOCUMENT = 'ID_DOC', _('ID Document')
        POLICE_REPORT = 'POLICE_REPORT', _('Police Report')
        MEDICAL_REPORT = 'MEDICAL_REPORT', _('Medical Report')
        CLAIM_FORM = 'CLAIM_FORM', _('Claim Form')
        PROOF_OF_RELATIONSHIP = 'PROOF_REL', _('Proof of Relationship')
        BANK_DETAILS = 'BANK_DETAILS', _('Bank Details')
        BURIAL_ORDER = 'BURIAL_ORDER', _('Burial Order')
        OTHER = 'OTHER', _('Other Document')
    
    funeral_policy = models.ForeignKey(
        FuneralPolicy,
        on_delete=models.CASCADE,
        related_name='claim_requirements'
    )
    
    document_type = models.CharField(
        max_length=20,
        choices=DocumentType.choices,
        help_text=_("Type of required document")
    )
    
    document_name = models.CharField(
        max_length=255,
        help_text=_("Name of required document")
    )
    
    description = models.TextField(
        help_text=_("Description of what's required")
    )
    
    is_mandatory = models.BooleanField(
        default=True,
        help_text=_("Whether document is mandatory")
    )
    
    applies_to_natural_death = models.BooleanField(
        default=True,
        help_text=_("Whether required for natural death claims")
    )
    
    applies_to_accidental_death = models.BooleanField(
        default=True,
        help_text=_("Whether required for accidental death claims")
    )
    
    submission_deadline_days = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text=_("Days within which document must be submitted")
    )
    
    display_order = models.PositiveIntegerField(
        default=0,
        help_text=_("Display order")
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['funeral_policy', 'display_order']
        verbose_name = _("Claim Requirement")
        verbose_name_plural = _("Claim Requirements")
        indexes = [
            models.Index(fields=['funeral_policy']),
        ]
    
    def __str__(self):
        return f"{self.document_name} - {self.funeral_policy.name}"