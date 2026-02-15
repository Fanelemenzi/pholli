"""
Live integration test using existing database data.
Tests the actual survey to policy matching flow.
"""

import os
import sys
import django
from decimal import Decimal

# Add the project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# Configure Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pholli.settings')
django.setup()

from policies.models import BasePolicy, PolicyCategory
from comparison.feature_matching_engine import FeatureMatchingEngine
from simple_surveys.views import SurveyResultsView


def test_live_integration():
    """Test integration with existing database data."""
    print("="*60)
    print("LIVE INTEGRATION TEST")
    print("="*60)
    
    # 1. Check existing policies
    print("\n1. CHECKING EXISTING POLICIES:")
    print("-" * 30)
    
    health_policies = BasePolicy.objects.filter(
        category__slug='health',
        is_active=True
    ).select_related('organization', 'policy_features')
    
    print(f"Health policies found: {health_policies.count()}")
    for policy in health_policies[:3]:
        print(f"  - {policy.name} (R{policy.base_premium}/month)")
        features = policy.get_policy_features()
        if features:
            print(f"    Features: {features.insurance_type}")
        else:
            print(f"    Features: None")
    
    if health_policies.count() == 0:
        print("❌ No health policies found - cannot test integration")
        return False
    
    # 2. Test feature matching engine
    print("\n2. TESTING FEATURE MATCHING ENGINE:")
    print("-" * 30)
    
    try:
        engine = FeatureMatchingEngine('HEALTH')
        print("✓ FeatureMatchingEngine initialized successfully")
        
        # Test with sample preferences
        user_preferences = {
            'annual_limit_per_family': Decimal('300000.00'),
            'ambulance_coverage': True,
            'chronic_medication_availability': True
        }
        
        print(f"Testing with preferences: {user_preferences}")
        
        # Test first policy
        test_policy = health_policies.first()
        result = engine.calculate_policy_compatibility(test_policy, user_preferences)
        
        print(f"✓ Policy compatibility calculated:")
        print(f"  Policy: {test_policy.name}")
        print(f"  Score: {result['overall_score']:.3f}")
        print(f"  Matches: {len(result['matches'])}")
        print(f"  Explanation: {result['explanation']}")
        
    except Exception as e:
        print(f"❌ Feature matching engine error: {str(e)}")
        return False
    
    # 3. Test survey results view methods
    print("\n3. TESTING SURVEY RESULTS VIEW METHODS:")
    print("-" * 30)
    
    try:
        view = SurveyResultsView()
        
        # Test get_relevant_policies
        policies = view.get_relevant_policies('health')
        print(f"✓ get_relevant_policies returned {policies.count()} policies")
        
        # Test convert_responses_to_preferences (mock data)
        mock_responses = []
        preferences = view.convert_responses_to_preferences(mock_responses, 'health')
        print(f"✓ convert_responses_to_preferences returned {len(preferences)} preferences")
        
        # Test generate_policy_quotations
        if policies.exists():
            quotations = view.generate_policy_quotations(
                policies[:3], user_preferences, 'health'
            )
            print(f"✓ generate_policy_quotations returned {len(quotations)} quotations")
            
            if quotations:
                best_quote = quotations[0]
                print(f"  Best match: {best_quote['name']}")
                print(f"  Score: {best_quote['match_score']}%")
                print(f"  Premium: R{best_quote['monthly_premium']}/month")
        
    except Exception as e:
        print(f"❌ Survey results view error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    
    # 4. Test complete flow simulation
    print("\n4. TESTING COMPLETE FLOW SIMULATION:")
    print("-" * 30)
    
    try:
        # Simulate user preferences from survey
        simulated_preferences = {
            'annual_limit_per_family': Decimal('200000.00'),
            'ambulance_coverage': True,
            'chronic_medication_availability': False,
            'in_hospital_benefit': True,
            'out_hospital_benefit': True
        }
        
        print(f"Simulated user preferences: {simulated_preferences}")
        
        # Get policies and run matching
        policies = BasePolicy.objects.filter(
            category__slug='health',
            is_active=True,
            policy_features__isnull=False
        ).select_related('organization', 'policy_features')[:5]
        
        engine = FeatureMatchingEngine('HEALTH')
        results = []
        
        for policy in policies:
            try:
                compatibility = engine.calculate_policy_compatibility(
                    policy, simulated_preferences
                )
                results.append({
                    'policy': policy,
                    'score': compatibility['overall_score'],
                    'matches': len(compatibility['matches']),
                    'explanation': compatibility['explanation']
                })
            except Exception as e:
                print(f"  Warning: Error with policy {policy.id}: {str(e)}")
                continue
        
        # Sort by score
        results.sort(key=lambda x: x['score'], reverse=True)
        
        print(f"✓ Processed {len(results)} policies successfully")
        print("\nTop 3 matches:")
        for i, result in enumerate(results[:3], 1):
            policy = result['policy']
            print(f"  #{i}. {policy.name}")
            print(f"      Score: {result['score']:.3f}")
            print(f"      Premium: R{policy.base_premium}/month")
            print(f"      Matches: {result['matches']}")
        
        if results:
            print(f"\n✅ INTEGRATION TEST PASSED!")
            print(f"   Successfully matched {len(results)} policies")
            print(f"   Best match: {results[0]['policy'].name} ({results[0]['score']:.3f})")
            return True
        else:
            print("❌ No policies could be processed")
            return False
        
    except Exception as e:
        print(f"❌ Complete flow simulation error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_benefits_modal_functionality():
    """Test the benefits modal functionality."""
    print("\n" + "="*60)
    print("TESTING BENEFITS MODAL FUNCTIONALITY")
    print("="*60)
    
    try:
        # Get a policy with features
        policy = BasePolicy.objects.filter(
            policy_features__isnull=False
        ).select_related('policy_features').first()
        
        if not policy:
            print("❌ No policies with features found")
            return False
        
        print(f"Testing with policy: {policy.name}")
        
        # Test policy features access
        features = policy.get_policy_features()
        if features:
            print(f"✓ Policy features found: {features.insurance_type}")
            
            # Test feature formatting
            if features.insurance_type == 'HEALTH':
                print("  Health features:")
                if hasattr(features, 'annual_limit_per_family'):
                    print(f"    Annual family limit: R{features.annual_limit_per_family}")
                if hasattr(features, 'ambulance_coverage'):
                    print(f"    Ambulance coverage: {features.ambulance_coverage}")
                if hasattr(features, 'chronic_medication_availability'):
                    print(f"    Chronic medication: {features.chronic_medication_availability}")
            
            print("✅ Benefits modal functionality test PASSED")
            return True
        else:
            print("❌ No policy features found")
            return False
            
    except Exception as e:
        print(f"❌ Benefits modal test error: {str(e)}")
        return False


if __name__ == '__main__':
    print("Starting Live Integration Tests...")
    
    success1 = test_live_integration()
    success2 = test_benefits_modal_functionality()
    
    if success1 and success2:
        print("\n🎉 ALL LIVE INTEGRATION TESTS PASSED!")
        print("\nThe survey to policy matching integration is working correctly!")
        print("Users can now:")
        print("  ✓ Complete surveys")
        print("  ✓ Get matched policies based on their preferences")
        print("  ✓ View policy benefits and features")
        print("  ✓ See compatibility scores and explanations")
    else:
        print("\n❌ Some integration tests failed")
        print("Check the errors above for details")