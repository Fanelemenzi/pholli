#!/usr/bin/env python
"""
Script to create basic PolicyCategory records for the application.
"""
import os
import sys
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pholli.settings')
django.setup()

from policies.models import PolicyCategory

def create_categories():
    """Create basic policy categories."""
    categories = [
        {
            'name': 'Health Insurance',
            'slug': 'health',
            'description': 'Medical aid and health insurance policies',
            'icon': 'bi-heart-pulse',
            'display_order': 1
        },
        {
            'name': 'Funeral Cover',
            'slug': 'funeral',
            'description': 'Funeral insurance and burial cover policies',
            'icon': 'bi-people',
            'display_order': 2
        },
        {
            'name': 'Life Insurance',
            'slug': 'life',
            'description': 'Life insurance and investment policies',
            'icon': 'bi-shield-check',
            'display_order': 3
        }
    ]
    
    created_count = 0
    for category_data in categories:
        category, created = PolicyCategory.objects.get_or_create(
            slug=category_data['slug'],
            defaults=category_data
        )
        if created:
            print(f"✅ Created category: {category.name}")
            created_count += 1
        else:
            print(f"ℹ️  Category already exists: {category.name}")
    
    print(f"\n📊 Summary: {created_count} new categories created")
    print(f"📊 Total categories: {PolicyCategory.objects.count()}")
    
    # List all categories
    print("\n📋 All categories:")
    for cat in PolicyCategory.objects.all():
        print(f"  - {cat.name} (slug: {cat.slug})")

if __name__ == '__main__':
    create_categories()