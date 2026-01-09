"""
Survey API Views for Policy Comparison Surveys.
Provides REST API endpoints for survey functionality.
"""

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.db import transaction
from comparison.models import ComparisonSession
from policies.models import PolicyCategory
from .models import SurveyQuestion, SurveyResponse
# from .engine import SurveyEngine
import logging
import uuid

logger = logging.getLogger(__name__)


def get_category_or_404(category_slug):
    """Helper function to get category or return 404 response."""
    try:
        return PolicyCategory.objects.get(slug=category_slug), None
    except PolicyCategory.DoesNotExist:
        return None, Response({
            'error': f'Policy category not found: {category_slug}'
        }, status=status.HTTP_404_NOT_FOUND)


def get_session_or_404(session_key):
    """Helper function to get session or return 404 response."""
    try:
        return ComparisonSession.objects.get(session_key=session_key), None
    except ComparisonSession.DoesNotExist:
        return None, Response({
            'error': f'Comparison session not found: {session_key}'
        }, status=status.HTTP_404_NOT_FOUND)


@api_view(['GET'])
@permission_classes([AllowAny])
def get_survey_questions(request, category_slug):
    """
    Retrieve survey questions by category.
    
    GET /api/surveys/{category_slug}/questions/
    
    Returns organized survey sections with questions for the specified category.
    """
    try:
        # Validate category exists
        category, error_response = get_category_or_404(category_slug)
        if error_response:
            return error_response
        
        # TODO: Initialize survey engine when task 3 is complete
        # survey_engine = SurveyEngine(category_slug)
        
        # For now, return placeholder sections
        sections = [
            {
                'name': 'Personal Information',
                'description': 'Basic personal details',
                'questions': []
            }
        ]
        
        # Get template info (placeholder)
        template_info = {
            'name': f'{category.name} Survey',
            'description': f'Survey for {category.name}',
            'version': '1.0'
        }
        
        return Response({
            'category': category_slug,
            'category_name': category.name,
            'template': template_info,
            'sections': sections,
            'total_questions': sum(len(section['questions']) for section in sections)
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error retrieving survey questions for {category_slug}: {str(e)}")
        return Response({
            'error': 'Failed to retrieve survey questions'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([AllowAny])
def save_survey_response(request):
    """
    Save individual survey response.
    
    POST /api/surveys/responses/
    
    Expected payload:
    {
        "session_key": "unique-session-identifier",
        "category_slug": "health",
        "question_id": 123,
        "response_value": "answer",
        "confidence_level": 4
    }
    """
    try:
        # Extract data from request
        session_key = request.data.get('session_key')
        category_slug = request.data.get('category_slug')
        question_id = request.data.get('question_id')
        response_value = request.data.get('response_value')
        confidence_level = request.data.get('confidence_level', 3)
        
        # Validate required fields
        if not all([session_key, category_slug, question_id is not None]):
            return Response({
                'error': 'Missing required fields: session_key, category_slug, question_id'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Validate category exists
        category, error_response = get_category_or_404(category_slug)
        if error_response:
            return error_response
        
        # Get or create comparison session
        session, created = ComparisonSession.objects.get_or_create(
            session_key=session_key,
            defaults={
                'category': category,
                'user': request.user if request.user.is_authenticated else None
            }
        )
        
        # Ensure session is for the correct category
        if session.category != category:
            return Response({
                'error': f'Session category mismatch. Expected: {category_slug}, Got: {session.category.slug}'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # TODO: Initialize survey engine when task 3 is complete
        # survey_engine = SurveyEngine(category_slug)
        
        # For now, create a simple response record
        with transaction.atomic():
            try:
                question = SurveyQuestion.objects.get(id=question_id)
                response_obj, created = SurveyResponse.objects.update_or_create(
                    session=session,
                    question=question,
                    defaults={
                        'response_value': response_value,
                        'confidence_level': confidence_level
                    }
                )
            except SurveyQuestion.DoesNotExist:
                return Response({
                    'error': f'Survey question not found: {question_id}'
                }, status=status.HTTP_404_NOT_FOUND)
            
            result = {
                'success': True,
                'response_id': response_obj.id,
                'created': created,
                'errors': []
            }
        
        # Simple progress calculation
        total_responses = SurveyResponse.objects.filter(session=session).count()
        completion_percentage = min(100.0, (total_responses / 10) * 100)  # Assume 10 questions for now
        
        return Response({
            'success': True,
            'response_id': result['response_id'],
            'created': result['created'],
            'session_key': session_key,
            'completion_percentage': completion_percentage,
            'survey_completed': completion_percentage >= 100.0
        }, status=status.HTTP_201_CREATED if result['created'] else status.HTTP_200_OK)
        
    except SurveyQuestion.DoesNotExist:
        return Response({
            'error': f'Survey question not found: {question_id}'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"Error saving survey response: {str(e)}")
        return Response({
            'error': 'Failed to save survey response'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([AllowAny])
def get_survey_progress(request, session_key):
    """
    Retrieve survey progress and completion status.
    
    GET /api/surveys/progress/{session_key}/
    
    Returns comprehensive survey progress information for the session.
    """
    try:
        # Get the comparison session
        session, error_response = get_session_or_404(session_key)
        if error_response:
            return error_response
        
        # TODO: Initialize survey engine when task 3 is complete
        # survey_engine = SurveyEngine(session.category.slug)
        
        # Simple survey summary for now
        total_responses = SurveyResponse.objects.filter(session=session).count()
        survey_summary = {
            'total_questions': 10,  # Placeholder
            'answered_questions': total_responses,
            'completion_percentage': min(100.0, (total_responses / 10) * 100)
        }
        
        # Simple responses structure
        responses = {}
        
        # Simple session status
        session_status = {
            'is_complete': total_responses >= 8,  # 80% completion
            'can_submit': total_responses >= 8
        }
        
        return Response({
            'session_key': session_key,
            'category': session.category.slug,
            'category_name': session.category.name,
            'survey_summary': survey_summary,
            'session_status': session_status,
            'responses_by_section': responses,
            'created_at': session.created_at,
            'updated_at': session.updated_at
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error retrieving survey progress for {session_key}: {str(e)}")
        return Response({
            'error': 'Failed to retrieve survey progress'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([AllowAny])
def submit_completed_survey(request):
    """
    Submit completed survey and trigger comparison processing.
    
    POST /api/surveys/submit/
    
    Expected payload:
    {
        "session_key": "unique-session-identifier",
        "category_slug": "health"
    }
    
    Processes survey responses and generates comparison results.
    """
    try:
        # Extract data from request
        session_key = request.data.get('session_key')
        category_slug = request.data.get('category_slug')
        
        # Validate required fields
        if not all([session_key, category_slug]):
            return Response({
                'error': 'Missing required fields: session_key, category_slug'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Validate category exists
        category, error_response = get_category_or_404(category_slug)
        if error_response:
            return error_response
        
        # Get the comparison session
        session, error_response = get_session_or_404(session_key)
        if error_response:
            return error_response
        
        # Ensure session is for the correct category
        if session.category != category:
            return Response({
                'error': f'Session category mismatch. Expected: {category_slug}, Got: {session.category.slug}'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # TODO: Initialize survey engine when task 3 is complete
        # survey_engine = SurveyEngine(category_slug)
        
        # Simple completion check for now
        total_responses = SurveyResponse.objects.filter(session=session).count()
        completion_percentage = min(100.0, (total_responses / 10) * 100)  # Assume 10 questions
        
        if completion_percentage < 80.0:  # Allow submission at 80% completion
            return Response({
                'error': 'Survey must be at least 80% complete to submit',
                'completion_percentage': completion_percentage,
                'required_percentage': 80.0
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Process survey responses
        with transaction.atomic():
            try:
                # For now, create a simple user profile from responses
                # This will be enhanced when ResponseProcessor is implemented
                responses = SurveyResponse.objects.filter(session=session)
                user_profile = {}
                comparison_criteria = {}
                
                for response in responses:
                    field_name = response.question.field_name
                    user_profile[field_name] = {
                        'value': response.response_value,
                        'confidence': response.confidence_level,
                        'weight': float(response.question.weight_impact)
                    }
                    
                    # Simple criteria mapping
                    comparison_criteria[field_name] = {
                        'value': response.response_value,
                        'weight': float(response.question.weight_impact) * response.confidence_level
                    }
                
                # Update session with processed data
                session.mark_survey_completed(user_profile)
                session.criteria = comparison_criteria
                session.save(update_fields=['criteria'])
                
                # TODO: Trigger comparison engine processing
                # This would be implemented when task 7 is completed
                # For now, we'll just mark the survey as processed
                
                return Response({
                    'success': True,
                    'session_key': session_key,
                    'completion_percentage': completion_percentage,
                    'survey_completed': True,
                    'comparison_criteria_generated': True,
                    'user_profile_created': bool(user_profile),
                    'next_step': 'comparison_processing',
                    'message': 'Survey submitted successfully. Comparison processing will begin shortly.'
                }, status=status.HTTP_200_OK)
                
            except Exception as processing_error:
                logger.error(f"Error processing survey responses: {str(processing_error)}")
                return Response({
                    'error': 'Failed to process survey responses',
                    'details': str(processing_error)
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
    except Exception as e:
        logger.error(f"Error submitting completed survey: {str(e)}")
        return Response({
            'error': 'Failed to submit survey'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([AllowAny])
def create_survey_session(request):
    """
    Create a new survey session.
    
    POST /api/surveys/sessions/
    
    Expected payload:
    {
        "category_slug": "health"
    }
    
    Creates a new comparison session for survey completion.
    """
    try:
        category_slug = request.data.get('category_slug')
        
        if not category_slug:
            return Response({
                'error': 'Missing required field: category_slug'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Validate category exists
        category, error_response = get_category_or_404(category_slug)
        if error_response:
            return error_response
        
        # Generate unique session key
        session_key = str(uuid.uuid4())
        
        # Create new comparison session
        session = ComparisonSession.objects.create(
            session_key=session_key,
            category=category,
            user=request.user if request.user.is_authenticated else None
        )
        
        return Response({
            'session_key': session_key,
            'category': category_slug,
            'category_name': category.name,
            'created_at': session.created_at,
            'expires_at': session.expires_at
        }, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        logger.error(f"Error creating survey session: {str(e)}")
        return Response({
            'error': 'Failed to create survey session'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([AllowAny])
def get_survey_categories(request):
    """
    Get available survey categories.
    
    GET /api/surveys/categories/
    
    Returns list of policy categories that have active survey templates.
    """
    try:
        from .models import SurveyTemplate
        
        # Get categories that have active survey templates
        categories_with_surveys = PolicyCategory.objects.filter(
            survey_templates__is_active=True
        ).distinct().values('slug', 'name', 'description')
        
        return Response({
            'categories': list(categories_with_surveys),
            'count': len(categories_with_surveys)
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error retrieving survey categories: {str(e)}")
        return Response({
            'error': 'Failed to retrieve survey categories'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['DELETE'])
@permission_classes([AllowAny])
def delete_survey_session(request, session_key):
    """
    Delete a survey session and all associated responses.
    
    DELETE /api/surveys/sessions/{session_key}/
    
    Removes the session and all survey responses.
    """
    try:
        # Get the comparison session
        session, error_response = get_session_or_404(session_key)
        if error_response:
            return error_response
        
        # Check if user has permission to delete this session
        if request.user.is_authenticated and session.user and session.user != request.user:
            return Response({
                'error': 'Permission denied. You can only delete your own sessions.'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Delete the session (cascade will delete responses)
        session.delete()
        
        return Response({
            'success': True,
            'message': f'Survey session {session_key} deleted successfully'
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        logger.error(f"Error deleting survey session {session_key}: {str(e)}")
        return Response({
            'error': 'Failed to delete survey session'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)