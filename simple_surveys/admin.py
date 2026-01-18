from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from django.db.models import Count
from .models import SimpleSurveyQuestion, SimpleSurveyResponse, QuotationSession, SimpleSurvey


@admin.register(SimpleSurvey)
class SimpleSurveyAdmin(admin.ModelAdmin):
    """Admin interface for SimpleSurvey"""
    
    list_display = [
        'full_name', 'insurance_type', 'date_of_birth', 'email', 'phone',
        'is_complete_display', 'created_at'
    ]
    list_filter = ['insurance_type', 'created_at', 'date_of_birth']
    search_fields = ['first_name', 'last_name', 'email', 'phone']
    ordering = ['-created_at']
    
    fieldsets = (
        ('Contact Information', {
            'fields': ('first_name', 'last_name', 'date_of_birth', 'email', 'phone')
        }),
        ('Insurance Type', {
            'fields': ('insurance_type',)
        }),
        ('Health Policy Preferences', {
            'fields': (
                'preferred_annual_limit', 'household_income', 'wants_in_hospital_benefit',
                'wants_out_hospital_benefit', 'needs_chronic_medication'
            ),
            'classes': ('collapse',)
        }),
        ('Funeral Policy Preferences', {
            'fields': (
                'preferred_cover_amount', 'marital_status', 'gender', 'net_income'
            ),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['created_at', 'updated_at']
    
    def full_name(self, obj):
        """Display full name"""
        return f"{obj.first_name} {obj.last_name}"
    full_name.short_description = "Name"
    
    def is_complete_display(self, obj):
        """Display completion status with color coding"""
        if obj.is_complete():
            return format_html('<span style="color: #28a745; font-weight: bold;">{}</span>', 'Complete')
        else:
            missing_fields = obj.get_missing_fields()
            return format_html(
                '<span style="color: #dc3545; font-weight: bold;" title="Missing: {}">Incomplete</span>',
                ', '.join(missing_fields)
            )
    is_complete_display.short_description = "Status"
    
    def get_queryset(self, request):
        """Optimize queryset"""
        return super().get_queryset(request).select_related()
    
    actions = ['export_preferences']
    
    def export_preferences(self, request, queryset):
        """Export user preferences for selected surveys"""
        # This could be expanded to generate CSV or other export formats
        count = queryset.count()
        self.message_user(request, f'Preferences exported for {count} surveys.')
    export_preferences.short_description = "Export preferences for selected surveys"


@admin.register(SimpleSurveyQuestion)
class SimpleSurveyQuestionAdmin(admin.ModelAdmin):
    """Admin interface for SimpleSurveyQuestion"""
    
    list_display = [
        'question_text_short', 'category', 'field_name', 'input_type', 
        'is_required', 'display_order', 'response_count'
    ]
    list_filter = ['category', 'input_type', 'is_required', 'created_at']
    search_fields = ['question_text', 'field_name']
    ordering = ['category', 'display_order']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('category', 'question_text', 'field_name', 'input_type')
        }),
        ('Configuration', {
            'fields': ('choices', 'is_required', 'display_order', 'validation_rules')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['created_at', 'updated_at']
    
    def question_text_short(self, obj):
        """Display shortened question text"""
        return obj.question_text[:60] + "..." if len(obj.question_text) > 60 else obj.question_text
    question_text_short.short_description = "Question"
    
    def response_count(self, obj):
        """Display count of responses for this question"""
        count = SimpleSurveyResponse.objects.filter(question=obj).count()
        return format_html('<span style="color: #0066cc;">{}</span>', count)
    response_count.short_description = "Responses"
    
    def get_queryset(self, request):
        """Optimize queryset with response counts"""
        return super().get_queryset(request).annotate(
            response_count=Count('simplesurveyresponse')
        )


@admin.register(SimpleSurveyResponse)
class SimpleSurveyResponseAdmin(admin.ModelAdmin):
    """Admin interface for SimpleSurveyResponse"""
    
    list_display = [
        'session_key_short', 'category', 'question_field_name', 
        'response_display', 'created_at'
    ]
    list_filter = ['category', 'question__input_type', 'created_at']
    search_fields = ['session_key', 'question__question_text', 'question__field_name']
    ordering = ['-created_at']
    
    fieldsets = (
        ('Response Information', {
            'fields': ('session_key', 'category', 'question', 'response_value')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['created_at', 'updated_at']
    
    def session_key_short(self, obj):
        """Display shortened session key"""
        return obj.session_key[:12] + "..." if len(obj.session_key) > 12 else obj.session_key
    session_key_short.short_description = "Session"
    
    def question_field_name(self, obj):
        """Display question field name"""
        return obj.question.field_name
    question_field_name.short_description = "Field"
    
    def response_display(self, obj):
        """Display formatted response value"""
        display_value = obj.get_display_value()
        if len(display_value) > 50:
            display_value = display_value[:47] + "..."
        return format_html('<span title="{}">{}</span>', obj.get_display_value(), display_value)
    response_display.short_description = "Response"


@admin.register(QuotationSession)
class QuotationSessionAdmin(admin.ModelAdmin):
    """Admin interface for QuotationSession"""
    
    list_display = [
        'session_key_short', 'category', 'is_completed', 'completion_percentage',
        'response_count_display', 'created_at', 'expires_at', 'status'
    ]
    list_filter = ['category', 'is_completed', 'created_at', 'expires_at']
    search_fields = ['session_key']
    ordering = ['-created_at']
    
    fieldsets = (
        ('Session Information', {
            'fields': ('session_key', 'category', 'is_completed')
        }),
        ('User Criteria', {
            'fields': ('user_criteria',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'expires_at')
        }),
    )
    
    readonly_fields = ['created_at']
    
    def session_key_short(self, obj):
        """Display shortened session key"""
        return obj.session_key[:12] + "..." if len(obj.session_key) > 12 else obj.session_key
    session_key_short.short_description = "Session"
    
    def completion_percentage(self, obj):
        """Display completion percentage with color coding"""
        percentage = obj.get_completion_percentage()
        if percentage == 100:
            color = "#28a745"  # Green
        elif percentage >= 50:
            color = "#ffc107"  # Yellow
        else:
            color = "#dc3545"  # Red
        
        return format_html(
            '<span style="color: {}; font-weight: bold;">{} %</span>',
            color, percentage
        )
    completion_percentage.short_description = "Progress"
    
    def response_count_display(self, obj):
        """Display response count"""
        count = obj.get_response_count()
        return format_html('<span style="color: #0066cc;">{}</span>', count)
    response_count_display.short_description = "Responses"
    
    def status(self, obj):
        """Display session status with color coding"""
        if obj.is_expired():
            return format_html('<span style="color: #dc3545;">{}</span>', 'Expired')
        elif obj.is_completed:
            return format_html('<span style="color: #28a745;">{}</span>', 'Completed')
        else:
            return format_html('<span style="color: #ffc107;">{}</span>', 'Active')
    status.short_description = "Status"
    
    actions = ['mark_completed', 'extend_expiry', 'cleanup_expired']
    
    def mark_completed(self, request, queryset):
        """Mark selected sessions as completed"""
        updated = queryset.update(is_completed=True)
        self.message_user(request, f'{updated} sessions marked as completed.')
    mark_completed.short_description = "Mark selected sessions as completed"
    
    def extend_expiry(self, request, queryset):
        """Extend expiry of selected sessions by 24 hours"""
        for session in queryset:
            session.extend_expiry()
        self.message_user(request, f'{queryset.count()} sessions extended by 24 hours.')
    extend_expiry.short_description = "Extend expiry by 24 hours"
    
    def cleanup_expired(self, request, queryset):
        """Delete expired sessions and their responses"""
        expired_sessions = queryset.filter(expires_at__lte=timezone.now())
        count = expired_sessions.count()
        
        # Delete associated responses first
        SimpleSurveyResponse.objects.filter(
            session_key__in=expired_sessions.values_list('session_key', flat=True)
        ).delete()
        
        # Delete expired sessions
        expired_sessions.delete()
        
        self.message_user(request, f'{count} expired sessions and their responses deleted.')
    cleanup_expired.short_description = "Delete expired sessions"


# Custom admin site configuration
admin.site.site_header = "Simple Surveys Administration"
admin.site.site_title = "Simple Surveys Admin"
admin.site.index_title = "Welcome to Simple Surveys Administration"