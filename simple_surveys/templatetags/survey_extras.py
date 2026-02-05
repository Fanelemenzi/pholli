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