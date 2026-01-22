"""
Feature Matching Engine for Insurance Policies.
Specialized engine for matching user preferences against policy features
based on standardized health and funeral insurance features.
"""

from decimal import Decimal, ROUND_HALF_UP
from typing import List, Dict, Any, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class FeatureMatchingEngine:
    """
    Matches user preferences against policy features for health and funeral insurance.
    Provides compatibility scoring based on feature alignment.
    """
    
    def __init__(self, insurance_type: str):
        """
        Initialize the feature matching engine for a specific insurance type.
        
        Args:
            insurance_type: Type of insurance ('HEALTH' or 'FUNERAL')
        """
        self.insurance_type = insurance_type.upper()
        if self.insurance_type not in ['HEALTH', 'FUNERAL']:
            raise ValueError("Insurance type must be 'HEALTH' or 'FUNERAL'")
    
    def calculate_policy_compatibility(self, policy, user_preferences: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate compatibility score between policy and user preferences.
        
        Args:
            policy: BasePolicy instance with policy_features
            user_preferences: Dictionary of user preferences from survey
            
        Returns:
            dict: {
                'overall_score': float,
                'feature_scores': dict,
                'matches': list,
                'mismatches': list,
                'explanation': str
            }
        """
        try:
            policy_features = policy.get_policy_features()
            if not policy_features or policy_features.insurance_type != self.insurance_type:
                return self._empty_result("Policy type does not match survey type")
            
            feature_scores = {}
            matches = []
            mismatches = []
            
            # Get relevant features based on insurance type
            relevant_features = self._get_relevant_features()
            
            for feature_name in relevant_features:
                user_pref = user_preferences.get(feature_name)
                if user_pref is None:
                    continue
                    
                policy_value = getattr(policy_features, feature_name, None)
                if policy_value is None:
                    continue
                
                score = self._calculate_feature_score(feature_name, policy_value, user_pref)
                feature_scores[feature_name] = score
                
                # Categorize as match or mismatch
                if score >= 0.8:  # High match threshold
                    matches.append({
                        'feature': self._get_feature_display_name(feature_name),
                        'user_preference': self._format_preference_value(feature_name, user_pref),
                        'policy_value': self._format_policy_value(feature_name, policy_value),
                        'score': score,
                        'match_type': 'excellent' if score >= 0.95 else 'good'
                    })
                elif score < 0.5:  # Low match threshold
                    mismatches.append({
                        'feature': self._get_feature_display_name(feature_name),
                        'user_preference': self._format_preference_value(feature_name, user_pref),
                        'policy_value': self._format_policy_value(feature_name, policy_value),
                        'score': score,
                        'mismatch_severity': 'major' if score < 0.2 else 'moderate'
                    })
            
            # Calculate overall score
            overall_score = self._calculate_overall_score(feature_scores)
            
            # Generate explanation
            explanation = self._generate_explanation(matches, mismatches, overall_score)
            
            return {
                'overall_score': overall_score,
                'feature_scores': feature_scores,
                'matches': matches,
                'mismatches': mismatches,
                'explanation': explanation,
                'insurance_type': self.insurance_type,
                'total_features_compared': len(feature_scores)
            }
            
        except Exception as e:
            logger.error(f"Error calculating policy compatibility: {str(e)}")
            return self._empty_result(f"Error calculating compatibility: {str(e)}")
    
    def _get_relevant_features(self) -> List[str]:
        """
        Get list of relevant features based on insurance type.
        
        Returns:
            List of feature field names
        """
        if self.insurance_type == 'HEALTH':
            return [
                'annual_limit_per_member',
                'annual_limit_per_family',  # New field
                'monthly_household_income',
                'currently_on_medical_aid',  # New field
                'ambulance_coverage',  # New field
                'in_hospital_benefit',
                'out_hospital_benefit',
                'chronic_medication_availability'
            ]
        elif self.insurance_type == 'FUNERAL':
            return [
                'cover_amount',
                'marital_status_requirement',
                'gender_requirement'
            ]
        return []
    
    def _calculate_feature_score(self, feature_name: str, policy_value: Any, user_preference: Any) -> float:
        """
        Calculate score for individual feature match.
        
        Args:
            feature_name: Name of the feature being compared
            policy_value: Value from policy features
            user_preference: User's preferred value
            
        Returns:
            Score from 0.0 to 1.0
        """
        try:
            # Boolean features (exact match required)
            if isinstance(policy_value, bool) and isinstance(user_preference, bool):
                return 1.0 if policy_value == user_preference else 0.0
            
            # Numeric features (coverage amounts, income requirements)
            elif isinstance(policy_value, (int, float, Decimal)) and isinstance(user_preference, (int, float, Decimal)):
                return self._score_numeric_feature(feature_name, policy_value, user_preference)
            
            # String features (marital status, gender)
            elif isinstance(policy_value, str) and isinstance(user_preference, str):
                return self._score_string_feature(feature_name, policy_value, user_preference)
            
            # Handle None values
            elif policy_value is None or user_preference is None:
                return 0.5  # Neutral score for missing data
            
            else:
                logger.warning(f"Unhandled feature types for {feature_name}: {type(policy_value)}, {type(user_preference)}")
                return 0.5
                
        except Exception as e:
            logger.error(f"Error scoring feature {feature_name}: {str(e)}")
            return 0.0
    
    def _score_numeric_feature(self, feature_name: str, policy_value: Any, user_preference: Any) -> float:
        """
        Score numeric features with context-aware logic.
        
        Args:
            feature_name: Name of the feature
            policy_value: Policy's numeric value
            user_preference: User's preferred numeric value
            
        Returns:
            Score from 0.0 to 1.0
        """
        policy_val = float(policy_value)
        user_pref = float(user_preference)
        
        # Coverage amounts and limits - higher is generally better
        if feature_name in ['annual_limit_per_member', 'annual_limit_per_family', 'cover_amount']:
            if policy_val >= user_pref:
                # Policy meets or exceeds preference - excellent
                return 1.0
            else:
                # Policy is below preference - score based on how close
                ratio = policy_val / user_pref if user_pref > 0 else 0
                return max(0.0, min(1.0, ratio))
        
        # Income requirements - policy should not exceed user's income
        elif feature_name in ['monthly_household_income', 'monthly_net_income']:
            if policy_val <= user_pref:
                # User meets income requirement - excellent
                return 1.0
            else:
                # User doesn't meet requirement - score based on gap
                ratio = user_pref / policy_val if policy_val > 0 else 0
                return max(0.0, min(1.0, ratio))
        
        else:
            # Default numeric comparison - closer is better
            if user_pref == 0:
                return 1.0 if policy_val == 0 else 0.0
            
            difference = abs(policy_val - user_pref)
            max_acceptable_diff = user_pref * 0.2  # 20% tolerance
            
            if difference <= max_acceptable_diff:
                return 1.0 - (difference / max_acceptable_diff) * 0.2
            else:
                return max(0.0, 0.8 - (difference / user_pref))
    
    def _score_string_feature(self, feature_name: str, policy_value: str, user_preference: str) -> float:
        """
        Score string features with fuzzy matching.
        
        Args:
            feature_name: Name of the feature
            policy_value: Policy's string value
            user_preference: User's preferred string value
            
        Returns:
            Score from 0.0 to 1.0
        """
        policy_val = policy_value.lower().strip()
        user_pref = user_preference.lower().strip()
        
        # Exact match
        if policy_val == user_pref:
            return 1.0
        
        # Handle common variations
        if feature_name == 'marital_status_requirement':
            # Map common variations
            status_mappings = {
                'single': ['unmarried', 'not married', 'single'],
                'married': ['married', 'wed'],
                'divorced': ['divorced', 'separated'],
                'widowed': ['widowed', 'widow', 'widower'],
                'any': ['any', 'all', 'no requirement', 'none']
            }
            
            for canonical, variations in status_mappings.items():
                if policy_val in variations and user_pref in variations:
                    return 1.0
        
        elif feature_name == 'gender_requirement':
            # Map gender variations
            gender_mappings = {
                'male': ['male', 'm', 'man'],
                'female': ['female', 'f', 'woman'],
                'any': ['any', 'all', 'both', 'no requirement', 'none']
            }
            
            for canonical, variations in gender_mappings.items():
                if policy_val in variations and user_pref in variations:
                    return 1.0
        
        # Partial match based on string similarity
        if user_pref in policy_val or policy_val in user_pref:
            return 0.7
        
        # No match
        return 0.0
    
    def _calculate_overall_score(self, feature_scores: Dict[str, float]) -> float:
        """
        Calculate overall compatibility score from individual feature scores.
        
        Args:
            feature_scores: Dictionary of feature names to scores
            
        Returns:
            Overall score from 0.0 to 1.0
        """
        if not feature_scores:
            return 0.0
        
        # Apply feature weights based on insurance type
        weights = self._get_feature_weights()
        
        weighted_sum = 0.0
        total_weight = 0.0
        
        for feature_name, score in feature_scores.items():
            weight = weights.get(feature_name, 1.0)
            weighted_sum += score * weight
            total_weight += weight
        
        if total_weight == 0:
            return 0.0
        
        overall_score = weighted_sum / total_weight
        return round(overall_score, 3)
    
    def _get_feature_weights(self) -> Dict[str, float]:
        """
        Get feature weights based on insurance type and importance.
        
        Returns:
            Dictionary of feature names to weights
        """
        if self.insurance_type == 'HEALTH':
            return {
                'annual_limit_per_family': 2.2,  # Very important - new primary field
                'annual_limit_per_member': 1.8,  # Important but secondary to family limit
                'monthly_household_income': 1.8,  # Very important for eligibility
                'currently_on_medical_aid': 1.6,  # Important for eligibility and compatibility
                'ambulance_coverage': 1.4,  # Important safety feature
                'in_hospital_benefit': 1.5,  # Important
                'out_hospital_benefit': 1.5,  # Important
                'chronic_medication_availability': 1.3  # Moderately important
            }
        elif self.insurance_type == 'FUNERAL':
            return {
                'cover_amount': 2.0,  # Very important
                'marital_status_requirement': 1.0,  # Standard importance
                'gender_requirement': 1.0  # Standard importance
            }
        return {}
    
    def _generate_explanation(self, matches: List[Dict], mismatches: List[Dict], overall_score: float) -> str:
        """
        Generate human-readable explanation of the match.
        
        Args:
            matches: List of matching features
            mismatches: List of mismatching features
            overall_score: Overall compatibility score
            
        Returns:
            Human-readable explanation string
        """
        match_count = len(matches)
        mismatch_count = len(mismatches)
        
        if overall_score >= 0.9:
            base_msg = "Excellent match"
        elif overall_score >= 0.75:
            base_msg = "Very good match"
        elif overall_score >= 0.6:
            base_msg = "Good match"
        elif overall_score >= 0.4:
            base_msg = "Partial match"
        else:
            base_msg = "Poor match"
        
        # Add details about matches and mismatches
        details = []
        
        if match_count > 0:
            excellent_matches = sum(1 for m in matches if m.get('match_type') == 'excellent')
            if excellent_matches > 0:
                details.append(f"{excellent_matches} excellent feature match{'es' if excellent_matches != 1 else ''}")
            
            good_matches = match_count - excellent_matches
            if good_matches > 0:
                details.append(f"{good_matches} good feature match{'es' if good_matches != 1 else ''}")
        
        if mismatch_count > 0:
            major_mismatches = sum(1 for m in mismatches if m.get('mismatch_severity') == 'major')
            if major_mismatches > 0:
                details.append(f"{major_mismatches} major mismatch{'es' if major_mismatches != 1 else ''}")
            
            moderate_mismatches = mismatch_count - major_mismatches
            if moderate_mismatches > 0:
                details.append(f"{moderate_mismatches} moderate mismatch{'es' if moderate_mismatches != 1 else ''}")
        
        if details:
            return f"{base_msg} with {', '.join(details)}"
        else:
            return f"{base_msg} - no specific features compared"
    
    def _get_feature_display_name(self, feature_name: str) -> str:
        """
        Get human-readable display name for feature.
        
        Args:
            feature_name: Internal feature name
            
        Returns:
            Human-readable feature name
        """
        display_names = {
            'annual_limit_per_member': 'Annual Limit per Member',
            'annual_limit_per_family': 'Annual Limit per Family',
            'monthly_household_income': 'Monthly Household Income Requirement',
            'currently_on_medical_aid': 'Current Medical Aid Status',
            'ambulance_coverage': 'Ambulance Coverage',
            'in_hospital_benefit': 'In-Hospital Benefits',
            'out_hospital_benefit': 'Out-of-Hospital Benefits',
            'chronic_medication_availability': 'Chronic Medication Coverage',
            'cover_amount': 'Coverage Amount',
            'marital_status_requirement': 'Marital Status Requirement',
            'gender_requirement': 'Gender Requirement',
            'monthly_net_income': 'Monthly Net Income Requirement'
        }
        
        return display_names.get(feature_name, feature_name.replace('_', ' ').title())
    
    def _format_preference_value(self, feature_name: str, value: Any) -> str:
        """
        Format user preference value for display.
        
        Args:
            feature_name: Name of the feature
            value: User preference value
            
        Returns:
            Formatted string representation
        """
        if isinstance(value, bool):
            return "Yes" if value else "No"
        elif isinstance(value, (int, float, Decimal)):
            if feature_name in ['annual_limit_per_member', 'annual_limit_per_family', 'cover_amount', 'monthly_household_income', 'monthly_net_income']:
                return f"R{value:,.2f}"
            else:
                return str(value)
        elif isinstance(value, str):
            return value.title()
        else:
            return str(value)
    
    def _format_policy_value(self, feature_name: str, value: Any) -> str:
        """
        Format policy value for display.
        
        Args:
            feature_name: Name of the feature
            value: Policy value
            
        Returns:
            Formatted string representation
        """
        return self._format_preference_value(feature_name, value)
    
    def _empty_result(self, reason: str = "No comparison possible") -> Dict[str, Any]:
        """
        Return empty result for incompatible policies.
        
        Args:
            reason: Reason for empty result
            
        Returns:
            Empty result dictionary
        """
        return {
            'overall_score': 0.0,
            'feature_scores': {},
            'matches': [],
            'mismatches': [],
            'explanation': reason,
            'insurance_type': self.insurance_type,
            'total_features_compared': 0
        }


class FeatureComparisonResult:
    """
    Helper class for storing and managing feature comparison results.
    """
    
    def __init__(self, policy, compatibility_data: Dict[str, Any]):
        """
        Initialize comparison result.
        
        Args:
            policy: BasePolicy instance
            compatibility_data: Result from FeatureMatchingEngine
        """
        self.policy = policy
        self.overall_score = compatibility_data['overall_score']
        self.feature_scores = compatibility_data['feature_scores']
        self.matches = compatibility_data['matches']
        self.mismatches = compatibility_data['mismatches']
        self.explanation = compatibility_data['explanation']
        self.insurance_type = compatibility_data['insurance_type']
        self.total_features_compared = compatibility_data['total_features_compared']
    
    def get_compatibility_category(self) -> str:
        """
        Get compatibility category based on overall score.
        
        Returns:
            Category string
        """
        if self.overall_score >= 0.9:
            return 'PERFECT_MATCH'
        elif self.overall_score >= 0.75:
            return 'EXCELLENT_MATCH'
        elif self.overall_score >= 0.6:
            return 'GOOD_MATCH'
        elif self.overall_score >= 0.4:
            return 'PARTIAL_MATCH'
        else:
            return 'POOR_MATCH'
    
    def get_recommendation_strength(self) -> str:
        """
        Get recommendation strength.
        
        Returns:
            Strength level string
        """
        category = self.get_compatibility_category()
        strength_map = {
            'PERFECT_MATCH': 'Highly Recommended',
            'EXCELLENT_MATCH': 'Strongly Recommended',
            'GOOD_MATCH': 'Recommended',
            'PARTIAL_MATCH': 'Consider with Caution',
            'POOR_MATCH': 'Not Recommended'
        }
        return strength_map.get(category, 'Unknown')
    
    def get_top_matches(self, limit: int = 3) -> List[Dict]:
        """
        Get top matching features.
        
        Args:
            limit: Maximum number of matches to return
            
        Returns:
            List of top matches
        """
        # Sort matches by score (descending)
        sorted_matches = sorted(self.matches, key=lambda x: x['score'], reverse=True)
        return sorted_matches[:limit]
    
    def get_major_concerns(self, limit: int = 3) -> List[Dict]:
        """
        Get major mismatches/concerns.
        
        Args:
            limit: Maximum number of concerns to return
            
        Returns:
            List of major concerns
        """
        # Filter for major mismatches and sort by severity
        major_mismatches = [m for m in self.mismatches if m.get('mismatch_severity') == 'major']
        moderate_mismatches = [m for m in self.mismatches if m.get('mismatch_severity') == 'moderate']
        
        # Combine and limit
        all_concerns = major_mismatches + moderate_mismatches
        return all_concerns[:limit]
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert result to dictionary for serialization.
        
        Returns:
            Dictionary representation
        """
        return {
            'policy_id': self.policy.id,
            'policy_name': self.policy.name,
            'overall_score': self.overall_score,
            'feature_scores': self.feature_scores,
            'matches': self.matches,
            'mismatches': self.mismatches,
            'explanation': self.explanation,
            'insurance_type': self.insurance_type,
            'total_features_compared': self.total_features_compared,
            'compatibility_category': self.get_compatibility_category(),
            'recommendation_strength': self.get_recommendation_strength(),
            'top_matches': self.get_top_matches(),
            'major_concerns': self.get_major_concerns()
        }