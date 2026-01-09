#!/usr/bin/env python
"""
Script to check survey templates and their active status.
"""
import os
import sys
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pholli.settings')
django.setup()

from surveys.models import SurveyTemplate, TemplateQuestion
from policies.models import PolicyCategory

def check_templates():
    """Check survey templates and their configuration."""
    print("🔍 Checking survey templates...")
    
    categories = PolicyCategory.objects.all()
    
    for category in categories:
        print(f"\n📋 Category: {category.name} (slug: {category.slug})")
        
        # Get all templates for this category
        templates = SurveyTemplate.objects.filter(category=category)
        print(f"  Total templates: {templates.count()}")
        
        # Check active templates
        active_templates = templates.filter(is_active=True)
        print(f"  Active templates: {active_templates.count()}")
        
        if active_templates.count() == 0:
            print(f"  ❌ No active templates for {category.slug}!")
        elif active_templates.count() > 1:
            print(f"  ⚠️  Multiple active templates for {category.slug}!")
        
        # Check template questions
        for template in active_templates:
            template_questions = TemplateQuestion.objects.filter(template=template)
            print(f"    Template '{template.name}': {template_questions.count()} questions")
            
            if template_questions.count() == 0:
                print(f"    ❌ Template '{template.name}' has no questions!")

if __name__ == '__main__':
    check_templates()