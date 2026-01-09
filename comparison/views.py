from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, Http404
from django.views.decorators.http import require_http_methods
from django.contrib import messages
from django.urls import reverse
from django.core.paginator import Paginator
from django.db.models import Q
from .models import ComparisonSession, ComparisonResult
from .engine import PolicyComparisonEngine
from policies.models import PolicyCategory
import json
import logging

logger = logging.getLogger(__name__)


def enhanced_results_view(request, session_key):
    """
    Display enhanced comparison results with survey context and personalized recommendations.
    """
    try:
        # Get comparison session
        session = get_object_or_404(ComparisonSession, session_key=session_key)
        
        # Check if session has results
        if not session.results.exists():
            messages.error(request, 'No comparison results found for this session.')
            return redirect('surveys:category_selection')
        
        # Get results ordered by rank
        results = session.results.select_related('policy', 'policy__organization').order_by('rank')
        
        # Check if this is a survey-based comparison
        is_survey_based = session.is_survey_based_comparison()
        
        # Get survey context if available
        survey_context = {}
        if is_survey_based:
            survey_context = {
                'user_profile': session.user_profile,
                'completion_percentage': float(session.survey_completion_percentage),
                'responses_count': session.survey_responses_count
            }
        
        # Generate recommendation categories
        recommendations = _generate_recommendation_categories(results, survey_context)
        
        # Get comparison insights
        insights = _generate_comparison_insights(results, session, survey_context)
        
        # Prepare context
        context = {
            'session': session,
            'session_key': session_key,
            'category': session.category,
            'results': results,
            'is_survey_based': is_survey_based,
            'survey_context': survey_context,
            'recommendations': recommendations,
            'insights': insights,
            'total_policies': results.count(),
            'best_match': results.first() if results.exists() else None,
        }
        
        return render(request, 'comparison/enhanced_results.html', context)
        
    except Exception as e:
        logger.error(f"Error displaying enhanced results for session {session_key}: {str(e)}")
        messages.error(request, 'An error occurred while loading comparison results.')
        return redirect('surveys:category_selection')


def policy_detail_modal_view(request, session_key, policy_id):
    """
    AJAX view to get detailed policy information for modal display.
    """
    try:
        session = get_object_or_404(ComparisonSession, session_key=session_key)
        result = get_object_or_404(
            ComparisonResult, 
            session=session, 
            policy_id=policy_id
        )
        
        # Get survey context if available
        survey_context = {}
        if session.is_survey_based_comparison():
            survey_context = {
                'user_profile': session.user_profile,
                'personalization_factors': result.criteria_scores.get('survey_enhancements', {}).get('personalization_factors', [])
            }
        
        # Prepare detailed policy data
        policy_data = {
            'id': result.policy.id,
            'name': result.policy.name,
            'organization': result.policy.organization.name,
            'overall_score': result.overall_score,
            'rank': result.rank,
            'match_percentage': round(result.overall_score, 1),
            'criteria_scores': result.criteria_scores,
            'pros': result.pros,
            'cons': result.cons,
            'recommendation_reason': result.recommendation_reason,
            'survey_context': survey_context,
            'policy_details': _get_policy_details(result.policy),
        }
        
        return JsonResponse({
            'success': True,
            'policy': policy_data
        })
        
    except Exception as e:
        logger.error(f"Error getting policy detail for {policy_id}: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': 'Failed to load policy details'
        }, status=500)


def comparison_matrix_view(request, session_key):
    """
    Display side-by-side comparison matrix emphasizing survey criteria.
    """
    try:
        session = get_object_or_404(ComparisonSession, session_key=session_key)
        results = session.results.select_related('policy', 'policy__organization').order_by('rank')
        
        if not results.exists():
            messages.error(request, 'No comparison results found.')
            return redirect('surveys:category_selection')
        
        # Get top policies for matrix (limit to 4 for readability)
        top_results = results[:4]
        
        # Build comparison matrix data
        matrix_data = _build_comparison_matrix(top_results, session)
        
        context = {
            'session': session,
            'session_key': session_key,
            'results': top_results,
            'matrix_data': matrix_data,
            'is_survey_based': session.is_survey_based_comparison(),
        }
        
        return render(request, 'comparison/comparison_matrix.html', context)
        
    except Exception as e:
        logger.error(f"Error displaying comparison matrix for session {session_key}: {str(e)}")
        messages.error(request, 'An error occurred while loading comparison matrix.')
        return redirect('surveys:category_selection')


@require_http_methods(["POST"])
def update_criteria_weights_ajax(request, session_key):
    """
    AJAX endpoint to update criteria weights and regenerate results.
    """
    try:
        session = get_object_or_404(ComparisonSession, session_key=session_key)
        
        data = json.loads(request.body)
        new_weights = data.get('weights', {})
        
        if not new_weights:
            return JsonResponse({
                'success': False,
                'error': 'No weights provided'
            }, status=400)
        
        # Update session criteria with new weights
        updated_criteria = session.criteria.copy()
        updated_criteria['weights'] = new_weights
        session.criteria = updated_criteria
        session.save()
        
        # Regenerate comparison results
        engine = PolicyComparisonEngine(session.category.slug)
        policy_ids = list(session.policies.values_list('id', flat=True))
        
        # Include survey context if available
        survey_context = None
        if session.is_survey_based_comparison():
            survey_context = {
                'user_profile': session.user_profile,
                'filters': session.criteria.get('filters', {}),
            }
        
        comparison_result = engine.compare_policies(
            policy_ids=policy_ids,
            user_criteria=updated_criteria,
            user=session.user,
            session_key=session_key,
            survey_context=survey_context
        )
        
        if comparison_result.get('success'):
            return JsonResponse({
                'success': True,
                'message': 'Criteria updated and results regenerated',
                'redirect_url': reverse('comparison:enhanced_results', kwargs={'session_key': session_key})
            })
        else:
            return JsonResponse({
                'success': False,
                'error': comparison_result.get('error', 'Failed to regenerate results')
            }, status=500)
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON data'
        }, status=400)
    except Exception as e:
        logger.error(f"Error updating criteria weights: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': 'An error occurred while updating criteria'
        }, status=500)


def _generate_recommendation_categories(results, survey_context):
    """
    Generate categorized recommendations (best match, best value, most popular).
    """
    if not results:
        return {}
    
    recommendations = {}
    
    # Best Match - highest overall score
    best_match = results.first()
    recommendations['best_match'] = {
        'policy': best_match,
        'reason': 'Highest overall match based on your criteria',
        'highlight': f"{best_match.overall_score:.1f}% match"
    }
    
    # Best Value - highest value score
    best_value = max(results, key=lambda r: r.criteria_scores.get('value_score', 0))
    recommendations['best_value'] = {
        'policy': best_value,
        'reason': 'Best value for money based on coverage vs premium',
        'highlight': f"Value score: {best_value.criteria_scores.get('value_score', 0):.1f}"
    }
    
    # Most Popular - highest review score
    most_popular = max(results, key=lambda r: r.criteria_scores.get('review_score', 0))
    recommendations['most_popular'] = {
        'policy': most_popular,
        'reason': 'Highest customer satisfaction ratings',
        'highlight': f"Review score: {most_popular.criteria_scores.get('review_score', 0):.1f}"
    }
    
    # Survey-specific recommendations
    if survey_context and survey_context.get('user_profile'):
        user_profile = survey_context['user_profile']
        priorities = user_profile.get('priorities', {})
        
        # Find policy that best matches top priority
        if priorities:
            top_priority = max(priorities.items(), key=lambda x: x[1] if isinstance(x[1], (int, float)) else 0)
            if top_priority:
                priority_field, priority_value = top_priority
                # Find policy with best performance in this area
                priority_best = max(
                    results, 
                    key=lambda r: r.criteria_scores.get(priority_field, {}).get('score', 0)
                )
                recommendations['priority_match'] = {
                    'policy': priority_best,
                    'reason': f'Best match for your top priority: {priority_field.replace("_", " ").title()}',
                    'highlight': f"Priority score: {priority_best.criteria_scores.get(priority_field, {}).get('score', 0):.1f}"
                }
    
    return recommendations


def _generate_comparison_insights(results, session, survey_context):
    """
    Generate insights about the comparison results.
    """
    insights = []
    
    if not results:
        return insights
    
    # Score distribution insight
    scores = [r.overall_score for r in results]
    score_range = max(scores) - min(scores)
    
    if score_range < 10:
        insights.append({
            'type': 'info',
            'title': 'Close Competition',
            'message': f'All policies scored within {score_range:.1f} points of each other, indicating similar suitability.'
        })
    elif score_range > 30:
        insights.append({
            'type': 'warning',
            'title': 'Wide Score Range',
            'message': f'Scores vary by {score_range:.1f} points. Consider focusing on the top-ranked options.'
        })
    
    # Survey-specific insights
    if survey_context and survey_context.get('user_profile'):
        user_profile = survey_context['user_profile']
        
        # Confidence level insight
        confidence_levels = user_profile.get('confidence_levels', {})
        if confidence_levels:
            avg_confidence = sum(confidence_levels.values()) / len(confidence_levels)
            if avg_confidence < 3:
                insights.append({
                    'type': 'tip',
                    'title': 'Consider Additional Research',
                    'message': 'Your survey responses showed lower confidence levels. Consider researching specific features before deciding.'
                })
            elif avg_confidence >= 4:
                insights.append({
                    'type': 'success',
                    'title': 'Strong Preferences Identified',
                    'message': 'Your confident responses helped create highly personalized recommendations.'
                })
        
        # Budget insight
        user_values = user_profile.get('user_values', {})
        if 'monthly_budget' in user_values:
            budget = user_values['monthly_budget']
            if isinstance(budget, (int, float)):
                within_budget = [r for r in results if r.policy.base_premium <= budget]
                if len(within_budget) < len(results) / 2:
                    insights.append({
                        'type': 'warning',
                        'title': 'Budget Considerations',
                        'message': f'Only {len(within_budget)} of {len(results)} policies fit your R{budget:.0f} budget.'
                    })
    
    # Category-specific insights
    if session.category.slug == 'health':
        insights.extend(_get_health_specific_insights(results, survey_context))
    elif session.category.slug == 'funeral':
        insights.extend(_get_funeral_specific_insights(results, survey_context))
    
    return insights


def _get_health_specific_insights(results, survey_context):
    """Generate health insurance specific insights."""
    insights = []
    
    # Check for chronic medication coverage
    chronic_covered = sum(1 for r in results if getattr(r.policy, 'chronic_medication_covered', False))
    if chronic_covered > 0:
        insights.append({
            'type': 'info',
            'title': 'Chronic Medication Coverage',
            'message': f'{chronic_covered} of {len(results)} policies include chronic medication coverage.'
        })
    
    return insights


def _get_funeral_specific_insights(results, survey_context):
    """Generate funeral insurance specific insights."""
    insights = []
    
    # Check for repatriation coverage
    repatriation_covered = sum(1 for r in results if getattr(r.policy, 'repatriation_covered', False))
    if repatriation_covered > 0:
        insights.append({
            'type': 'info',
            'title': 'Repatriation Services',
            'message': f'{repatriation_covered} of {len(results)} policies include repatriation services.'
        })
    
    return insights


def _build_comparison_matrix(results, session):
    """
    Build comparison matrix data structure for side-by-side comparison.
    """
    matrix_data = {
        'policies': [],
        'criteria': [],
        'comparison_rows': []
    }
    
    # Get policies
    policies = [r.policy for r in results]
    matrix_data['policies'] = policies
    
    # Get criteria from first result (all should have same criteria)
    if results:
        first_result = results[0]
        criteria_scores = first_result.criteria_scores
        
        # Build criteria list
        for field_name, score_data in criteria_scores.items():
            if isinstance(score_data, dict) and 'score' in score_data:
                matrix_data['criteria'].append({
                    'field_name': field_name,
                    'display_name': field_name.replace('_', ' ').title(),
                    'weight': score_data.get('weight', 0)
                })
    
    # Build comparison rows
    for criterion in matrix_data['criteria']:
        field_name = criterion['field_name']
        row = {
            'criterion': criterion,
            'values': []
        }
        
        for result in results:
            score_data = result.criteria_scores.get(field_name, {})
            row['values'].append({
                'score': score_data.get('score', 0),
                'display_value': _get_display_value(result.policy, field_name),
                'is_best': False  # Will be set after comparing all values
            })
        
        # Mark best value in this row
        if row['values']:
            best_score = max(row['values'], key=lambda x: x['score'])['score']
            for value in row['values']:
                if value['score'] == best_score:
                    value['is_best'] = True
                    break
        
        matrix_data['comparison_rows'].append(row)
    
    return matrix_data


def _get_display_value(policy, field_name):
    """
    Get human-readable display value for a policy field.
    """
    value = getattr(policy, field_name, None)
    
    if value is None:
        return 'N/A'
    
    # Format specific field types
    if field_name in ['base_premium', 'coverage_amount']:
        return f"R{value:,.0f}"
    elif field_name in ['waiting_period_days']:
        return f"{value} days"
    elif isinstance(value, bool):
        return 'Yes' if value else 'No'
    elif isinstance(value, (int, float)):
        return f"{value:,.0f}"
    
    return str(value)


def _get_policy_details(policy):
    """
    Get detailed policy information for modal display.
    """
    details = {
        'basic_info': {
            'Premium': f"R{policy.base_premium:,.0f}/month",
            'Coverage': f"R{policy.coverage_amount:,.0f}",
            'Waiting Period': f"{policy.waiting_period_days} days",
            'Age Range': f"{policy.minimum_age} - {policy.maximum_age} years"
        },
        'features': [],
        'benefits': []
    }
    
    # Add category-specific details
    if hasattr(policy, 'chronic_medication_covered'):
        details['features'].append(f"Chronic Medication: {'Covered' if policy.chronic_medication_covered else 'Not Covered'}")
    
    if hasattr(policy, 'includes_dental_cover'):
        details['features'].append(f"Dental Cover: {'Included' if policy.includes_dental_cover else 'Not Included'}")
    
    if hasattr(policy, 'includes_optical_cover'):
        details['features'].append(f"Optical Cover: {'Included' if policy.includes_optical_cover else 'Not Included'}")
    
    if hasattr(policy, 'repatriation_covered'):
        details['features'].append(f"Repatriation: {'Covered' if policy.repatriation_covered else 'Not Covered'}")
    
    return details