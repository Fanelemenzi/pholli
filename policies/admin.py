from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.urls import reverse
from django.db.models import Avg, Count, Q
from .models import (
    PolicyCategory,
    PolicyType,
    BasePolicy,
    PolicyFeature,
    PolicyEligibility,
    PolicyExclusion,
    PolicyDocument,
    PolicyPremiumCalculation,
    PolicyReview
)


# Inline Admin Classes
class PolicyFeatureInline(admin.TabularInline):
    model = PolicyFeature
    extra = 1
    fields = ['title', 'description', 'icon', 'is_highlighted', 'display_order']
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
        PolicyFeatureInline,
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
            return format_html('<span style="color: green;">✓ Approved</span>')
        return format_html('<span style="color: orange;">⧗ Pending</span>')
    approval_status.short_description = _('Status')
    approval_status.boolean = True


# Register remaining models with simple admin
@admin.register(PolicyFeature)
class PolicyFeatureAdmin(admin.ModelAdmin):
    list_display = ['title', 'policy', 'is_highlighted', 'display_order']
    list_filter = ['is_highlighted', 'policy__category']
    search_fields = ['title', 'description', 'policy__name']
    list_select_related = ['policy']


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