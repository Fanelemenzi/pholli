"""
API views for user profile management functionality.
"""

from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
import json
import logging

from .models import SavedSurveyProfile, UserSurveyProfile
from .user_profile import UserProfileManager, SurveyPreFillService
from comparison.models import ComparisonSession
from policies.models import PolicyCategory

User = get_user_model()
logger = logging.getLogger(__name__)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_profiles(request):
    """
    Get all saved survey profiles for the authenticated user.
    
    Query parameters:
    - category: Optional category slug to filter profiles
    """
    try:
        category = None
        category_slug = request.GET.get('category')
        
        if category_slug:
            try:
                category = PolicyCategory.objects.get(slug=category_slug)
            except PolicyCategory.DoesNotExist:
                return Response(
                    {'error': f'Category "{category_slug}" not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
        
        profile_manager = UserProfileManager(request.user)
        profiles = profile_manager.get_user_profiles(category=category)
        
        profiles_data = []
        for profile in profiles:
            profiles_data.append({
                'id': profile.id,
                'name': profile.name,
                'category': {
                    'id': profile.category.id,
                    'name': profile.category.name,
                    'slug': profile.category.slug
                },
                'description': profile.description,
                'is_default': profile.is_default,
                'usage_count': profile.usage_count,
                'last_used': profile.last_used.isoformat() if profile.last_used else None,
                'created_at': profile.created_at.isoformat(),
                'updated_at': profile.updated_at.isoformat(),
            })
        
        return Response({
            'profiles': profiles_data,
            'count': len(profiles_data)
        })
        
    except Exception as e:
        logger.error(f"Error getting user profiles: {str(e)}")
        return Response(
            {'error': 'Failed to retrieve profiles'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def save_survey_profile(request):
    """
    Save a survey profile from a completed comparison session.
    
    Expected JSON payload:
    {
        "name": "Profile name",
        "description": "Optional description",
        "session_id": 123,
        "set_as_default": false
    }
    """
    try:
        data = request.data
        
        # Validate required fields
        if not data.get('name'):
            return Response(
                {'error': 'Profile name is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not data.get('session_id'):
            return Response(
                {'error': 'Session ID is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get the comparison session
        try:
            session = ComparisonSession.objects.get(
                id=data['session_id'],
                user=request.user
            )
        except ComparisonSession.DoesNotExist:
            return Response(
                {'error': 'Session not found or not owned by user'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        if not session.survey_completed:
            return Response(
                {'error': 'Cannot save profile from incomplete survey'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Save the profile
        profile_manager = UserProfileManager(request.user)
        
        profile = profile_manager.save_survey_profile(
            name=data['name'],
            category=session.category,
            session=session,
            description=data.get('description', ''),
            set_as_default=data.get('set_as_default', False)
        )
        
        return Response({
            'id': profile.id,
            'name': profile.name,
            'category': {
                'id': profile.category.id,
                'name': profile.category.name,
                'slug': profile.category.slug
            },
            'description': profile.description,
            'is_default': profile.is_default,
            'created_at': profile.created_at.isoformat(),
            'message': 'Profile saved successfully'
        }, status=status.HTTP_201_CREATED)
        
    except ValidationError as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        logger.error(f"Error saving survey profile: {str(e)}")
        return Response(
            {'error': 'Failed to save profile'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def apply_profile_to_session(request):
    """
    Apply a saved profile to a comparison session.
    
    Expected JSON payload:
    {
        "profile_id": 123,
        "session_id": 456
    }
    """
    try:
        data = request.data
        
        if not data.get('profile_id') or not data.get('session_id'):
            return Response(
                {'error': 'Both profile_id and session_id are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get the profile and session
        profile_manager = UserProfileManager(request.user)
        
        profile = profile_manager.load_survey_profile(data['profile_id'])
        if not profile:
            return Response(
                {'error': 'Profile not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        try:
            session = ComparisonSession.objects.get(
                id=data['session_id'],
                user=request.user
            )
        except ComparisonSession.DoesNotExist:
            return Response(
                {'error': 'Session not found or not owned by user'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Apply the profile
        responses_created = profile_manager.apply_profile_to_session(profile, session)
        
        return Response({
            'message': 'Profile applied successfully',
            'responses_created': responses_created,
            'session_id': session.id,
            'profile_name': profile.name
        })
        
    except ValidationError as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        logger.error(f"Error applying profile to session: {str(e)}")
        return Response(
            {'error': 'Failed to apply profile'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_profile(request, profile_id):
    """
    Delete a saved survey profile.
    """
    try:
        profile_manager = UserProfileManager(request.user)
        
        if profile_manager.delete_profile(profile_id):
            return Response({'message': 'Profile deleted successfully'})
        else:
            return Response(
                {'error': 'Profile not found'},
                status=status.HTTP_404_NOT_FOUND
            )
            
    except Exception as e:
        logger.error(f"Error deleting profile: {str(e)}")
        return Response(
            {'error': 'Failed to delete profile'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def set_default_profile(request, profile_id):
    """
    Set a profile as the default for its category.
    """
    try:
        profile = get_object_or_404(
            SavedSurveyProfile,
            id=profile_id,
            user=request.user
        )
        
        profile.set_as_default()
        
        return Response({
            'message': f'Profile "{profile.name}" set as default for {profile.category.name}',
            'profile_id': profile.id
        })
        
    except Exception as e:
        logger.error(f"Error setting default profile: {str(e)}")
        return Response(
            {'error': 'Failed to set default profile'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_survey_history(request):
    """
    Get user's survey history.
    
    Query parameters:
    - category: Optional category slug to filter history
    - limit: Maximum number of sessions to return (default: 50)
    """
    try:
        category = None
        category_slug = request.GET.get('category')
        limit = int(request.GET.get('limit', 50))
        
        if category_slug:
            try:
                category = PolicyCategory.objects.get(slug=category_slug)
            except PolicyCategory.DoesNotExist:
                return Response(
                    {'error': f'Category "{category_slug}" not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
        
        profile_manager = UserProfileManager(request.user)
        sessions = profile_manager.get_survey_history(category=category, limit=limit)
        
        history_data = []
        for session in sessions:
            history_data.append({
                'id': session.id,
                'category': {
                    'id': session.category.id,
                    'name': session.category.name,
                    'slug': session.category.slug
                },
                'survey_completed': session.survey_completed,
                'completion_percentage': float(session.survey_completion_percentage),
                'responses_count': session.survey_responses_count,
                'created_at': session.created_at.isoformat(),
                'updated_at': session.updated_at.isoformat(),
                'has_results': bool(session.match_scores),
            })
        
        return Response({
            'history': history_data,
            'count': len(history_data)
        })
        
    except Exception as e:
        logger.error(f"Error getting survey history: {str(e)}")
        return Response(
            {'error': 'Failed to retrieve survey history'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_prefill_data(request):
    """
    Get pre-fill data for a survey based on user history.
    
    Query parameters:
    - category: Category slug (required)
    - confidence_threshold: Minimum confidence level (default: 3)
    """
    try:
        category_slug = request.GET.get('category')
        if not category_slug:
            return Response(
                {'error': 'Category parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            category = PolicyCategory.objects.get(slug=category_slug)
        except PolicyCategory.DoesNotExist:
            return Response(
                {'error': f'Category "{category_slug}" not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Get survey template (assuming there's an active one)
        from .models import SurveyTemplate
        try:
            template = SurveyTemplate.objects.get(category=category, is_active=True)
        except SurveyTemplate.DoesNotExist:
            return Response(
                {'error': f'No active survey template found for category "{category_slug}"'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        prefill_service = SurveyPreFillService(request.user)
        prefill_data = prefill_service.get_prefill_data(category, template)
        
        return Response({
            'prefill_data': prefill_data,
            'category': {
                'id': category.id,
                'name': category.name,
                'slug': category.slug
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting prefill data: {str(e)}")
        return Response(
            {'error': 'Failed to retrieve prefill data'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def apply_prefill_to_session(request):
    """
    Apply pre-fill data to a comparison session.
    
    Expected JSON payload:
    {
        "session_id": 123,
        "confidence_threshold": 3
    }
    """
    try:
        data = request.data
        
        if not data.get('session_id'):
            return Response(
                {'error': 'Session ID is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            session = ComparisonSession.objects.get(
                id=data['session_id'],
                user=request.user
            )
        except ComparisonSession.DoesNotExist:
            return Response(
                {'error': 'Session not found or not owned by user'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Get survey template
        from .models import SurveyTemplate
        try:
            template = SurveyTemplate.objects.get(category=session.category, is_active=True)
        except SurveyTemplate.DoesNotExist:
            return Response(
                {'error': 'No active survey template found for this category'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Get prefill data and apply it
        prefill_service = SurveyPreFillService(request.user)
        prefill_data = prefill_service.get_prefill_data(session.category, template)
        
        confidence_threshold = data.get('confidence_threshold', 3)
        responses_created = prefill_service.apply_prefill_to_session(
            session, prefill_data, confidence_threshold
        )
        
        return Response({
            'message': 'Pre-fill data applied successfully',
            'responses_created': responses_created,
            'session_id': session.id
        })
        
    except Exception as e:
        logger.error(f"Error applying prefill to session: {str(e)}")
        return Response(
            {'error': 'Failed to apply prefill data'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def export_survey_data(request):
    """
    Export user's survey data.
    
    Query parameters:
    - format: Export format ('json' or 'csv', default: 'json')
    - category: Optional category slug to filter data
    - include_responses: Include survey responses (default: true)
    - include_profiles: Include saved profiles (default: true)
    """
    try:
        export_format = request.GET.get('format', 'json').lower()
        category_slug = request.GET.get('category')
        include_responses = request.GET.get('include_responses', 'true').lower() == 'true'
        include_profiles = request.GET.get('include_profiles', 'true').lower() == 'true'
        
        category = None
        if category_slug:
            try:
                category = PolicyCategory.objects.get(slug=category_slug)
            except PolicyCategory.DoesNotExist:
                return Response(
                    {'error': f'Category "{category_slug}" not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
        
        profile_manager = UserProfileManager(request.user)
        
        try:
            export_data = profile_manager.export_survey_data(
                format=export_format,
                category=category,
                include_responses=include_responses,
                include_profiles=include_profiles
            )
        except ValueError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Determine content type and filename
        if export_format == 'json':
            content_type = 'application/json'
            filename = f'survey_data_{request.user.username}.json'
        else:  # csv
            content_type = 'text/csv'
            filename = f'survey_data_{request.user.username}.csv'
        
        response = HttpResponse(export_data, content_type=content_type)
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        return response
        
    except Exception as e:
        logger.error(f"Error exporting survey data: {str(e)}")
        return Response(
            {'error': 'Failed to export survey data'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET', 'PUT'])
@permission_classes([IsAuthenticated])
def user_survey_settings(request):
    """
    Get or update user survey profile settings.
    """
    try:
        profile_manager = UserProfileManager(request.user)
        survey_profile = profile_manager.survey_profile
        
        if request.method == 'GET':
            return Response({
                'auto_save_responses': survey_profile.auto_save_responses,
                'prefill_from_history': survey_profile.prefill_from_history,
                'email_survey_reminders': survey_profile.email_survey_reminders,
                'data_retention_days': survey_profile.data_retention_days,
                'total_surveys_completed': survey_profile.total_surveys_completed,
                'last_survey_date': survey_profile.last_survey_date.isoformat() if survey_profile.last_survey_date else None,
                'preferred_categories': [
                    {
                        'id': cat.id,
                        'name': cat.name,
                        'slug': cat.slug
                    }
                    for cat in survey_profile.preferred_categories.all()
                ]
            })
        
        elif request.method == 'PUT':
            data = request.data
            
            # Update settings
            if 'auto_save_responses' in data:
                survey_profile.auto_save_responses = data['auto_save_responses']
            
            if 'prefill_from_history' in data:
                survey_profile.prefill_from_history = data['prefill_from_history']
            
            if 'email_survey_reminders' in data:
                survey_profile.email_survey_reminders = data['email_survey_reminders']
            
            if 'data_retention_days' in data:
                survey_profile.data_retention_days = data['data_retention_days']
            
            survey_profile.save()
            
            # Update preferred categories if provided
            if 'preferred_categories' in data:
                category_ids = data['preferred_categories']
                categories = PolicyCategory.objects.filter(id__in=category_ids)
                survey_profile.preferred_categories.set(categories)
            
            return Response({
                'message': 'Settings updated successfully',
                'auto_save_responses': survey_profile.auto_save_responses,
                'prefill_from_history': survey_profile.prefill_from_history,
                'email_survey_reminders': survey_profile.email_survey_reminders,
                'data_retention_days': survey_profile.data_retention_days,
            })
            
    except Exception as e:
        logger.error(f"Error handling user survey settings: {str(e)}")
        return Response(
            {'error': 'Failed to handle survey settings'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def cleanup_old_data(request):
    """
    Clean up old survey data based on user's retention policy.
    """
    try:
        profile_manager = UserProfileManager(request.user)
        deleted_count = profile_manager.cleanup_old_data()
        
        return Response({
            'message': 'Data cleanup completed',
            'deleted_sessions': deleted_count or 0
        })
        
    except Exception as e:
        logger.error(f"Error cleaning up old data: {str(e)}")
        return Response(
            {'error': 'Failed to cleanup old data'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )