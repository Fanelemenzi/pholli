from django import forms
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from decimal import Decimal
from .models import PolicyFeatures, AdditionalFeatures, BasePolicy


class HealthPolicyFilterForm(forms.Form):
    """
    Filter form for health insurance policies.
    """
    min_annual_limit = forms.DecimalField(
        required=False,
        min_value=0,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Minimum annual limit'
        }),
        label=_('Minimum Annual Limit')
    )
    
    max_income_requirement = forms.DecimalField(
        required=False,
        min_value=0,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Maximum income requirement'
        }),
        label=_('Maximum Income Requirement')
    )
    
    in_hospital_benefit = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        }),
        label=_('In-Hospital Benefit Required')
    )
    
    out_hospital_benefit = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        }),
        label=_('Out-of-Hospital Benefit Required')
    )
    
    chronic_medication = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        }),
        label=_('Chronic Medication Coverage Required')
    )


class FuneralPolicyFilterForm(forms.Form):
    """
    Filter form for funeral insurance policies.
    """
    min_cover_amount = forms.DecimalField(
        required=False,
        min_value=0,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Minimum cover amount'
        }),
        label=_('Minimum Cover Amount')
    )
    
    max_income_requirement = forms.DecimalField(
        required=False,
        min_value=0,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Maximum income requirement'
        }),
        label=_('Maximum Income Requirement')
    )
    
    marital_status = forms.ChoiceField(
        required=False,
        choices=[
            ('', _('Any')),
            ('single', _('Single')),
            ('married', _('Married')),
            ('divorced', _('Divorced')),
            ('widowed', _('Widowed')),
        ],
        widget=forms.Select(attrs={
            'class': 'form-select'
        }),
        label=_('Marital Status')
    )
    
    gender = forms.ChoiceField(
        required=False,
        choices=[
            ('', _('Any')),
            ('male', _('Male')),
            ('female', _('Female')),
        ],
        widget=forms.Select(attrs={
            'class': 'form-select'
        }),
        label=_('Gender')
    )
    
    max_waiting_period = forms.IntegerField(
        required=False,
        min_value=0,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Maximum waiting period (days)'
        }),
        label=_('Maximum Waiting Period (Days)')
    )


class PolicyFeaturesAdminForm(forms.ModelForm):
    """
    Custom admin form for PolicyFeatures with dynamic field visibility
    based on insurance type.
    """
    
    class Meta:
        model = PolicyFeatures
        fields = '__all__'
        widgets = {
            'insurance_type': forms.Select(attrs={
                'onchange': 'toggleFeatureFields(this.value)',
                'class': 'insurance-type-selector'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Add CSS classes for field grouping
        self._add_field_classes()
        
        # Set up field help texts
        self._setup_help_texts()
        
        # If editing existing instance, set up initial visibility
        if self.instance and self.instance.pk:
            self._setup_field_visibility()
    
    def _add_field_classes(self):
        """Add CSS classes to group fields by insurance type."""
        
        # Health insurance fields
        health_fields = [
            'annual_limit_per_member', 'annual_limit_per_family',
            'annual_limit_family_range', 'annual_limit_member_range',
            'monthly_household_income', 'currently_on_medical_aid',
            'ambulance_coverage', 'in_hospital_benefit',
            'in_hospital_benefit_level', 'out_hospital_benefit',
            'out_hospital_benefit_level', 'chronic_medication_availability'
        ]
        
        # Funeral insurance fields
        funeral_fields = [
            'cover_amount', 'cover_amount_range', 'funeral_service_type',
            'family_coverage_type', 'max_family_members',
            'waiting_period_natural_death', 'waiting_period_accidental_death',
            'includes_coffin', 'includes_transport', 'includes_venue',
            'includes_catering', 'includes_flowers', 'includes_memorial_service',
            'repatriation_covered', 'grocery_benefit', 'grocery_benefit_amount',
            'mourning_clothes_benefit', 'claim_payout_hours',
            'marital_status_requirement', 'gender_requirement', 'monthly_net_income'
        ]
        
        for field_name in health_fields:
            if field_name in self.fields:
                self.fields[field_name].widget.attrs.update({
                    'class': 'health-field',
                    'data-insurance-type': 'HEALTH'
                })
        
        for field_name in funeral_fields:
            if field_name in self.fields:
                self.fields[field_name].widget.attrs.update({
                    'class': 'funeral-field',
                    'data-insurance-type': 'FUNERAL'
                })
    
    def _setup_help_texts(self):
        """Set up enhanced help texts for better user guidance."""
        
        help_texts = {
            'insurance_type': _('Select the insurance type to show relevant fields. This determines which features are available for configuration.'),
            
            # Health fields
            'annual_limit_family_range': _('Select the annual coverage limit range for the entire family. This is used for matching user preferences.'),
            'in_hospital_benefit_level': _('Level of in-hospital coverage provided. Higher levels include more comprehensive hospital care.'),
            'out_hospital_benefit_level': _('Level of out-of-hospital coverage. Includes GP visits, specialists, and day-to-day medical care.'),
            
            # Funeral fields
            'cover_amount_range': _('Select the coverage amount range. This helps users find policies within their budget expectations.'),
            'funeral_service_type': _('Type of funeral service provided. Basic = essential only, Standard = comprehensive, Premium = luxury service.'),
            'family_coverage_type': _('Type of family coverage offered. Determines how many and which family members are covered.'),
            'waiting_period_natural_death': _('Waiting period before natural death claims are covered. Shorter periods are more attractive to customers.'),
            'includes_coffin': _('Check if a coffin/casket is included in the funeral service package.'),
            'includes_catering': _('Check if catering for mourners is included in the service.'),
        }
        
        for field_name, help_text in help_texts.items():
            if field_name in self.fields:
                self.fields[field_name].help_text = help_text
    
    def _setup_field_visibility(self):
        """Set up field visibility based on current insurance type."""
        if self.instance.insurance_type == 'HEALTH':
            # Make health fields required
            required_health_fields = [
                'annual_limit_family_range', 'in_hospital_benefit_level',
                'out_hospital_benefit_level'
            ]
            for field_name in required_health_fields:
                if field_name in self.fields:
                    self.fields[field_name].required = True
        
        elif self.instance.insurance_type == 'FUNERAL':
            # Make funeral fields required
            required_funeral_fields = [
                'cover_amount_range', 'funeral_service_type',
                'family_coverage_type', 'waiting_period_natural_death'
            ]
            for field_name in required_funeral_fields:
                if field_name in self.fields:
                    self.fields[field_name].required = True
    
    def clean(self):
        """Custom validation to ensure appropriate fields are filled based on insurance type."""
        cleaned_data = super().clean()
        insurance_type = cleaned_data.get('insurance_type')
        
        if not insurance_type:
            raise ValidationError(_('Insurance type is required.'))
        
        if insurance_type == 'HEALTH':
            self._validate_health_fields(cleaned_data)
        elif insurance_type == 'FUNERAL':
            self._validate_funeral_fields(cleaned_data)
        
        return cleaned_data
    
    def _validate_health_fields(self, cleaned_data):
        """Validate health insurance specific fields."""
        errors = {}
        
        # Check required health fields
        required_fields = {
            'annual_limit_family_range': _('Annual limit family range is required for health policies.'),
            'in_hospital_benefit_level': _('In-hospital benefit level is required for health policies.'),
            'out_hospital_benefit_level': _('Out-of-hospital benefit level is required for health policies.'),
        }
        
        for field_name, error_message in required_fields.items():
            if not cleaned_data.get(field_name):
                errors[field_name] = error_message
        
        # Check that funeral fields are not filled
        funeral_fields = [
            'cover_amount', 'cover_amount_range', 'funeral_service_type',
            'family_coverage_type', 'waiting_period_natural_death'
        ]
        
        filled_funeral_fields = [
            field for field in funeral_fields 
            if cleaned_data.get(field) is not None
        ]
        
        if filled_funeral_fields:
            errors['insurance_type'] = _(
                f'Funeral fields should not be filled for health policies: {", ".join(filled_funeral_fields)}'
            )
        
        if errors:
            raise ValidationError(errors)
    
    def _validate_funeral_fields(self, cleaned_data):
        """Validate funeral insurance specific fields."""
        errors = {}
        
        # Check required funeral fields
        required_fields = {
            'cover_amount_range': _('Cover amount range is required for funeral policies.'),
            'funeral_service_type': _('Funeral service type is required for funeral policies.'),
            'family_coverage_type': _('Family coverage type is required for funeral policies.'),
            'waiting_period_natural_death': _('Waiting period for natural death is required for funeral policies.'),
        }
        
        for field_name, error_message in required_fields.items():
            if not cleaned_data.get(field_name):
                errors[field_name] = error_message
        
        # Check that health fields are not filled
        health_fields = [
            'annual_limit_per_member', 'annual_limit_per_family',
            'annual_limit_family_range', 'annual_limit_member_range',
            'in_hospital_benefit_level', 'out_hospital_benefit_level'
        ]
        
        filled_health_fields = [
            field for field in health_fields 
            if cleaned_data.get(field) is not None
        ]
        
        if filled_health_fields:
            errors['insurance_type'] = _(
                f'Health fields should not be filled for funeral policies: {", ".join(filled_health_fields)}'
            )
        
        # Validate logical relationships
        if cleaned_data.get('grocery_benefit') and not cleaned_data.get('grocery_benefit_amount'):
            errors['grocery_benefit_amount'] = _(
                'Grocery benefit amount is required when grocery benefit is enabled.'
            )
        
        if errors:
            raise ValidationError(errors)
    
    class Media:
        css = {
            'all': ('admin/css/policy_features_admin.css',)
        }
        js = ('admin/js/policy_features_admin.js',)


class AdditionalFeaturesAdminForm(forms.ModelForm):
    """
    Custom admin form for AdditionalFeatures with enhanced validation.
    """
    
    class Meta:
        model = AdditionalFeatures
        fields = '__all__'
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
            'coverage_details': forms.Textarea(attrs={'rows': 4}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Add help texts
        self.fields['title'].help_text = _('Brief, descriptive title for this additional feature.')
        self.fields['description'].help_text = _('Detailed description of what this feature provides.')
        self.fields['coverage_details'].help_text = _('Specific coverage information, limits, and conditions.')
        self.fields['is_highlighted'].help_text = _('Highlighted features appear prominently in policy comparisons.')
    
    def clean(self):
        """Custom validation for additional features."""
        cleaned_data = super().clean()
        
        # Ensure coverage details are provided for highlighted features
        if cleaned_data.get('is_highlighted') and not cleaned_data.get('coverage_details'):
            raise ValidationError({
                'coverage_details': _('Coverage details are required for highlighted features.')
            })
        
        return cleaned_data


class BasePolicyAdminForm(forms.ModelForm):
    """
    Custom admin form for BasePolicy with enhanced validation and help.
    """
    
    class Meta:
        model = BasePolicy
        fields = '__all__'
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
            'short_description': forms.Textarea(attrs={'rows': 2}),
            'terms_and_conditions': forms.Textarea(attrs={'rows': 6}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Add enhanced help texts
        help_texts = {
            'name': _('Clear, descriptive name for the policy (e.g., "Comprehensive Family Health Plan").'),
            'short_description': _('Brief summary for policy listings and comparisons (max 500 characters).'),
            'base_premium': _('Base monthly premium amount. Additional calculations can be added via Premium Calculation rules.'),
            'coverage_amount': _('Maximum benefit/coverage amount provided by this policy.'),
            'minimum_age': _('Minimum age for policy eligibility. Consider your target market.'),
            'maximum_age': _('Maximum age for policy eligibility. Higher ages may require medical underwriting.'),
            'waiting_period_days': _('Days before coverage begins. Shorter periods are more attractive to customers.'),
            'is_featured': _('Featured policies appear prominently in search results and comparisons.'),
        }
        
        for field_name, help_text in help_texts.items():
            if field_name in self.fields:
                self.fields[field_name].help_text = help_text
        
        # Set up category-based field requirements
        if self.instance and self.instance.pk:
            self._setup_category_requirements()
    
    def _setup_category_requirements(self):
        """Set up field requirements based on policy category."""
        if self.instance.category:
            category_slug = self.instance.category.slug
            
            if category_slug == 'funeral':
                # Funeral policies should have specific age ranges
                self.fields['minimum_age'].help_text += _(' Funeral policies typically start from age 18.')
                self.fields['maximum_age'].help_text += _(' Funeral policies often extend to age 75-85.')
            
            elif category_slug == 'health':
                # Health policies have different considerations
                self.fields['minimum_age'].help_text += _(' Health policies may start from birth or age 18.')
                self.fields['maximum_age'].help_text += _(' Health policies may have no upper age limit.')
    
    def clean(self):
        """Custom validation for base policy."""
        cleaned_data = super().clean()
        
        # Validate age ranges
        min_age = cleaned_data.get('minimum_age')
        max_age = cleaned_data.get('maximum_age')
        
        if min_age is not None and max_age is not None:
            if min_age >= max_age:
                raise ValidationError({
                    'maximum_age': _('Maximum age must be greater than minimum age.')
                })
        
        # Validate premium and coverage amounts
        base_premium = cleaned_data.get('base_premium')
        coverage_amount = cleaned_data.get('coverage_amount')
        
        if base_premium and coverage_amount:
            # Basic sanity check - premium shouldn't be more than 10% of coverage per month
            if base_premium > (coverage_amount * Decimal('0.1')):
                raise ValidationError({
                    'base_premium': _('Premium seems unusually high compared to coverage amount. Please verify.')
                })
        
        # Validate short description length
        short_desc = cleaned_data.get('short_description', '')
        if len(short_desc) > 500:
            raise ValidationError({
                'short_description': _('Short description must be 500 characters or less.')
            })
        
        return cleaned_data