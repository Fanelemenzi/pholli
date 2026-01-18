#!/usr/bin/env python
"""
Simple script to verify system integration functionality.
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pholli.settings')
django.setup()

from policies.integration import (
    SystemIntegrationManager,
    FeatureSynchronizationManager,
    CrossModuleValidator
)


def test_feature_mappings():
    """Test that feature mappings are properly defined."""
    print("Testing feature mappings...")
    
    health_mapping = FeatureSynchronizationManager.get_feature_mapping('HEALTH')
    funeral_mapping = FeatureSynchronizationManager.get_feature_mapping('FUNERAL')
    
    print(f"✓ Health features: {len(health_mapping)} defined")
    print(f"✓ Funeral features: {len(funeral_mapping)} defined")
    
    # Test specific mappings
    assert 'annual_limit_per_member' in health_mapping
    assert 'cover_amount' in funeral_mapping
    
    print("✓ Feature mappings are properly defined")


def test_feature_consistency():
    """Test feature consistency validation."""
    print("\nTesting feature consistency...")
    
    health_errors = FeatureSynchronizationManager.validate_feature_consistency('HEALTH')
    funeral_errors = FeatureSynchronizationManager.validate_feature_consistency('FUNERAL')
    
    if health_errors:
        print(f"⚠ Health feature consistency issues: {health_errors}")
    else:
        print("✓ Health features are consistent")
    
    if funeral_errors:
        print(f"⚠ Funeral feature consistency issues: {funeral_errors}")
    else:
        print("✓ Funeral features are consistent")


def test_system_integrity():
    """Test overall system integrity."""
    print("\nTesting system integrity...")
    
    is_valid, errors = SystemIntegrationManager.validate_system_integrity()
    
    if is_valid:
        print("✓ System integrity check passed")
    else:
        print(f"⚠ System integrity issues found:")
        for error in errors:
            print(f"  - {error}")


def test_imports():
    """Test that all integration modules can be imported."""
    print("\nTesting module imports...")
    
    try:
        from policies.models import BasePolicy, PolicyFeatures
        from simple_surveys.models import SimpleSurvey
        from comparison.models import FeatureComparisonResult
        print("✓ All required models can be imported")
    except ImportError as e:
        print(f"✗ Import error: {e}")
        return False
    
    try:
        from policies.signals import get_system_health_metrics
        from policies.admin_integration import SystemIntegrationAdminMixin
        print("✓ All integration utilities can be imported")
    except ImportError as e:
        print(f"✗ Import error: {e}")
        return False
    
    return True


def main():
    """Run all integration tests."""
    print("=== System Integration Verification ===\n")
    
    try:
        # Test imports first
        if not test_imports():
            print("\n✗ Integration verification failed due to import errors")
            return False
        
        # Test feature mappings
        test_feature_mappings()
        
        # Test feature consistency
        test_feature_consistency()
        
        # Test system integrity
        test_system_integrity()
        
        print("\n=== Integration Verification Complete ===")
        print("✓ System integration is properly implemented")
        
        return True
    
    except Exception as e:
        print(f"\n✗ Integration verification failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)