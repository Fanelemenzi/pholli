from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from .models import (
    ComparisonSession,
    ComparisonResult,
    ComparisonCriteria,
    UserPreferenceProfile
)


class ComparisonResultInline(admin.TabularInline):
    """Inline admin for comparison results."""
    model = ComparisonResult
    extra = 0
    fields = ['policy', 'overall_score', 'rank', 'created_at']
    readonly_fields = ['policy', 'overall_score', 'rank', 'created_at']
    can_delete = False
    
    def has_add_permission(self, request, obj=None):
        return False


@admin.register(ComparisonSession)
class ComparisonSessionAdmin(admin.ModelAdmin):
    """Admin interface for Comparison Sessions."""
    
    list_display = [
        'id',
        'user_display',
        'category',
        'policies_count',
        'best_match_display',
        'status_badge',
        'created_at'
    ]
    
    list_filter = [
        'status',
        'category',
        ('created_at', admin.DateFieldListFilter),
        ('expires_at', admin.DateFieldListFilter)
    ]
    
    search_fields = [
        'session_key',
        'user__username',
        'user__email'
    ]
    
    readonly_fields = [
        'session_key',
        'user',
        'category',
        'created_at',
        'updated_at',
        'criteria_display',
        'match_scores_display'
    ]
    
    fieldsets = (
        (_('Session Information'), {
            'fields': (
                'user',
                'session_key',
                'category',
                'status'
            )
        }),
        (_('Comparison Details'), {
            'fields': (
                'policies',
                'best_match_policy',
                'criteria_display',
                'match_scores_display'
            )
        }),
        (_('Metadata'), {
            'fields': (
                'created_at',
                'updated_at',
                'expires_at'
            ),
            'classes': ('collapse',)
        })
    )
    
    inlines = [ComparisonResultInline]
    
    list_select_related = ['user', 'category', 'best_match_policy']
    list_per_page = 50
    date_hierarchy = 'created_at'
    
    def user_display(self, obj):
        """Display user or anonymous."""
        if obj.user:
            return format_html(
                '<a href="/admin/auth/user/{}/change/">{}</a>',
                obj.user.id,
                obj.user.username
            )
        return format_html('<span style="color: #6C757D;">Anonymous</span>')
    user_display.short_description = _('User')
    
    def policies_count(self, obj):
        """Display count of policies in comparison."""
        count = obj.policies.count()
        return format_html(
            '<span style="background: #E3F2FD; padding: 4px 10px; '
            'border-radius: 4px; font-weight: bold; color: #1976D2;">{} policies</span>',
            count
        )
    policies_count.short_description = _('Policies')
    
    def best_match_display(self, obj):
        """Display best match policy."""
        if obj.best_match_policy:
            return format_html(
                '<strong>{}</strong><br>'
                '<span style="font-size: 11px; color: #6C757D;">{}</span>',
                obj.best_match_policy.name,
                obj.best_match_policy.organization.name
            )
        return '-'
    best_match_display.short_description = _('Best Match')
    
    def status_badge(self, obj):
        """Display status with badge."""
        colors = {
            'ACTIVE': '#28A745',
            'COMPLETED': '#007BFF',
            'EXPIRED': '#6C757D'
        }
        color = colors.get(obj.status, '#6C757D')
        return format_html(
            '<span style="background: {}; color: white; padding: 4px 10px; '
            'border-radius: 4px; font-weight: bold; font-size: 11px;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = _('Status')
    status_badge.admin_order_field = 'status'
    
    def criteria_display(self, obj):
        """Display criteria in readable format."""
        if not obj.criteria:
            return 'No criteria specified'
        
        html = '<div style="background: #F8F9FA; padding: 10px; border-radius: 5px;">'
        for key, value in obj.criteria.items():
            if key != 'weights':
                html += f'<div><strong>{key}:</strong> {value}</div>'
        html += '</div>'
        return format_html(html)
    criteria_display.short_description = _('User Criteria')
    
    def match_scores_display(self, obj):
        """Display match scores for all policies."""
        if not obj.match_scores:
            return 'No scores calculated'
        
        html = '<div style="background: #F8F9FA; padding: 10px; border-radius: 5px;">'
        sorted_scores = sorted(
            obj.match_scores.items(),
            key=lambda x: x[1],
            reverse=True
        )
        for policy_id, score in sorted_scores:
            html += f'<div>Policy #{policy_id}: <strong>{score:.1f}/100</strong></div>'
        html += '</div>'
        return format_html(html)
    match_scores_display.short_description = _('Match Scores')


@admin.register(ComparisonResult)
class ComparisonResultAdmin(admin.ModelAdmin):
    """Admin interface for Comparison Results."""
    
    list_display = [
        'policy',
        'session',
        'overall_score_display',
        'rank_display',
        'created_at'
    ]
    
    list_filter = [
        'rank',
        ('created_at', admin.DateFieldListFilter),
        'policy__category'
    ]
    
    search_fields = [
        'policy__name',
        'session__session_key'
    ]
    
    readonly_fields = [
        'session',
        'policy',
        'overall_score',
        'criteria_scores',
        'rank',
        'pros',
        'cons',
        'recommendation_reason',
        'created_at',
        'pros_display',
        'cons_display',
        'scores_breakdown'
    ]
    
    fieldsets = (
        (_('Result Information'), {
            'fields': (
                'session',
                'policy',
                'rank',
                'overall_score'
            )
        }),
        (_('Score Breakdown'), {
            'fields': ('scores_breakdown',)
        }),
        (_('Analysis'), {
            'fields': (
                'pros_display',
                'cons_display',
                'recommendation_reason'
            )
        }),
        (_('Metadata'), {
            'fields': ('created_at',),
            'classes': ('collapse',)
        })
    )
    
    list_select_related = ['policy', 'session']
    list_per_page = 50
    
    def overall_score_display(self, obj):
        """Display score with color coding."""
        score = float(obj.overall_score)
        if score >= 80:
            color = '#28A745'
        elif score >= 60:
            color = '#FFC107'
        else:
            color = '#DC3545'
        
        return format_html(
            '<div style="text-align: center;">'
            '<span style="font-size: 20px; font-weight: bold; color: {};">{:.1f}</span>'
            '<div style="font-size: 11px; color: #6C757D;">/ 100</div>'
            '</div>',
            color,
            score
        )
    overall_score_display.short_description = _('Score')
    overall_score_display.admin_order_field = 'overall_score'
    
    def rank_display(self, obj):
        """Display rank with medal icons."""
        if obj.rank == 1:
            return format_html('<span style="font-size: 24px;">🥇</span>')
        elif obj.rank == 2:
            return format_html('<span style="font-size: 24px;">🥈</span>')
        elif obj.rank == 3:
            return format_html('<span style="font-size: 24px;">🥉</span>')
        return format_html('<span style="font-weight: bold;">#{}</span>', obj.rank)
    rank_display.short_description = _('Rank')
    rank_display.admin_order_field = 'rank'
    
    def pros_display(self, obj):
        """Display pros in formatted list."""
        if not obj.pros:
            return 'No pros recorded'
        
        html = '<ul style="background: #D4EDDA; padding: 15px; border-radius: 5px; color: #155724;">'
        for pro in obj.pros:
            html += f'<li style="margin: 5px 0;">✓ {pro}</li>'
        html += '</ul>'
        return format_html(html)
    pros_display.short_description = _('Advantages')
    
    def cons_display(self, obj):
        """Display cons in formatted list."""
        if not obj.cons:
            return 'No cons recorded'
        
        html = '<ul style="background: #F8D7DA; padding: 15px; border-radius: 5px; color: #721C24;">'
        for con in obj.cons:
            html += f'<li style="margin: 5px 0;">✗ {con}</li>'
        html += '</ul>'
        return format_html(html)
    cons_display.short_description = _('Disadvantages')
    
    def scores_breakdown(self, obj):
        """Display detailed score breakdown."""
        if not obj.criteria_scores:
            return 'No criteria scores available'
        
        html = '<table style="width: 100%; background: #F8F9FA; border-radius: 5px;">'
        html += '<tr style="background: #E9ECEF;"><th>Criteria</th><th>Score</th><th>Weight</th><th>Weighted Score</th></tr>'
        
        for field_name, scores in obj.criteria_scores.items():
            score = scores.get('score', 0)
            weight = scores.get('weight', 0)
            weighted = scores.get('weighted_score', 0)
            
            # Color code the score
            if score >= 80:
                score_color = '#28A745'
            elif score >= 60:
                score_color = '#FFC107'
            else:
                score_color = '#DC3545'
            
            html += f'''
            <tr>
                <td style="padding: 8px;"><strong>{field_name.replace('_', ' ').title()}</strong></td>
                <td style="padding: 8px; text-align: center; color: {score_color}; font-weight: bold;">{score:.1f}</td>
                <td style="padding: 8px; text-align: center;">{weight}</td>
                <td style="padding: 8px; text-align: center; font-weight: bold;">{weighted:.1f}</td>
            </tr>
            '''
        
        html += '</table>'
        return format_html(html)
    scores_breakdown.short_description = _('Criteria Scores Breakdown')


@admin.register(ComparisonCriteria)
class ComparisonCriteriaAdmin(admin.ModelAdmin):
    """Admin interface for Comparison Criteria."""
    
    list_display = [
        'name',
        'category',
        'field_name',
        'weight',
        'comparison_type',
        'required_badge',
        'active_status',
        'display_order'
    ]
    
    list_filter = [
        'category',
        'comparison_type',
        'is_required',
        'is_active'
    ]
    
    search_fields = ['name', 'description', 'field_name']
    
    fieldsets = (
        (_('Criteria Information'), {
            'fields': (
                'category',
                'name',
                'description',
                'field_name'
            )
        }),
        (_('Comparison Settings'), {
            'fields': (
                'comparison_type',
                'weight',
                'is_required',
                'is_active'
            )
        }),
        (_('Display'), {
            'fields': ('display_order',)
        })
    )
    
    list_per_page = 50
    ordering = ['category', 'display_order']
    
    def required_badge(self, obj):
        """Display required status."""
        if obj.is_required:
            return format_html(
                '<span style="background: #DC3545; color: white; padding: 3px 10px; '
                'border-radius: 3px; font-weight: bold;">REQUIRED</span>'
            )
        return format_html('<span style="color: #6C757D;">Optional</span>')
    required_badge.short_description = _('Required')
    required_badge.admin_order_field = 'is_required'
    
    def active_status(self, obj):
        """Display active status."""
        if obj.is_active:
            return format_html('<span style="color: green; font-size: 16px;">✓</span>')
        return format_html('<span style="color: red; font-size: 16px;">✗</span>')
    active_status.short_description = _('Active')
    active_status.admin_order_field = 'is_active'


@admin.register(UserPreferenceProfile)
class UserPreferenceProfileAdmin(admin.ModelAdmin):
    """Admin interface for User Preference Profiles."""
    
    list_display = [
        'name',
        'user',
        'category',
        'default_badge',
        'created_at'
    ]
    
    list_filter = [
        'category',
        'is_default',
        ('created_at', admin.DateFieldListFilter)
    ]
    
    search_fields = [
        'name',
        'user__username',
        'user__email'
    ]
    
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        (_('Profile Information'), {
            'fields': (
                'user',
                'name',
                'category',
                'is_default'
            )
        }),
        (_('Preferences'), {
            'fields': ('preferences',)
        }),
        (_('Metadata'), {
            'fields': (
                'created_at',
                'updated_at'
            ),
            'classes': ('collapse',)
        })
    )
    
    list_select_related = ['user', 'category']
    list_per_page = 50
    
    def default_badge(self, obj):
        """Display default status."""
        if obj.is_default:
            return format_html(
                '<span style="color: #FFC107; font-size: 18px;" title="Default Profile">★</span>'
            )
        return format_html('<span style="color: #DEE2E6; font-size: 18px;">☆</span>')
    default_badge.short_description = _('Default')
    default_badge.admin_order_field = 'is_default'