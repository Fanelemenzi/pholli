"""
User profile management for survey functionality.
Handles saving, loading, and managing user survey preferences and history.
"""

from django.contrib.auth import get_user_model
from django.db import models, transaction
from django.utils import timezone
from django.core.exceptions import ValidationError
from typing import Dict, List, Optional, Any
import json
import csv
import io
from datetime import datetime, timedelta

from .models import (
    SurveyResponse, SurveyQuestion, SurveyTemplate,
    UserSurveyProfile, SavedSurveyProfile
)
from comparison.models import ComparisonSession, UserPreferenceProfile
from policies.models import PolicyCategory

User = get_user_model()


class UserProfileManager:
    """
    Manager class for handling user profile operations.
    """
    
    def __init__(self, user: User):
        self.user = user
        self._ensure_survey_profile()
    
    def _ensure_survey_profile(self):
        """Ensure user has a survey profile."""
        self.survey_profile, created = UserSurveyProfile.objects.get_or_create(
            user=self.user
        )
    
    def save_survey_profile(
        self,
        name: str,
        category: PolicyCategory,
        session: ComparisonSession,
        description: str = "",
        set_as_default: bool = False
    ) -> SavedSurveyProfile:
        """
        Save a complete survey profile from a comparison session.
        
        Args:
            name: Name for the saved profile
            category: Policy category
            session: Comparison session with completed survey
            description: Optional description
            set_as_default: Whether to set as default profile
            
        Returns:
            SavedSurveyProfile: The created profile
        """
        if not session.survey_completed:
            raise ValidationError("Cannot save profile from incomplete survey")
        
        # Collect survey responses
        responses = SurveyResponse.objects.filter(session=session)
        survey_data = {}
        
        for response in responses:
            survey_data[response.question.field_name] = {
                'value': response.response_value,
                'confidence': response.confidence_level,
                'question_id': response.question.id,
                'question_text': response.question.question_text,
                'section': response.question.section
            }
        
        # Create or update saved profile
        profile, created = SavedSurveyProfile.objects.update_or_create(
            user=self.user,
            category=category,
            name=name,
            defaults={
                'description': description,
                'survey_responses': survey_data,
                'criteria_weights': session.get_survey_criteria_weights(),
                'user_profile_data': session.user_profile,
            }
        )
        
        if set_as_default:
            profile.set_as_default()
        
        return profile
    
    def load_survey_profile(self, profile_id: int) -> Optional[SavedSurveyProfile]:
        """
        Load a saved survey profile.
        
        Args:
            profile_id: ID of the profile to load
            
        Returns:
            SavedSurveyProfile or None if not found
        """
        try:
            profile = SavedSurveyProfile.objects.get(
                id=profile_id,
                user=self.user
            )
            profile.mark_used()
            return profile
        except SavedSurveyProfile.DoesNotExist:
            return None
    
    def get_user_profiles(self, category: Optional[PolicyCategory] = None) -> List[SavedSurveyProfile]:
        """
        Get all saved profiles for the user, optionally filtered by category.
        
        Args:
            category: Optional category filter
            
        Returns:
            List of SavedSurveyProfile objects
        """
        queryset = SavedSurveyProfile.objects.filter(user=self.user)
        
        if category:
            queryset = queryset.filter(category=category)
        
        return list(queryset.order_by('-is_default', '-last_used', '-created_at'))
    
    def get_default_profile(self, category: PolicyCategory) -> Optional[SavedSurveyProfile]:
        """
        Get the default profile for a category.
        
        Args:
            category: Policy category
            
        Returns:
            SavedSurveyProfile or None if no default set
        """
        try:
            return SavedSurveyProfile.objects.get(
                user=self.user,
                category=category,
                is_default=True
            )
        except SavedSurveyProfile.DoesNotExist:
            return None
    
    def delete_profile(self, profile_id: int) -> bool:
        """
        Delete a saved profile.
        
        Args:
            profile_id: ID of profile to delete
            
        Returns:
            bool: True if deleted, False if not found
        """
        try:
            profile = SavedSurveyProfile.objects.get(
                id=profile_id,
                user=self.user
            )
            profile.delete()
            return True
        except SavedSurveyProfile.DoesNotExist:
            return False
    
    def apply_profile_to_session(
        self,
        profile: SavedSurveyProfile,
        session: ComparisonSession
    ) -> int:
        """
        Apply a saved profile to a comparison session by creating survey responses.
        
        Args:
            profile: Saved profile to apply
            session: Target comparison session
            
        Returns:
            int: Number of responses created
        """
        if session.category != profile.category:
            raise ValidationError("Profile category must match session category")
        
        responses_created = 0
        
        with transaction.atomic():
            # Clear existing responses
            SurveyResponse.objects.filter(session=session).delete()
            
            # Create responses from saved profile
            for field_name, response_data in profile.survey_responses.items():
                try:
                    question = SurveyQuestion.objects.get(
                        id=response_data['question_id'],
                        category=session.category
                    )
                    
                    SurveyResponse.objects.create(
                        session=session,
                        question=question,
                        response_value=response_data['value'],
                        confidence_level=response_data.get('confidence', 3)
                    )
                    responses_created += 1
                    
                except SurveyQuestion.DoesNotExist:
                    # Question may have been deleted or modified
                    continue
            
            # Update session with profile data
            session.user_profile = profile.user_profile_data.copy()
            session.survey_responses_count = responses_created
            session.survey_completion_percentage = 100.0
            session.survey_completed = True
            session.save()
        
        return responses_created
    
    def get_survey_history(
        self,
        category: Optional[PolicyCategory] = None,
        limit: int = 50
    ) -> List[ComparisonSession]:
        """
        Get user's survey history.
        
        Args:
            category: Optional category filter
            limit: Maximum number of sessions to return
            
        Returns:
            List of ComparisonSession objects
        """
        queryset = ComparisonSession.objects.filter(
            user=self.user,
            survey_responses_count__gt=0
        ).order_by('-updated_at')
        
        if category:
            queryset = queryset.filter(category=category)
        
        return list(queryset[:limit])
    
    def export_survey_data(
        self,
        format: str = 'json',
        category: Optional[PolicyCategory] = None,
        include_responses: bool = True,
        include_profiles: bool = True
    ) -> str:
        """
        Export user's survey data in specified format.
        
        Args:
            format: Export format ('json' or 'csv')
            category: Optional category filter
            include_responses: Whether to include survey responses
            include_profiles: Whether to include saved profiles
            
        Returns:
            str: Exported data as string
        """
        export_data = {
            'user': self.user.username,
            'export_date': timezone.now().isoformat(),
            'category': category.name if category else 'all',
        }
        
        if include_responses:
            export_data['survey_history'] = self._export_survey_history(category)
        
        if include_profiles:
            export_data['saved_profiles'] = self._export_saved_profiles(category)
        
        if format.lower() == 'json':
            return json.dumps(export_data, indent=2, default=str)
        elif format.lower() == 'csv':
            return self._export_to_csv(export_data)
        else:
            raise ValueError("Unsupported export format. Use 'json' or 'csv'.")
    
    def _export_survey_history(self, category: Optional[PolicyCategory] = None) -> List[Dict]:
        """Export survey history data."""
        sessions = self.get_survey_history(category=category, limit=100)
        history_data = []
        
        for session in sessions:
            session_data = {
                'session_id': session.id,
                'category': session.category.name,
                'completed': session.survey_completed,
                'completion_percentage': float(session.survey_completion_percentage),
                'responses_count': session.survey_responses_count,
                'created_at': session.created_at.isoformat(),
                'updated_at': session.updated_at.isoformat(),
                'user_profile': session.user_profile,
            }
            
            # Include individual responses if requested
            responses = SurveyResponse.objects.filter(session=session)
            session_data['responses'] = []
            
            for response in responses:
                session_data['responses'].append({
                    'question': response.question.question_text,
                    'field_name': response.question.field_name,
                    'section': response.question.section,
                    'response_value': response.response_value,
                    'confidence_level': response.confidence_level,
                    'created_at': response.created_at.isoformat(),
                })
            
            history_data.append(session_data)
        
        return history_data
    
    def _export_saved_profiles(self, category: Optional[PolicyCategory] = None) -> List[Dict]:
        """Export saved profiles data."""
        profiles = self.get_user_profiles(category=category)
        profiles_data = []
        
        for profile in profiles:
            profile_data = {
                'id': profile.id,
                'name': profile.name,
                'category': profile.category.name,
                'description': profile.description,
                'is_default': profile.is_default,
                'usage_count': profile.usage_count,
                'last_used': profile.last_used.isoformat() if profile.last_used else None,
                'created_at': profile.created_at.isoformat(),
                'survey_responses': profile.survey_responses,
                'criteria_weights': profile.criteria_weights,
                'user_profile_data': profile.user_profile_data,
            }
            profiles_data.append(profile_data)
        
        return profiles_data
    
    def _export_to_csv(self, export_data: Dict) -> str:
        """Convert export data to CSV format."""
        output = io.StringIO()
        
        # Write metadata
        output.write(f"User: {export_data['user']}\n")
        output.write(f"Export Date: {export_data['export_date']}\n")
        output.write(f"Category: {export_data['category']}\n\n")
        
        # Write survey history
        if 'survey_history' in export_data:
            output.write("Survey History\n")
            if export_data['survey_history']:
                writer = csv.DictWriter(
                    output,
                    fieldnames=['session_id', 'category', 'completed', 'completion_percentage', 
                              'responses_count', 'created_at', 'updated_at']
                )
                writer.writeheader()
                
                for session in export_data['survey_history']:
                    writer.writerow({
                        'session_id': session['session_id'],
                        'category': session['category'],
                        'completed': session['completed'],
                        'completion_percentage': session['completion_percentage'],
                        'responses_count': session['responses_count'],
                        'created_at': session['created_at'],
                        'updated_at': session['updated_at'],
                    })
            output.write("\n")
        
        # Write saved profiles
        if 'saved_profiles' in export_data:
            output.write("Saved Profiles\n")
            if export_data['saved_profiles']:
                writer = csv.DictWriter(
                    output,
                    fieldnames=['id', 'name', 'category', 'description', 'is_default', 
                              'usage_count', 'last_used', 'created_at']
                )
                writer.writeheader()
                
                for profile in export_data['saved_profiles']:
                    writer.writerow({
                        'id': profile['id'],
                        'name': profile['name'],
                        'category': profile['category'],
                        'description': profile['description'],
                        'is_default': profile['is_default'],
                        'usage_count': profile['usage_count'],
                        'last_used': profile['last_used'],
                        'created_at': profile['created_at'],
                    })
        
        return output.getvalue()
    
    def cleanup_old_data(self):
        """Clean up old survey data based on retention policy."""
        if self.survey_profile.data_retention_days == 0:
            return  # Indefinite retention
        
        cutoff_date = timezone.now() - timedelta(days=self.survey_profile.data_retention_days)
        
        # Delete old comparison sessions
        old_sessions = ComparisonSession.objects.filter(
            user=self.user,
            created_at__lt=cutoff_date
        )
        
        deleted_count = old_sessions.count()
        old_sessions.delete()
        
        return deleted_count


class SurveyPreFillService:
    """
    Service for pre-filling survey questions based on user history.
    """
    
    def __init__(self, user: User):
        self.user = user
        self.profile_manager = UserProfileManager(user)
    
    def get_prefill_data(
        self,
        category: PolicyCategory,
        template: SurveyTemplate
    ) -> Dict[str, Any]:
        """
        Get pre-fill data for a survey based on user history.
        
        Args:
            category: Policy category
            template: Survey template
            
        Returns:
            Dict mapping field names to suggested values
        """
        prefill_data = {}
        
        # First, try to use default profile
        default_profile = self.profile_manager.get_default_profile(category)
        if default_profile:
            for field_name, response_data in default_profile.survey_responses.items():
                prefill_data[field_name] = {
                    'value': response_data['value'],
                    'confidence': response_data.get('confidence', 3),
                    'source': 'default_profile',
                    'source_name': default_profile.name
                }
        
        # Then, supplement with recent response history
        recent_responses = self._get_recent_responses(category, days=90)
        
        for field_name, response_data in recent_responses.items():
            if field_name not in prefill_data:
                prefill_data[field_name] = {
                    'value': response_data['value'],
                    'confidence': response_data.get('confidence', 3),
                    'source': 'recent_history',
                    'source_date': response_data.get('date')
                }
        
        return prefill_data
    
    def _get_recent_responses(self, category: PolicyCategory, days: int = 90) -> Dict[str, Any]:
        """Get recent survey responses for pre-filling."""
        cutoff_date = timezone.now() - timedelta(days=days)
        
        recent_sessions = ComparisonSession.objects.filter(
            user=self.user,
            category=category,
            survey_responses_count__gt=0,
            updated_at__gte=cutoff_date
        ).order_by('-updated_at')
        
        response_data = {}
        
        for session in recent_sessions:
            responses = SurveyResponse.objects.filter(session=session)
            
            for response in responses:
                field_name = response.question.field_name
                
                # Use most recent response for each field
                if field_name not in response_data:
                    response_data[field_name] = {
                        'value': response.response_value,
                        'confidence': response.confidence_level,
                        'date': response.updated_at.isoformat()
                    }
        
        return response_data
    
    def apply_prefill_to_session(
        self,
        session: ComparisonSession,
        prefill_data: Dict[str, Any],
        confidence_threshold: int = 3
    ) -> int:
        """
        Apply pre-fill data to a session by creating survey responses.
        
        Args:
            session: Target session
            prefill_data: Pre-fill data from get_prefill_data
            confidence_threshold: Minimum confidence level to apply prefill
            
        Returns:
            int: Number of responses pre-filled
        """
        responses_created = 0
        
        questions = SurveyQuestion.objects.filter(
            category=session.category,
            is_active=True
        )
        
        question_map = {q.field_name: q for q in questions}
        
        with transaction.atomic():
            for field_name, prefill_info in prefill_data.items():
                if field_name in question_map:
                    question = question_map[field_name]
                    confidence = prefill_info.get('confidence', 3)
                    
                    # Only prefill if confidence meets threshold
                    if confidence >= confidence_threshold:
                        SurveyResponse.objects.update_or_create(
                            session=session,
                            question=question,
                            defaults={
                                'response_value': prefill_info['value'],
                                'confidence_level': confidence
                            }
                        )
                        responses_created += 1
            
            # Update session progress
            if responses_created > 0:
                total_questions = questions.count()
                completion_percentage = (responses_created / total_questions) * 100
                session.update_survey_progress(
                    responses_count=responses_created,
                    completion_percentage=completion_percentage
                )
        
        return responses_created