"""
Template tags and filters for simple surveys.
"""
from django import template

register = template.Library()


@register.filter
def get_item(dictionary, key):
    """
    Get an item from a dictionary using a key.
    Usage: {{ dict|get_item:key }}
    """
    if isinstance(dictionary, dict):
        return dictionary.get(key)
    return None


@register.filter
def is_in_list(value, list_value):
    """
    Check if a value is in a list.
    Usage: {{ value|is_in_list:list }}
    """
    if isinstance(list_value, list):
        return value in list_value
    return False


@register.filter
def default_if_none(value, default):
    """
    Return default if value is None, otherwise return value.
    Usage: {{ value|default_if_none:"default" }}
    """
    return default if value is None else value


@register.filter
def format_benefit_level(value):
    """
    Format benefit level codes into human-readable text.
    Usage: {{ benefit_level|format_benefit_level }}
    """
    if not value:
        return "Not specified"
    
    # Mapping for benefit levels
    benefit_mappings = {
        'no_cover': 'No Coverage',
        'basic': 'Basic Coverage',
        'basic_visits': 'Basic Visits Only',
        'moderate': 'Moderate Coverage',
        'routine_care': 'Routine Care',
        'extensive': 'Extensive Coverage',
        'extended_care': 'Extended Care',
        'comprehensive': 'Comprehensive Coverage',
        'comprehensive_care': 'Comprehensive Care',
    }
    
    return benefit_mappings.get(value, value.replace('_', ' ').title())


@register.filter
def format_annual_limit_range(value):
    """
    Format annual limit range codes into human-readable text.
    Usage: {{ range_code|format_annual_limit_range }}
    """
    if not value:
        return "Not specified"
    
    # Mapping for annual limit ranges
    range_mappings = {
        '10k-25k': 'R10,000 - R25,000',
        '10k-50k': 'R10,000 - R50,000',
        '25k-50k': 'R25,000 - R50,000',
        '50k-100k': 'R50,000 - R100,000',
        '100k-200k': 'R100,000 - R200,000',
        '100k-250k': 'R100,000 - R250,000',
        '200k-500k': 'R200,000 - R500,000',
        '250k-500k': 'R250,000 - R500,000',
        '500k-1m': 'R500,000 - R1,000,000',
        '1m-2m': 'R1,000,000 - R2,000,000',
        '2m-5m': 'R2,000,000 - R5,000,000',
        '2m-plus': 'R2,000,000+',
        '5m-plus': 'R5,000,000+',
        'not_sure': 'Guidance Needed',
    }
    
    return range_mappings.get(value, value.replace('_', ' ').title())