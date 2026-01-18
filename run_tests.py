#!/usr/bin/env python
"""
Simple test runner for the Eswatini policy system comprehensive tests.
This script can be run directly to execute all the new comprehensive tests.
"""

import os
import sys
import django
from django.core.management import execute_from_command_line

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pholli.settings')

def main():
    """Run the comprehensive tests."""
    try:
        django.setup()
    except Exception as e:
        print(f"Error setting up Django: {e}")
        sys.exit(1)
    
    # Test modules to run
    test_modules = [
        'tests.test_comprehensive_models',
        'tests.test_feature_matching_integration', 
        'tests.test_end_to_end_survey_flow'
    ]
    
    print("Running Comprehensive Tests for Eswatini Policy System")
    print("=" * 60)
    
    all_passed = True
    
    for module in test_modules:
        print(f"\nRunning tests in {module}...")
        try:
            # Use Django's test command
            result = execute_from_command_line([
                'manage.py', 'test', module, '--verbosity=2', '--keepdb'
            ])
            if result != 0:
                all_passed = False
                print(f"❌ Tests in {module} failed")
            else:
                print(f"✅ Tests in {module} passed")
        except SystemExit as e:
            if e.code != 0:
                all_passed = False
                print(f"❌ Tests in {module} failed with exit code {e.code}")
            else:
                print(f"✅ Tests in {module} passed")
        except Exception as e:
            all_passed = False
            print(f"❌ Error running tests in {module}: {e}")
    
    print("\n" + "=" * 60)
    if all_passed:
        print("🎉 All comprehensive tests passed!")
        print("The new feature-based policy system is working correctly.")
    else:
        print("⚠️  Some tests failed. Please review the output above.")
    print("=" * 60)
    
    return 0 if all_passed else 1

if __name__ == '__main__':
    sys.exit(main())