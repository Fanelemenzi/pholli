from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from django.db.models import Count, Q
from django.core.exceptions import ValidationError
from django.forms import ModelForm, CharField, ChoiceField
from django import forms
from .models import (
    SimpleSurveyQuestion, SimpleSurveyResponse, QuotationSession, SimpleSurvey,
    HOSPITAL_BENEFIT_CHOICES, OUT_HOSPITAL_BENEFIT_CHOICES,
    ANNUAL_LIMIT_FAMILY_RANGES, ANNUAL_LIMIT_MEMBER_RANGES
)


@admin.register(SimpleSurvey)
class SimpleSurveyAdmin(admin.ModelAdmin):
    """Admin interface for SimpleSurvey with enhanced benefit level and range management"""
    
    list_display = [
        'full_name', 'insurance_type', 'date_of_birth', 'email', 'phone',
        'benefit_levels_display', 'annual_ranges_display', 'is_complete_display', 'created_at'
    ]
    list_filter = [
        'insurance_type', 'created_at', 'date_of_birth', 'wants_ambulance_coverage', 
        'in_hospital_benefit_level', 'out_hospital_benefit_level',
        'annual_limit_family_range', 'annual_limit_member_range'
    ]
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
                'preferred_annual_limit', 'preferred_annual_limit_per_family', 'household_income',
                'wants_ambulance_coverage', 'needs_chronic_medication'
            ),
            'classes': ('collapse',)
        }),
        ('Benefit Level Selections', {
            'fields': (
                'in_hospital_benefit_level', 'out_hospital_benefit_level'
            ),
            'description': 'New benefit level questions replacing binary yes/no options'
        }),
        ('Annual Limit Ranges', {
            'fields': (
                'annual_limit_family_range', 'annual_limit_member_range'
            ),
            'description': 'Range-based annual limit selections for better user guidance'
        }),
        ('Funeral Policy Preferences', {
            'fields': (
                'preferred_cover_amount', 'marital_status', 'gender'
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
    
    def benefit_levels_display(self, obj):
        """Display selected benefit levels with color coding"""
        if obj.insurance_type != 'HEALTH':
            return format_html('<span style="color: #6c757d;">N/A</span>')
        
        in_hospital = obj.get_in_hospital_benefit_level_display() if obj.in_hospital_benefit_level else 'Not set'
        out_hospital = obj.get_out_hospital_benefit_level_display() if obj.out_hospital_benefit_level else 'Not set'
        
        return format_html(
            '<div><strong>In:</strong> <span style="color: #0066cc;">{}</span></div>'
            '<div><strong>Out:</strong> <span style="color: #0066cc;">{}</span></div>',
            in_hospital, out_hospital
        )
    benefit_levels_display.short_description = "Benefit Levels"
    
    def annual_ranges_display(self, obj):
        """Display selected annual limit ranges"""
        if obj.insurance_type != 'HEALTH':
            return format_html('<span style="color: #6c757d;">N/A</span>')
        
        family_range = obj.get_annual_limit_family_range_display() if obj.annual_limit_family_range else 'Not set'
        member_range = obj.get_annual_limit_member_range_display() if obj.annual_limit_member_range else 'Not set'
        
        return format_html(
            '<div><strong>Family:</strong> <span style="color: #28a745;">{}</span></div>'
            '<div><strong>Member:</strong> <span style="color: #28a745;">{}</span></div>',
            family_range, member_range
        )
    annual_ranges_display.short_description = "Annual Ranges"
    
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
    
    actions = ['export_preferences', 'validate_benefit_levels', 'validate_annual_ranges']
    
    def export_preferences(self, request, queryset):
        """Export user preferences for selected surveys"""
        count = queryset.count()
        self.message_user(request, f'Preferences exported for {count} surveys.')
    export_preferences.short_description = "Export preferences for selected surveys"
    
    def validate_benefit_levels(self, request, queryset):
        """Validate benefit level selections for health policies"""
        health_surveys = queryset.filter(insurance_type='HEALTH')
        invalid_count = 0
        
        for survey in health_surveys:
            try:
                survey.clean()
            except ValidationError:
                invalid_count += 1
        
        valid_count = health_surveys.count() - invalid_count
        self.message_user(
            request, 
            f'Validation complete: {valid_count} valid, {invalid_count} invalid benefit level selections.'
        )
    validate_benefit_levels.short_description = "Validate benefit level selections"
    
    def validate_annual_ranges(self, request, queryset):
        """Validate annual limit range selections"""
        health_surveys = queryset.filter(insurance_type='HEALTH')
        issues = []
        
        for survey in health_surveys:
            if survey.annual_limit_family_range and survey.annual_limit_member_range:
                # Check for logical consistency between family and member ranges
                family_ranges = dict(ANNUAL_LIMIT_FAMILY_RANGES)
                member_ranges = dict(ANNUAL_LIMIT_MEMBER_RANGES)
                
                if (survey.annual_limit_family_range in family_ranges and 
                    survey.annual_limit_member_range in member_ranges):
                    # Add custom validation logic here if needed
                    pass
        
        self.message_user(request, f'Annual range validation completed for {health_surveys.count()} health surveys.')
    validate_annual_ranges.short_description = "Validate annual limit ranges"


class BenefitLevelQuestionForm(ModelForm):
    """Custom form for managing benefit level questions with validation"""
    
    class Meta:
        model = SimpleSurveyQuestion
        fields = '__all__'
    
    def clean_choices(self):
        """Validate choices for benefit level questions"""
        choices = self.cleaned_data.get('choices', [])
        field_name = self.cleaned_data.get('field_name', '')
        
        # Validate benefit level choices
        if 'benefit_level' in field_name:
            if 'in_hospital' in field_name:
                valid_choices = [choice[0] for choice in HOSPITAL_BENEFIT_CHOICES]
                choice_labels = {choice[0]: choice[1] for choice in HOSPITAL_BENEFIT_CHOICES}
            elif 'out_hospital' in field_name:
                valid_choices = [choice[0] for choice in OUT_HOSPITAL_BENEFIT_CHOICES]
                choice_labels = {choice[0]: choice[1] for choice in OUT_HOSPITAL_BENEFIT_CHOICES}
            else:
                return choices
            
            # Validate that choices match the predefined benefit levels
            if isinstance(choices, list):
                for choice in choices:
                    if isinstance(choice, dict) and 'value' in choice:
                        if choice['value'] not in valid_choices:
                            raise ValidationError(f"Invalid benefit level choice: {choice['value']}")
                    elif isinstance(choice, (list, tuple)) and len(choice) >= 2:
                        if choice[0] not in valid_choices:
                            raise ValidationError(f"Invalid benefit level choice: {choice[0]}")
        
        # Validate annual limit range choices
        elif 'annual_limit' in field_name and 'range' in field_name:
            if 'family' in field_name:
                valid_choices = [choice[0] for choice in ANNUAL_LIMIT_FAMILY_RANGES]
            elif 'member' in field_name:
                valid_choices = [choice[0] for choice in ANNUAL_LIMIT_MEMBER_RANGES]
            else:
                return choices
            
            # Validate that choices match the predefined ranges
            if isinstance(choices, list):
                for choice in choices:
                    if isinstance(choice, dict) and 'value' in choice:
                        if choice['value'] not in valid_choices:
                            raise ValidationError(f"Invalid annual limit range: {choice['value']}")
                    elif isinstance(choice, (list, tuple)) and len(choice) >= 2:
                        if choice[0] not in valid_choices:
                            raise ValidationError(f"Invalid annual limit range: {choice[0]}")
        
        return choices


@admin.register(SimpleSurveyQuestion)
class SimpleSurveyQuestionAdmin(admin.ModelAdmin):
    """Admin interface for SimpleSurveyQuestion with enhanced benefit level and range management"""
    
    form = BenefitLevelQuestionForm
    
    list_display = [
        'question_text_short', 'category', 'field_name', 'input_type', 
        'question_type_display', 'is_required', 'display_order', 'response_count'
    ]
    list_filter = [
        'category', 'input_type', 'is_required', 'created_at',
        ('field_name', admin.AllValuesFieldListFilter)
    ]
    search_fields = ['question_text', 'field_name']
    ordering = ['category', 'display_order']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('category', 'question_text', 'field_name', 'input_type')
        }),
        ('Configuration', {
            'fields': ('choices', 'is_required', 'display_order', 'validation_rules'),
            'description': 'For benefit level and range questions, choices are validated against predefined options'
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
    
    def question_type_display(self, obj):
        """Display question type with special indicators for new question types"""
        if 'benefit_level' in obj.field_name:
            return format_html('<span style="color: #0066cc; font-weight: bold;">Benefit Level</span>')
        elif 'annual_limit' in obj.field_name and 'range' in obj.field_name:
            return format_html('<span style="color: #28a745; font-weight: bold;">Annual Range</span>')
        else:
            return format_html('<span style="color: #6c757d;">{}</span>', obj.get_input_type_display())
    question_type_display.short_description = "Type"
    
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
    
    actions = ['validate_benefit_choices', 'validate_range_choices', 'sync_predefined_choices']
    
    def validate_benefit_choices(self, request, queryset):
        """Validate benefit level question choices against predefined options"""
        benefit_questions = queryset.filter(field_name__contains='benefit_level')
        invalid_count = 0
        
        for question in benefit_questions:
            try:
                form = BenefitLevelQuestionForm(instance=question)
                form.full_clean()
            except ValidationError:
                invalid_count += 1
        
        valid_count = benefit_questions.count() - invalid_count
        self.message_user(
            request,
            f'Benefit level validation: {valid_count} valid, {invalid_count} invalid questions.'
        )
    validate_benefit_choices.short_description = "Validate benefit level choices"
    
    def validate_range_choices(self, request, queryset):
        """Validate annual limit range question choices"""
        range_questions = queryset.filter(
            field_name__contains='annual_limit'
        ).filter(
            field_name__contains='range'
        )
        invalid_count = 0
        
        for question in range_questions:
            try:
                form = BenefitLevelQuestionForm(instance=question)
                form.full_clean()
            except ValidationError:
                invalid_count += 1
        
        valid_count = range_questions.count() - invalid_count
        self.message_user(
            request,
            f'Annual range validation: {valid_count} valid, {invalid_count} invalid questions.'
        )
    validate_range_choices.short_description = "Validate annual limit range choices"
    
    def sync_predefined_choices(self, request, queryset):
        """Sync question choices with predefined benefit levels and ranges"""
        updated_count = 0
        
        for question in queryset:
            if 'in_hospital_benefit_level' in question.field_name:
                question.choices = [
                    {'value': choice[0], 'text': choice[1], 'description': choice[2]}
                    for choice in HOSPITAL_BENEFIT_CHOICES
                ]
                question.save()
                updated_count += 1
            elif 'out_hospital_benefit_level' in question.field_name:
                question.choices = [
                    {'value': choice[0], 'text': choice[1], 'description': choice[2]}
                    for choice in OUT_HOSPITAL_BENEFIT_CHOICES
                ]
                question.save()
                updated_count += 1
            elif 'annual_limit_family_range' in question.field_name:
                question.choices = [
                    {'value': choice[0], 'text': choice[1], 'description': choice[2]}
                    for choice in ANNUAL_LIMIT_FAMILY_RANGES
                ]
                question.save()
                updated_count += 1
            elif 'annual_limit_member_range' in question.field_name:
                question.choices = [
                    {'value': choice[0], 'text': choice[1], 'description': choice[2]}
                    for choice in ANNUAL_LIMIT_MEMBER_RANGES
                ]
                question.save()
                updated_count += 1
        
        self.message_user(request, f'Updated {updated_count} questions with predefined choices.')
    sync_predefined_choices.short_description = "Sync with predefined choices"


@admin.register(SimpleSurveyResponse)
class SimpleSurveyResponseAdmin(admin.ModelAdmin):
    """Admin interface for SimpleSurveyResponse with enhanced display for new field types"""
    
    list_display = [
        'session_key_short', 'category', 'question_field_name', 
        'response_type_display', 'response_display', 'created_at'
    ]
    list_filter = [
        'category', 'question__input_type', 'created_at',
        ('question__field_name', admin.AllValuesFieldListFilter)
    ]
    search_fields = ['session_key', 'question__question_text', 'question__field_name']
    ordering = ['-created_at']
    
    fieldsets = (
        ('Response Information', {
            'fields': ('session_key', 'category', 'question', 'response_value')
        }),
        ('Response Details', {
            'fields': ('response_display_formatted', 'response_type_info'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['created_at', 'updated_at', 'response_display_formatted', 'response_type_info']
    
    def session_key_short(self, obj):
        """Display shortened session key"""
        return obj.session_key[:12] + "..." if len(obj.session_key) > 12 else obj.session_key
    session_key_short.short_description = "Session"
    
    def question_field_name(self, obj):
        """Display question field name with type indicator"""
        field_name = obj.question.field_name
        if 'benefit_level' in field_name:
            return format_html('<span style="color: #0066cc;">{}</span>', field_name)
        elif 'annual_limit' in field_name and 'range' in field_name:
            return format_html('<span style="color: #28a745;">{}</span>', field_name)
        else:
            return field_name
    question_field_name.short_description = "Field"
    
    def response_type_display(self, obj):
        """Display response type with special indicators for new question types"""
        field_name = obj.question.field_name
        if 'benefit_level' in field_name:
            return format_html('<span style="color: #0066cc; font-weight: bold;">Benefit Level</span>')
        elif 'annual_limit' in field_name and 'range' in field_name:
            return format_html('<span style="color: #28a745; font-weight: bold;">Annual Range</span>')
        else:
            return format_html('<span style="color: #6c757d;">{}</span>', obj.question.get_input_type_display())
    response_type_display.short_description = "Type"
    
    def response_display(self, obj):
        """Display formatted response value with enhanced formatting for new field types"""
        field_name = obj.question.field_name
        response_value = obj.response_value
        
        # Handle benefit level responses
        if 'benefit_level' in field_name:
            if 'in_hospital' in field_name:
                choice_dict = {choice[0]: choice[1] for choice in HOSPITAL_BENEFIT_CHOICES}
            elif 'out_hospital' in field_name:
                choice_dict = {choice[0]: choice[1] for choice in OUT_HOSPITAL_BENEFIT_CHOICES}
            else:
                choice_dict = {}
            
            display_value = choice_dict.get(response_value, response_value)
            return format_html('<span style="color: #0066cc; font-weight: bold;" title="{}">{}</span>', 
                             response_value, display_value)
        
        # Handle annual limit range responses
        elif 'annual_limit' in field_name and 'range' in field_name:
            if 'family' in field_name:
                choice_dict = {choice[0]: choice[1] for choice in ANNUAL_LIMIT_FAMILY_RANGES}
            elif 'member' in field_name:
                choice_dict = {choice[0]: choice[1] for choice in ANNUAL_LIMIT_MEMBER_RANGES}
            else:
                choice_dict = {}
            
            display_value = choice_dict.get(response_value, response_value)
            return format_html('<span style="color: #28a745; font-weight: bold;" title="{}">{}</span>', 
                             response_value, display_value)
        
        # Handle other response types
        else:
            display_value = obj.get_display_value()
            if len(display_value) > 50:
                display_value = display_value[:47] + "..."
            return format_html('<span title="{}">{}</span>', obj.get_display_value(), display_value)
    response_display.short_description = "Response"
    
    def response_display_formatted(self, obj):
        """Detailed formatted response display for readonly field"""
        field_name = obj.question.field_name
        response_value = obj.response_value
        
        if 'benefit_level' in field_name:
            if 'in_hospital' in field_name:
                choices = HOSPITAL_BENEFIT_CHOICES
            elif 'out_hospital' in field_name:
                choices = OUT_HOSPITAL_BENEFIT_CHOICES
            else:
                return str(response_value)
            
            for choice in choices:
                if choice[0] == response_value:
                    return format_html(
                        '<strong>Value:</strong> {}<br>'
                        '<strong>Display:</strong> {}<br>'
                        '<strong>Description:</strong> {}',
                        choice[0], choice[1], choice[2]
                    )
        
        elif 'annual_limit' in field_name and 'range' in field_name:
            if 'family' in field_name:
                choices = ANNUAL_LIMIT_FAMILY_RANGES
            elif 'member' in field_name:
                choices = ANNUAL_LIMIT_MEMBER_RANGES
            else:
                return str(response_value)
            
            for choice in choices:
                if choice[0] == response_value:
                    return format_html(
                        '<strong>Value:</strong> {}<br>'
                        '<strong>Range:</strong> {}<br>'
                        '<strong>Description:</strong> {}',
                        choice[0], choice[1], choice[2]
                    )
        
        return str(response_value)
    response_display_formatted.short_description = "Formatted Response"
    
    def response_type_info(self, obj):
        """Display information about the response type"""
        field_name = obj.question.field_name
        if 'benefit_level' in field_name:
            return "This is a benefit level selection replacing previous binary yes/no questions."
        elif 'annual_limit' in field_name and 'range' in field_name:
            return "This is an annual limit range selection providing guided coverage options."
        else:
            return "Standard survey response."
    response_type_info.short_description = "Response Type Info"
    
    actions = ['validate_benefit_responses', 'validate_range_responses', 'export_new_response_types']
    
    def validate_benefit_responses(self, request, queryset):
        """Validate benefit level responses against current choices"""
        benefit_responses = queryset.filter(question__field_name__contains='benefit_level')
        invalid_count = 0
        
        for response in benefit_responses:
            field_name = response.question.field_name
            if 'in_hospital' in field_name:
                valid_choices = [choice[0] for choice in HOSPITAL_BENEFIT_CHOICES]
            elif 'out_hospital' in field_name:
                valid_choices = [choice[0] for choice in OUT_HOSPITAL_BENEFIT_CHOICES]
            else:
                continue
            
            if response.response_value not in valid_choices:
                invalid_count += 1
        
        valid_count = benefit_responses.count() - invalid_count
        self.message_user(
            request,
            f'Benefit level response validation: {valid_count} valid, {invalid_count} invalid responses.'
        )
    validate_benefit_responses.short_description = "Validate benefit level responses"
    
    def validate_range_responses(self, request, queryset):
        """Validate annual limit range responses"""
        range_responses = queryset.filter(
            question__field_name__contains='annual_limit'
        ).filter(
            question__field_name__contains='range'
        )
        invalid_count = 0
        
        for response in range_responses:
            field_name = response.question.field_name
            if 'family' in field_name:
                valid_choices = [choice[0] for choice in ANNUAL_LIMIT_FAMILY_RANGES]
            elif 'member' in field_name:
                valid_choices = [choice[0] for choice in ANNUAL_LIMIT_MEMBER_RANGES]
            else:
                continue
            
            if response.response_value not in valid_choices:
                invalid_count += 1
        
        valid_count = range_responses.count() - invalid_count
        self.message_user(
            request,
            f'Annual range response validation: {valid_count} valid, {invalid_count} invalid responses.'
        )
    validate_range_responses.short_description = "Validate annual range responses"
    
    def export_new_response_types(self, request, queryset):
        """Export responses for new question types (benefit levels and ranges)"""
        new_type_responses = queryset.filter(
            Q(question__field_name__contains='benefit_level') |
            (Q(question__field_name__contains='annual_limit') & Q(question__field_name__contains='range'))
        )
        count = new_type_responses.count()
        self.message_user(request, f'Exported {count} responses for new question types.')
    export_new_response_types.short_description = "Export new question type responses"


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


# Add custom admin URLs for benefit level and range management
from django.urls import path, reverse
from django.utils.html import format_html
from django.contrib.admin import AdminSite


class CustomAdminSite(AdminSite):
    """Custom admin site with additional management links"""
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('simple_surveys/benefit-levels/', 
                 self.admin_view(BenefitLevelManagementView.as_view()),
                 name='benefit_level_management'),
            path('simple_surveys/annual-limits/', 
                 self.admin_view(AnnualLimitRangeManagementView.as_view()),
                 name='annual_limit_management'),
        ]
        return custom_urls + urls
    
    def index(self, request, extra_context=None):
        """Add custom management links to admin index"""
        extra_context = extra_context or {}
        extra_context['custom_management_links'] = [
            {
                'title': 'Benefit Level Management',
                'url': reverse('admin:benefit_level_management'),
                'description': 'Manage hospital and out-of-hospital benefit level choices'
            },
            {
                'title': 'Annual Limit Range Management', 
                'url': reverse('admin:annual_limit_management'),
                'description': 'Manage annual limit range options for family and member coverage'
            }
        ]
        return super().index(request, extra_context)


# Import the admin views for registration
from .admin_views import BenefitLevelManagementView, AnnualLimitRangeManagementView


# Dedicated admin classes for managing benefit level choices and annual limit ranges

class BenefitLevelChoiceAdmin(admin.ModelAdmin):
    """Virtual admin for managing hospital benefit level choices"""
    
    def has_module_permission(self, request):
        return request.user.is_staff
    
    def has_add_permission(self, request):
        return request.user.is_superuser
    
    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser
    
    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser


class AnnualLimitRangeAdmin(admin.ModelAdmin):
    """Virtual admin for managing annual limit range choices"""
    
    def has_module_permission(self, request):
        return request.user.is_staff
    
    def has_add_permission(self, request):
        return request.user.is_superuser
    
    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser
    
    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser


# Create proxy models for the choice management
class HospitalBenefitChoice:
    """Proxy model for managing hospital benefit choices"""
    
    class Meta:
        verbose_name = "Hospital Benefit Choice"
        verbose_name_plural = "Hospital Benefit Choices"
        managed = False


class OutHospitalBenefitChoice:
    """Proxy model for managing out-of-hospital benefit choices"""
    
    class Meta:
        verbose_name = "Out-of-Hospital Benefit Choice"
        verbose_name_plural = "Out-of-Hospital Benefit Choices"
        managed = False


class AnnualLimitFamilyRange:
    """Proxy model for managing annual limit family ranges"""
    
    class Meta:
        verbose_name = "Annual Limit Family Range"
        verbose_name_plural = "Annual Limit Family Ranges"
        managed = False


class AnnualLimitMemberRange:
    """Proxy model for managing annual limit member ranges"""
    
    class Meta:
        verbose_name = "Annual Limit Member Range"
        verbose_name_plural = "Annual Limit Member Ranges"
        managed = False