from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from .models import PolicyFeatures, AdditionalFeatures


class PolicyFeaturesAdminForm(forms.ModelForm):
    """
    Custom admin form for PolicyFeatures with enhanced validation.
    """
    
    class Meta:
        model = PolicyFeatures
        fields = '__all__'
        widgets = {
            'annual_limit_per_member': forms.NumberInput(attrs={
                'step': '0.01',
                'min': '0',
                'placeholder': 'e.g., 50000.00'
            }),
            'monthly_household_income': forms.NumberInput(attrs={
                'step': '0.01',
                'min': '0',
                'placeholder': 'e.g., 5000.00'
            }),
            'cover_amount': forms.NumberInput(attrs={
                'step': '0.01',
                'min': '0',
                'placeholder': 'e.g., 25000.00'
            }),
            'monthly_net_income': forms.NumberInput(attrs={
                'step': '0.01',
                'min': '0',
                'placeholder': 'e.g., 3000.00'
            }),
            'marital_status_requirement': forms.Select(choices=[
                ('', '--- Select ---'),
                ('single', 'Single'),
                ('married', 'Married'),
                ('divorced', 'Divorced'),
                ('widowed', 'Widowed'),
                ('any', 'Any')
            ]),
            'gender_requirement': forms.Select(choices=[
                ('', '--- Select ---'),
                ('male', 'Male'),
                ('female', 'Female'),
                ('any', 'Any')
            ])
        }
        help_texts = {
            'insurance_type': _('Select the type of insurance. This determines which feature fields are relevant.'),
            'annual_limit_per_member': _('Maximum annual coverage per family member (Health policies only)'),
            'monthly_household_income': _('Required monthly household income (Health policies only)'),
            'in_hospital_benefit': _('Whether in-hospital benefits are included (Health policies only)'),
            'out_hospital_benefit': _('Whether out-of-hospital benefits are included (Health policies only)'),
            'chronic_medication_availability': _('Whether chronic medication is covered (Health policies only)'),
            'cover_amount': _('Total coverage amount for funeral expenses (Funeral policies only)'),
            'marital_status_requirement': _('Required marital status (Funeral policies only)'),
            'gender_requirement': _('Required gender (Funeral policies only)'),
            'monthly_net_income': _('Required monthly net income (Funeral policies only)'),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Add CSS classes for better styling
        for field_name, field in self.fields.items():
            if isinstance(field.widget, forms.NumberInput):
                field.widget.attrs['class'] = 'form-control'
            elif isinstance(field.widget, forms.Select):
                field.widget.attrs['class'] = 'form-control'
            elif isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs['class'] = 'form-check-input'
        
        # Set initial insurance type based on policy category if available
        if self.instance and self.instance.policy_id:
            policy = self.instance.policy
            if policy.category.name.lower() in ['health', 'medical']:
                self.fields['insurance_type'].initial = 'HEALTH'
            elif policy.category.name.lower() == 'funeral':
                self.fields['insurance_type'].initial = 'FUNERAL'
    
    def clean(self):
        """
        Custom validation to ensure features match insurance type.
        """
        cleaned_data = super().clean()
        insurance_type = cleaned_data.get('insurance_type')
        
        if not insurance_type:
            raise ValidationError(_('Insurance type is required.'))
        
        errors = {}
        
        if insurance_type == 'HEALTH':
            # Validate health features
            health_fields = [
                'annual_limit_per_member',
                'monthly_household_income',
                'in_hospital_benefit',
                'out_hospital_benefit',
                'chronic_medication_availability'
            ]
            
            # Check for missing required health features
            missing_health = []
            for field in health_fields:
                if cleaned_data.get(field) is None:
                    missing_health.append(field.replace('_', ' ').title())
            
            if missing_health:
                errors['__all__'] = [
                    _('Health policies require the following features: {}').format(
                        ', '.join(missing_health)
                    )
                ]
            
            # Ensure funeral features are not filled
            funeral_fields = [
                'cover_amount',
                'marital_status_requirement',
                'gender_requirement',
                'monthly_net_income'
            ]
            
            filled_funeral = []
            for field in funeral_fields:
                if cleaned_data.get(field) is not None:
                    filled_funeral.append(field.replace('_', ' ').title())
                    # Clear the field
                    cleaned_data[field] = None
            
            if filled_funeral:
                if '__all__' not in errors:
                    errors['__all__'] = []
                errors['__all__'].append(
                    _('Health policies should not have funeral features. Cleared: {}').format(
                        ', '.join(filled_funeral)
                    )
                )
        
        elif insurance_type == 'FUNERAL':
            # Validate funeral features
            funeral_fields = [
                'cover_amount',
                'marital_status_requirement',
                'gender_requirement',
                'monthly_net_income'
            ]
            
            # Check for missing required funeral features
            missing_funeral = []
            for field in funeral_fields:
                if cleaned_data.get(field) is None:
                    missing_funeral.append(field.replace('_', ' ').title())
            
            if missing_funeral:
                errors['__all__'] = [
                    _('Funeral policies require the following features: {}').format(
                        ', '.join(missing_funeral)
                    )
                ]
            
            # Ensure health features are not filled
            health_fields = [
                'annual_limit_per_member',
                'monthly_household_income',
                'in_hospital_benefit',
                'out_hospital_benefit',
                'chronic_medication_availability'
            ]
            
            filled_health = []
            for field in health_fields:
                if cleaned_data.get(field) is not None:
                    filled_health.append(field.replace('_', ' ').title())
                    # Clear the field
                    cleaned_data[field] = None
            
            if filled_health:
                if '__all__' not in errors:
                    errors['__all__'] = []
                errors['__all__'].append(
                    _('Funeral policies should not have health features. Cleared: {}').format(
                        ', '.join(filled_health)
                    )
                )
        
        # Validate numeric values
        numeric_fields = [
            ('annual_limit_per_member', 'Annual limit per member'),
            ('monthly_household_income', 'Monthly household income'),
            ('cover_amount', 'Cover amount'),
            ('monthly_net_income', 'Monthly net income')
        ]
        
        for field_name, field_label in numeric_fields:
            value = cleaned_data.get(field_name)
            if value is not None and value <= 0:
                errors[field_name] = [_('{}  must be a positive number.').format(field_label)]
        
        if errors:
            raise ValidationError(errors)
        
        return cleaned_data


class AdditionalFeaturesAdminForm(forms.ModelForm):
    """
    Custom admin form for AdditionalFeatures with enhanced validation.
    """
    
    class Meta:
        model = AdditionalFeatures
        fields = '__all__'
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., 24/7 Customer Support'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Detailed description of this additional feature...'
            }),
            'icon': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., fa-phone, icon-support'
            }),
            'display_order': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0'
            })
        }
        help_texts = {
            'title': _('Short, descriptive title for this additional feature'),
            'description': _('Detailed explanation of what this feature provides'),
            'icon': _('CSS class or icon name for visual representation'),
            'is_highlighted': _('Check to make this feature stand out in listings'),
            'display_order': _('Lower numbers appear first (0 = first)')
        }
    
    def clean_title(self):
        """Validate title field"""
        title = self.cleaned_data.get('title')
        if title:
            title = title.strip()
            if len(title) < 3:
                raise ValidationError(_('Title must be at least 3 characters long.'))
            if len(title) > 255:
                raise ValidationError(_('Title cannot exceed 255 characters.'))
        return title
    
    def clean_description(self):
        """Validate description field"""
        description = self.cleaned_data.get('description')
        if description:
            description = description.strip()
            if len(description) < 10:
                raise ValidationError(_('Description must be at least 10 characters long.'))
        return description
    
    def clean_display_order(self):
        """Validate display order"""
        display_order = self.cleaned_data.get('display_order')
        if display_order is not None and display_order < 0:
            raise ValidationError(_('Display order cannot be negative.'))
        return display_order
    
    def clean(self):
        """Additional validation"""
        cleaned_data = super().clean()
        
        # Check for duplicate titles within the same policy
        title = cleaned_data.get('title')
        policy = cleaned_data.get('policy')
        
        if title and policy:
            existing = AdditionalFeatures.objects.filter(
                policy=policy,
                title__iexact=title
            )
            
            # Exclude current instance if editing
            if self.instance.pk:
                existing = existing.exclude(pk=self.instance.pk)
            
            if existing.exists():
                raise ValidationError({
                    'title': _('A feature with this title already exists for this policy.')
                })
        
        return cleaned_data


class HealthPolicyFilterForm(forms.Form):
    """
    Filter form for health policy listings.
    Implements requirements 8.1, 8.2, 8.3 for feature-based filtering.
    """
    
    min_annual_limit = forms.DecimalField(
        required=False,
        min_value=0,
        decimal_places=2,
        max_digits=12,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Minimum annual limit',
            'step': '1000'
        }),
        label=_('Minimum Annual Limit per Member')
    )
    
    max_income_requirement = forms.DecimalField(
        required=False,
        min_value=0,
        decimal_places=2,
        max_digits=10,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Maximum income requirement',
            'step': '500'
        }),
        label=_('Maximum Income Requirement')
    )
    
    # Requirement 8.1: In-hospital benefit filtering
    in_hospital_benefit = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        }),
        label=_('Must include in-hospital benefits')
    )
    
    # Requirement 8.2: Out-of-hospital benefit filtering
    out_hospital_benefit = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        }),
        label=_('Must include out-of-hospital benefits')
    )
    
    # Requirement 8.3: Chronic medication filtering
    chronic_medication = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        }),
        label=_('Must include chronic medication coverage')
    )
    
    def clean_min_annual_limit(self):
        """Validate minimum annual limit"""
        value = self.cleaned_data.get('min_annual_limit')
        if value is not None and value <= 0:
            raise ValidationError(_('Minimum annual limit must be positive.'))
        return value
    
    def clean_max_income_requirement(self):
        """Validate maximum income requirement"""
        value = self.cleaned_data.get('max_income_requirement')
        if value is not None and value <= 0:
            raise ValidationError(_('Maximum income requirement must be positive.'))
        return value


class FuneralPolicyFilterForm(forms.Form):
    """
    Filter form for funeral policy listings.
    Implements requirements 8.4, 8.5 for feature-based filtering.
    """
    
    min_cover_amount = forms.DecimalField(
        required=False,
        min_value=0,
        decimal_places=2,
        max_digits=12,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Minimum cover amount',
            'step': '1000'
        }),
        label=_('Minimum Cover Amount')
    )
    
    max_income_requirement = forms.DecimalField(
        required=False,
        min_value=0,
        decimal_places=2,
        max_digits=10,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Maximum income requirement',
            'step': '500'
        }),
        label=_('Maximum Income Requirement')
    )
    
    marital_status = forms.ChoiceField(
        required=False,
        choices=[
            ('', '--- Any ---'),
            ('single', 'Single'),
            ('married', 'Married'),
            ('divorced', 'Divorced'),
            ('widowed', 'Widowed'),
        ],
        widget=forms.Select(attrs={
            'class': 'form-control'
        }),
        label=_('Marital Status')
    )
    
    gender = forms.ChoiceField(
        required=False,
        choices=[
            ('', '--- Any ---'),
            ('male', 'Male'),
            ('female', 'Female'),
        ],
        widget=forms.Select(attrs={
            'class': 'form-control'
        }),
        label=_('Gender')
    )
    
    # Requirement 8.5: Waiting period filtering
    max_waiting_period = forms.IntegerField(
        required=False,
        min_value=0,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Maximum waiting period (days)',
            'step': '30'
        }),
        label=_('Maximum Waiting Period (days)')
    )
    
    def clean_min_cover_amount(self):
        """Validate minimum cover amount"""
        value = self.cleaned_data.get('min_cover_amount')
        if value is not None and value <= 0:
            raise ValidationError(_('Minimum cover amount must be positive.'))
        return value
    
    def clean_max_income_requirement(self):
        """Validate maximum income requirement"""
        value = self.cleaned_data.get('max_income_requirement')
        if value is not None and value <= 0:
            raise ValidationError(_('Maximum income requirement must be positive.'))
        return value
    
    def clean_max_waiting_period(self):
        """Validate maximum waiting period"""
        value = self.cleaned_data.get('max_waiting_period')
        if value is not None and value < 0:
            raise ValidationError(_('Maximum waiting period cannot be negative.'))
        return value