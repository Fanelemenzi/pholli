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