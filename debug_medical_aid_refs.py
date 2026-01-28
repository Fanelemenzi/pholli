#!/usr/bin/env python
"""
Debug script to find medical aid references in analytics data.
"""

import os
import sys
import django
import json

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pholli.settings')
django.setup()

from simple_surveys.analytics import SimpleSurveyAnalytics


def find_medical_aid_refs():
    """Find medical aid references in analytics data"""
    analytics = SimpleSurveyAnalytics()
    
    try:
        # Test with empty data
        benefit_data = analytics.get_benefit_level_analytics('health', 7)
        range_data = analytics.get_range_selection_analytics('health', 7)
        completion_data = analytics.get_completion_analytics('health', 7)
        comprehensive_data = analytics.get_comprehensive_report('health', 7)
        
        # Check each data structure
        data_sets = {
            'benefit_data': benefit_data,
            'range_data': range_data,
            'completion_data': completion_data,
            'comprehensive_data': comprehensive_data
        }
        
        medical_aid_refs = ['medical_aid', 'currently_on_medical_aid', 'medical aid status']
        
        for data_name, data in data_sets.items():
            json_str = json.dumps(data, indent=2).lower()
            
            print(f"\n=== Checking {data_name} ===")
            
            for ref in medical_aid_refs:
                if ref in json_str:
                    print(f"❌ Found '{ref}' in {data_name}")
                    
                    # Find the specific location
                    lines = json_str.split('\n')
                    for i, line in enumerate(lines):
                        if ref in line:
                            print(f"   Line {i+1}: {line.strip()}")
                            # Show context
                            start = max(0, i-2)
                            end = min(len(lines), i+3)
                            print("   Context:")
                            for j in range(start, end):
                                marker = ">>> " if j == i else "    "
                                print(f"   {marker}{j+1}: {lines[j].strip()}")
                            print()
                else:
                    print(f"✅ No '{ref}' found in {data_name}")
        
        # Also check the raw data structure
        print(f"\n=== Raw Data Structure ===")
        print("Benefit data keys:", list(benefit_data.keys()))
        print("Range data keys:", list(range_data.keys()))
        print("Completion data keys:", list(completion_data.keys()))
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    find_medical_aid_refs()