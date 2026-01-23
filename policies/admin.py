from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.urls import reverse
from django.db.models import Avg, Count, Q
from django.core.exceptions import ValidationError
from .models import (
    PolicyCategory,
    PolicyType,
    BasePolicy,
    PolicyFeatures,
    AdditionalFeatures,
    PolicyEligibility,
    PolicyExclusion,
    PolicyDocument,
    PolicyPremiumCalculation,
    PolicyReview,
    Rewards
)
from .forms import PolicyFeaturesAdminForm, AdditionalFeaturesAdminForm


# Inline Admin Classes
class PolicyFeaturesInline(admin.StackedInline):
    model = PolicyFeatures
    extra = 0
    fields = [
        'insurance_type',
        # Health Policy Features
        'annual_limit_per_member',
        'annual_limit_per_family',
        'monthly_household_income',
        'currently_on_medical_aid',
        'ambulance_coverage',
        'in_hospital_benefit',
        'out_hospital_benefit',
        'chronic_medication_availability',
        # Funeral Policy Features
        'cover_amount',
        'marital_status_requirement',
        'gender_requirement',
        'monthly_net_income'
    ]
    classes = ['collapse']


class AdditionalFeaturesInline(admin.TabularInline):
    model = AdditionalFeatures
    extra = 1
    fields = ['title', 'description', 'coverage_details', 'icon', 'is_highlighted', 'display_order']
    classes = ['collapse']


class PolicyEligibilityInline(admin.TabularInline):
    model = PolicyEligibility
    extra = 1
    fields = ['criterion', 'description', 'is_mandatory', 'display_order']
    classes = ['collapse']


class PolicyExclusionInline(admin.TabularInline):
    model = PolicyExclusion
    extra = 1
    fields = ['title', 'description', 'display_order']
    classes = ['collapse']


class PolicyDocumentInline(admin.TabularInline):
    model = PolicyDocument
    extra = 0
    fields = ['document_type', 'title', 'file', 'is_public']
    classes = ['collapse']


class PolicyPremiumCalculationInline(admin.TabularInline):
    model = PolicyPremiumCalculation
    extra = 0
    fields = ['factor_name', 'factor_value', 'multiplier', 'additional_amount', 'is_active']
    classes = ['collapse']


class RewardsInline(admin.TabularInline):
    model = Rewards
    extra = 1
    fields = ['title', 'reward_type', 'value', 'percentage', 'is_active', 'display_order']
    classes = ['collapse']
    ordering = ['display_order', 'title']


# Main Admin Classes
@admin.register(PolicyCategory)
class PolicyCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'display_order', 'get_policy_count', 'is_active', 'get_icon_display']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at', 'updated_at']
    prepopulated_fields = {'slug': ('name',)}
    ordering = ['display_order', 'name']
    list_editable = ['is_active', 'display_order']
    
    fieldsets = (
        (_('Basic Information'), {
            'fields': ('name', 'slug', 'description', 'icon')
        }),
        (_('Display Settings'), {
            'fields': ('display_order', 'is_active')
        }),
        (_('Metadata'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def get_policy_count(self, obj):
        """Return the number of policies in this category"""
        count = obj.policies.count()
        if count > 0:
            return f"📄 {count}"
        return "📄 0"
    get_policy_count.short_description = _('Policies')
    get_policy_count.admin_order_field = 'policies__count'
    
    def get_icon_display(self, obj):
        """Display the icon if available"""
        if obj.icon:
            return f"🎨 {obj.icon}"
        return "—"
    get_icon_display.short_description = _('Icon')
    
    def get_queryset(self, request):
        """Optimize queryset with annotations"""
        qs = super().get_queryset(request)
        return qs.prefetch_related('policies')
    
    # Admin actions
    actions = ['activate_categories', 'deactivate_categories']
    
    @admin.action(description=_('Activate selected categories'))
    def activate_categories(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} categories activated.')
    
    @admin.action(description=_('Deactivate selected categories'))
    def deactivate_categories(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} categories deactivated.')


@admin.register(PolicyType)
class PolicyTypeAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'slug', 'display_order', 'get_policy_count', 'is_active']
    list_filter = ['category', 'is_active', 'created_at']
    search_fields = ['name', 'description', 'category__name']
    readonly_fields = ['created_at', 'updated_at']
    prepopulated_fields = {'slug': ('name',)}
    list_select_related = ['category']
    ordering = ['category', 'display_order', 'name']
    list_editable = ['is_active', 'display_order']
    
    fieldsets = (
        (_('Basic Information'), {
            'fields': ('category', 'name', 'slug', 'description')
        }),
        (_('Display Settings'), {
            'fields': ('display_order', 'is_active')
        }),
        (_('Metadata'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def get_policy_count(self, obj):
        """Return the number of policies for this type"""
        count = obj.policies.count()
        if count > 0:
            return f"📋 {count}"
        return "📋 0"
    get_policy_count.short_description = _('Policies')
    get_policy_count.admin_order_field = 'policies__count'
    
    def get_queryset(self, request):
        """Optimize queryset with annotations"""
        qs = super().get_queryset(request)
        return qs.select_related('category').prefetch_related('policies')
    
    def save_model(self, request, obj, form, change):
        """Custom save logic if needed"""
        super().save_model(request, obj, form, change)
    
    # Admin actions
    actions = ['activate_types', 'deactivate_types']
    
    @admin.action(description=_('Activate selected policy types'))
    def activate_types(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} policy types activated.')
    
    @admin.action(description=_('Deactivate selected policy types'))
    def deactivate_types(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} policy types deactivated.')


@admin.register(BasePolicy)
class BasePolicyAdmin(admin.ModelAdmin):
    list_display = [
        'name',
        'organization',
        'category',
        'policy_type',
        'base_premium_display',
        'approval_status_display',
        'active_status',
        'featured_status',
        'views_count',
        'created_at'
    ]
    
    list_filter = [
        'category',
        'policy_type',
        'approval_status',
        'is_active',
        'is_featured',
        'organization',
        ('created_at', admin.DateFieldListFilter),
        'currency'
    ]
    
    search_fields = [
        'name',
        'policy_number',
        'description',
        'short_description',
        'organization__name'
    ]
    
    readonly_fields = [
        'policy_number',
        'approved_at',
        'approved_by',
        'views_count',
        'comparison_count',
        'created_at',
        'updated_at'
    ]
    
    fieldsets = (
        (_('Basic Information'), {
            'fields': (
                'organization',
                'category',
                'policy_type',
                'name',
                'policy_number',
                'short_description',
                'description'
            )
        }),
        (_('Pricing & Coverage'), {
            'fields': (
                'base_premium',
                'currency',
                'coverage_amount'
            )
        }),
        (_('Eligibility'), {
            'fields': (
                'minimum_age',
                'maximum_age',
                'waiting_period_days'
            )
        }),
        (_('Terms & Conditions'), {
            'fields': ('terms_and_conditions',),
            'classes': ('collapse',)
        }),
        (_('Status & Approval'), {
            'fields': (
                'approval_status',
                'is_active',
                'is_featured',
                'approved_at',
                'approved_by'
            )
        }),
        (_('Documents'), {
            'fields': (
                'brochure',
                'application_form'
            ),
            'classes': ('collapse',)
        }),
        (_('Additional Settings'), {
            'fields': (
                'tags',
                'custom_fields'
            ),
            'classes': ('collapse',)
        }),
        (_('Metadata'), {
            'fields': (
                'views_count',
                'comparison_count',
                'created_at',
                'updated_at'
            ),
            'classes': ('collapse',)
        })
    )
    
    inlines = [
        PolicyFeaturesInline,
        AdditionalFeaturesInline,
        RewardsInline,
        PolicyEligibilityInline,
        PolicyExclusionInline,
        PolicyDocumentInline,
        PolicyPremiumCalculationInline
    ]
    
    actions = [
        'approve_policies',
        'reject_policies',
        'activate_policies',
        'deactivate_policies',
        'feature_policies',
        'unfeature_policies'
    ]
    
    list_select_related = ['organization', 'category', 'policy_type', 'approved_by']
    list_per_page = 25
    date_hierarchy = 'created_at'
    save_on_top = True
    
    def base_premium_display(self, obj):
        try:
            # Convert Decimal to float for formatting
            premium_value = float(obj.base_premium)
            return format_html(
                '<strong>{} {:,.2f}</strong>',
                obj.currency,
                premium_value
            )
        except (ValueError, TypeError):
            # Fallback if there's any formatting issue
            return format_html(
                '<strong>{} {}</strong>',
                obj.currency,
                obj.base_premium
            )
    base_premium_display.short_description = _('Premium')
    base_premium_display.admin_order_field = 'base_premium'
    
    def approval_status_display(self, obj):
        colors = {
            'DRAFT': '#6c757d',
            'PENDING': '#ffc107',
            'APPROVED': '#28a745',
            'REJECTED': '#dc3545',
            'ARCHIVED': '#6c757d'
        }
        color = colors.get(obj.approval_status, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 3px; font-size: 11px;">{}</span>',
            color,
            obj.get_approval_status_display()
        )
    approval_status_display.short_description = _('Status')
    approval_status_display.admin_order_field = 'approval_status'
    
    def active_status(self, obj):
        """Display active status using simple text"""
        return "✅ Active" if obj.is_active else "❌ Inactive"
    active_status.short_description = _('Active')
    active_status.admin_order_field = 'is_active'
    
    def featured_status(self, obj):
        """Display featured status using simple text"""
        return "⭐ Featured" if obj.is_featured else "☆ Regular"
    featured_status.short_description = _('Featured')
    featured_status.admin_order_field = 'is_featured'
    
    def save_model(self, request, obj, form, change):
        if not obj.policy_number:
            from django.utils.crypto import get_random_string
            prefix = obj.category.slug.upper()[:3]
            random_part = get_random_string(8, allowed_chars='0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ')
            obj.policy_number = f"{prefix}-{random_part}"
        
        super().save_model(request, obj, form, change)
    
    # Admin Actions
    @admin.action(description=_('Approve selected policies'))
    def approve_policies(self, request, queryset):
        updated = queryset.update(
            approval_status=BasePolicy.ApprovalStatus.APPROVED,
            approved_by=request.user,
            approved_at=timezone.now()
        )
        self.message_user(request, f'{updated} policies approved successfully.')
    
    @admin.action(description=_('Reject selected policies'))
    def reject_policies(self, request, queryset):
        updated = queryset.update(approval_status=BasePolicy.ApprovalStatus.REJECTED)
        self.message_user(request, f'{updated} policies rejected.')
    
    @admin.action(description=_('Activate selected policies'))
    def activate_policies(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} policies activated.')
    
    @admin.action(description=_('Deactivate selected policies'))
    def deactivate_policies(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} policies deactivated.')
    
    @admin.action(description=_('Feature selected policies'))
    def feature_policies(self, request, queryset):
        updated = queryset.update(is_featured=True)
        self.message_user(request, f'{updated} policies featured.')
    
    @admin.action(description=_('Unfeature selected policies'))
    def unfeature_policies(self, request, queryset):
        updated = queryset.update(is_featured=False)
        self.message_user(request, f'{updated} policies unfeatured.')


@admin.register(PolicyReview)
class PolicyReviewAdmin(admin.ModelAdmin):
    list_display = [
        'policy_link',
        'user_name',
        'rating_stars',
        'title',
        'approval_status',
        'is_verified_purchase',
        'created_at'
    ]
    
    list_filter = [
        'rating',
        'is_approved',
        'is_verified_purchase',
        'created_at',
        'policy__category'
    ]
    
    search_fields = [
        'policy__name',
        'user__username',
        'user__first_name',
        'user__last_name',
        'title',
        'comment'
    ]
    
    readonly_fields = ['created_at', 'updated_at', 'helpful_count']
    
    fieldsets = (
        (_('Review Information'), {
            'fields': ('policy', 'user', 'rating', 'title', 'comment')
        }),
        (_('Status'), {
            'fields': ('is_approved', 'is_verified_purchase')
        }),
        (_('Metadata'), {
            'fields': ('helpful_count', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    list_select_related = ['policy', 'user']
    list_per_page = 50
    
    def policy_link(self, obj):
        url = reverse('admin:policies_basepolicy_change', args=[obj.policy.pk])
        return format_html(
            '<a href="{}" style="text-decoration: none;">{}</a>',
            url,
            obj.policy.name
        )
    policy_link.short_description = _('Policy')
    
    def user_name(self, obj):
        return obj.user.get_full_name() or obj.user.username
    user_name.short_description = _('User')
    user_name.admin_order_field = 'user__username'
    
    def rating_stars(self, obj):
        stars = '★' * obj.rating + '☆' * (5 - obj.rating)
        return format_html(
            '<span style="color: #ffc107; font-size: 14px;">{}</span>',
            stars
        )
    rating_stars.short_description = _('Rating')
    rating_stars.admin_order_field = 'rating'
    
    def approval_status(self, obj):
        if obj.is_approved:
            return format_html('<span style="color: green;">{}</span>', '✓ Approved')
        return format_html('<span style="color: orange;">{}</span>', '⧗ Pending')
    approval_status.short_description = _('Status')
    approval_status.boolean = True


# Enhanced Admin Classes for Policy Features
@admin.register(PolicyFeatures)
class PolicyFeaturesAdmin(admin.ModelAdmin):
    form = PolicyFeaturesAdminForm
    list_display = [
        'policy_name_display',
        'insurance_type_display',
        'feature_summary',
        'validation_status',
        'created_at'
    ]
    list_filter = [
        'insurance_type',
        'policy__category',
        'policy__organization',
        'policy__approval_status',
        'created_at'
    ]
    search_fields = [
        'policy__name',
        'policy__policy_number',
        'policy__organization__name'
    ]
    list_select_related = ['policy', 'policy__organization', 'policy__category']
    readonly_fields = ['created_at', 'updated_at', 'validation_status_display']
    
    fieldsets = (
        (_('Policy Association'), {
            'fields': ('policy', 'insurance_type'),
            'description': _('Select the policy and specify the insurance type. This determines which feature fields are relevant.')
        }),
        (_('Health Policy Features'), {
            'fields': (
                'annual_limit_per_member',
                'annual_limit_per_family',
                'monthly_household_income',
                'currently_on_medical_aid',
                'ambulance_coverage',
                'in_hospital_benefit',
                'out_hospital_benefit',
                'chronic_medication_availability'
            ),
            'description': _('Features specific to health/medical insurance policies. Only fill these if insurance type is Health.'),
            'classes': ('collapse',)
        }),
        (_('Funeral Policy Features'), {
            'fields': (
                'cover_amount',
                'marital_status_requirement',
                'gender_requirement',
                'monthly_net_income'
            ),
            'description': _('Features specific to funeral insurance policies. Only fill these if insurance type is Funeral.'),
            'classes': ('collapse',)
        }),
        (_('Validation & Metadata'), {
            'fields': ('validation_status_display', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    actions = [
        'validate_features',
        'clear_irrelevant_features',
        'duplicate_features_to_similar_policies'
    ]
    
    def policy_name_display(self, obj):
        """Display policy name with link to policy admin"""
        url = reverse('admin:policies_basepolicy_change', args=[obj.policy.pk])
        return format_html(
            '<a href="{}" style="text-decoration: none;">{}</a>',
            url,
            obj.policy.name
        )
    policy_name_display.short_description = _('Policy')
    policy_name_display.admin_order_field = 'policy__name'
    
    def insurance_type_display(self, obj):
        """Display insurance type with color coding"""
        colors = {
            'HEALTH': '#28a745',
            'FUNERAL': '#6f42c1'
        }
        color = colors.get(obj.insurance_type, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 3px; font-size: 11px;">{}</span>',
            color,
            obj.get_insurance_type_display()
        )
    insurance_type_display.short_description = _('Insurance Type')
    insurance_type_display.admin_order_field = 'insurance_type'
    
    def feature_summary(self, obj):
        """Display summary of filled features"""
        if obj.insurance_type == 'HEALTH':
            features = [
                obj.annual_limit_per_member,
                obj.annual_limit_per_family,
                obj.monthly_household_income,
                obj.currently_on_medical_aid,
                obj.ambulance_coverage,
                obj.in_hospital_benefit,
                obj.out_hospital_benefit,
                obj.chronic_medication_availability
            ]
            filled = sum(1 for f in features if f is not None)
            return f"💊 {filled}/8 features"
        elif obj.insurance_type == 'FUNERAL':
            features = [
                obj.cover_amount,
                obj.marital_status_requirement,
                obj.gender_requirement,
                obj.monthly_net_income
            ]
            filled = sum(1 for f in features if f is not None)
            return f"⚱️ {filled}/4 features"
        return "❓ Unknown type"
    feature_summary.short_description = _('Features Filled')
    
    def validation_status(self, obj):
        """Display validation status"""
        errors = self._validate_features(obj)
        if not errors:
            return format_html('<span style="color: green;">{}</span>', '✓ Valid')
        return format_html('<span style="color: red;">✗ {} errors</span>', len(errors))
    validation_status.short_description = _('Validation')
    
    def validation_status_display(self, obj):
        """Detailed validation status for readonly field"""
        errors = self._validate_features(obj)
        if not errors:
            return "✅ All features are valid"
        return "❌ Validation errors:\n" + "\n".join(f"• {error}" for error in errors)
    validation_status_display.short_description = _('Validation Status')
    
    def _validate_features(self, obj):
        """Internal method to validate features"""
        errors = []
        
        if obj.insurance_type == 'HEALTH':
            # Check that health features are filled and funeral features are empty
            health_features = [
                ('annual_limit_per_member', obj.annual_limit_per_member),
                ('annual_limit_per_family', obj.annual_limit_per_family),
                ('monthly_household_income', obj.monthly_household_income),
                ('currently_on_medical_aid', obj.currently_on_medical_aid),
                ('ambulance_coverage', obj.ambulance_coverage),
                ('in_hospital_benefit', obj.in_hospital_benefit),
                ('out_hospital_benefit', obj.out_hospital_benefit),
                ('chronic_medication_availability', obj.chronic_medication_availability)
            ]
            
            # Check for missing required health features
            missing_health = [name for name, value in health_features if value is None]
            if missing_health:
                errors.append(f"Missing health features: {', '.join(missing_health)}")
            
            # Check for incorrectly filled funeral features
            funeral_features = [
                ('cover_amount', obj.cover_amount),
                ('marital_status_requirement', obj.marital_status_requirement),
                ('gender_requirement', obj.gender_requirement),
                ('monthly_net_income', obj.monthly_net_income)
            ]
            filled_funeral = [name for name, value in funeral_features if value is not None]
            if filled_funeral:
                errors.append(f"Funeral features should be empty for health policies: {', '.join(filled_funeral)}")
                
        elif obj.insurance_type == 'FUNERAL':
            # Check that funeral features are filled and health features are empty
            funeral_features = [
                ('cover_amount', obj.cover_amount),
                ('marital_status_requirement', obj.marital_status_requirement),
                ('gender_requirement', obj.gender_requirement),
                ('monthly_net_income', obj.monthly_net_income)
            ]
            
            # Check for missing required funeral features
            missing_funeral = [name for name, value in funeral_features if value is None]
            if missing_funeral:
                errors.append(f"Missing funeral features: {', '.join(missing_funeral)}")
            
            # Check for incorrectly filled health features
            health_features = [
                ('annual_limit_per_member', obj.annual_limit_per_member),
                ('annual_limit_per_family', obj.annual_limit_per_family),
                ('monthly_household_income', obj.monthly_household_income),
                ('currently_on_medical_aid', obj.currently_on_medical_aid),
                ('ambulance_coverage', obj.ambulance_coverage),
                ('in_hospital_benefit', obj.in_hospital_benefit),
                ('out_hospital_benefit', obj.out_hospital_benefit),
                ('chronic_medication_availability', obj.chronic_medication_availability)
            ]
            filled_health = [name for name, value in health_features if value is not None]
            if filled_health:
                errors.append(f"Health features should be empty for funeral policies: {', '.join(filled_health)}")
        
        # Validate numeric values
        if obj.annual_limit_per_member is not None and obj.annual_limit_per_member <= 0:
            errors.append("Annual limit per member must be positive")
        if obj.annual_limit_per_family is not None and obj.annual_limit_per_family <= 0:
            errors.append("Annual limit per family must be positive")
        if obj.monthly_household_income is not None and obj.monthly_household_income <= 0:
            errors.append("Monthly household income must be positive")
        if obj.cover_amount is not None and obj.cover_amount <= 0:
            errors.append("Cover amount must be positive")
            
        return errors
    
    def clean(self):
        """Custom validation for the admin form"""
        from django.core.exceptions import ValidationError
        errors = self._validate_features(self)
        if errors:
            raise ValidationError(errors)
    
    # Admin Actions
    @admin.action(description=_('Validate selected policy features'))
    def validate_features(self, request, queryset):
        total_errors = 0
        for obj in queryset:
            errors = self._validate_features(obj)
            if errors:
                total_errors += len(errors)
                self.message_user(
                    request,
                    f'{obj.policy.name}: {", ".join(errors)}',
                    level='ERROR'
                )
        
        if total_errors == 0:
            self.message_user(request, f'All {queryset.count()} policy features are valid.')
        else:
            self.message_user(
                request,
                f'Found {total_errors} validation errors across {queryset.count()} policies.',
                level='WARNING'
            )
    
    @admin.action(description=_('Clear irrelevant features based on insurance type'))
    def clear_irrelevant_features(self, request, queryset):
        updated_count = 0
        for obj in queryset:
            if obj.insurance_type == 'HEALTH':
                # Clear funeral features
                obj.cover_amount = None
                obj.marital_status_requirement = None
                obj.gender_requirement = None
                obj.monthly_net_income = None
                obj.save()
                updated_count += 1
            elif obj.insurance_type == 'FUNERAL':
                # Clear health features
                obj.annual_limit_per_member = None
                obj.annual_limit_per_family = None
                obj.monthly_household_income = None
                obj.currently_on_medical_aid = None
                obj.ambulance_coverage = None
                obj.in_hospital_benefit = None
                obj.out_hospital_benefit = None
                obj.chronic_medication_availability = None
                obj.save()
                updated_count += 1
        
        self.message_user(request, f'Cleared irrelevant features for {updated_count} policies.')
    
    @admin.action(description=_('Duplicate features to similar policies'))
    def duplicate_features_to_similar_policies(self, request, queryset):
        if queryset.count() != 1:
            self.message_user(request, 'Please select exactly one policy to use as template.', level='ERROR')
            return
        
        template = queryset.first()
        similar_policies = BasePolicy.objects.filter(
            category=template.policy.category,
            policy_type=template.policy.policy_type
        ).exclude(pk=template.policy.pk)
        
        duplicated_count = 0
        for policy in similar_policies:
            features, created = PolicyFeatures.objects.get_or_create(
                policy=policy,
                defaults={
                    'insurance_type': template.insurance_type,
                    'annual_limit_per_member': template.annual_limit_per_member,
                    'annual_limit_per_family': template.annual_limit_per_family,
                    'monthly_household_income': template.monthly_household_income,
                    'currently_on_medical_aid': template.currently_on_medical_aid,
                    'ambulance_coverage': template.ambulance_coverage,
                    'in_hospital_benefit': template.in_hospital_benefit,
                    'out_hospital_benefit': template.out_hospital_benefit,
                    'chronic_medication_availability': template.chronic_medication_availability,
                    'cover_amount': template.cover_amount,
                    'marital_status_requirement': template.marital_status_requirement,
                    'gender_requirement': template.gender_requirement,
                    'monthly_net_income': template.monthly_net_income,
                }
            )
            if created:
                duplicated_count += 1
        
        self.message_user(request, f'Duplicated features to {duplicated_count} similar policies.')


@admin.register(Rewards)
class RewardsAdmin(admin.ModelAdmin):
    list_display = [
        'title',
        'policy_name_display',
        'reward_type_display',
        'value_display',
        'percentage_display',
        'is_active',
        'display_order',
        'created_at'
    ]
    
    list_filter = [
        'reward_type',
        'is_active',
        'policy__category',
        'policy__organization',
        'created_at'
    ]
    
    search_fields = [
        'title',
        'description',
        'policy__name',
        'policy__policy_number',
        'policy__organization__name'
    ]
    
    list_select_related = ['policy', 'policy__organization', 'policy__category']
    readonly_fields = ['created_at', 'updated_at']
    list_editable = ['is_active', 'display_order']
    ordering = ['policy', 'display_order', 'title']
    
    fieldsets = (
        (_('Basic Information'), {
            'fields': ('policy', 'title', 'description', 'reward_type'),
            'description': _('Basic reward information and type classification.')
        }),
        (_('Reward Value'), {
            'fields': ('value', 'percentage'),
            'description': _('Specify either monetary value or percentage. Not all reward types require values.')
        }),
        (_('Eligibility & Terms'), {
            'fields': ('eligibility_criteria', 'terms_and_conditions'),
            'description': _('Detailed criteria and terms for this reward.'),
            'classes': ('collapse',)
        }),
        (_('Display Settings'), {
            'fields': ('is_active', 'display_order'),
            'description': _('Control visibility and ordering of rewards.')
        }),
        (_('Metadata'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    actions = [
        'activate_rewards',
        'deactivate_rewards',
        'duplicate_to_similar_policies'
    ]
    
    def policy_name_display(self, obj):
        """Display policy name with link to policy admin"""
        url = reverse('admin:policies_basepolicy_change', args=[obj.policy.pk])
        return format_html(
            '<a href="{}" style="text-decoration: none;">{}</a>',
            url,
            obj.policy.name
        )
    policy_name_display.short_description = _('Policy')
    policy_name_display.admin_order_field = 'policy__name'
    
    def reward_type_display(self, obj):
        """Display reward type with color coding"""
        colors = {
            'CASHBACK': '#28a745',
            'DISCOUNT': '#17a2b8',
            'BENEFIT': '#6f42c1',
            'POINTS': '#fd7e14',
            'OTHER': '#6c757d'
        }
        color = colors.get(obj.reward_type, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 3px; font-size: 11px;">{}</span>',
            color,
            obj.get_reward_type_display()
        )
    reward_type_display.short_description = _('Type')
    reward_type_display.admin_order_field = 'reward_type'
    
    def value_display(self, obj):
        """Display monetary value if available"""
        if obj.value is not None:
            return format_html(
                '<strong>{} {:,.2f}</strong>',
                obj.policy.currency if hasattr(obj.policy, 'currency') else 'R',
                float(obj.value)
            )
        return "—"
    value_display.short_description = _('Value')
    value_display.admin_order_field = 'value'
    
    def percentage_display(self, obj):
        """Display percentage value if available"""
        if obj.percentage is not None:
            return format_html(
                '<strong>{}%</strong>',
                float(obj.percentage)
            )
        return "—"
    percentage_display.short_description = _('Percentage')
    percentage_display.admin_order_field = 'percentage'
    
    def is_active_display(self, obj):
        """Display active status with icons"""
        return "✅ Active" if obj.is_active else "❌ Inactive"
    is_active_display.short_description = _('Status')
    is_active_display.admin_order_field = 'is_active'
    
    # Admin Actions
    @admin.action(description=_('Activate selected rewards'))
    def activate_rewards(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} rewards activated.')
    
    @admin.action(description=_('Deactivate selected rewards'))
    def deactivate_rewards(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} rewards deactivated.')
    
    @admin.action(description=_('Duplicate rewards to similar policies'))
    def duplicate_to_similar_policies(self, request, queryset):
        if queryset.count() != 1:
            self.message_user(request, 'Please select exactly one reward to duplicate.', level='ERROR')
            return
        
        template_reward = queryset.first()
        similar_policies = BasePolicy.objects.filter(
            category=template_reward.policy.category,
            policy_type=template_reward.policy.policy_type
        ).exclude(pk=template_reward.policy.pk)
        
        duplicated_count = 0
        for policy in similar_policies:
            # Check if a similar reward already exists
            existing = Rewards.objects.filter(
                policy=policy,
                title=template_reward.title,
                reward_type=template_reward.reward_type
            ).exists()
            
            if not existing:
                Rewards.objects.create(
                    policy=policy,
                    title=template_reward.title,
                    description=template_reward.description,
                    reward_type=template_reward.reward_type,
                    value=template_reward.value,
                    percentage=template_reward.percentage,
                    eligibility_criteria=template_reward.eligibility_criteria,
                    terms_and_conditions=template_reward.terms_and_conditions,
                    is_active=template_reward.is_active,
                    display_order=template_reward.display_order
                )
                duplicated_count += 1
        
        self.message_user(request, f'Duplicated reward to {duplicated_count} similar policies.')


@admin.register(AdditionalFeatures)
class AdditionalFeaturesAdmin(admin.ModelAdmin):
    form = AdditionalFeaturesAdminForm
    list_display = [
        'title',
        'policy_name_display',
        'insurance_type_display',
        'has_coverage_details',
        'is_highlighted_display',
        'display_order',
        'created_at'
    ]
    list_filter = [
        'is_highlighted',
        'policy__category',
        'policy__organization',
        'policy__policy_features__insurance_type',
        'created_at'
    ]
    search_fields = [
        'title',
        'description',
        'coverage_details',
        'policy__name',
        'policy__organization__name'
    ]
    list_select_related = ['policy', 'policy__organization', 'policy__policy_features']
    list_editable = ['display_order']
    ordering = ['policy', 'display_order', 'title']
    
    fieldsets = (
        (_('Basic Information'), {
            'fields': ('policy', 'title', 'description'),
            'description': _('Basic information about this additional feature.')
        }),
        (_('Coverage Details'), {
            'fields': ('coverage_details',),
            'description': _('Detailed coverage information and descriptions for this feature.')
        }),
        (_('Display Settings'), {
            'fields': ('icon', 'is_highlighted', 'display_order'),
            'description': _('Control how this feature appears in the user interface.')
        }),
        (_('Metadata'), {
            'fields': ('created_at',),
            'classes': ('collapse',)
        })
    )
    
    readonly_fields = ['created_at']
    
    actions = [
        'highlight_features',
        'unhighlight_features',
        'duplicate_to_similar_policies'
    ]
    
    def policy_name_display(self, obj):
        """Display policy name with link"""
        url = reverse('admin:policies_basepolicy_change', args=[obj.policy.pk])
        return format_html(
            '<a href="{}" style="text-decoration: none;">{}</a>',
            url,
            obj.policy.name
        )
    policy_name_display.short_description = _('Policy')
    policy_name_display.admin_order_field = 'policy__name'
    
    def insurance_type_display(self, obj):
        """Display insurance type from related PolicyFeatures"""
        try:
            insurance_type = obj.policy.policy_features.insurance_type
            colors = {
                'HEALTH': '#28a745',
                'FUNERAL': '#6f42c1'
            }
            color = colors.get(insurance_type, '#6c757d')
            display_name = obj.policy.policy_features.get_insurance_type_display()
            return format_html(
                '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 3px; font-size: 11px;">{}</span>',
                color,
                display_name
            )
        except PolicyFeatures.DoesNotExist:
            return format_html('<span style="color: #6c757d;">{}</span>', '❓ Not Set')
    insurance_type_display.short_description = _('Insurance Type')
    
    def is_highlighted_display(self, obj):
        """Display highlighted status with visual indicator"""
        if obj.is_highlighted:
            return format_html('<span style="color: #ffc107;">{}</span>', '⭐ Highlighted')
        return format_html('<span style="color: #6c757d;">{}</span>', '☆ Regular')
    is_highlighted_display.short_description = _('Highlight Status')
    is_highlighted_display.admin_order_field = 'is_highlighted'
    
    def has_coverage_details(self, obj):
        """Display whether coverage details are provided"""
        if obj.coverage_details and obj.coverage_details.strip():
            return format_html('<span style="color: #28a745;">{}</span>', '✓ Details')
        return format_html('<span style="color: #6c757d;">{}</span>', '— No Details')
    has_coverage_details.short_description = _('Coverage Details')
    has_coverage_details.admin_order_field = 'coverage_details'
    
    def get_queryset(self, request):
        """Optimize queryset with related objects"""
        qs = super().get_queryset(request)
        return qs.select_related(
            'policy',
            'policy__organization',
            'policy__policy_features'
        )
    
    # Admin Actions
    @admin.action(description=_('Highlight selected features'))
    def highlight_features(self, request, queryset):
        updated = queryset.update(is_highlighted=True)
        self.message_user(request, f'{updated} features highlighted.')
    
    @admin.action(description=_('Remove highlight from selected features'))
    def unhighlight_features(self, request, queryset):
        updated = queryset.update(is_highlighted=False)
        self.message_user(request, f'{updated} features unhighlighted.')
    
    @admin.action(description=_('Duplicate features to similar policies'))
    def duplicate_to_similar_policies(self, request, queryset):
        duplicated_count = 0
        for feature in queryset:
            # Find similar policies (same category and type)
            similar_policies = BasePolicy.objects.filter(
                category=feature.policy.category,
                policy_type=feature.policy.policy_type
            ).exclude(pk=feature.policy.pk)
            
            for policy in similar_policies:
                # Check if similar feature already exists
                if not AdditionalFeatures.objects.filter(
                    policy=policy,
                    title=feature.title
                ).exists():
                    AdditionalFeatures.objects.create(
                        policy=policy,
                        title=feature.title,
                        description=feature.description,
                        icon=feature.icon,
                        is_highlighted=feature.is_highlighted,
                        display_order=feature.display_order
                    )
                    duplicated_count += 1
        
        self.message_user(request, f'Duplicated {duplicated_count} features to similar policies.')


@admin.register(PolicyEligibility)
class PolicyEligibilityAdmin(admin.ModelAdmin):
    list_display = ['criterion', 'policy', 'is_mandatory', 'display_order']
    list_filter = ['is_mandatory', 'policy__category']
    search_fields = ['criterion', 'description', 'policy__name']
    list_select_related = ['policy']


@admin.register(PolicyExclusion)
class PolicyExclusionAdmin(admin.ModelAdmin):
    list_display = ['title', 'policy', 'display_order']
    list_filter = ['policy__category']
    search_fields = ['title', 'description', 'policy__name']
    list_select_related = ['policy']


@admin.register(PolicyDocument)
class PolicyDocumentAdmin(admin.ModelAdmin):
    list_display = ['title', 'policy', 'document_type', 'is_public', 'uploaded_at']
    list_filter = ['document_type', 'is_public', 'uploaded_at', 'policy__category']
    search_fields = ['title', 'description', 'policy__name']
    list_select_related = ['policy']


@admin.register(PolicyPremiumCalculation)
class PolicyPremiumCalculationAdmin(admin.ModelAdmin):
    list_display = ['factor_name', 'factor_value', 'policy', 'multiplier', 'additional_amount', 'is_active']
    list_filter = ['factor_name', 'is_active', 'policy__category']
    search_fields = ['factor_name', 'factor_value', 'policy__name']
    list_select_related = ['policy']

# Import integration utilities
from .admin_integration import (
    SystemIntegrationAdminMixin,
    validate_policies_action,
    validate_surveys_action,
    IntegrationStatusFilter,
    integration_urlpatterns
)
from .signals import get_cached_validation_errors


# Add integration features to existing admin classes
class IntegratedBasePolicyAdmin(BasePolicyAdmin, SystemIntegrationAdminMixin):
    """Enhanced BasePolicy admin with integration features."""
    
    list_display = BasePolicyAdmin.list_display + ['integration_status']
    list_filter = BasePolicyAdmin.list_filter + [IntegrationStatusFilter]
    actions = BasePolicyAdmin.actions + [validate_policies_action]
    
    def integration_status(self, obj):
        """Display integration status for policy."""
        return self.get_validation_errors_display(obj, 'policy')
    
    integration_status.short_description = "Integration Status"


class IntegratedPolicyFeaturesAdmin(PolicyFeaturesAdmin, SystemIntegrationAdminMixin):
    """Enhanced PolicyFeatures admin with integration features."""
    
    list_display = PolicyFeaturesAdmin.list_display + ['integration_status']
    actions = PolicyFeaturesAdmin.actions + [validate_policies_action]
    
    def integration_status(self, obj):
        """Display integration status for policy features."""
        return self.get_validation_errors_display(obj.policy, 'policy')
    
    integration_status.short_description = "Integration Status"


# Re-register with integration features
admin.site.unregister(BasePolicy)
admin.site.unregister(PolicyFeatures)

admin.site.register(BasePolicy, IntegratedBasePolicyAdmin)
admin.site.register(PolicyFeatures, IntegratedPolicyFeaturesAdmin)


# Add integration URLs to admin - removed to avoid recursion
# Integration URLs will be added through the custom admin site instead


# Add integration menu item to admin
def add_integration_to_admin_index(request):
    """Add integration link to admin index."""
    from django.template.response import TemplateResponse
    from django.urls import reverse
    
    # This would be used in a custom admin template
    integration_url = reverse('admin:system_integration')
    return {
        'integration_url': integration_url,
        'integration_title': 'System Integration'
    }


# Custom admin site configuration
class IntegratedAdminSite(admin.AdminSite):
    """Custom admin site with integration features."""
    
    site_header = "Policy System Administration"
    site_title = "Policy Admin"
    index_title = "Policy System Management"
    
    def get_urls(self):
        """Add integration URLs to admin."""
        urls = super().get_urls()
        integration_urls = [
            path('integration/', include(integration_urlpatterns)),
        ]
        return integration_urls + urls
    
    def index(self, request, extra_context=None):
        """Add integration context to admin index."""
        extra_context = extra_context or {}
        
        # Add system health metrics
        from .signals import get_system_health_metrics
        extra_context['system_health'] = get_system_health_metrics()
        
        # Add integration status
        from .integration import SystemIntegrationManager
        try:
            system_status = SystemIntegrationManager.perform_full_system_check()
            extra_context['system_status'] = system_status['overall_status']
        except Exception:
            extra_context['system_status'] = 'unknown'
        
        return super().index(request, extra_context)


# Create integrated admin site instance
integrated_admin_site = IntegratedAdminSite(name='integrated_admin')

# Register models with integrated admin site
integrated_admin_site.register(PolicyCategory, PolicyCategoryAdmin)
integrated_admin_site.register(PolicyType, PolicyTypeAdmin)
integrated_admin_site.register(BasePolicy, IntegratedBasePolicyAdmin)
integrated_admin_site.register(PolicyFeatures, IntegratedPolicyFeaturesAdmin)
integrated_admin_site.register(AdditionalFeatures, AdditionalFeaturesAdmin)
integrated_admin_site.register(PolicyReview, PolicyReviewAdmin)