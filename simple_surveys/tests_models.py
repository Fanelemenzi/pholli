"""
Unit tests for SimpleSurvey models.
Tests SimpleSurvey model and related functionality.
"""

from django.test import TestCase
from django.core.exceptions import ValidationError
from decimal import Decimal
from datetime import date

from .models import SimpleSurvey


class SimpleSurveyModelTest(TestCase):
    """Test SimpleSurvey model functionality."""
    
    def setUp(self):
        """Set up test data."""
        self.health_survey_data = {
            'first_name': 'John',
            'last_name': 'Doe',
            'date_of_birth': date(1990, 1, 1),
            'email': 'john@example.com',
            'phone': '+268123456789',
            'insurance_type': SimpleSurvey.InsuranceType.HEALTH,
            'preferred_annual_limit': Decimal('50000.00'),
            'household_income': Decimal('10000.00'),
            'wants_in_hospital_benefit': True,
            'wants_out_hospital_benefit': True,
            'needs_chronic_medication': False
        }
        
        self.funeral_survey_data = {
            'first_name': 'Jane',
            'last_name': 'Smith',
            'date_of_birth': date(1985, 5, 15),
            'email': 'jane@example.com',
            'phone': '+268987654321',
            'insurance_type': SimpleSurvey.InsuranceType.FUNERAL,
            'preferred_cover_amount': Decimal('25000.00'),
            'marital_status': 'Married',
            'gender': 'Female',
            'net_income': Decimal('8000.00')
        }
    
    def test_health_survey_creation(self):
        """Test creating a valid health survey."""
        survey = SimpleSurvey.objects.create(**self.health_survey_data)
        
        self.assertEqual(survey.first_name, 'John')
        self.assertEqual(survey.insurance_type, SimpleSurvey.InsuranceType.HEALTH)
        self.assertEqual(survey.preferred_annual_limit, Decimal('50000.00'))
        self.assertTrue(survey.wants_in_hospital_benefit)
        self.assertEqual(str(survey), "John Doe - Health Policies")
    
    def test_funeral_survey_creation(self):
        """Test creating a valid funeral survey."""
        survey = SimpleSurvey.objects.create(**self.funeral_survey_data)
        
        self.assertEqual(survey.first_name, 'Jane')
        self.assertEqual(survey.insurance_type, SimpleSurvey.InsuranceType.FUNERAL)
        self.assertEqual(survey.preferred_cover_amount, Decimal('25000.00'))
        self.assertEqual(survey.marital_status, 'Married')
        self.assertEqual(str(survey), "Jane Smith - Funeral Policies")
    
    def test_health_survey_validation_complete(self):
        """Test validation of complete health survey."""
        survey = SimpleSurvey(**self.health_survey_data)
        survey.full_clean()  # Should not raise ValidationError
        self.assertTrue(survey.is_complete())
        self.assertEqual(survey.get_missing_fields(), [])
    
    def test_funeral_survey_validation_complete(self):
        """Test validation of complete funeral survey."""
        survey = SimpleSurvey(**self.funeral_survey_data)
        survey.full_clean()  # Should not raise ValidationError
        self.assertTrue(survey.is_complete())
        self.assertEqual(survey.get_missing_fields(), [])
    
    def test_health_survey_validation_missing_annual_limit(self):
        """Test validation when health survey missing annual limit."""
        data = self.health_survey_data.copy()
        data['preferred_annual_limit'] = None
        
        survey = SimpleSurvey(**data)
        with self.assertRaises(ValidationError) as context:
            survey.full_clean()
        
        self.assertIn('preferred_annual_limit', context.exception.message_dict)
        self.assertFalse(survey.is_complete())
        self.assertIn('preferred_annual_limit', survey.get_missing_fields())
    
    def test_health_survey_validation_negative_annual_limit(self):
        """Test validation when health survey has negative annual limit."""
        data = self.health_survey_data.copy()
        data['preferred_annual_limit'] = Decimal('-1000.00')
        
        survey = SimpleSurvey(**data)
        with self.assertRaises(ValidationError) as context:
            survey.full_clean()
        
        self.assertIn('preferred_annual_limit', context.exception.message_dict)
    
    def test_health_survey_validation_missing_household_income(self):
        """Test validation when health survey missing household income."""
        data = self.health_survey_data.copy()
        data['household_income'] = None
        
        survey = SimpleSurvey(**data)
        with self.assertRaises(ValidationError) as context:
            survey.full_clean()
        
        self.assertIn('household_income', context.exception.message_dict)
    
    def test_health_survey_validation_negative_household_income(self):
        """Test validation when health survey has negative household income."""
        data = self.health_survey_data.copy()
        data['household_income'] = Decimal('-5000.00')
        
        survey = SimpleSurvey(**data)
        with self.assertRaises(ValidationError) as context:
            survey.full_clean()
        
        self.assertIn('household_income', context.exception.message_dict)
    
    def test_health_survey_validation_missing_benefit_preferences(self):
        """Test validation when health survey missing benefit preferences."""
        data = self.health_survey_data.copy()
        data['wants_in_hospital_benefit'] = None
        data['wants_out_hospital_benefit'] = None
        data['needs_chronic_medication'] = None
        
        survey = SimpleSurvey(**data)
        with self.assertRaises(ValidationError) as context:
            survey.full_clean()
        
        errors = context.exception.message_dict
        self.assertIn('wants_in_hospital_benefit', errors)
        self.assertIn('wants_out_hospital_benefit', errors)
        self.assertIn('needs_chronic_medication', errors)
    
    def test_funeral_survey_validation_missing_cover_amount(self):
        """Test validation when funeral survey missing cover amount."""
        data = self.funeral_survey_data.copy()
        data['preferred_cover_amount'] = None
        
        survey = SimpleSurvey(**data)
        with self.assertRaises(ValidationError) as context:
            survey.full_clean()
        
        self.assertIn('preferred_cover_amount', context.exception.message_dict)
    
    def test_funeral_survey_validation_negative_cover_amount(self):
        """Test validation when funeral survey has negative cover amount."""
        data = self.funeral_survey_data.copy()
        data['preferred_cover_amount'] = Decimal('-10000.00')
        
        survey = SimpleSurvey(**data)
        with self.assertRaises(ValidationError) as context:
            survey.full_clean()
        
        self.assertIn('preferred_cover_amount', context.exception.message_dict)
    
    def test_funeral_survey_validation_missing_marital_status(self):
        """Test validation when funeral survey missing marital status."""
        data = self.funeral_survey_data.copy()
        data['marital_status'] = ''
        
        survey = SimpleSurvey(**data)
        with self.assertRaises(ValidationError) as context:
            survey.full_clean()
        
        self.assertIn('marital_status', context.exception.message_dict)
    
    def test_funeral_survey_validation_missing_gender(self):
        """Test validation when funeral survey missing gender."""
        data = self.funeral_survey_data.copy()
        data['gender'] = ''
        
        survey = SimpleSurvey(**data)
        with self.assertRaises(ValidationError) as context:
            survey.full_clean()
        
        self.assertIn('gender', context.exception.message_dict)
    
    def test_funeral_survey_validation_missing_net_income(self):
        """Test validation when funeral survey missing net income."""
        data = self.funeral_survey_data.copy()
        data['net_income'] = None
        
        survey = SimpleSurvey(**data)
        with self.assertRaises(ValidationError) as context:
            survey.full_clean()
        
        self.assertIn('net_income', context.exception.message_dict)
    
    def test_funeral_survey_validation_negative_net_income(self):
        """Test validation when funeral survey has negative net income."""
        data = self.funeral_survey_data.copy()
        data['net_income'] = Decimal('-3000.00')
        
        survey = SimpleSurvey(**data)
        with self.assertRaises(ValidationError) as context:
            survey.full_clean()
        
        self.assertIn('net_income', context.exception.message_dict)
    
    def test_get_preferences_dict_health(self):
        """Test get_preferences_dict for health survey."""
        survey = SimpleSurvey(**self.health_survey_data)
        preferences = survey.get_preferences_dict()
        
        expected_preferences = {
            'annual_limit_per_member': Decimal('50000.00'),
            'monthly_household_income': Decimal('10000.00'),
            'in_hospital_benefit': True,
            'out_hospital_benefit': True,
            'chronic_medication_availability': False
        }
        
        self.assertEqual(preferences, expected_preferences)
    
    def test_get_preferences_dict_funeral(self):
        """Test get_preferences_dict for funeral survey."""
        survey = SimpleSurvey(**self.funeral_survey_data)
        preferences = survey.get_preferences_dict()
        
        expected_preferences = {
            'cover_amount': Decimal('25000.00'),
            'marital_status_requirement': 'Married',
            'gender_requirement': 'Female',
            'monthly_net_income': Decimal('8000.00')
        }
        
        self.assertEqual(preferences, expected_preferences)
    
    def test_get_preferences_dict_unknown_type(self):
        """Test get_preferences_dict for unknown insurance type."""
        data = self.health_survey_data.copy()
        survey = SimpleSurvey(**data)
        survey.insurance_type = 'UNKNOWN'  # Invalid type
        
        preferences = survey.get_preferences_dict()
        self.assertEqual(preferences, {})
    
    def test_survey_optional_fields(self):
        """Test that email and phone are optional."""
        data = self.health_survey_data.copy()
        data['email'] = ''
        data['phone'] = ''
        
        survey = SimpleSurvey(**data)
        survey.full_clean()  # Should not raise ValidationError
        
        survey.save()
        self.assertEqual(survey.email, '')
        self.assertEqual(survey.phone, '')
    
    def test_survey_insurance_type_choices(self):
        """Test insurance type choices validation."""
        data = self.health_survey_data.copy()
        survey = SimpleSurvey(**data)
        
        # Valid choices
        survey.insurance_type = SimpleSurvey.InsuranceType.HEALTH
        survey.full_clean()  # Should not raise
        
        survey.insurance_type = SimpleSurvey.InsuranceType.FUNERAL
        survey.full_clean()  # Should not raise
    
    def test_survey_mixed_type_validation(self):
        """Test that surveys can't have mixed type data."""
        # Create survey with health type but funeral data
        data = {
            'first_name': 'Mixed',
            'last_name': 'Survey',
            'date_of_birth': date(1990, 1, 1),
            'insurance_type': SimpleSurvey.InsuranceType.HEALTH,
            # Health fields missing, funeral fields present
            'preferred_cover_amount': Decimal('25000.00'),
            'marital_status': 'Single',
            'gender': 'Male',
            'net_income': Decimal('5000.00')
        }
        
        survey = SimpleSurvey(**data)
        with self.assertRaises(ValidationError):
            survey.full_clean()
    
    def test_survey_partial_data_validation(self):
        """Test validation with partial data."""
        # Health survey with only some fields
        data = {
            'first_name': 'Partial',
            'last_name': 'Survey',
            'date_of_birth': date(1990, 1, 1),
            'insurance_type': SimpleSurvey.InsuranceType.HEALTH,
            'preferred_annual_limit': Decimal('50000.00'),
            # Missing other required health fields
        }
        
        survey = SimpleSurvey(**data)
        self.assertFalse(survey.is_complete())
        
        missing_fields = survey.get_missing_fields()
        self.assertIn('household_income', missing_fields)
        self.assertIn('wants_in_hospital_benefit', missing_fields)
        self.assertIn('wants_out_hospital_benefit', missing_fields)
        self.assertIn('needs_chronic_medication', missing_fields)
    
    def test_survey_model_meta(self):
        """Test model meta configuration."""
        # Test verbose names
        self.assertEqual(SimpleSurvey._meta.verbose_name, "Simple Survey")
        self.assertEqual(SimpleSurvey._meta.verbose_name_plural, "Simple Surveys")
        
        # Test indexes exist
        index_fields = [index.fields for index in SimpleSurvey._meta.indexes]
        self.assertIn(['insurance_type', 'created_at'], index_fields)
        self.assertIn(['created_at'], index_fields)
    
    def test_survey_timestamps(self):
        """Test that timestamps are set correctly."""
        survey = SimpleSurvey.objects.create(**self.health_survey_data)
        
        self.assertIsNotNone(survey.created_at)
        self.assertIsNotNone(survey.updated_at)
        
        # Update survey and check updated_at changes
        original_updated_at = survey.updated_at
        survey.first_name = 'Updated'
        survey.save()
        
        self.assertGreater(survey.updated_at, original_updated_at)
    
    def test_survey_decimal_precision(self):
        """Test decimal field precision and scale."""
        # Test maximum values within precision limits
        data = self.health_survey_data.copy()
        data['preferred_annual_limit'] = Decimal('9999999999.99')  # Max for 12,2
        data['household_income'] = Decimal('99999999.99')  # Max for 10,2
        
        survey = SimpleSurvey(**data)
        survey.full_clean()  # Should not raise ValidationError
        
        survey.save()
        self.assertEqual(survey.preferred_annual_limit, Decimal('9999999999.99'))
        self.assertEqual(survey.household_income, Decimal('99999999.99'))
    
    def test_survey_boolean_field_handling(self):
        """Test boolean field handling for benefit preferences."""
        data = self.health_survey_data.copy()
        
        # Test all combinations of boolean values
        boolean_combinations = [
            (True, True, True),
            (True, True, False),
            (True, False, True),
            (True, False, False),
            (False, True, True),
            (False, True, False),
            (False, False, True),
            (False, False, False),
        ]
        
        for in_hospital, out_hospital, chronic_med in boolean_combinations:
            data['wants_in_hospital_benefit'] = in_hospital
            data['wants_out_hospital_benefit'] = out_hospital
            data['needs_chronic_medication'] = chronic_med
            
            survey = SimpleSurvey(**data)
            survey.full_clean()  # Should not raise ValidationError
            
            preferences = survey.get_preferences_dict()
            self.assertEqual(preferences['in_hospital_benefit'], in_hospital)
            self.assertEqual(preferences['out_hospital_benefit'], out_hospital)
            self.assertEqual(preferences['chronic_medication_availability'], chronic_med)