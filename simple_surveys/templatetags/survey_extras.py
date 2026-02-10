from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """
    Template filter to get an item from a dictionary by key.
    Usage: {{ dict|get_item:key }}
    """
    if dictionary is None:
        return None
    return dictionary.get(key)

@register.filter
def in_list(value, list_string):
    """
    Template filter to check if a value is in a comma-separated list.
    Usage: {{ value|in_list:list_string }}
    """
    if not list_string:
        return False
    if isinstance(list_string, list):
        return value in list_string
    return str(value) in str(list_string).split(',')

@register.filter
def format_annual_limit_range(range_value):
    """
    Template filter to format annual limit range values into display text.
    Usage: {{ range_value|format_annual_limit_range }}
    """
    if not range_value:
        return ''
    
    # Import the range choices
    from simple_surveys.models import ANNUAL_LIMIT_FAMILY_RANGES, ANNUAL_LIMIT_MEMBER_RANGES
    
    # Check family ranges first
    for choice in ANNUAL_LIMIT_FAMILY_RANGES:
        if choice[0] == range_value:
            return choice[1]  # Return the display text
    
    # Check member ranges
    for choice in ANNUAL_LIMIT_MEMBER_RANGES:
        if choice[0] == range_value:
            return choice[1]  # Return the display text
    
    # If not found, return the original value
    return range_value

@register.filter
def format_benefit_level(level_value):
    """
    Template filter to format benefit level values into display text.
    Usage: {{ level_value|format_benefit_level }}
    """
    if not level_value:
        return ''
    
    # Import the benefit level choices
    from simple_surveys.models import HOSPITAL_BENEFIT_CHOICES, OUT_HOSPITAL_BENEFIT_CHOICES
    
    # Check hospital benefit choices first
    for choice in HOSPITAL_BENEFIT_CHOICES:
        if choice[0] == level_value:
            return choice[1]  # Return the display text
    
    # Check out-of-hospital benefit choices
    for choice in OUT_HOSPITAL_BENEFIT_CHOICES:
        if choice[0] == level_value:
            return choice[1]  # Return the display text
    
    # If not found, return the original value
    return level_value