#!/usr/bin/env python
"""
Demonstration of Simple Survey Comparison Integration.

This script shows how the simplified survey system integrates with the 
existing comparison engine to generate policy quotations.
"""

from typing import Dict, Any
from .comparison_adapter import SimpleSurveyComparisonAdapter, SimplifiedPolicyComparisonEngine
from .models import SimpleSurveyResponse, QuotationSession


def demonstrate_integration():
    """
    Demonstrate the integration between simple surveys and comparison engine.
    
    This function shows:
    1. How survey responses are converted to comparison criteria
    2. How the simplified engine processes policies
    3. How results are formatted for display
    """
    
    print("Simple Survey Comparison Integration Demo")
    print("=" * 50)
    
    # Example 1: Health Insurance Survey Integration
    print("\n1. Health Insurance Survey Integration")
    print("-" * 40)
    
    health_adapter = SimpleSurveyComparisonAdapter('health')
    
    # Simulate survey responses
    sample_health_responses = {
        'age': 35,
        'location': 'gauteng',
        'family_size': 3,
        'health_status': 'good',
        'chronic_conditions': ['none'],
        'coverage_priority': 'comprehensive',
        'monthly_budget': 800,
        'preferred_deductible': 'R1000'
    }
    
    print(f"Sample survey responses: {sample_health_responses}")
    
    # Convert to comparison criteria
    field_mappings = health_adapter._get_field_mappings()
    converted_criteria = {}
    
    for survey_field, response_value in sample_health_responses.items():
        if survey_field in field_mappings:
            comparison_field = field_mappings[survey_field]
            converted_value = health_adapter._convert_response_value(survey_field, response_value)
            converted_criteria[comparison_field] = converted_value
    
    # Add default weights
    converted_criteria['weights'] = health_adapter._get_default_weights(converted_criteria)
    
    print(f"Converted criteria: {converted_criteria}")
    
    # Example 2: Funeral Insurance Survey Integration
    print("\n2. Funeral Insurance Survey Integration")
    print("-" * 40)
    
    funeral_adapter = SimpleSurveyComparisonAdapter('funeral')
    
    # Simulate survey responses
    sample_funeral_responses = {
        'age': 45,
        'location': 'western_cape',
        'family_members_to_cover': 8,
        'coverage_amount_needed': 'R50k',
        'service_preference': 'standard',
        'monthly_budget': 250,
        'waiting_period_tolerance': '6 months'
    }
    
    print(f"Sample survey responses: {sample_funeral_responses}")
    
    # Convert to comparison criteria
    field_mappings = funeral_adapter._get_field_mappings()
    converted_criteria = {}
    
    for survey_field, response_value in sample_funeral_responses.items():
        if survey_field in field_mappings:
            comparison_field = field_mappings[survey_field]
            converted_value = funeral_adapter._convert_response_value(survey_field, response_value)
            converted_criteria[comparison_field] = converted_value
    
    # Add default weights
    converted_criteria['weights'] = funeral_adapter._get_default_weights(converted_criteria)
    
    print(f"Converted criteria: {converted_criteria}")
    
    # Example 3: Simplified Scoring Algorithm
    print("\n3. Simplified Scoring Algorithm")
    print("-" * 40)
    
    engine = SimplifiedPolicyComparisonEngine('health')
    
    print(f"Simplified weights:")
    print(f"  - Criteria: {engine.CRITERIA_WEIGHT} (70%)")
    print(f"  - Value: {engine.VALUE_WEIGHT} (20%)")
    print(f"  - Reviews: {engine.REVIEW_WEIGHT} (5%)")
    print(f"  - Organization: {engine.ORGANIZATION_WEIGHT} (5%)")
    
    # Example scoring
    class MockPolicy:
        def __init__(self, premium, coverage, waiting_days):
            self.base_premium = premium
            self.coverage_amount = coverage
            self.waiting_period_days = waiting_days
            self.organization = type('Org', (), {'is_verified': True})()
    
    mock_policy = MockPolicy(600, 150000, 30)
    user_budget = 800
    
    premium_score = engine._score_premium_match(mock_policy, user_budget)
    coverage_score = engine._score_coverage_match(mock_policy, 100000)
    waiting_score = engine._score_waiting_period_match(mock_policy, 60)
    
    print(f"\nExample scoring for policy (R{mock_policy.base_premium}, R{mock_policy.coverage_amount}, {mock_policy.waiting_period_days} days):")
    print(f"  - Premium score (budget R{user_budget}): {premium_score}")
    print(f"  - Coverage score (need R100k): {coverage_score}")
    print(f"  - Waiting period score (tolerance 60 days): {waiting_score}")
    
    # Example 4: Key Features Extraction
    print("\n4. Key Features Extraction")
    print("-" * 40)
    
    # Mock policy with features
    mock_policy.includes_dental_cover = True
    mock_policy.chronic_medication_covered = True
    mock_policy.waiting_period_days = 0
    
    features = health_adapter._extract_key_features(mock_policy)
    print(f"Extracted key features: {features}")
    
    # Example 5: Value Rating
    print("\n5. Value Rating System")
    print("-" * 40)
    
    value_scores = [85, 70, 55, 40]
    for score in value_scores:
        rating = health_adapter._get_value_rating(score)
        print(f"  - Score {score}: {rating}")
    
    print("\n" + "=" * 50)
    print("Integration Demo Complete!")
    print("\nKey Benefits of the Integration:")
    print("✓ Simplified scoring algorithm (70% criteria focus)")
    print("✓ Automatic survey response conversion")
    print("✓ Category-specific processing")
    print("✓ Streamlined policy comparison")
    print("✓ Mobile-optimized results format")


def show_integration_flow():
    """Show the complete integration flow."""
    
    print("\nIntegration Flow:")
    print("=" * 50)
    
    flow_steps = [
        "1. User completes simple survey (8-10 questions)",
        "2. SimpleSurveyEngine processes responses",
        "3. SimpleSurveyComparisonAdapter converts to criteria",
        "4. SimplifiedPolicyComparisonEngine scores policies",
        "5. Results simplified and formatted for display",
        "6. Top 5 policies returned with key information"
    ]
    
    for step in flow_steps:
        print(f"   {step}")
    
    print("\nSimplifications Made:")
    print("-" * 30)
    
    simplifications = [
        "• Removed complex survey context processing",
        "• Streamlined scoring weights (4 factors vs 10+)",
        "• Eliminated A/B testing and analytics",
        "• Focused on essential policy comparison",
        "• Reduced database queries for performance",
        "• Simplified result format for mobile display"
    ]
    
    for simplification in simplifications:
        print(f"   {simplification}")


if __name__ == '__main__':
    demonstrate_integration()
    show_integration_flow()