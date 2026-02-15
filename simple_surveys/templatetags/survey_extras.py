"""
Template filters for survey results display.
Provides formatting functions for policy features and values.
"""

from django import template
from decimal import Decimal

register = template.Library()


@register.filter
def format_annual_limit_range(value):
    """Format annual limit range for display"""
    if not value:
        return "Not specified"
    
    range_mappings = {
        '10k-50k': 'R10,000 - R50,000',
        '50k-100k': 'R50,001 - R100,000',
        '100k-250k': 'R100,001 - R250,000',
        '250k-500k': 'R250,001 - R500,000',
        '500k-1m': 'R500,001 - R1,000,000',
        '1m-2m': 'R1,000,001 - R2,000,000',
        '2m-5m': 'R2,000,001 - R5,000,000',
        '5m-plus': 'R5,000,001+',
        'not_sure': 'Not sure / Need guidance'
    }
    
    return range_mappings.get(value, value.replace('_', ' ').title())


@register.filter
def format_benefit_level(value):
    """Format benefit level for display"""
    if not value:
        return "Not specified"
    
    level_mappings = {
        'no_cover': 'No Coverage',
        'basic': 'Basic Coverage',
        'moderate': 'Moderate Coverage',
        'extensive': 'Extensive Coverage',
        'comprehensive': 'Comprehensive Coverage',
        'basic_visits': 'Basic Clinic Visits',
        'routine_care': 'Routine Medical Care',
        'extended_care': 'Extended Medical Care',
        'comprehensive_care': 'Comprehensive Day-to-Day Care'
    }
    
    return level_mappings.get(value, value.replace('_', ' ').title())


@register.filter
def format_currency(value):
    """Format currency values"""
    if not value:
        return "R0"
    
    try:
        amount = float(value)
        if amount >= 1000000:
            return f"R{amount/1000000:.1f}M"
        elif amount >= 1000:
            return f"R{amount/1000:.0f}K"
        else:
            return f"R{amount:,.0f}"
    except (ValueError, TypeError):
        return str(value)


@register.filter
def format_percentage(value):
    """Format percentage values"""
    if not value:
        return "0%"
    
    try:
        return f"{float(value):.1f}%"
    except (ValueError, TypeError):
        return str(value)


@register.filter
def format_yes_no(value):
    """Format boolean values as Yes/No"""
    if value is None:
        return "Not specified"
    
    return "Yes" if value else "No"


@register.filter
def format_cover_amount_range(value):
    """Format funeral cover amount range for display"""
    if not value:
        return "Not specified"
    
    range_mappings = {
        '10k-25k': 'R10,000 - R25,000',
        '25k-50k': 'R25,001 - R50,000',
        '50k-75k': 'R50,001 - R75,000',
        '75k-100k': 'R75,001 - R100,000',
        '100k-150k': 'R100,001 - R150,000',
        '150k-200k': 'R150,001 - R200,000',
        '200k-plus': 'R200,001+'
    }
    
    return range_mappings.get(value, value.replace('_', ' ').title())


@register.filter
def format_service_type(value):
    """Format funeral service type for display"""
    if not value:
        return "Not specified"
    
    service_mappings = {
        'basic': 'Basic Service - Essential arrangements only',
        'standard': 'Standard Service - Comprehensive package',
        'premium': 'Premium Service - Full luxury service',
        'cash_only': 'Cash Payout Only - No managed services'
    }
    
    return service_mappings.get(value, value.replace('_', ' ').title())


@register.filter
def format_waiting_period(value):
    """Format waiting period for display"""
    if not value:
        return "Not specified"
    
    period_mappings = {
        'none': 'No Waiting Period',
        '1_month': '1 Month',
        '3_months': '3 Months',
        '6_months': '6 Months',
        '12_months': '12 Months'
    }
    
    return period_mappings.get(value, value.replace('_', ' ').title())


@register.filter
def format_family_coverage(value):
    """Format family coverage type for display"""
    if not value:
        return "Not specified"
    
    coverage_mappings = {
        'individual': 'Individual Only',
        'spouse': 'Main Member + Spouse',
        'nuclear_family': 'Nuclear Family (Parents + Children)',
        'extended_family': 'Extended Family (Up to 15 members)'
    }
    
    return coverage_mappings.get(value, value.replace('_', ' ').title())


@register.simple_tag
def get_match_score_class(score):
    """Get CSS class for match score styling"""
    try:
        score_value = float(score)
        if score_value >= 90:
            return 'text-success fw-bold'
        elif score_value >= 75:
            return 'text-primary fw-bold'
        elif score_value >= 60:
            return 'text-info'
        elif score_value >= 40:
            return 'text-warning'
        else:
            return 'text-muted'
    except (ValueError, TypeError):
        return 'text-muted'


@register.simple_tag
def get_match_score_badge(score):
    """Get badge class for match score"""
    try:
        score_value = float(score)
        if score_value >= 90:
            return 'badge bg-success'
        elif score_value >= 75:
            return 'badge bg-primary'
        elif score_value >= 60:
            return 'badge bg-info'
        elif score_value >= 40:
            return 'badge bg-warning'
        else:
            return 'badge bg-secondary'
    except (ValueError, TypeError):
        return 'badge bg-secondary'


@register.filter
def multiply(value, arg):
    """Multiply filter for calculations"""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0


@register.filter
def divide(value, arg):
    """Divide filter for calculations"""
    try:
        return float(value) / float(arg)
    except (ValueError, TypeError, ZeroDivisionError):
        return 0


@register.filter
def format_premium_range(min_premium, max_premium):
    """Format premium range for display"""
    try:
        min_val = float(min_premium)
        max_val = float(max_premium)
        
        if min_val == max_val:
            return f"R{min_val:,.0f}"
        else:
            return f"R{min_val:,.0f} - R{max_val:,.0f}"
    except (ValueError, TypeError):
        return "Premium not available"


@register.inclusion_tag('surveys/partials/policy_feature_item.html')
def policy_feature_item(label, value, feature_type='text'):
    """Render a policy feature item with proper formatting"""
    formatted_value = value
    
    if feature_type == 'currency':
        formatted_value = format_currency(value)
    elif feature_type == 'percentage':
        formatted_value = format_percentage(value)
    elif feature_type == 'yes_no':
        formatted_value = format_yes_no(value)
    elif feature_type == 'annual_limit_range':
        formatted_value = format_annual_limit_range(value)
    elif feature_type == 'benefit_level':
        formatted_value = format_benefit_level(value)
    
    return {
        'label': label,
        'value': formatted_value,
        'raw_value': value
    }


@register.filter
def get_item(dictionary, key):
    """Get item from dictionary by key"""
    if not dictionary or not key:
        return None
    return dictionary.get(key)


@register.filter
def default_if_none(value, default):
    """Return default if value is None"""
    return default if value is None else value