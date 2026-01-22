"""
Match Explanation Generator for Feature-Based Policy Comparisons.
Generates human-readable explanations for policy matches and recommendations.
"""

from typing import List, Dict, Any, Optional
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)


class MatchExplanationGenerator:
    """
    Generates detailed explanations for policy matches and comparisons.
    """
    
    def __init__(self, insurance_type: str):
        """
        Initialize explanation generator.
        
        Args:
            insurance_type: Type of insurance ('HEALTH' or 'FUNERAL')
        """
        self.insurance_type = insurance_type.upper()
    
    def generate_detailed_explanation(
        self,
        policy,
        compatibility_data: Dict[str, Any],
        user_preferences: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate detailed explanation for a policy match.
        
        Args:
            policy: BasePolicy instance
            compatibility_data: Result from FeatureMatchingEngine
            user_preferences: User preferences from survey
            
        Returns:
            Dictionary with detailed explanations
        """
        try:
            overall_score = compatibility_data['overall_score']
            matches = compatibility_data['matches']
            mismatches = compatibility_data['mismatches']
            
            explanation = {
                'overall_assessment': self._generate_overall_assessment(overall_score),
                'why_recommended': self._generate_recommendation_reasons(matches, overall_score),
                'potential_concerns': self._generate_concern_explanations(mismatches),
                'feature_breakdown': self._generate_feature_breakdown(compatibility_data),
                'personalized_insights': self._generate_personalized_insights(
                    policy, matches, mismatches, user_preferences
                ),
                'comparison_context': self._generate_comparison_context(overall_score),
                'next_steps': self._generate_next_steps(overall_score, matches, mismatches)
            }
            
            return explanation
            
        except Exception as e:
            logger.error(f"Error generating detailed explanation: {str(e)}")
            return {'error': f'Failed to generate explanation: {str(e)}'}
    
    def _generate_overall_assessment(self, overall_score: float) -> Dict[str, Any]:
        """
        Generate overall assessment based on compatibility score.
        
        Args:
            overall_score: Overall compatibility score (0.0 to 1.0)
            
        Returns:
            Overall assessment dictionary
        """
        score_percentage = overall_score * 100
        
        if overall_score >= 0.9:
            category = "Excellent Match"
            description = "This policy aligns exceptionally well with your stated preferences and requirements."
            confidence = "Very High"
        elif overall_score >= 0.75:
            category = "Very Good Match"
            description = "This policy meets most of your important requirements with only minor gaps."
            confidence = "High"
        elif overall_score >= 0.6:
            category = "Good Match"
            description = "This policy covers your key needs but may not meet all your preferences."
            confidence = "Moderate"
        elif overall_score >= 0.4:
            category = "Partial Match"
            description = "This policy meets some of your requirements but has several areas that don't align with your preferences."
            confidence = "Low"
        else:
            category = "Poor Match"
            description = "This policy does not align well with your stated preferences and requirements."
            confidence = "Very Low"
        
        return {
            'category': category,
            'score_percentage': round(score_percentage, 1),
            'description': description,
            'confidence_level': confidence,
            'recommendation_strength': self._get_recommendation_strength(overall_score)
        }
    
    def _generate_recommendation_reasons(self, matches: List[Dict], overall_score: float) -> List[str]:
        """
        Generate reasons why this policy is recommended.
        
        Args:
            matches: List of matching features
            overall_score: Overall compatibility score
            
        Returns:
            List of recommendation reasons
        """
        reasons = []
        
        if not matches:
            if overall_score >= 0.5:
                reasons.append("While specific feature matches are limited, this policy shows overall compatibility with your needs.")
            return reasons
        
        # Group matches by quality
        excellent_matches = [m for m in matches if m.get('match_type') == 'excellent']
        good_matches = [m for m in matches if m.get('match_type') == 'good']
        
        # Generate reasons based on excellent matches
        if excellent_matches:
            if len(excellent_matches) == 1:
                feature = excellent_matches[0]['feature']
                reasons.append(f"Perfect alignment with your {feature.lower()} requirements.")
            else:
                features = [m['feature'] for m in excellent_matches[:3]]
                if len(features) <= 2:
                    reasons.append(f"Perfect match for {' and '.join(features).lower()}.")
                else:
                    reasons.append(f"Perfect match for {', '.join(features[:-1]).lower()}, and {features[-1].lower()}.")
        
        # Add reasons for good matches
        if good_matches:
            if len(good_matches) == 1:
                feature = good_matches[0]['feature']
                reasons.append(f"Strong compatibility with your {feature.lower()} preferences.")
            elif len(good_matches) <= 3:
                features = [m['feature'] for m in good_matches]
                reasons.append(f"Good alignment with {', '.join(features).lower()}.")
            else:
                reasons.append(f"Good alignment with {len(good_matches)} of your key requirements.")
        
        # Add insurance-type specific reasons
        if self.insurance_type == 'HEALTH':
            health_reasons = self._generate_health_specific_reasons(matches)
            reasons.extend(health_reasons)
        elif self.insurance_type == 'FUNERAL':
            funeral_reasons = self._generate_funeral_specific_reasons(matches)
            reasons.extend(funeral_reasons)
        
        return reasons[:5]  # Limit to top 5 reasons
    
    def _generate_concern_explanations(self, mismatches: List[Dict]) -> List[Dict[str, Any]]:
        """
        Generate explanations for potential concerns.
        
        Args:
            mismatches: List of mismatching features
            
        Returns:
            List of concern explanations
        """
        concerns = []
        
        for mismatch in mismatches:
            severity = mismatch.get('mismatch_severity', 'moderate')
            feature = mismatch['feature']
            user_pref = mismatch['user_preference']
            policy_value = mismatch['policy_value']
            
            concern = {
                'feature': feature,
                'severity': severity,
                'explanation': self._generate_mismatch_explanation(
                    feature, user_pref, policy_value, severity
                ),
                'impact': self._assess_mismatch_impact(feature, severity),
                'mitigation': self._suggest_mitigation(feature, user_pref, policy_value)
            }
            
            concerns.append(concern)
        
        return concerns
    
    def _generate_mismatch_explanation(
        self,
        feature: str,
        user_pref: str,
        policy_value: str,
        severity: str
    ) -> str:
        """
        Generate explanation for a specific mismatch.
        
        Args:
            feature: Feature name
            user_pref: User preference
            policy_value: Policy value
            severity: Mismatch severity
            
        Returns:
            Explanation string
        """
        if severity == 'major':
            return f"This policy's {feature.lower()} ({policy_value}) significantly differs from your preference ({user_pref})."
        else:
            return f"This policy's {feature.lower()} ({policy_value}) doesn't fully match your preference ({user_pref})."
    
    def _assess_mismatch_impact(self, feature: str, severity: str) -> str:
        """
        Assess the impact of a feature mismatch.
        
        Args:
            feature: Feature name
            severity: Mismatch severity
            
        Returns:
            Impact assessment string
        """
        high_impact_features = [
            'Annual Limit per Member',
            'Coverage Amount',
            'Monthly Household Income Requirement',
        ]
        
        if feature in high_impact_features:
            if severity == 'major':
                return "High impact - this could significantly affect your coverage or eligibility."
            else:
                return "Moderate impact - this may affect your coverage or costs."
        else:
            if severity == 'major':
                return "Moderate impact - this affects an important aspect of your coverage."
            else:
                return "Low impact - this is a minor difference that may not significantly affect you."
    
    def _suggest_mitigation(self, feature: str, user_pref: str, policy_value: str) -> Optional[str]:
        """
        Suggest ways to mitigate a mismatch.
        
        Args:
            feature: Feature name
            user_pref: User preference
            policy_value: Policy value
            
        Returns:
            Mitigation suggestion or None
        """
        mitigation_suggestions = {
            'Annual Limit per Member': "Consider if the policy limit meets your minimum needs, or look for supplementary coverage.",
            'Coverage Amount': "Evaluate if this coverage amount provides adequate financial protection for your situation.",
            'Monthly Household Income Requirement': "Verify that you meet the income requirements for this policy.",
            'In-Hospital Benefits': "Consider the importance of in-hospital coverage for your health needs.",
            'Out-of-Hospital Benefits': "Evaluate how often you might need out-of-hospital medical services.",
            'Chronic Medication Coverage': "If you need chronic medication, this could be a significant gap in coverage."
        }
        
        return mitigation_suggestions.get(feature)
    
    def _generate_feature_breakdown(self, compatibility_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate detailed breakdown of feature performance.
        
        Args:
            compatibility_data: Compatibility data from matching engine
            
        Returns:
            Feature breakdown dictionary
        """
        feature_scores = compatibility_data.get('feature_scores', {})
        
        breakdown = {
            'total_features_evaluated': len(feature_scores),
            'feature_performance': {},
            'score_distribution': {
                'excellent': 0,  # >= 0.9
                'good': 0,       # 0.7-0.89
                'fair': 0,       # 0.5-0.69
                'poor': 0        # < 0.5
            }
        }
        
        for feature_name, score in feature_scores.items():
            # Categorize score
            if score >= 0.9:
                category = 'excellent'
                breakdown['score_distribution']['excellent'] += 1
            elif score >= 0.7:
                category = 'good'
                breakdown['score_distribution']['good'] += 1
            elif score >= 0.5:
                category = 'fair'
                breakdown['score_distribution']['fair'] += 1
            else:
                category = 'poor'
                breakdown['score_distribution']['poor'] += 1
            
            breakdown['feature_performance'][feature_name] = {
                'score': score,
                'category': category,
                'percentage': round(score * 100, 1)
            }
        
        return breakdown
    
    def _generate_personalized_insights(
        self,
        policy,
        matches: List[Dict],
        mismatches: List[Dict],
        user_preferences: Dict[str, Any]
    ) -> List[str]:
        """
        Generate personalized insights based on user preferences.
        
        Args:
            policy: Policy instance
            matches: Matching features
            mismatches: Mismatching features
            user_preferences: User preferences
            
        Returns:
            List of personalized insights
        """
        insights = []
        
        # Analyze user priorities vs policy strengths
        if self.insurance_type == 'HEALTH':
            insights.extend(self._generate_health_insights(policy, matches, mismatches, user_preferences))
        elif self.insurance_type == 'FUNERAL':
            insights.extend(self._generate_funeral_insights(policy, matches, mismatches, user_preferences))
        
        # General insights
        if len(matches) > len(mismatches):
            insights.append("This policy aligns well with most of your stated preferences.")
        elif len(mismatches) > len(matches):
            insights.append("This policy has several areas that don't match your preferences - consider if the benefits outweigh the drawbacks.")
        
        return insights[:4]  # Limit to top 4 insights
    
    def _generate_health_insights(
        self,
        policy,
        matches: List[Dict],
        mismatches: List[Dict],
        user_preferences: Dict[str, Any]
    ) -> List[str]:
        """
        Generate health insurance specific insights.
        
        Args:
            policy: Policy instance
            matches: Matching features
            mismatches: Mismatching features
            user_preferences: User preferences
            
        Returns:
            List of health-specific insights
        """
        insights = []
        
        # Check annual family limit preferences
        family_limit_pref = user_preferences.get('preferred_annual_limit_per_family')
        if family_limit_pref:
            family_limit_match = any(m['feature'] == 'Annual Limit per Family' for m in matches)
            if family_limit_match:
                insights.append(f"The annual family limit meets your preference of R{family_limit_pref:,.0f}.")
            else:
                family_limit_mismatch = any(m['feature'] == 'Annual Limit per Family' for m in mismatches)
                if family_limit_mismatch:
                    insights.append("The annual family limit may not meet your preferred amount.")
        
        # Check medical aid status compatibility
        currently_on_aid = user_preferences.get('currently_on_medical_aid')
        if currently_on_aid is not None:
            aid_match = any(m['feature'] == 'Current Medical Aid Status' for m in matches)
            if aid_match:
                if currently_on_aid:
                    insights.append("This policy is compatible with your current medical aid status.")
                else:
                    insights.append("This policy is suitable for someone not currently on medical aid.")
        
        # Check ambulance coverage needs
        wants_ambulance = user_preferences.get('wants_ambulance_coverage')
        if wants_ambulance:
            ambulance_match = any(m['feature'] == 'Ambulance Coverage' for m in matches)
            if ambulance_match:
                insights.append("Great news - this policy includes ambulance coverage as you requested.")
            else:
                ambulance_mismatch = any(m['feature'] == 'Ambulance Coverage' for m in mismatches)
                if ambulance_mismatch:
                    insights.append("Important: This policy may not include ambulance coverage, which you indicated as needed.")
        
        # Check chronic medication needs
        chronic_needed = user_preferences.get('needs_chronic_medication')
        if chronic_needed:
            chronic_match = any(m['feature'] == 'Chronic Medication Coverage' for m in matches)
            if chronic_match:
                insights.append("Great news - this policy covers chronic medication as you requested.")
            else:
                chronic_mismatch = any(m['feature'] == 'Chronic Medication Coverage' for m in mismatches)
                if chronic_mismatch:
                    insights.append("Important: This policy may not cover chronic medication, which you indicated as needed.")
        
        # Check hospital benefits
        in_hospital_wanted = user_preferences.get('wants_in_hospital_benefit')
        out_hospital_wanted = user_preferences.get('wants_out_hospital_benefit')
        
        if in_hospital_wanted and out_hospital_wanted:
            both_match = (
                any(m['feature'] == 'In-Hospital Benefits' for m in matches) and
                any(m['feature'] == 'Out-of-Hospital Benefits' for m in matches)
            )
            if both_match:
                insights.append("This policy provides both in-hospital and out-of-hospital benefits as you wanted.")
        
        return insights
    
    def _generate_funeral_insights(
        self,
        policy,
        matches: List[Dict],
        mismatches: List[Dict],
        user_preferences: Dict[str, Any]
    ) -> List[str]:
        """
        Generate funeral insurance specific insights.
        
        Args:
            policy: Policy instance
            matches: Matching features
            mismatches: Mismatching features
            user_preferences: User preferences
            
        Returns:
            List of funeral-specific insights
        """
        insights = []
        
        # Check coverage amount adequacy
        preferred_amount = user_preferences.get('preferred_cover_amount')
        if preferred_amount:
            amount_match = any(m['feature'] == 'Coverage Amount' for m in matches)
            if amount_match:
                insights.append(f"The coverage amount meets your preference of R{preferred_amount:,.2f}.")
            else:
                insights.append("Consider whether the coverage amount provides adequate financial protection.")
        
        # Check income requirements
        user_income = user_preferences.get('net_income')
        if user_income:
            income_match = any(m['feature'] == 'Monthly Net Income Requirement' for m in matches)
            if income_match:
                insights.append("Your income meets the policy requirements.")
            else:
                insights.append("Please verify that your income meets this policy's requirements.")
        
        return insights
    
    def _generate_comparison_context(self, overall_score: float) -> Dict[str, Any]:
        """
        Generate context for how this score compares to typical results.
        
        Args:
            overall_score: Overall compatibility score
            
        Returns:
            Comparison context dictionary
        """
        context = {
            'score_interpretation': self._interpret_score(overall_score),
            'typical_range': self._get_typical_score_range(),
            'relative_performance': self._assess_relative_performance(overall_score)
        }
        
        return context
    
    def _generate_next_steps(
        self,
        overall_score: float,
        matches: List[Dict],
        mismatches: List[Dict]
    ) -> List[str]:
        """
        Generate suggested next steps based on the match quality.
        
        Args:
            overall_score: Overall compatibility score
            matches: Matching features
            mismatches: Mismatching features
            
        Returns:
            List of suggested next steps
        """
        next_steps = []
        
        if overall_score >= 0.8:
            next_steps.append("This is a strong match - consider requesting a detailed quote.")
            next_steps.append("Contact the insurer to discuss specific terms and conditions.")
        elif overall_score >= 0.6:
            next_steps.append("This policy shows good potential - review the areas of concern carefully.")
            next_steps.append("Consider speaking with an agent to address any questions about mismatched features.")
        elif overall_score >= 0.4:
            next_steps.append("This policy has mixed compatibility - weigh the pros and cons carefully.")
            next_steps.append("Consider comparing with other options before making a decision.")
        else:
            next_steps.append("This policy may not be the best fit - consider exploring other options.")
            next_steps.append("If interested, discuss with the insurer how the gaps might be addressed.")
        
        # Add specific steps based on mismatches
        if mismatches:
            major_mismatches = [m for m in mismatches if m.get('mismatch_severity') == 'major']
            if major_mismatches:
                next_steps.append("Pay special attention to the major mismatches identified.")
        
        return next_steps[:4]  # Limit to top 4 steps
    
    def _generate_health_specific_reasons(self, matches: List[Dict]) -> List[str]:
        """Generate health insurance specific recommendation reasons."""
        reasons = []
        
        # Check for important health features
        important_health_features = [
            'Annual Limit per Family',
            'Current Medical Aid Status',
            'Ambulance Coverage',
            'Chronic Medication Coverage',
            'In-Hospital Benefits',
            'Out-of-Hospital Benefits'
        ]
        
        matched_important = [m for m in matches if m['feature'] in important_health_features]
        if len(matched_important) >= 2:
            features = [m['feature'] for m in matched_important]
            reasons.append(f"Covers key health benefits: {', '.join(features).lower()}.")
        
        # Specific feature highlights
        if any(m['feature'] == 'Annual Limit per Family' for m in matches):
            reasons.append("Annual family limit meets your requirements.")
        
        if any(m['feature'] == 'Ambulance Coverage' for m in matches):
            reasons.append("Includes ambulance coverage as requested.")
        
        return reasons
    
    def _generate_funeral_specific_reasons(self, matches: List[Dict]) -> List[str]:
        """Generate funeral insurance specific recommendation reasons."""
        reasons = []
        
        # Check for coverage amount match
        coverage_match = any(m['feature'] == 'Coverage Amount' for m in matches)
        if coverage_match:
            reasons.append("Provides the coverage amount you're looking for.")
        
        return reasons
    
    def _get_recommendation_strength(self, overall_score: float) -> str:
        """Get recommendation strength based on score."""
        if overall_score >= 0.9:
            return "Highly Recommended"
        elif overall_score >= 0.75:
            return "Strongly Recommended"
        elif overall_score >= 0.6:
            return "Recommended"
        elif overall_score >= 0.4:
            return "Consider with Caution"
        else:
            return "Not Recommended"
    
    def _interpret_score(self, score: float) -> str:
        """Interpret what the score means."""
        percentage = score * 100
        if percentage >= 90:
            return f"Exceptional compatibility ({percentage:.1f}%) - this policy aligns very well with your needs."
        elif percentage >= 75:
            return f"High compatibility ({percentage:.1f}%) - this policy meets most of your requirements."
        elif percentage >= 60:
            return f"Good compatibility ({percentage:.1f}%) - this policy covers your main needs."
        elif percentage >= 40:
            return f"Moderate compatibility ({percentage:.1f}%) - this policy has some alignment with your needs."
        else:
            return f"Low compatibility ({percentage:.1f}%) - this policy doesn't align well with your preferences."
    
    def _get_typical_score_range(self) -> Dict[str, float]:
        """Get typical score ranges for context."""
        return {
            'excellent': 0.9,
            'very_good': 0.75,
            'good': 0.6,
            'fair': 0.4,
            'poor': 0.0
        }
    
    def _assess_relative_performance(self, score: float) -> str:
        """Assess how this score performs relative to typical results."""
        if score >= 0.9:
            return "This is an exceptionally high compatibility score."
        elif score >= 0.75:
            return "This is a very good compatibility score."
        elif score >= 0.6:
            return "This is a solid compatibility score."
        elif score >= 0.4:
            return "This is a moderate compatibility score."
        else:
            return "This is a below-average compatibility score."