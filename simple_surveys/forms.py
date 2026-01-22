from django import forms
from django.core.exceptions import ValidationError
from .models import SimpleSurvey


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
            'preferred_annual_limit_per_family', 'household_income', 'currently_on_medical_aid',
            'wants_ambulance_coverage', 'wants_in_hospital_benefit',
            'wants_out_hospital_benefit', 'needs_chronic_medication',
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
            'currently_on_medical_aid': forms.Select(
                choices=[(None, 'Select an option'), (True, 'Yes'), (False, 'No')],
                attrs={'class': 'form-control health-field'}
            ),
            'wants_ambulance_coverage': forms.Select(
                choices=[(None, 'Select an option'), (True, 'Yes'), (False, 'No')],
                attrs={'class': 'form-control health-field'}
            ),
            'wants_in_hospital_benefit': forms.Select(
                choices=[(None, 'Select an option'), (True, 'Yes'), (False, 'No')],
                attrs={'class': 'form-control health-field'}
            ),
            'wants_out_hospital_benefit': forms.Select(
                choices=[(None, 'Select an option'), (True, 'Yes'), (False, 'No')],
                attrs={'class': 'form-control health-field'}
            ),
            'needs_chronic_medication': forms.Select(
                choices=[(None, 'Select an option'), (True, 'Yes'), (False, 'No')],
                attrs={'class': 'form-control health-field'}
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
            'currently_on_medical_aid': 'Are you currently on medical aid?',
            'wants_ambulance_coverage': 'Do you want ambulance coverage?',
            'wants_in_hospital_benefit': 'Do you want in-hospital benefits?',
            'wants_out_hospital_benefit': 'Do you want out-of-hospital benefits?',
            'needs_chronic_medication': 'Do you need chronic medication coverage?',
            # Funeral field labels
            'preferred_cover_amount': 'Preferred Cover Amount',
            'marital_status': 'Marital Status',
            'gender': 'Gender',
        }
        
        for field_name, label in field_labels.items():
            if field_name in self.fields:
                self.fields[field_name].label = label
    
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
            
            if cleaned_data.get('currently_on_medical_aid') is None:
                health_errors['currently_on_medical_aid'] = 'This field is required for health policies.'
            
            if cleaned_data.get('wants_ambulance_coverage') is None:
                health_errors['wants_ambulance_coverage'] = 'This field is required for health policies.'
            
            if cleaned_data.get('wants_in_hospital_benefit') is None:
                health_errors['wants_in_hospital_benefit'] = 'This field is required for health policies.'
            
            if cleaned_data.get('wants_out_hospital_benefit') is None:
                health_errors['wants_out_hospital_benefit'] = 'This field is required for health policies.'
            
            if cleaned_data.get('needs_chronic_medication') is None:
                health_errors['needs_chronic_medication'] = 'This field is required for health policies.'
            
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
            'preferred_annual_limit_per_family', 'household_income', 'currently_on_medical_aid',
            'wants_ambulance_coverage', 'wants_in_hospital_benefit',
            'wants_out_hospital_benefit', 'needs_chronic_medication'
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
            'preferred_annual_limit_per_family', 'household_income', 'currently_on_medical_aid',
            'wants_ambulance_coverage', 'wants_in_hospital_benefit',
            'wants_out_hospital_benefit', 'needs_chronic_medication'
        ]
        for field in health_fields:
            if field in self.fields:
                del self.fields[field]