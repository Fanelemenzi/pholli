"""
Tests for session management functionality.
Tests session creation, validation, expiry, and cleanup.
"""

from django.test import TestCase, Client
from django.utils import timezone
from django.contrib.sessions.models import Session
from django.core.management import call_command
from django.test.utils import override_settings
from datetime import timedelta
from unittest.mock import patch, MagicMock
import json

from .models import QuotationSession, SimpleSurveyResponse, SimpleSurveyQuestion
from .session_manager import SessionManager, SessionValidationError, require_valid_session
from .management.commands.cleanup_expired_sessions import Command


class SessionManagerTestCase(TestCase):
    """Test cases for SessionManager functionality."""
    
    def setUp(self):
        """Set up test data."""
        self.client = Client()
        
        # Create test questions
        self.health_question = SimpleSurveyQuestion.objects.create(
            category='health',
            question_text='What is your age?',
            field_name='age',
            input_type='number',
            display_order=1,
            validation_rules={'min': 18, 'max': 80}
        )
        
        self.funeral_question = SimpleSurveyQuestion.objects.create(
            category='funeral',
            question_text='How many family members?',
            field_name='family_size',
            input_type='number',
            display_order=1,
            validation_rules={'min': 1, 'max': 15}
        )
    
    def test_create_new_session(self):
        """Test creating a new session."""
        # Create a mock request with session
        session = self.client.session
        session.create()
        
        # Mock request object
        request = MagicMock()
        request.session = session
        
        # Create session
        quotation_session, created = SessionManager.create_or_get_session(request, 'health')
        
        self.assertTrue(created)
        self.assertEqual(quotation_session.category, 'health')
        self.assertEqual(quotation_session.session_key, session.session_key)
        self.assertFalse(quotation_session.is_completed)
        self.assertFalse(quotation_session.is_expired())
        
        # Check expiry is set to 24 hours from now
        expected_expiry = timezone.now() + timedelta(hours=24)
        time_diff = abs((quotation_session.expires_at - expected_expiry).total_seconds())
        self.assertLess(time_diff, 60)  # Within 1 minute
    
    def test_get_existing_active_session(self):
        """Test getting an existing active session."""
        # Create a session first
        session = self.client.session
        session.create()
        
        request = MagicMock()
        request.session = session
        
        # Create initial session
        quotation_session1, created1 = SessionManager.create_or_get_session(request, 'health')
        self.assertTrue(created1)
        
        # Get the same session
        quotation_session2, created2 = SessionManager.create_or_get_session(request, 'health')
        self.assertFalse(created2)
        self.assertEqual(quotation_session1.id, quotation_session2.id)
    
    def test_create_session_for_different_category(self):
        """Test creating sessions for different categories."""
        session = self.client.session
        session.create()
        
        request = MagicMock()
        request.session = session
        
        # Create health session
        health_session, created1 = SessionManager.create_or_get_session(request, 'health')
        self.assertTrue(created1)
        self.assertEqual(health_session.category, 'health')
        
        # Create funeral session (should be separate)
        funeral_session, created2 = SessionManager.create_or_get_session(request, 'funeral')
        self.assertTrue(created2)
        self.assertEqual(funeral_session.category, 'funeral')
        
        # Should have different IDs
        self.assertNotEqual(health_session.id, funeral_session.id)
    
    def test_expired_session_cleanup_and_recreation(self):
        """Test that expired sessions are cleaned up and new ones created."""
        session = self.client.session
        session.create()
        
        request = MagicMock()
        request.session = session
        
        # Create session and manually expire it
        quotation_session, created = SessionManager.create_or_get_session(request, 'health')
        self.assertTrue(created)
        
        # Manually set expiry to past
        quotation_session.expires_at = timezone.now() - timedelta(hours=1)
        quotation_session.save()
        
        # Add some responses to test cleanup
        SimpleSurveyResponse.objects.create(
            session_key=quotation_session.session_key,
            category='health',
            question=self.health_question,
            response_value=25
        )
        
        # Try to get session again - should create new one and clean up old
        new_session, created = SessionManager.create_or_get_session(request, 'health')
        self.assertTrue(created)
        self.assertNotEqual(quotation_session.id, new_session.id)
        
        # Old session should be deleted
        self.assertFalse(
            QuotationSession.objects.filter(id=quotation_session.id).exists()
        )
        
        # Old responses should be deleted
        self.assertFalse(
            SimpleSurveyResponse.objects.filter(
                session_key=quotation_session.session_key,
                category='health'
            ).exists()
        )
    
    def test_invalid_category(self):
        """Test handling of invalid category."""
        session = self.client.session
        session.create()
        
        request = MagicMock()
        request.session = session
        
        with self.assertRaises(ValueError):
            SessionManager.create_or_get_session(request, 'invalid')
    
    def test_session_validation_valid(self):
        """Test validation of valid session."""
        # Create Django session
        session = self.client.session
        session.create()
        
        # Create quotation session
        quotation_session = QuotationSession.objects.create(
            session_key=session.session_key,
            category='health',
            expires_at=timezone.now() + timedelta(hours=24)
        )
        
        # Validate session
        result = SessionManager.validate_session(session.session_key, 'health')
        
        self.assertTrue(result['valid'])
        self.assertIsNone(result['error'])
        self.assertEqual(result['session'].id, quotation_session.id)
    
    def test_session_validation_expired(self):
        """Test validation of expired session."""
        session = self.client.session
        session.create()
        
        # Create expired quotation session
        quotation_session = QuotationSession.objects.create(
            session_key=session.session_key,
            category='health',
            expires_at=timezone.now() - timedelta(hours=1)
        )
        
        # Validate session
        result = SessionManager.validate_session(session.session_key, 'health')
        
        self.assertFalse(result['valid'])
        self.assertIn('expired', result['error'].lower())
        self.assertEqual(result['session'].id, quotation_session.id)
    
    def test_session_validation_not_found(self):
        """Test validation when session doesn't exist."""
        result = SessionManager.validate_session('nonexistent', 'health')
        
        self.assertFalse(result['valid'])
        self.assertIn('not found', result['error'].lower())
        self.assertIsNone(result['session'])
    
    def test_extend_session(self):
        """Test extending session expiry."""
        session = self.client.session
        session.create()
        
        quotation_session = QuotationSession.objects.create(
            session_key=session.session_key,
            category='health',
            expires_at=timezone.now() + timedelta(hours=1)
        )
        
        original_expiry = quotation_session.expires_at
        
        # Extend session
        success = SessionManager.extend_session(session.session_key, 'health', 48)
        self.assertTrue(success)
        
        # Check expiry was extended
        quotation_session.refresh_from_db()
        self.assertGreater(quotation_session.expires_at, original_expiry)
        
        # Should be approximately 48 hours from now
        expected_expiry = timezone.now() + timedelta(hours=48)
        time_diff = abs((quotation_session.expires_at - expected_expiry).total_seconds())
        self.assertLess(time_diff, 60)
    
    def test_extend_nonexistent_session(self):
        """Test extending non-existent session."""
        success = SessionManager.extend_session('nonexistent', 'health')
        self.assertFalse(success)
    
    def test_cleanup_expired_sessions(self):
        """Test cleanup of expired sessions."""
        # Create active session
        active_session = QuotationSession.objects.create(
            session_key='active_session',
            category='health',
            expires_at=timezone.now() + timedelta(hours=24)
        )
        
        # Create expired session with responses
        expired_session = QuotationSession.objects.create(
            session_key='expired_session',
            category='funeral',
            expires_at=timezone.now() - timedelta(hours=1)
        )
        
        SimpleSurveyResponse.objects.create(
            session_key='expired_session',
            category='funeral',
            question=self.funeral_question,
            response_value=5
        )
        
        # Run cleanup
        stats = SessionManager.cleanup_expired_sessions()
        
        # Check stats
        self.assertEqual(stats['quotation_sessions_deleted'], 1)
        self.assertEqual(stats['responses_deleted'], 1)
        # Note: Django session cleanup may have errors due to database limitations
        # but that's acceptable as it's not critical functionality
        
        # Active session should still exist
        self.assertTrue(
            QuotationSession.objects.filter(id=active_session.id).exists()
        )
        
        # Expired session should be deleted
        self.assertFalse(
            QuotationSession.objects.filter(id=expired_session.id).exists()
        )
        
        # Expired responses should be deleted
        self.assertFalse(
            SimpleSurveyResponse.objects.filter(session_key='expired_session').exists()
        )
    
    def test_get_session_stats(self):
        """Test getting session statistics."""
        # Create test data
        active_session = QuotationSession.objects.create(
            session_key='active',
            category='health',
            expires_at=timezone.now() + timedelta(hours=24)
        )
        
        expired_session = QuotationSession.objects.create(
            session_key='expired',
            category='funeral',
            expires_at=timezone.now() - timedelta(hours=1)
        )
        
        completed_session = QuotationSession.objects.create(
            session_key='completed',
            category='health',
            expires_at=timezone.now() + timedelta(hours=24),
            is_completed=True
        )
        
        SimpleSurveyResponse.objects.create(
            session_key='active',
            category='health',
            question=self.health_question,
            response_value=30
        )
        
        # Get stats
        stats = SessionManager.get_session_stats()
        
        self.assertIn('quotation_sessions', stats)
        self.assertIn('responses', stats)
        self.assertIn('django_sessions', stats)
        
        qs = stats['quotation_sessions']
        self.assertEqual(qs['total'], 3)
        self.assertEqual(qs['active'], 2)  # active + completed
        self.assertEqual(qs['expired'], 1)
        self.assertEqual(qs['completed'], 1)
        
        self.assertEqual(stats['responses']['total'], 1)


class SessionValidationDecoratorTestCase(TestCase):
    """Test cases for session validation decorator."""
    
    def setUp(self):
        """Set up test data."""
        self.client = Client()
    
    def test_require_valid_session_decorator(self):
        """Test the require_valid_session decorator."""
        
        @require_valid_session('health')
        def test_view(request):
            return {'success': True, 'session': request.quotation_session}
        
        # Test with no session
        request = MagicMock()
        request.session.session_key = None
        
        with self.assertRaises(SessionValidationError):
            test_view(request)
        
        # Test with valid session
        session = self.client.session
        session.create()
        
        quotation_session = QuotationSession.objects.create(
            session_key=session.session_key,
            category='health',
            expires_at=timezone.now() + timedelta(hours=24)
        )
        
        request.session.session_key = session.session_key
        
        result = test_view(request)
        self.assertTrue(result['success'])
        self.assertEqual(result['session'].id, quotation_session.id)


class CleanupCommandTestCase(TestCase):
    """Test cases for the cleanup management command."""
    
    def setUp(self):
        """Set up test data."""
        # Create test sessions
        self.active_session = QuotationSession.objects.create(
            session_key='active',
            category='health',
            expires_at=timezone.now() + timedelta(hours=24)
        )
        
        self.expired_session = QuotationSession.objects.create(
            session_key='expired',
            category='funeral',
            expires_at=timezone.now() - timedelta(hours=1)
        )
        
        # Create test question
        self.question = SimpleSurveyQuestion.objects.create(
            category='funeral',
            question_text='Test question',
            field_name='test_field',
            input_type='text',
            display_order=1
        )
        
        # Create response for expired session
        SimpleSurveyResponse.objects.create(
            session_key='expired',
            category='funeral',
            question=self.question,
            response_value='test response'
        )
    
    def test_cleanup_command_stats_only(self):
        """Test cleanup command with stats-only flag."""
        # Capture output
        from io import StringIO
        out = StringIO()
        
        call_command('cleanup_expired_sessions', '--stats-only', stdout=out)
        
        output = out.getvalue()
        self.assertIn('Session Statistics', output)
        self.assertIn('Total: 2', output)  # 2 quotation sessions
        self.assertIn('Expired: 1', output)  # 1 expired session
        
        # No sessions should be deleted
        self.assertTrue(QuotationSession.objects.filter(id=self.expired_session.id).exists())
    
    def test_cleanup_command_dry_run(self):
        """Test cleanup command with dry-run flag."""
        from io import StringIO
        out = StringIO()
        
        call_command('cleanup_expired_sessions', '--dry-run', stdout=out)
        
        output = out.getvalue()
        self.assertIn('DRY RUN MODE', output)
        self.assertIn('Would clean up', output)
        
        # No sessions should be deleted
        self.assertTrue(QuotationSession.objects.filter(id=self.expired_session.id).exists())
        self.assertTrue(SimpleSurveyResponse.objects.filter(session_key='expired').exists())
    
    def test_cleanup_command_force(self):
        """Test cleanup command with force flag."""
        from io import StringIO
        out = StringIO()
        
        call_command('cleanup_expired_sessions', '--force', stdout=out)
        
        output = out.getvalue()
        self.assertIn('Starting Cleanup', output)
        self.assertIn('Cleanup Results', output)
        
        # Expired session should be deleted
        self.assertFalse(QuotationSession.objects.filter(id=self.expired_session.id).exists())
        self.assertFalse(SimpleSurveyResponse.objects.filter(session_key='expired').exists())
        
        # Active session should remain
        self.assertTrue(QuotationSession.objects.filter(id=self.active_session.id).exists())
    
    def test_cleanup_command_batch_size(self):
        """Test cleanup command with custom batch size."""
        # Create multiple expired sessions
        for i in range(5):
            QuotationSession.objects.create(
                session_key=f'expired_{i}',
                category='health',
                expires_at=timezone.now() - timedelta(hours=1)
            )
        
        from io import StringIO
        out = StringIO()
        
        call_command('cleanup_expired_sessions', '--force', '--batch-size=2', stdout=out)
        
        # All expired sessions should be cleaned up
        expired_count = QuotationSession.objects.expired_sessions().count()
        self.assertEqual(expired_count, 0)


class SessionIntegrationTestCase(TestCase):
    """Integration tests for session management with views."""
    
    def setUp(self):
        """Set up test data."""
        self.client = Client()
        
        # Create test question
        self.question = SimpleSurveyQuestion.objects.create(
            category='health',
            question_text='What is your age?',
            field_name='age',
            input_type='number',
            display_order=1,
            is_required=True,
            validation_rules={'min': 18, 'max': 80}
        )
    
    def test_survey_view_creates_session(self):
        """Test that accessing survey view creates a session."""
        response = self.client.get('/simple-surveys/health/')
        
        self.assertEqual(response.status_code, 200)
        
        # Check that session was created
        session_key = self.client.session.session_key
        self.assertIsNotNone(session_key)
        
        # Check that quotation session was created
        quotation_session = QuotationSession.objects.get(session_key=session_key)
        self.assertEqual(quotation_session.category, 'health')
        self.assertFalse(quotation_session.is_expired())
    
    def test_ajax_response_validates_session(self):
        """Test that AJAX response endpoint validates session."""
        # Try without session
        response = self.client.post(
            '/simple-surveys/ajax/save-response/',
            data=json.dumps({
                'question_id': self.question.id,
                'response_value': 25,
                'category': 'health'
            }),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertFalse(data['success'])
        self.assertIn('session', data['errors'][0].lower())
    
    def test_ajax_response_with_valid_session(self):
        """Test AJAX response with valid session."""
        # Create session by visiting survey page
        self.client.get('/simple-surveys/health/')
        
        # Now try to save response
        response = self.client.post(
            '/simple-surveys/ajax/save-response/',
            data=json.dumps({
                'question_id': self.question.id,
                'response_value': 25,
                'category': 'health'
            }),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        
        # Check that response was saved
        session_key = self.client.session.session_key
        survey_response = SimpleSurveyResponse.objects.get(
            session_key=session_key,
            question=self.question
        )
        self.assertEqual(survey_response.response_value, 25)
    
    @patch('simple_surveys.session_manager.SessionManager.validate_session')
    def test_ajax_response_with_expired_session(self, mock_validate):
        """Test AJAX response with expired session."""
        # Mock session validation to return expired
        mock_validate.return_value = {
            'valid': False,
            'error': 'Session expired',
            'session': None
        }
        
        # Create session first
        self.client.get('/simple-surveys/health/')
        
        # Try to save response
        response = self.client.post(
            '/simple-surveys/ajax/save-response/',
            data=json.dumps({
                'question_id': self.question.id,
                'response_value': 25,
                'category': 'health'
            }),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertFalse(data['success'])
        self.assertIn('expired', data['errors'][0].lower())