from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, Http404
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages
from django.urls import reverse
from django.core.paginator import Paginator
from django.db.models import Q
from decimal import Decimal
from .models import ComparisonSession, ComparisonResult, FeatureComparisonResult
from .engine import PolicyComparisonEngine
from .feature_comparison_manager import FeatureComparisonManager
from .ranking_utils import ComparisonResultAnalyzer
from policies.models import PolicyCategory
from simple_surveys.models import SimpleSurvey
import json
import logging

logger = logging.getLogger(__name__)


def feature_comparison_results_view(request, survey_id):
    """
    Display feature-based comparison results for a SimpleSurvey with filtering and sorting.
    """
    try:
        # Get the survey
        survey = get_object_or_404(SimpleSurvey, id=survey_id)
        
        # Check if survey is complete
        if not survey.is_complete():
            messages.error(request, 'Survey must be completed before viewing results.')
            return redirect('simple_surveys:survey_form', insurance_type=survey.insurance_type.lower())
        
        # Get or generate comparison results
        comparison_manager = FeatureComparisonManager()
        all_results = comparison_manager.compare_policies_for_survey(survey)
        
        if not all_results:
            messages.warning(request, 'No matching policies found for your preferences.')
            return redirect('simple_surveys:survey_form', insurance_type=survey.insurance_type.lower())
        
        # Apply filtering and sorting
        filtered_results = _apply_feature_filters(request, all_results, survey)
        sorted_results = _apply_sorting(request, filtered_results)
        
        # Pagination
        page_size = int(request.GET.get('page_size', 10))
        paginator = Paginator(sorted_results, page_size)
        page_number = request.GET.get('page')
        results_page = paginator.get_page(page_number)
        
        # Get analysis
        analyzer = ComparisonResultAnalyzer()
        analysis = analyzer.analyze_survey_results(survey, all_results)
        
        # Get available filter options
        filter_options = _get_filter_options(all_results, survey)
        
        # Prepare context
        context = {
            'survey': survey,
            'results': results_page,
            'all_results': all_results,
            'total_results': len(all_results),
            'filtered_count': len(sorted_results),
            'analysis': analysis,
            'best_match': all_results[0] if all_results else None,
            'insurance_type': survey.get_insurance_type_display(),
            'user_preferences': survey.get_preferences_dict(),
            'filter_options': filter_options,
            'current_filters': _get_current_filters(request),
            'current_sort': request.GET.get('sort', 'compatibility_rank'),
            'page_sizes': [5, 10, 20, 50],
            'current_page_size': page_size,
        }
        
        return render(request, 'comparison/feature_results.html', context)
        
    except Exception as e:
        logger.error(f"Error displaying feature comparison results for survey {survey_id}: {str(e)}")
        messages.error(request, 'An error occurred while loading comparison results.')
        return redirect('simple_surveys:category_selection')


def feature_comparison_detail_view(request, survey_id, result_id):
    """
    Display detailed view of a specific feature comparison result.
    """
    try:
        survey = get_object_or_404(SimpleSurvey, id=survey_id)
        result = get_object_or_404(
            FeatureComparisonResult, 
            id=result_id, 
            survey=survey
        )
        
        # Get all results for context
        all_results = FeatureComparisonResult.objects.filter(
            survey=survey
        ).order_by('compatibility_rank')
        
        # Get detailed feature analysis
        feature_analysis = {}
        for feature_name, score_data in result.feature_scores.items():
            if isinstance(score_data, dict):
                feature_analysis[feature_name] = {
                    'display_name': feature_name.replace('_', ' ').title(),
                    'score': score_data.get('score', 0),
                    'user_preference': score_data.get('user_preference'),
                    'policy_value': score_data.get('policy_value'),
                    'explanation': score_data.get('explanation', '')
                }
        
        context = {
            'survey': survey,
            'result': result,
            'all_results': all_results,
            'feature_analysis': feature_analysis,
            'user_preferences': survey.get_preferences_dict(),
        }
        
        return render(request, 'comparison/feature_result_detail.html', context)
        
    except Exception as e:
        logger.error(f"Error displaying feature comparison detail: {str(e)}")
        messages.error(request, 'An error occurred while loading result details.')
        return redirect('comparison:feature_results', survey_id=survey_id)


def feature_comparison_matrix_view(request, survey_id):
    """
    Display side-by-side feature comparison matrix for top policies.
    """
    try:
        survey = get_object_or_404(SimpleSurvey, id=survey_id)
        
        # Get top results (limit to 4 for readability)
        results = FeatureComparisonResult.objects.filter(
            survey=survey
        ).select_related('policy', 'policy__organization').order_by('compatibility_rank')[:4]
        
        if not results.exists():
            messages.error(request, 'No comparison results found.')
            return redirect('comparison:feature_results', survey_id=survey_id)
        
        # Build comparison matrix
        matrix_data = _build_feature_comparison_matrix(results, survey)
        
        context = {
            'survey': survey,
            'results': results,
            'matrix_data': matrix_data,
            'user_preferences': survey.get_preferences_dict(),
        }
        
        return render(request, 'comparison/feature_matrix.html', context)
        
    except Exception as e:
        logger.error(f"Error displaying feature comparison matrix: {str(e)}")
        messages.error(request, 'An error occurred while loading comparison matrix.')
        return redirect('comparison:feature_results', survey_id=survey_id)


@require_http_methods(["POST"])
@csrf_exempt
def regenerate_comparison_results_ajax(request, survey_id):
    """
    AJAX endpoint to regenerate comparison results for a survey.
    """
    try:
        survey = get_object_or_404(SimpleSurvey, id=survey_id)
        
        if not survey.is_complete():
            return JsonResponse({
                'success': False,
                'error': 'Survey must be completed before generating results'
            }, status=400)
        
        # Regenerate results
        comparison_manager = FeatureComparisonManager()
        results = comparison_manager.compare_policies_for_survey(
            survey, 
            force_regenerate=True
        )
        
        if results:
            return JsonResponse({
                'success': True,
                'message': f'Generated {len(results)} comparison results',
                'results_count': len(results),
                'best_match_score': float(results[0].overall_compatibility_score) if results else 0
            })
        else:
            return JsonResponse({
                'success': False,
                'error': 'No matching policies found for your preferences'
            }, status=404)
        
    except Exception as e:
        logger.error(f"Error regenerating comparison results: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': 'An error occurred while regenerating results'
        }, status=500)


def _build_feature_comparison_matrix(results, survey):
    """
    Build feature comparison matrix data for side-by-side comparison.
    
    Args:
        results: QuerySet of FeatureComparisonResult instances
        survey: SimpleSurvey instance
        
    Returns:
        Dictionary with matrix data structure
    """
    matrix_data = {
        'policies': [],
        'features': [],
        'comparison_rows': []
    }
    
    if not results:
        return matrix_data
    
    # Get policies
    policies = [r.policy for r in results]
    matrix_data['policies'] = policies
    
    # Get user preferences for comparison
    user_preferences = survey.get_preferences_dict()
    
    # Build feature list from first result
    first_result = results[0]
    feature_names = list(first_result.feature_scores.keys())
    
    for feature_name in feature_names:
        display_name = feature_name.replace('_', ' ').title()
        user_pref = user_preferences.get(feature_name)
        
        matrix_data['features'].append({
            'name': feature_name,
            'display_name': display_name,
            'user_preference': user_pref
        })
    
    # Build comparison rows
    for feature in matrix_data['features']:
        feature_name = feature['name']
        row = {
            'feature': feature,
            'values': []
        }
        
        for result in results:
            score_data = result.feature_scores.get(feature_name, {})
            policy_value = score_data.get('policy_value', 'N/A')
            score = score_data.get('score', 0)
            
            row['values'].append({
                'policy': result.policy,
                'value': policy_value,
                'score': score,
                'formatted_value': _format_feature_value(feature_name, policy_value),
                'matches_preference': score >= 0.8  # High match threshold
            })
        
        matrix_data['comparison_rows'].append(row)
    
    return matrix_data


def _format_feature_value(feature_name, value):
    """
    Format feature value for display in comparison matrix.
    
    Args:
        feature_name: Name of the feature
        value: Raw feature value
        
    Returns:
        Formatted string for display
    """
    if value is None or value == 'N/A':
        return 'N/A'
    
    # Format based on feature type
    if 'amount' in feature_name.lower() or 'limit' in feature_name.lower():
        if isinstance(value, (int, float)):
            return f"R{value:,.0f}"
    elif 'income' in feature_name.lower():
        if isinstance(value, (int, float)):
            return f"R{value:,.0f}/month"
    elif isinstance(value, bool):
        return 'Yes' if value else 'No'
    elif isinstance(value, (int, float)):
        return f"{value:,.0f}"
    
    return str(value)


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
@csrf_exempt
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


def _apply_feature_filters(request, results, survey):
    """
    Apply feature-based filters to comparison results.
    
    Args:
        request: HTTP request object with filter parameters
        results: List of FeatureComparisonResult objects
        survey: SimpleSurvey instance
        
    Returns:
        Filtered list of results
    """
    filtered_results = results.copy()
    
    # Compatibility score filter
    min_score = request.GET.get('min_score')
    if min_score:
        try:
            min_score = float(min_score)
            filtered_results = [r for r in filtered_results if r.overall_compatibility_score >= min_score]
        except ValueError:
            pass
    
    # Premium range filter
    min_premium = request.GET.get('min_premium')
    max_premium = request.GET.get('max_premium')
    if min_premium:
        try:
            min_premium = float(min_premium)
            filtered_results = [r for r in filtered_results if r.policy.base_premium >= min_premium]
        except (ValueError, AttributeError):
            pass
    if max_premium:
        try:
            max_premium = float(max_premium)
            filtered_results = [r for r in filtered_results if r.policy.base_premium <= max_premium]
        except (ValueError, AttributeError):
            pass
    
    # Coverage amount filter
    min_coverage = request.GET.get('min_coverage')
    if min_coverage:
        try:
            min_coverage = float(min_coverage)
            filtered_results = [r for r in filtered_results if r.policy.coverage_amount >= min_coverage]
        except (ValueError, AttributeError):
            pass
    
    # Insurance type specific filters
    if survey.insurance_type == 'HEALTH':
        filtered_results = _apply_health_filters(request, filtered_results)
    elif survey.insurance_type == 'FUNERAL':
        filtered_results = _apply_funeral_filters(request, filtered_results)
    
    # Organization filter
    organization = request.GET.get('organization')
    if organization:
        filtered_results = [r for r in filtered_results if r.policy.organization.name == organization]
    
    # Recommendation category filter
    recommendation_category = request.GET.get('recommendation_category')
    if recommendation_category:
        filtered_results = [r for r in filtered_results if r.recommendation_category == recommendation_category]
    
    return filtered_results


def _apply_health_filters(request, results):
    """
    Apply health insurance specific filters.
    
    Args:
        request: HTTP request object
        results: List of FeatureComparisonResult objects
        
    Returns:
        Filtered list of results
    """
    filtered_results = results.copy()
    
    # In-hospital benefit filter
    in_hospital_benefit = request.GET.get('in_hospital_benefit')
    if in_hospital_benefit == 'true':
        filtered_results = [r for r in filtered_results 
                          if r.policy.policy_features and r.policy.policy_features.in_hospital_benefit == True]
    elif in_hospital_benefit == 'false':
        filtered_results = [r for r in filtered_results 
                          if r.policy.policy_features and r.policy.policy_features.in_hospital_benefit == False]
    
    # Out-of-hospital benefit filter
    out_hospital_benefit = request.GET.get('out_hospital_benefit')
    if out_hospital_benefit == 'true':
        filtered_results = [r for r in filtered_results 
                          if r.policy.policy_features and r.policy.policy_features.out_hospital_benefit == True]
    elif out_hospital_benefit == 'false':
        filtered_results = [r for r in filtered_results 
                          if r.policy.policy_features and r.policy.policy_features.out_hospital_benefit == False]
    
    # Chronic medication coverage filter
    chronic_medication = request.GET.get('chronic_medication')
    if chronic_medication == 'true':
        filtered_results = [r for r in filtered_results 
                          if r.policy.policy_features and r.policy.policy_features.chronic_medication_availability == True]
    elif chronic_medication == 'false':
        filtered_results = [r for r in filtered_results 
                          if r.policy.policy_features and r.policy.policy_features.chronic_medication_availability == False]
    
    # Annual limit filter
    min_annual_limit = request.GET.get('min_annual_limit')
    if min_annual_limit:
        try:
            min_annual_limit = float(min_annual_limit)
            filtered_results = [r for r in filtered_results 
                              if r.policy.policy_features and 
                              r.policy.policy_features.annual_limit_per_member and
                              r.policy.policy_features.annual_limit_per_member >= min_annual_limit]
        except ValueError:
            pass
    
    return filtered_results


def _apply_funeral_filters(request, results):
    """
    Apply funeral insurance specific filters.
    
    Args:
        request: HTTP request object
        results: List of FeatureComparisonResult objects
        
    Returns:
        Filtered list of results
    """
    filtered_results = results.copy()
    
    # Cover amount filter
    min_cover_amount = request.GET.get('min_cover_amount')
    if min_cover_amount:
        try:
            min_cover_amount = float(min_cover_amount)
            filtered_results = [r for r in filtered_results 
                              if r.policy.policy_features and 
                              r.policy.policy_features.cover_amount and
                              r.policy.policy_features.cover_amount >= min_cover_amount]
        except ValueError:
            pass
    
    # Marital status requirement filter
    marital_status = request.GET.get('marital_status')
    if marital_status:
        filtered_results = [r for r in filtered_results 
                          if r.policy.policy_features and 
                          r.policy.policy_features.marital_status_requirement == marital_status]
    
    # Gender requirement filter
    gender = request.GET.get('gender')
    if gender:
        filtered_results = [r for r in filtered_results 
                          if r.policy.policy_features and 
                          r.policy.policy_features.gender_requirement == gender]
    
    # Waiting period filter
    max_waiting_period = request.GET.get('max_waiting_period')
    if max_waiting_period:
        try:
            max_waiting_period = int(max_waiting_period)
            filtered_results = [r for r in filtered_results 
                              if r.policy.waiting_period_days <= max_waiting_period]
        except (ValueError, AttributeError):
            pass
    
    return filtered_results


def _apply_sorting(request, results):
    """
    Apply sorting to comparison results.
    
    Args:
        request: HTTP request object
        results: List of FeatureComparisonResult objects
        
    Returns:
        Sorted list of results
    """
    sort_by = request.GET.get('sort', 'compatibility_rank')
    sort_order = request.GET.get('order', 'asc')
    
    reverse = sort_order == 'desc'
    
    if sort_by == 'compatibility_rank':
        # Default sorting by compatibility rank (ascending = best first)
        sorted_results = sorted(results, key=lambda r: r.compatibility_rank, reverse=False)
    elif sort_by == 'compatibility_score':
        # Sort by compatibility score (descending = highest first)
        sorted_results = sorted(results, key=lambda r: r.overall_compatibility_score, reverse=True)
    elif sort_by == 'premium':
        # Sort by premium
        sorted_results = sorted(results, key=lambda r: r.policy.base_premium or 0, reverse=reverse)
    elif sort_by == 'coverage':
        # Sort by coverage amount
        sorted_results = sorted(results, key=lambda r: r.policy.coverage_amount or 0, reverse=reverse)
    elif sort_by == 'organization':
        # Sort by organization name
        sorted_results = sorted(results, key=lambda r: r.policy.organization.name, reverse=reverse)
    elif sort_by == 'policy_name':
        # Sort by policy name
        sorted_results = sorted(results, key=lambda r: r.policy.name, reverse=reverse)
    elif sort_by == 'feature_matches':
        # Sort by number of feature matches
        sorted_results = sorted(results, key=lambda r: r.feature_match_count, reverse=not reverse)
    elif sort_by == 'waiting_period':
        # Sort by waiting period
        sorted_results = sorted(results, key=lambda r: r.policy.waiting_period_days or 0, reverse=reverse)
    else:
        # Default to compatibility rank
        sorted_results = sorted(results, key=lambda r: r.compatibility_rank, reverse=False)
    
    return sorted_results


def _get_filter_options(results, survey):
    """
    Get available filter options based on the results.
    
    Args:
        results: List of FeatureComparisonResult objects
        survey: SimpleSurvey instance
        
    Returns:
        Dictionary of filter options
    """
    filter_options = {
        'organizations': [],
        'recommendation_categories': [],
        'premium_range': {'min': 0, 'max': 0},
        'coverage_range': {'min': 0, 'max': 0},
        'score_range': {'min': 0, 'max': 100},
    }
    
    if not results:
        return filter_options
    
    # Get unique organizations
    organizations = set()
    premiums = []
    coverages = []
    scores = []
    recommendation_categories = set()
    
    for result in results:
        organizations.add(result.policy.organization.name)
        recommendation_categories.add(result.recommendation_category)
        scores.append(float(result.overall_compatibility_score))
        
        if result.policy.base_premium:
            premiums.append(float(result.policy.base_premium))
        if result.policy.coverage_amount:
            coverages.append(float(result.policy.coverage_amount))
    
    filter_options['organizations'] = sorted(list(organizations))
    filter_options['recommendation_categories'] = sorted(list(recommendation_categories))
    
    if premiums:
        filter_options['premium_range'] = {
            'min': min(premiums),
            'max': max(premiums)
        }
    
    if coverages:
        filter_options['coverage_range'] = {
            'min': min(coverages),
            'max': max(coverages)
        }
    
    if scores:
        filter_options['score_range'] = {
            'min': min(scores),
            'max': max(scores)
        }
    
    # Add insurance type specific options
    if survey.insurance_type == 'HEALTH':
        filter_options.update(_get_health_filter_options(results))
    elif survey.insurance_type == 'FUNERAL':
        filter_options.update(_get_funeral_filter_options(results))
    
    return filter_options


def _get_health_filter_options(results):
    """Get health insurance specific filter options."""
    options = {
        'annual_limits': [],
        'has_in_hospital': False,
        'has_out_hospital': False,
        'has_chronic_medication': False,
    }
    
    annual_limits = set()
    
    for result in results:
        if result.policy.policy_features:
            features = result.policy.policy_features
            
            if features.annual_limit_per_member:
                annual_limits.add(float(features.annual_limit_per_member))
            
            if features.in_hospital_benefit:
                options['has_in_hospital'] = True
            
            if features.out_hospital_benefit:
                options['has_out_hospital'] = True
            
            if features.chronic_medication_availability:
                options['has_chronic_medication'] = True
    
    if annual_limits:
        options['annual_limits'] = sorted(list(annual_limits))
    
    return options


def _get_funeral_filter_options(results):
    """Get funeral insurance specific filter options."""
    options = {
        'cover_amounts': [],
        'marital_statuses': [],
        'genders': [],
        'waiting_periods': [],
    }
    
    cover_amounts = set()
    marital_statuses = set()
    genders = set()
    waiting_periods = set()
    
    for result in results:
        if result.policy.policy_features:
            features = result.policy.policy_features
            
            if features.cover_amount:
                cover_amounts.add(float(features.cover_amount))
            
            if features.marital_status_requirement:
                marital_statuses.add(features.marital_status_requirement)
            
            if features.gender_requirement:
                genders.add(features.gender_requirement)
        
        if result.policy.waiting_period_days:
            waiting_periods.add(result.policy.waiting_period_days)
    
    options['cover_amounts'] = sorted(list(cover_amounts))
    options['marital_statuses'] = sorted(list(marital_statuses))
    options['genders'] = sorted(list(genders))
    options['waiting_periods'] = sorted(list(waiting_periods))
    
    return options


def _get_current_filters(request):
    """
    Get currently applied filters from request.
    
    Args:
        request: HTTP request object
        
    Returns:
        Dictionary of current filter values
    """
    filters = {}
    
    # General filters
    for param in ['min_score', 'min_premium', 'max_premium', 'min_coverage', 
                  'organization', 'recommendation_category']:
        value = request.GET.get(param)
        if value:
            filters[param] = value
    
    # Health specific filters
    for param in ['in_hospital_benefit', 'out_hospital_benefit', 'chronic_medication', 'min_annual_limit']:
        value = request.GET.get(param)
        if value:
            filters[param] = value
    
    # Funeral specific filters
    for param in ['min_cover_amount', 'marital_status', 'gender', 'max_waiting_period']:
        value = request.GET.get(param)
        if value:
            filters[param] = value
    
    return filters