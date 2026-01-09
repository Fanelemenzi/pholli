from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import Organization, OrganizationContact, OrganizationDocument


class OrganizationContactInline(admin.TabularInline):
    """Inline admin for organization contacts."""
    model = OrganizationContact
    extra = 1
    fields = ('first_name', 'last_name', 'role', 'email', 'phone', 'is_primary', 'is_active')
    readonly_fields = ('created_at', 'updated_at')


class OrganizationDocumentInline(admin.TabularInline):
    """Inline admin for organization documents."""
    model = OrganizationDocument
    extra = 0
    fields = ('document_type', 'title', 'file', 'is_verified', 'expiry_date')
    readonly_fields = ('uploaded_at', 'verified_at', 'verified_by')


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    """Admin interface for Organization model."""
    
    list_display = (
        'name', 
        'verification_status_badge', 
        'is_active', 
        'active_policies_count',
        'email', 
        'phone',
        'city',
        'created_at'
    )
    
    list_filter = (
        'verification_status',
        'is_active',
        'country',
        'state_province',
        'created_at',
        'updated_at'
    )
    
    search_fields = (
        'name',
        'email',
        'registration_number',
        'license_number',
        'city',
        'description'
    )
    
    readonly_fields = (
        'created_at',
        'updated_at',
        'verified_at',
        'active_policies_count',
        'logo_preview'
    )
    
    fieldsets = (
        (_('Basic Information'), {
            'fields': (
                'name',
                'logo',
                'logo_preview',
                'description'
            )
        }),
        (_('Contact Details'), {
            'fields': (
                'email',
                'phone',
                'alternative_phone',
                'website'
            )
        }),
        (_('Address'), {
            'fields': (
                'address_line1',
                'address_line2',
                'city',
                'state_province',
                'postal_code',
                'country'
            )
        }),
        (_('Registration & License'), {
            'fields': (
                'registration_number',
                'license_number'
            )
        }),
        (_('Status & Verification'), {
            'fields': (
                'verification_status',
                'is_active',
                'verified_at'
            )
        }),
        (_('Configuration'), {
            'fields': (
                'max_policies',
                'commission_rate',
                'custom_config'
            ),
            'classes': ('collapse',)
        }),
        (_('Additional Information'), {
            'fields': (
                'year_established',
                'employee_count_range'
            ),
            'classes': ('collapse',)
        }),
        (_('Metadata'), {
            'fields': (
                'active_policies_count',
                'created_at',
                'updated_at'
            ),
            'classes': ('collapse',)
        })
    )
    
    inlines = [OrganizationContactInline, OrganizationDocumentInline]
    
    actions = ['verify_organizations', 'suspend_organizations', 'activate_organizations']
    
    def verification_status_badge(self, obj):
        """Display verification status with colored badge."""
        colors = {
            'PENDING': '#ffc107',
            'VERIFIED': '#28a745',
            'REJECTED': '#dc3545',
            'SUSPENDED': '#6c757d'
        }
        color = colors.get(obj.verification_status, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; '
            'border-radius: 3px; font-size: 11px; font-weight: bold;">{}</span>',
            color,
            obj.get_verification_status_display()
        )
    verification_status_badge.short_description = _('Status')
    verification_status_badge.admin_order_field = 'verification_status'
    
    def active_policies_count(self, obj):
        """Display count of active policies with link."""
        count = obj.get_active_policies_count()
        if count > 0:
            # Assuming there's a policy admin with organization filter
            url = reverse('admin:policies_policy_changelist') + f'?organization__id__exact={obj.id}'
            return format_html('<a href="{}">{} policies</a>', url, count)
        return '0 policies'
    active_policies_count.short_description = _('Active Policies')
    
    def logo_preview(self, obj):
        """Display logo preview in admin."""
        if obj.logo:
            return format_html(
                '<img src="{}" style="max-height: 100px; max-width: 100px;" />',
                obj.logo.url
            )
        return _('No logo uploaded')
    logo_preview.short_description = _('Logo Preview')
    
    def verify_organizations(self, request, queryset):
        """Bulk action to verify organizations."""
        from django.utils import timezone
        updated = queryset.update(
            verification_status=Organization.VerificationStatus.VERIFIED,
            verified_at=timezone.now()
        )
        self.message_user(
            request,
            f'{updated} organization(s) were successfully verified.'
        )
    verify_organizations.short_description = _('Verify selected organizations')
    
    def suspend_organizations(self, request, queryset):
        """Bulk action to suspend organizations."""
        updated = queryset.update(
            verification_status=Organization.VerificationStatus.SUSPENDED,
            is_active=False
        )
        self.message_user(
            request,
            f'{updated} organization(s) were successfully suspended.'
        )
    suspend_organizations.short_description = _('Suspend selected organizations')
    
    def activate_organizations(self, request, queryset):
        """Bulk action to activate organizations."""
        updated = queryset.update(is_active=True)
        self.message_user(
            request,
            f'{updated} organization(s) were successfully activated.'
        )
    activate_organizations.short_description = _('Activate selected organizations')


@admin.register(OrganizationContact)
class OrganizationContactAdmin(admin.ModelAdmin):
    """Admin interface for OrganizationContact model."""
    
    list_display = (
        'get_full_name',
        'organization',
        'role',
        'email',
        'phone',
        'is_primary',
        'is_active'
    )
    
    list_filter = (
        'role',
        'is_primary',
        'is_active',
        'organization__verification_status'
    )
    
    search_fields = (
        'first_name',
        'last_name',
        'email',
        'organization__name',
        'job_title'
    )
    
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        (_('Contact Information'), {
            'fields': (
                'organization',
                'first_name',
                'last_name',
                'job_title',
                'role'
            )
        }),
        (_('Contact Details'), {
            'fields': (
                'email',
                'phone'
            )
        }),
        (_('Status'), {
            'fields': (
                'is_primary',
                'is_active'
            )
        }),
        (_('Additional Information'), {
            'fields': (
                'notes',
            )
        }),
        (_('Metadata'), {
            'fields': (
                'created_at',
                'updated_at'
            ),
            'classes': ('collapse',)
        })
    )
    
    def get_full_name(self, obj):
        """Display full name of contact."""
        return obj.get_full_name()
    get_full_name.short_description = _('Full Name')
    get_full_name.admin_order_field = 'last_name'


@admin.register(OrganizationDocument)
class OrganizationDocumentAdmin(admin.ModelAdmin):
    """Admin interface for OrganizationDocument model."""
    
    list_display = (
        'title',
        'organization',
        'document_type',
        'is_verified',
        'expiry_status',
        'uploaded_at'
    )
    
    list_filter = (
        'document_type',
        'is_verified',
        'issue_date',
        'expiry_date',
        'uploaded_at'
    )
    
    search_fields = (
        'title',
        'organization__name',
        'description'
    )
    
    readonly_fields = (
        'uploaded_at',
        'verified_at',
        'verified_by',
        'file_preview'
    )
    
    fieldsets = (
        (_('Document Information'), {
            'fields': (
                'organization',
                'document_type',
                'title',
                'description'
            )
        }),
        (_('File'), {
            'fields': (
                'file',
                'file_preview'
            )
        }),
        (_('Dates'), {
            'fields': (
                'issue_date',
                'expiry_date'
            )
        }),
        (_('Verification'), {
            'fields': (
                'is_verified',
                'verified_by',
                'verified_at'
            )
        }),
        (_('Metadata'), {
            'fields': (
                'uploaded_at',
            ),
            'classes': ('collapse',)
        })
    )
    
    actions = ['verify_documents', 'unverify_documents']
    
    def expiry_status(self, obj):
        """Display expiry status with colored indicator."""
        if not obj.expiry_date:
            return _('No expiry')
        
        if obj.is_expired:
            return format_html(
                '<span style="color: #dc3545; font-weight: bold;">Expired</span>'
            )
        else:
            return format_html(
                '<span style="color: #28a745;">Valid</span>'
            )
    expiry_status.short_description = _('Expiry Status')
    
    def file_preview(self, obj):
        """Display file preview or download link."""
        if obj.file:
            file_url = obj.file.url
            file_name = obj.file.name.split('/')[-1]
            return format_html(
                '<a href="{}" target="_blank">{}</a>',
                file_url,
                file_name
            )
        return _('No file uploaded')
    file_preview.short_description = _('File')
    
    def verify_documents(self, request, queryset):
        """Bulk action to verify documents."""
        from django.utils import timezone
        updated = queryset.update(
            is_verified=True,
            verified_by=request.user,
            verified_at=timezone.now()
        )
        self.message_user(
            request,
            f'{updated} document(s) were successfully verified.'
        )
    verify_documents.short_description = _('Verify selected documents')
    
    def unverify_documents(self, request, queryset):
        """Bulk action to unverify documents."""
        updated = queryset.update(
            is_verified=False,
            verified_by=None,
            verified_at=None
        )
        self.message_user(
            request,
            f'{updated} document(s) were successfully unverified.'
        )
    unverify_documents.short_description = _('Unverify selected documents')