from django import forms
from django.core.exceptions import ValidationError
from .models import SimpleSurvey


# Benefit level choices with descriptions (from requirements)
HOSPITAL_BENEFIT_CHOICES = [
    ('no_cover', 'No hospital cover - I do not need cover for hospital admission'),
    ('basic', 'Basic hospital care - Covers admission and standard hospital treatment'),
    ('moderate', 'Moderate hospital care - Covers admission, procedures, and specialist treatment'),
    ('extensive', 'Extensive hospital care - Covers most hospital needs, including major procedures'),
    ('comprehensive', 'Comprehensive hospital care - Covers all hospital-related treatment and services'),
]

OUT_HOSPITAL_BENEFIT_CHOICES = [
    ('no_cover', 'No out-of-hospital cover - No cover for day-to-day medical care'),
    ('basic_visits', 'Basic clinic visits - Covers GP/clinic visits only'),
    ('routine_care', 'Routine medical care - Covers GP visits and basic medication'),
    ('extended_care', 'Extended medical care - Covers GP visits, specialists, and diagnostics'),
    ('comprehensive_care', 'Comprehensive day-to-day care - Covers most medical needs outside hospital, including chronic care'),
]

ANNUAL_LIMIT_FAMILY_RANGES = [
    ('10k-50k', 'R10,000 - R50,000 - Basic family coverage for routine medical needs'),
    ('50k-100k', 'R50,001 - R100,000 - Standard family coverage for most medical situations'),
    ('100k-250k', 'R100,001 - R250,000 - Enhanced family coverage including specialist care'),
    ('250k-500k', 'R250,001 - R500,000 - Comprehensive family coverage for major medical needs'),
    ('500k-1m', 'R500,001 - R1,000,000 - Premium family coverage for extensive medical care'),
    ('1m-2m', 'R1,000,001 - R2,000,000 - High-end family coverage for complex medical needs'),
    ('2m-5m', 'R2,000,001 - R5,000,000 - Luxury family coverage for all medical scenarios'),
    ('5m-plus', 'R5,000,001+ - Unlimited family coverage preferred'),
    ('not_sure', 'Not sure / Need guidance - Help me choose based on my situation'),
]

ANNUAL_LIMIT_MEMBER_RANGES = [
    ('10k-25k', 'R10,000 - R25,000 - Basic individual coverage for routine care'),
    ('25k-50k', 'R25,001 - R50,000 - Standard individual coverage for most needs'),
    ('50k-100k', 'R50,001 - R100,000 - Enhanced individual coverage including specialists'),
    ('100k-200k', 'R100,001 - R200,000 - Comprehensive individual coverage for major needs'),
    ('200k-500k', 'R200,001 - R500,000 - Premium individual coverage for extensive care'),
    ('500k-1m', 'R500,001 - R1,000,000 - High-end individual coverage for complex needs'),
    ('1m-2m', 'R1,000,001 - R2,000,000 - Luxury individual coverage for all scenarios'),
    ('2m-plus', 'R2,000,001+ - Unlimited individual coverage preferred'),
    ('not_sure', 'Not sure / Need guidance - Help me choose based on my situation'),
]


class SimpleSurveyForm(forms.ModelForm):
    """
    Form for SimpleSurvey model with dynamic field display based on insurance type.
    """
    
    class Meta:
        model = SimpleSurvey
        fields = [
            'first_name', 'last_name', 'date_of_birth', 'email', 'phone',
            'insurance_type',
            # Health fields
            'preferred_annual_limit_per_family', 'household_income',
            'wants_ambulance_coverage', 'in_hospital_benefit_level',
            'out_hospital_benefit_level', 'needs_chronic_medication',
            'annual_limit_family_range', 'annual_limit_member_range',
            # Funeral fields
            'preferred_cover_amount', 'marital_status', 'gender'
        ]
        widgets = {
            'first_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter your first name'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter your last name'
            }),
            'date_of_birth': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter your email (optional)'
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter your phone number (optional)'
            }),
            'insurance_type': forms.Select(attrs={
                'class': 'form-control',
                'id': 'insurance-type-select'
            }),
            # Health fields
            'preferred_annual_limit_per_family': forms.NumberInput(attrs={
                'class': 'form-control health-field',
                'placeholder': 'Enter preferred annual limit per family',
                'step': '0.01',
                'min': '0'
            }),
            'household_income': forms.NumberInput(attrs={
                'class': 'form-control health-field',
                'placeholder': 'Enter monthly household income',
                'step': '0.01',
                'min': '0'
            }),
            'wants_ambulance_coverage': forms.Select(
                choices=[(None, 'Select an option'), (True, 'Yes'), (False, 'No')],
                attrs={'class': 'form-control health-field'}
            ),
            'in_hospital_benefit_level': forms.RadioSelect(
                choices=HOSPITAL_BENEFIT_CHOICES,
                attrs={
                    'class': 'form-check-input health-field benefit-level-radio',
                    'data-field': 'in_hospital_benefit_level'
                }
            ),
            'out_hospital_benefit_level': forms.RadioSelect(
                choices=OUT_HOSPITAL_BENEFIT_CHOICES,
                attrs={
                    'class': 'form-check-input health-field benefit-level-radio',
                    'data-field': 'out_hospital_benefit_level'
                }
            ),
            'needs_chronic_medication': forms.Select(
                choices=[(None, 'Select an option'), (True, 'Yes'), (False, 'No')],
                attrs={'class': 'form-control health-field'}
            ),
            'annual_limit_family_range': forms.Select(
                choices=[('', 'Select a range')] + ANNUAL_LIMIT_FAMILY_RANGES,
                attrs={
                    'class': 'form-control health-field range-select',
                    'data-field': 'annual_limit_family_range'
                }
            ),
            'annual_limit_member_range': forms.Select(
                choices=[('', 'Select a range')] + ANNUAL_LIMIT_MEMBER_RANGES,
                attrs={
                    'class': 'form-control health-field range-select',
                    'data-field': 'annual_limit_member_range'
                }
            ),
            # Funeral fields
            'preferred_cover_amount': forms.NumberInput(attrs={
                'class': 'form-control funeral-field',
                'placeholder': 'Enter preferred cover amount',
                'step': '0.01',
                'min': '0'
            }),
            'marital_status': forms.Select(
                choices=[
                    ('', 'Select marital status'),
                    ('single', 'Single'),
                    ('married', 'Married'),
                    ('divorced', 'Divorced'),
                    ('widowed', 'Widowed'),
                ],
                attrs={'class': 'form-control funeral-field'}
            ),
            'gender': forms.Select(
                choices=[
                    ('', 'Select gender'),
                    ('male', 'Male'),
                    ('female', 'Female'),
                    ('other', 'Other'),
                ],
                attrs={'class': 'form-control funeral-field'}
            ),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Set field labels (only for fields that exist)
        field_labels = {
            'first_name': 'First Name',
            'last_name': 'Last Name',
            'date_of_birth': 'Date of Birth',
            'email': 'Email Address',
            'phone': 'Phone Number',
            'insurance_type': 'Insurance Type',
            # Health field labels
            'preferred_annual_limit_per_family': 'Preferred Annual Limit per Family',
            'household_income': 'Monthly Household Income',
            'wants_ambulance_coverage': 'Do you want ambulance coverage?',
            'in_hospital_benefit_level': 'What level of in-hospital cover do you need?',
            'out_hospital_benefit_level': 'What level of out-of-hospital cover do you need?',
            'needs_chronic_medication': 'Do you need chronic medication coverage?',
            'annual_limit_family_range': 'What annual limit range per family would you prefer?',
            'annual_limit_member_range': 'What annual limit range per member would you prefer?',
            # Funeral field labels
            'preferred_cover_amount': 'Preferred Cover Amount',
            'marital_status': 'Marital Status',
            'gender': 'Gender',
        }
        
        for field_name, label in field_labels.items():
            if field_name in self.fields:
                self.fields[field_name].label = label
        
        # Add help text for benefit level fields
        if 'in_hospital_benefit_level' in self.fields:
            self.fields['in_hospital_benefit_level'].help_text = 'Select the level of hospital coverage that best matches your needs.'
        
        if 'out_hospital_benefit_level' in self.fields:
            self.fields['out_hospital_benefit_level'].help_text = 'Select the level of day-to-day medical coverage that best matches your needs.'
        
        # Add help text for range fields
        if 'annual_limit_family_range' in self.fields:
            self.fields['annual_limit_family_range'].help_text = 'Choose a range that represents how much annual coverage your family might need.'
        
        if 'annual_limit_member_range' in self.fields:
            self.fields['annual_limit_member_range'].help_text = 'Choose a range that represents how much annual coverage each family member might need.'
    
    def clean(self):
        """Custom validation based on insurance type."""
        cleaned_data = super().clean()
        insurance_type = cleaned_data.get('insurance_type')
        
        if not insurance_type:
            raise ValidationError('Please select an insurance type.')
        
        # Validate health policy fields
        if insurance_type == SimpleSurvey.InsuranceType.HEALTH:
            health_errors = {}
            
            if not cleaned_data.get('preferred_annual_limit_per_family'):
                health_errors['preferred_annual_limit_per_family'] = 'This field is required for health policies.'
            elif cleaned_data.get('preferred_annual_limit_per_family') <= 0:
                health_errors['preferred_annual_limit_per_family'] = 'Annual limit per family must be greater than 0.'
            
            if not cleaned_data.get('household_income'):
                health_errors['household_income'] = 'This field is required for health policies.'
            elif cleaned_data.get('household_income') <= 0:
                health_errors['household_income'] = 'Household income must be greater than 0.'
            
            if cleaned_data.get('wants_ambulance_coverage') is None:
                health_errors['wants_ambulance_coverage'] = 'This field is required for health policies.'
            
            if not cleaned_data.get('in_hospital_benefit_level'):
                health_errors['in_hospital_benefit_level'] = 'Please select your preferred in-hospital benefit level.'
            
            if not cleaned_data.get('out_hospital_benefit_level'):
                health_errors['out_hospital_benefit_level'] = 'Please select your preferred out-of-hospital benefit level.'
            
            if cleaned_data.get('needs_chronic_medication') is None:
                health_errors['needs_chronic_medication'] = 'This field is required for health policies.'
            
            # Validate range selections (optional but helpful)
            annual_limit_family_range = cleaned_data.get('annual_limit_family_range')
            annual_limit_member_range = cleaned_data.get('annual_limit_member_range')
            
            if annual_limit_family_range and annual_limit_family_range not in [choice[0] for choice in SimpleSurvey._meta.get_field('annual_limit_family_range').choices]:
                health_errors['annual_limit_family_range'] = 'Please select a valid family annual limit range.'
            
            if annual_limit_member_range and annual_limit_member_range not in [choice[0] for choice in SimpleSurvey._meta.get_field('annual_limit_member_range').choices]:
                health_errors['annual_limit_member_range'] = 'Please select a valid member annual limit range.'
            
            if health_errors:
                raise ValidationError(health_errors)
        
        # Validate funeral policy fields
        elif insurance_type == SimpleSurvey.InsuranceType.FUNERAL:
            funeral_errors = {}
            
            if not cleaned_data.get('preferred_cover_amount'):
                funeral_errors['preferred_cover_amount'] = 'This field is required for funeral policies.'
            elif cleaned_data.get('preferred_cover_amount') <= 0:
                funeral_errors['preferred_cover_amount'] = 'Cover amount must be greater than 0.'
            
            if not cleaned_data.get('marital_status'):
                funeral_errors['marital_status'] = 'This field is required for funeral policies.'
            
            if not cleaned_data.get('gender'):
                funeral_errors['gender'] = 'This field is required for funeral policies.'
            
            if funeral_errors:
                raise ValidationError(funeral_errors)
        
        return cleaned_data


class HealthSurveyForm(SimpleSurveyForm):
    """
    Specialized form for health insurance surveys.
    """
    
    class Meta(SimpleSurveyForm.Meta):
        fields = [
            'first_name', 'last_name', 'date_of_birth', 'email', 'phone',
            'insurance_type',  # Include insurance_type field
            'preferred_annual_limit_per_family', 'household_income',
            'wants_ambulance_coverage', 'in_hospital_benefit_level',
            'out_hospital_benefit_level', 'needs_chronic_medication',
            'annual_limit_family_range', 'annual_limit_member_range'
        ]
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set insurance type to health and hide the field
        if 'insurance_type' in self.fields:
            self.fields['insurance_type'].initial = SimpleSurvey.InsuranceType.HEALTH
            self.fields['insurance_type'].widget = forms.HiddenInput()
        
        # Remove funeral-specific fields that might be inherited
        funeral_fields = [
            'preferred_cover_amount', 'marital_status', 'gender'
        ]
        for field in funeral_fields:
            if field in self.fields:
                del self.fields[field]


class FuneralSurveyForm(SimpleSurveyForm):
    """
    Specialized form for funeral insurance surveys.
    """
    
    class Meta(SimpleSurveyForm.Meta):
        fields = [
            'first_name', 'last_name', 'date_of_birth', 'email', 'phone',
            'insurance_type',  # Include insurance_type field
            'preferred_cover_amount', 'marital_status', 'gender'
        ]
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set insurance type to funeral and hide the field
        if 'insurance_type' in self.fields:
            self.fields['insurance_type'].initial = SimpleSurvey.InsuranceType.FUNERAL
            self.fields['insurance_type'].widget = forms.HiddenInput()
        
        # Remove health-specific fields that might be inherited
        health_fields = [
            'preferred_annual_limit_per_family', 'household_income',
            'wants_ambulance_coverage', 'in_hospital_benefit_level',
            'out_hospital_benefit_level', 'needs_chronic_medication',
            'annual_limit_family_range', 'annual_limit_member_range'
        ]
        for field in health_fields:
            if field in self.fields:
                del self.fields[field]