from django.db import models
from django.core.validators import EmailValidator, URLValidator
from django.utils.translation import gettext_lazy as _


def default_custom_config():
    """Return default empty dict for custom_config field."""
    return {}


class Organization(models.Model):
    """
    Model representing insurance companies/providers in the platform.
    Each organization can create and manage their own policies.
    """
    
    class VerificationStatus(models.TextChoices):
        PENDING = 'PENDING', _('Pending Verification')
        VERIFIED = 'VERIFIED', _('Verified')
        REJECTED = 'REJECTED', _('Rejected')
        SUSPENDED = 'SUSPENDED', _('Suspended')
    
    # Basic Information
    name = models.CharField(
        max_length=255,
        unique=True,
        help_text=_("Official name of the insurance organization")
    )
    
    logo = models.ImageField(
        upload_to='organizations/logos/',
        blank=True,
        null=True,
        help_text=_("Organization logo (recommended: 400x400px)")
    )
    
    description = models.TextField(
        help_text=_("Brief description of the organization and its services")
    )
    
    # Contact Details
    email = models.EmailField(
        validators=[EmailValidator()],
        help_text=_("Primary contact email")
    )
    
    phone = models.CharField(
        max_length=20,
        help_text=_("Primary contact phone number")
    )
    
    alternative_phone = models.CharField(
        max_length=20,
        blank=True,
        help_text=_("Alternative contact phone number")
    )
    
    website = models.URLField(
        validators=[URLValidator()],
        blank=True,
        help_text=_("Organization website URL")
    )
    
    # Address Information
    address_line1 = models.CharField(
        max_length=255,
        help_text=_("Street address")
    )
    
    address_line2 = models.CharField(
        max_length=255,
        blank=True,
        help_text=_("Apartment, suite, unit, etc.")
    )
    
    city = models.CharField(
        max_length=100,
        help_text=_("City")
    )
    
    state_province = models.CharField(
        max_length=100,
        help_text=_("State or Province")
    )
    
    postal_code = models.CharField(
        max_length=20,
        help_text=_("Postal/ZIP code")
    )
    
    country = models.CharField(
        max_length=100,
        default='South Africa',
        help_text=_("Country")
    )
    
    # Verification and Status
    verification_status = models.CharField(
        max_length=20,
        choices=VerificationStatus.choices,
        default=VerificationStatus.PENDING,
        help_text=_("Current verification status")
    )
    
    is_active = models.BooleanField(
        default=True,
        help_text=_("Whether the organization is active on the platform")
    )
    
    verified_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_("Date and time when organization was verified")
    )
    
    # Registration and License Information
    registration_number = models.CharField(
        max_length=100,
        unique=True,
        help_text=_("Official business registration number")
    )
    
    license_number = models.CharField(
        max_length=100,
        unique=True,
        help_text=_("Insurance license number")
    )
    
    # Configuration
    max_policies = models.PositiveIntegerField(
        default=50,
        help_text=_("Maximum number of policies this organization can create")
    )
    
    commission_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0.00,
        help_text=_("Commission rate percentage for this organization")
    )
    
    custom_config = models.JSONField(
        default=default_custom_config,
        blank=True,
        help_text=_("Custom configuration settings (JSON format)")
    )
    
    # Additional Information
    year_established = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text=_("Year the organization was established")
    )
    
    employee_count_range = models.CharField(
        max_length=50,
        blank=True,
        help_text=_("Employee count range (e.g., '50-100', '100-500')")
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['name']
        verbose_name = _("Organization")
        verbose_name_plural = _("Organizations")
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['verification_status']),
            models.Index(fields=['is_active']),
        ]
    
    def __str__(self):
        return self.name
    
    def get_active_policies_count(self):
        """Returns the count of active policies for this organization."""
        return self.policies.filter(is_active=True).count()
    
    def can_create_policy(self):
        """Check if organization can create more policies."""
        return self.get_active_policies_count() < self.max_policies
    
    def get_full_address(self):
        """Returns formatted full address."""
        address_parts = [
            self.address_line1,
            self.address_line2,
            self.city,
            self.state_province,
            self.postal_code,
            self.country
        ]
        return ', '.join(filter(None, address_parts))
    
    @property
    def is_verified(self):
        """Check if organization is verified."""
        return self.verification_status == self.VerificationStatus.VERIFIED


class OrganizationContact(models.Model):
    """
    Model for additional contact persons within an organization.
    Allows multiple points of contact for different purposes.
    """
    
    class ContactRole(models.TextChoices):
        PRIMARY = 'PRIMARY', _('Primary Contact')
        BILLING = 'BILLING', _('Billing Contact')
        TECHNICAL = 'TECHNICAL', _('Technical Contact')
        CLAIMS = 'CLAIMS', _('Claims Contact')
        SUPPORT = 'SUPPORT', _('Support Contact')
    
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name='contacts'
    )
    
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    
    role = models.CharField(
        max_length=20,
        choices=ContactRole.choices,
        default=ContactRole.PRIMARY
    )
    
    job_title = models.CharField(
        max_length=100,
        blank=True,
        help_text=_("Job title or position")
    )
    
    email = models.EmailField(
        validators=[EmailValidator()],
        help_text=_("Contact email address")
    )
    
    phone = models.CharField(
        max_length=20,
        help_text=_("Contact phone number")
    )
    
    is_primary = models.BooleanField(
        default=False,
        help_text=_("Mark as primary contact for the organization")
    )
    
    is_active = models.BooleanField(
        default=True,
        help_text=_("Whether this contact is currently active")
    )
    
    notes = models.TextField(
        blank=True,
        help_text=_("Additional notes about this contact")
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-is_primary', 'last_name', 'first_name']
        verbose_name = _("Organization Contact")
        verbose_name_plural = _("Organization Contacts")
        indexes = [
            models.Index(fields=['organization', 'is_primary']),
        ]
    
    def __str__(self):
        return f"{self.get_full_name()} - {self.organization.name}"
    
    def get_full_name(self):
        """Returns the contact's full name."""
        return f"{self.first_name} {self.last_name}"
    
    def save(self, *args, **kwargs):
        """Ensure only one primary contact per organization."""
        if self.is_primary:
            OrganizationContact.objects.filter(
                organization=self.organization,
                is_primary=True
            ).exclude(pk=self.pk).update(is_primary=False)
        super().save(*args, **kwargs)


class OrganizationDocument(models.Model):
    """
    Model for storing organization-related documents.
    Used for licenses, certificates, and other verification documents.
    """
    
    class DocumentType(models.TextChoices):
        LICENSE = 'LICENSE', _('Insurance License')
        REGISTRATION = 'REGISTRATION', _('Business Registration')
        TAX_CERTIFICATE = 'TAX_CERT', _('Tax Certificate')
        CERTIFICATE = 'CERTIFICATE', _('Certificate')
        OTHER = 'OTHER', _('Other Document')
    
    organization = models.ForeignKey(
        Organization,
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
        help_text=_("Document title or name")
    )
    
    file = models.FileField(
        upload_to='organizations/documents/',
        help_text=_("Upload document file (PDF, DOCX, JPG, PNG)")
    )
    
    description = models.TextField(
        blank=True,
        help_text=_("Brief description of the document")
    )
    
    issue_date = models.DateField(
        null=True,
        blank=True,
        help_text=_("Date when document was issued")
    )
    
    expiry_date = models.DateField(
        null=True,
        blank=True,
        help_text=_("Date when document expires (if applicable)")
    )
    
    is_verified = models.BooleanField(
        default=False,
        help_text=_("Whether this document has been verified by admin")
    )
    
    verified_by = models.ForeignKey(
        'auth.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='verified_documents'
    )
    
    verified_at = models.DateTimeField(
        null=True,
        blank=True
    )
    
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-uploaded_at']
        verbose_name = _("Organization Document")
        verbose_name_plural = _("Organization Documents")
        indexes = [
            models.Index(fields=['organization', 'document_type']),
            models.Index(fields=['is_verified']),
        ]
    
    def __str__(self):
        return f"{self.title} - {self.organization.name}"
    
    @property
    def is_expired(self):
        """Check if document has expired."""
        if self.expiry_date:
            from django.utils import timezone
            return self.expiry_date < timezone.now().date()
        return False