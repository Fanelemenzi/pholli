"""
Example usage of the Feature Matching Engine.
Demonstrates how to use the feature-based policy comparison system.
"""

from .feature_matching_engine import FeatureMatchingEngine
from .feature_comparison_manager import FeatureComparisonManager
from .match_explanations import MatchExplanationGenerator
from decimal import Decimal


def example_health_policy_comparison():
    """
    Example of comparing health policies using feature matching.
    """
    print("=== Health Policy Feature Matching Example ===\n")
    
    # Initialize the engine for health insurance
    engine = FeatureMatchingEngine('HEALTH')
    
    # Example user preferences from a health survey
    user_preferences = {
        'annual_limit_per_member': Decimal('80000.00'),  # User wants R80k annual limit
        'monthly_household_income': Decimal('6000.00'),  # User earns R6k per month
        'in_hospital_benefit': True,  # User wants in-hospital benefits
        'out_hospital_benefit': True,  # User wants out-of-hospital benefits
        'chronic_medication_availability': True  # User needs chronic medication coverage
    }
    
    print("User Preferences:")
    for key, value in user_preferences.items():
        print(f"  {key.replace('_', ' ').title()}: {value}")
    print()
    
    # Note: In real usage, you would get actual policy objects from the database
    # This is just to show the expected data structure
    print("Example policy features structure:")
    print("""
    policy.get_policy_features() should return an object with:
    - insurance_type: 'HEALTH'
    - annual_limit_per_member: Decimal('100000.00')
    - monthly_household_income: Decimal('5000.00')
    - in_hospital_benefit: True
    - out_hospital_benefit: True
    - chronic_medication_availability: False
    """)
    
    return engine, user_preferences


def example_funeral_policy_comparison():
    """
    Example of comparing funeral policies using feature matching.
    """
    print("=== Funeral Policy Feature Matching Example ===\n")
    
    # Initialize the engine for funeral insurance
    engine = FeatureMatchingEngine('FUNERAL')
    
    # Example user preferences from a funeral survey
    user_preferences = {
        'cover_amount': Decimal('50000.00'),  # User wants R50k coverage
        'monthly_net_income': Decimal('4000.00'),  # User earns R4k per month
        'marital_status_requirement': 'married',  # User is married
        'gender_requirement': 'female'  # User is female
    }
    
    print("User Preferences:")
    for key, value in user_preferences.items():
        print(f"  {key.replace('_', ' ').title()}: {value}")
    print()
    
    print("Example policy features structure:")
    print("""
    policy.get_policy_features() should return an object with:
    - insurance_type: 'FUNERAL'
    - cover_amount: Decimal('45000.00')
    - monthly_net_income: Decimal('3500.00')
    - marital_status_requirement: 'any'
    - gender_requirement: 'any'
    """)
    
    return engine, user_preferences


def example_comparison_workflow():
    """
    Example of the complete comparison workflow.
    """
    print("=== Complete Comparison Workflow Example ===\n")
    
    print("""
    1. User completes survey with preferences
    2. System filters policies by insurance type
    3. Feature matching engine calculates compatibility
    4. Comparison manager ranks results
    5. Match explanations provide detailed insights
    
    Typical workflow:
    
    # Get policies from database
    policies = BasePolicy.objects.filter(
        category__slug='health',
        is_active=True,
        approval_status='APPROVED'
    )
    
    # Get user preferences from survey
    user_preferences = survey.get_preferences_dict()
    
    # Compare policies
    manager = FeatureComparisonManager('HEALTH')
    results = manager.compare_policies_by_features(
        policies, user_preferences
    )
    
    # Generate detailed explanations
    generator = MatchExplanationGenerator('HEALTH')
    for result in results['results']:
        explanation = generator.generate_detailed_explanation(
            result.policy, 
            result.to_dict(), 
            user_preferences
        )
        print(explanation)
    """)


def example_scoring_explanation():
    """
    Explain how the scoring system works.
    """
    print("=== Feature Scoring System Explanation ===\n")
    
    print("""
    The feature matching engine uses different scoring algorithms based on feature types:
    
    1. BOOLEAN FEATURES (e.g., in_hospital_benefit):
       - Exact match: 1.0 (100%)
       - No match: 0.0 (0%)
    
    2. NUMERIC FEATURES:
       a) Coverage amounts (higher is better):
          - Policy >= User preference: 1.0 (100%)
          - Policy < User preference: ratio (policy_value / user_preference)
       
       b) Income requirements (lower is better for policy):
          - User income >= Policy requirement: 1.0 (100%)
          - User income < Policy requirement: ratio (user_income / policy_requirement)
    
    3. STRING FEATURES (e.g., marital_status_requirement):
       - Exact match: 1.0 (100%)
       - Fuzzy match (variations): 1.0 (100%)
       - Partial match: 0.7 (70%)
       - No match: 0.0 (0%)
    
    4. OVERALL SCORE CALCULATION:
       - Weighted average of all feature scores
       - Important features (coverage, income) have higher weights
       - Final score is between 0.0 and 1.0
    
    5. COMPATIBILITY CATEGORIES:
       - 0.9+: Perfect Match
       - 0.75-0.89: Excellent Match
       - 0.6-0.74: Good Match
       - 0.4-0.59: Partial Match
       - <0.4: Poor Match
    """)


def example_integration_points():
    """
    Show how the feature matching integrates with existing system.
    """
    print("=== Integration with Existing System ===\n")
    
    print("""
    The feature matching engine integrates with:
    
    1. POLICY MODELS:
       - Uses existing BasePolicy model
       - Requires PolicyFeatures relationship
       - Works with health_policies and funeral_policies apps
    
    2. SURVEY SYSTEM:
       - Integrates with simple_surveys app
       - Uses SimpleSurvey.get_preferences_dict()
       - Maps survey responses to feature preferences
    
    3. COMPARISON SYSTEM:
       - Extends existing comparison app
       - Updates ComparisonSession and ComparisonResult models
       - Provides feature-based ranking
    
    4. ADMIN INTERFACE:
       - PolicyFeatures can be managed through admin
       - Feature definitions are configurable
       - Supports both insurance types
    
    5. API ENDPOINTS:
       - Can be exposed through existing comparison views
       - Returns structured JSON results
       - Supports filtering and sorting
    """)


if __name__ == '__main__':
    """
    Run all examples to demonstrate the feature matching system.
    """
    example_health_policy_comparison()
    print("\n" + "="*60 + "\n")
    
    example_funeral_policy_comparison()
    print("\n" + "="*60 + "\n")
    
    example_comparison_workflow()
    print("\n" + "="*60 + "\n")
    
    example_scoring_explanation()
    print("\n" + "="*60 + "\n")
    
    example_integration_points()