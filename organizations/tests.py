from django.test import TestCase
from django.utils import timezone
from datetime import timedelta
from .models import Organization, OrganizationContact, OrganizationDocument


class OrganizationModelTest(TestCase):
    """
    Test cases for the Organization model.
    Tests model methods, properties, and business logic.
    """
    
    def setUp(self):
        """Set up test data."""
        self.organization = Organization.objects.create(
            name="Test Insurance Co",
            description="Test insurance company",
            email="test@insurance.com",
            phone="+1234567890",
            address_line1="123 Test Street",
            city="Test City",
            state_province="Test Province",
            postal_code="12345",
            registration_number="REG123456",
            license_number="LIC123456",
            license_expiry_date=timezone.now().date() + timedelta(days=365)
        )
    
    def test_organization_creation(self):
        """Test that organization is created successfully."""
        self.assertEqual(self.organization.name, "Test Insurance Co")
        self.assertEqual(self.organization.verification_status, 'PENDING')
        self.assertTrue(self.organization.is_active)
    
    def test_slug_generation(self):
        """Test that slug is automatically generated from name."""
        self.assertEqual(self.organization.slug, "test-insurance-co")
    
    def test_unique_slug(self):
        """Test that duplicate names generate unique slugs."""
        org2 = Organization.objects.create(
            name="Test Insurance Co",
            description="Another test company",
            email="test2@insurance.com",
            phone="+1234567891",
            address_line1="456 Test Street",
            city="Test City",
            state_province="Test Province",
            postal_code="12345",
            registration_number="REG123457",
            license_number="LIC123457",
            license_expiry_date=timezone.now().date() + timedelta(days=365)
        )
        self.assertNotEqual(self.organization.slug, org2.slug)
        self.assertTrue(org2.slug.startswith("test-insurance-co"))
    
    def test_is_verified_property(self):
        """Test is_verified property returns correct status."""
        self.assertFalse(self.organization.is_verified)
        
        self.organization.verification_status = Organization.VerificationStatus.VERIFIED
        self.organization.save()
        self.assertTrue(self.organization.is_verified)
    
    def test_license_is_expired_property(self):
        """Test license expiry checking."""
        self.assertFalse(self.organization.license_is_expired)
        
        self.organization.license_expiry_date = timezone.now().date() - timedelta(days=1)
        self.organization.save()
        self.assertTrue(self.organization.license_is_expired)
    
    def test_get_full_address(self):
        """Test full address formatting."""
        expected = "123 Test Street, Test City, Test Province, 12345, South Africa"
        self.assertEqual(self.organization.get_full_address(), expected)
    
    def test_can_create_policy(self):
        """Test policy creation limit checking."""
        self.organization.max_policies = 5
        self.organization.save()
        self.assertTrue(self.organization.can_create_policy())
    
    def test_string_representation(self):
        """Test __str__ method."""
        self.assertEqual(str(self.organization), "Test Insurance Co")


class OrganizationContactModelTest(TestCase):
    """
    Test cases for the OrganizationContact model.
    """
    
    def setUp(self):
        """Set up test data."""
        self.organization = Organization.objects.create(
            name="Test Insurance Co",
            description="Test insurance company",
            email="test@insurance.com",
            phone="+1234567890",
            address_line1="123 Test Street",
            city="Test City",
            state_province="Test Province",
            postal_code="12345",
            registration_number="REG123456",
            license_number="LIC123456",
            license_expiry_date=timezone.now().date() + timedelta(days=365)
        )
        
        self.contact = OrganizationContact.objects.create(
            organization=self.organization,
            first_name="John",
            last_name="Doe",
            role=OrganizationContact.ContactRole.PRIMARY,
            email="john@insurance.com",
            phone="+1234567890",
            is_primary=True
        )
    
    def test_contact_creation(self):
        """Test that contact is created successfully."""
        self.assertEqual(self.contact.first_name, "John")
        self.assertEqual(self.contact.last_name, "Doe")
        self.assertTrue(self.contact.is_primary)
    
    def test_get_full_name(self):
        """Test full name method."""
        self.assertEqual(self.contact.get_full_name(), "John Doe")
    
    def test_single_primary_contact(self):
        """Test that only one primary contact can exist per organization."""
        contact2 = OrganizationContact.objects.create(
            organization=self.organization,
            first_name="Jane",
            last_name="Smith",
            role=OrganizationContact.ContactRole.BILLING,
            email="jane@insurance.com",
            phone="+1234567891",
            is_primary=True
        )
        
        # Refresh the first contact from database
        self.contact.refresh_from_db()
        
        # First contact should no longer be primary
        self.assertFalse(self.contact.is_primary)
        # Second contact should be primary
        self.assertTrue(contact2.is_primary)
    
    def test_string_representation(self):
        """Test __str__ method."""
        expected = "John Doe - Test Insurance Co"
        self.assertEqual(str(self.contact), expected)


class OrganizationDocumentModelTest(TestCase):
    """
    Test cases for the OrganizationDocument model.
    """
    
    def setUp(self):
        """Set up test data."""
        self.organization = Organization.objects.create(
            name="Test Insurance Co",
            description="Test insurance company",
            email="test@insurance.com",
            phone="+1234567890",
            address_line1="123 Test Street",
            city="Test City",
            state_province="Test Province",
            postal_code="12345",
            registration_number="REG123456",
            license_number="LIC123456",
            license_expiry_date=timezone.now().date() + timedelta(days=365)
        )
        
        self.document = OrganizationDocument.objects.create(
            organization=self.organization,
            document_type=OrganizationDocument.DocumentType.LICENSE,
            title="Insurance License",
            issue_date=timezone.now().date(),
            expiry_date=timezone.now().date() + timedelta(days=365)
        )
    
    def test_document_creation(self):
        """Test that document is created successfully."""
        self.assertEqual(self.document.title, "Insurance License")
        self.assertFalse(self.document.is_verified)
    
    def test_is_expired_property(self):
        """Test document expiry checking."""
        self.assertFalse(self.document.is_expired)
        
        self.document.expiry_date = timezone.now().date() - timedelta(days=1)
        self.document.save()
        self.assertTrue(self.document.is_expired)
    
    def test_is_expired_with_no_expiry(self):
        """Test is_expired returns False when no expiry date set."""
        self.document.expiry_date = None
        self.document.save()
        self.assertFalse(self.document.is_expired)
    
    def test_string_representation(self):
        """Test __str__ method."""
        expected = "Insurance License - Test Insurance Co"
        self.assertEqual(str(self.document), expected)


class OrganizationManagerTest(TestCase):
    """
    Test cases for custom manager methods.
    """
    
    def setUp(self):
        """Set up test data with multiple organizations."""
        self.verified_org = Organization.objects.create(
            name="Verified Insurance Co",
            description="Verified company",
            email="verified@insurance.com",
            phone="+1234567890",
            address_line1="123 Verified Street",
            city="Test City",
            state_province="Test Province",
            postal_code="12345",
            registration_number="REG123456",
            license_number="LIC123456",
            license_expiry_date=timezone.now().date() + timedelta(days=365),
            verification_status=Organization.VerificationStatus.VERIFIED,
            is_active=True
        )
        
        self.pending_org = Organization.objects.create(
            name="Pending Insurance Co",
            description="Pending company",
            email="pending@insurance.com",
            phone="+1234567891",
            address_line1="456 Pending Street",
            city="Test City",
            state_province="Test Province",
            postal_code="12345",
            registration_number="REG123457",
            license_number="LIC123457",
            license_expiry_date=timezone.now().date() + timedelta(days=365),
            verification_status=Organization.VerificationStatus.PENDING,
            is_active=True
        )
        
        self.expired_org = Organization.objects.create(
            name="Expired Insurance Co",
            description="Expired license company",
            email="expired@insurance.com",
            phone="+1234567892",
            address_line1="789 Expired Street",
            city="Test City",
            state_province="Test Province",
            postal_code="12345",
            registration_number="REG123458",
            license_number="LIC123458",
            license_expiry_date=timezone.now().date() - timedelta(days=10),
            verification_status=Organization.VerificationStatus.VERIFIED,
            is_active=True
        )
    
    def test_active_queryset(self):
        """Test active() manager method."""
        active_orgs = Organization.objects.active()
        self.assertEqual(active_orgs.count(), 3)
    
    def test_verified_queryset(self):
        """Test verified() manager method."""
        verified_orgs = Organization.objects.verified()
        self.assertEqual(verified_orgs.count(), 2)
        self.assertIn(self.verified_org, verified_orgs)
        self.assertNotIn(self.pending_org, verified_orgs)
    
    def test_active_and_verified_queryset(self):
        """Test active_and_verified() manager method."""
        active_verified = Organization.objects.active_and_verified()
        self.assertEqual(active_verified.count(), 2)
    
    def test_pending_verification_queryset(self):
        """Test pending_verification() manager method."""
        pending = Organization.objects.pending_verification()
        self.assertEqual(pending.count(), 1)
        self.assertEqual(pending.first(), self.pending_org)
    
    def test_with_expired_licenses_queryset(self):
        """Test with_expired_licenses() manager method."""
        expired = Organization.objects.with_expired_licenses()
        self.assertEqual(expired.count(), 1)
        self.assertEqual(expired.first(), self.expired_org)
    
    def test_with_expiring_licenses_queryset(self):
        """Test with_expiring_licenses() manager method."""
        expiring = Organization.objects.with_expiring_licenses(days=400)
        self.assertGreaterEqual(expiring.count(), 2)