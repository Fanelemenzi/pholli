from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse, path
from django.shortcuts import redirect
from .models import (
    SurveyTemplate, SurveyQuestion, TemplateQuestion, 
    SurveyResponse, QuestionDependency, SurveyAnalytics,
    UserSurveyProfile, SavedSurveyProfile, ABTestVariant, ABTestParticipant
)
# ABTestVariant and ABTestParticipant are imported from models.py


class TemplateQuestionInline(admin.TabularInline):
    """Inline admin for managing questions within a template."""
    model = TemplateQuestion
    extra = 0
    fields = ('question', 'display_order', 'is_required_override')
    ordering = ('display_order',)


@admin.register(SurveyTemplate)
class SurveyTemplateAdmin(admin.ModelAdmin):
    """Admin interface for Survey Templates."""
    list_display = ('name', 'category', 'version', 'is_active', 'created_at')
    list_filter = ('category', 'is_active', 'created_at')
    search_fields = ('name', 'description')
    readonly_fields = ('created_at', 'updated_at')
    inlines = [TemplateQuestionInline]
    
    fieldsets = (
        (None, {
            'fields': ('category', 'name', 'description', 'version', 'is_active')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


class QuestionDependencyInline(admin.TabularInline):
    """Inline admin for managing question dependencies."""
    model = QuestionDependency
    fk_name = 'parent_question'
    extra = 0
    fields = ('child_question', 'condition_operator', 'condition_value', 'is_active')


@admin.register(SurveyQuestion)
class SurveyQuestionAdmin(admin.ModelAdmin):
    """Admin interface for Survey Questions."""
    list_display = ('question_text_short', 'category', 'section', 'question_type', 'is_required', 'is_active', 'display_order')
    list_filter = ('category', 'section', 'question_type', 'is_required', 'is_active')
    search_fields = ('question_text', 'field_name', 'section')
    readonly_fields = ('created_at', 'updated_at')
    inlines = [QuestionDependencyInline]
    
    fieldsets = (
        (None, {
            'fields': ('category', 'section', 'question_text', 'question_type', 'field_name')
        }),
        ('Configuration', {
            'fields': ('choices', 'validation_rules', 'weight_impact', 'help_text')
        }),
        ('Display Options', {
            'fields': ('is_required', 'display_order', 'is_active')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def question_text_short(self, obj):
        """Return shortened question text for list display."""
        return obj.question_text[:50] + "..." if len(obj.question_text) > 50 else obj.question_text
    question_text_short.short_description = 'Question Text'


@admin.register(SurveyResponse)
class SurveyResponseAdmin(admin.ModelAdmin):
    """Admin interface for Survey Responses."""
    list_display = ('session', 'question_short', 'response_value_short', 'confidence_level', 'created_at')
    list_filter = ('question__category', 'question__section', 'confidence_level', 'created_at')
    search_fields = ('session__session_key', 'question__question_text')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        (None, {
            'fields': ('session', 'question', 'response_value', 'confidence_level')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def question_short(self, obj):
        """Return shortened question text for list display."""
        return obj.question.question_text[:30] + "..." if len(obj.question.question_text) > 30 else obj.question.question_text
    question_short.short_description = 'Question'
    
    def response_value_short(self, obj):
        """Return shortened response value for list display."""
        response_str = str(obj.response_value)
        return response_str[:30] + "..." if len(response_str) > 30 else response_str
    response_value_short.short_description = 'Response'


@admin.register(QuestionDependency)
class QuestionDependencyAdmin(admin.ModelAdmin):
    """Admin interface for Question Dependencies."""
    list_display = ('parent_question_short', 'child_question_short', 'condition_operator', 'condition_value', 'is_active')
    list_filter = ('condition_operator', 'is_active', 'parent_question__category')
    search_fields = ('parent_question__question_text', 'child_question__question_text')
    
    fieldsets = (
        (None, {
            'fields': ('parent_question', 'child_question', 'condition_operator', 'condition_value', 'is_active')
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    def parent_question_short(self, obj):
        """Return shortened parent question text for list display."""
        return obj.parent_question.question_text[:30] + "..." if len(obj.parent_question.question_text) > 30 else obj.parent_question.question_text
    parent_question_short.short_description = 'Parent Question'
    
    def child_question_short(self, obj):
        """Return shortened child question text for list display."""
        return obj.child_question.question_text[:30] + "..." if len(obj.child_question.question_text) > 30 else obj.child_question.question_text
    child_question_short.short_description = 'Child Question'


@admin.register(SurveyAnalytics)
class SurveyAnalyticsAdmin(admin.ModelAdmin):
    """Admin interface for Survey Analytics."""
    list_display = ('question_short', 'total_responses', 'completion_rate', 'skip_rate', 'last_updated')
    list_filter = ('question__category', 'question__section', 'last_updated')
    search_fields = ('question__question_text', 'question__field_name')
    readonly_fields = ('last_updated',)
    
    fieldsets = (
        (None, {
            'fields': ('question',)
        }),
        ('Statistics', {
            'fields': ('total_responses', 'completion_rate', 'skip_rate', 'average_response_time')
        }),
        ('Response Data', {
            'fields': ('most_common_response', 'response_distribution')
        }),
        ('Timestamps', {
            'fields': ('last_updated',),
            'classes': ('collapse',)
        }),
    )
    
    def question_short(self, obj):
        """Return shortened question text for list display."""
        return obj.question.question_text[:40] + "..." if len(obj.question.question_text) > 40 else obj.question.question_text
    question_short.short_description = 'Question'
    
    def has_add_permission(self, request):
        """Prevent manual creation of analytics records."""
        return False


@admin.register(TemplateQuestion)
class TemplateQuestionAdmin(admin.ModelAdmin):
    """Admin interface for Template Questions (through model)."""
    list_display = ('template', 'question_short', 'display_order', 'is_required')
    list_filter = ('template__category', 'template', 'is_required_override')
    search_fields = ('template__name', 'question__question_text')
    
    def question_short(self, obj):
        """Return shortened question text for list display."""
        return obj.question.question_text[:40] + "..." if len(obj.question.question_text) > 40 else obj.question.question_text
    question_short.short_description = 'Question'

@admin.register(UserSurveyProfile)
class UserSurveyProfileAdmin(admin.ModelAdmin):
    """Admin interface for User Survey Profiles."""
    list_display = ('user', 'total_surveys_completed', 'last_survey_date', 'auto_save_responses', 'created_at')
    list_filter = ('auto_save_responses', 'prefill_from_history', 'email_survey_reminders', 'created_at')
    search_fields = ('user__username', 'user__email')
    readonly_fields = ('total_surveys_completed', 'last_survey_date', 'created_at', 'updated_at')
    
    fieldsets = (
        (None, {
            'fields': ('user',)
        }),
        ('Preferences', {
            'fields': ('auto_save_responses', 'prefill_from_history', 'email_survey_reminders', 'data_retention_days')
        }),
        ('Statistics', {
            'fields': ('total_surveys_completed', 'last_survey_date', 'preferred_categories'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(SavedSurveyProfile)
class SavedSurveyProfileAdmin(admin.ModelAdmin):
    """Admin interface for Saved Survey Profiles."""
    list_display = ('name', 'user', 'category', 'is_default', 'usage_count', 'last_used', 'created_at')
    list_filter = ('category', 'is_default', 'created_at', 'last_used')
    search_fields = ('name', 'user__username', 'description')
    readonly_fields = ('usage_count', 'last_used', 'created_at', 'updated_at')
    
    fieldsets = (
        (None, {
            'fields': ('user', 'name', 'category', 'description', 'is_default')
        }),
        ('Survey Data', {
            'fields': ('survey_responses', 'criteria_weights', 'user_profile_data'),
            'classes': ('collapse',)
        }),
        ('Usage Statistics', {
            'fields': ('usage_count', 'last_used'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(ABTestVariant)
class ABTestVariantAdmin(admin.ModelAdmin):
    """Admin interface for A/B Test Variants."""
    list_display = ('name', 'status', 'traffic_percentage', 'participants_count', 'primary_metric', 'winning_variant', 'start_date')
    list_filter = ('status', 'primary_metric', 'start_date', 'created_at')
    search_fields = ('name', 'description')
    readonly_fields = ('participants_count', 'results_data', 'statistical_significance', 'winning_variant', 'created_at', 'updated_at')
    
    fieldsets = (
        (None, {
            'fields': ('name', 'description', 'status')
        }),
        ('Test Configuration', {
            'fields': ('traffic_percentage', 'start_date', 'end_date', 'primary_metric', 'minimum_sample_size')
        }),
        ('Variants', {
            'fields': ('variants_config',)
        }),
        ('Results', {
            'fields': ('participants_count', 'results_data', 'statistical_significance', 'winning_variant'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['start_test', 'stop_test', 'calculate_results']
    
    def start_test(self, request, queryset):
        """Start selected A/B tests."""
        from .ab_testing import ABTestManager
        manager = ABTestManager()
        
        updated = 0
        for test in queryset.filter(status=ABTestVariant.Status.DRAFT):
            if manager.start_test(test.id):
                updated += 1
        
        self.message_user(request, f"Started {updated} A/B tests.")
    start_test.short_description = "Start selected A/B tests"
    
    def stop_test(self, request, queryset):
        """Stop selected A/B tests."""
        from .ab_testing import ABTestManager
        manager = ABTestManager()
        
        updated = 0
        for test in queryset.filter(status=ABTestVariant.Status.ACTIVE):
            if manager.stop_test(test.id):
                updated += 1
        
        self.message_user(request, f"Stopped {updated} A/B tests.")
    stop_test.short_description = "Stop selected A/B tests"
    
    def calculate_results(self, request, queryset):
        """Calculate results for selected A/B tests."""
        from .ab_testing import ABTestManager
        manager = ABTestManager()
        
        updated = 0
        for test in queryset:
            manager.calculate_test_results(test.id)
            updated += 1
        
        self.message_user(request, f"Calculated results for {updated} A/B tests.")
    calculate_results.short_description = "Calculate results for selected tests"


@admin.register(ABTestParticipant)
class ABTestParticipantAdmin(admin.ModelAdmin):
    """Admin interface for A/B Test Participants."""
    list_display = ('test', 'session', 'variant', 'completion_rate', 'conversion_achieved', 'started_at')
    list_filter = ('test', 'variant', 'conversion_achieved', 'started_at')
    search_fields = ('test__name', 'session__session_key')
    readonly_fields = ('started_at', 'completed_at')
    
    fieldsets = (
        (None, {
            'fields': ('test', 'session', 'variant')
        }),
        ('Metrics', {
            'fields': ('completion_rate', 'response_time_seconds', 'responses_count', 'conversion_achieved')
        }),
        ('Timestamps', {
            'fields': ('started_at', 'completed_at'),
            'classes': ('collapse',)
        }),
    )