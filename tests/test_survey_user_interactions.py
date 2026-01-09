"""
Test user interactions with survey functionality.
Tests user flows, session management, and interactive features.
"""

import json
from unittest.mock import patch, MagicMock
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.messages import get_messages

from policies.models import PolicyCategory
from comparison.models import ComparisonSession
from surveys.models import SurveyQuestion, SurveyResponse

User = get_user_model()


class UserSurveyFlowTests(TestCase):
    """Test complete user survey flow."""
    
    def setUp(self):
        self.client = Client()
        self.category = PolicyCategory.objects.create(
            name="Health Insurance",
            slug="health",
            description="Health insurance policies"
        )
        
        self.questions = [
            SurveyQuestion.objects.create(
                category=self.category,
                section="Personal Info",
                question_text="What is your age?",
                question_type=SurveyQuestion.QuestionType.NUMBER,
                field_name="age",
                validation_rules={"min_value": 18, "max_value": 100},
                is_required=True,
                display_order=1
            ),
            SurveyQuestion.objects.create(
                category=self.category,
                section="Personal Info",
                question_text="What is your name?",
                question_type=SurveyQuestion.QuestionType.TEXT,
                field_name="name",
                is_required=True,
                display_order=2
            ),
            SurveyQuestion.objects.create(
                category=self.category,
                section="Health Status",
                question_text="Do you smoke?",
                question_type=SurveyQuestion.QuestionType.BOOLEAN,
                field_name="smoker",
                is_required=True,
                display_order=3
            )
        ]
        
    @patch('surveys.views.SurveyFlowController')
    def test_complete_survey_flow(self, mock_flow_controller):
        """Test complete user survey flow from start to finish."""
        # Mock flow controller for different stages
        mock_instance = MagicMock()
        mock_instance.session_key = "test-session-123"
        mock_instance.category = self.category
        mock_instance.validate_session.return_value = True
        mock_flow_controller.return_value = mock_instance
        
        # Stage 1: Start survey
        mock_instance.get_current_section_and_question.return_value = ("Personal Info", self.questions[0])
        mock_instance.engine.get_survey_sections.return_value = [
            {"name": "Personal Info", "progress": 0.0}
        ]
        mock_instance.get_section_progress.return_value = {"Personal Info": 0.0}
        mock_instance.get_survey_summary.return_value = {
            'completion_percentage': 0.0,
            'total_questions': 3,
            'answered_questions': 0
        }
        
        response = self.client.get(reverse('surveys:survey_form', kwargs={
            'category_slug': 'health'
        }) + '?session=test-session-123')
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.questions[0].question_text)
        
        # Stage 2: Answer first question
        session = ComparisonSession.objects.create(
            session_key="test-session-123",
            category=self.category
        )
        
        mock_instance.session = session
        mock_instance.get_next_question.return_value = {
            'success': True,
            'question': self.questions[1]
        }
        
        response = self.client.post(reverse('surveys:survey_form', kwargs={
            'category_slug': 'health'
        }) + '?session=test-session-123', {
            'response_value': 35,
            'confidence_level': 4
        })
        
        self.assertEqual(response.status_code, 302)  # Redirect to next question
        
        # Verify response was saved
        survey_response = SurveyResponse.objects.get(session=session, question=self.questions[0])
        self.assertEqual(survey_response.response_value, 35)
        
        # Stage 3: Continue with second question
        mock_instance.get_current_section_and_question.return_value = ("Personal Info", self.questions[1])
        mock_instance.get_survey_summary.return_value = {
            'completion_percentage': 33.3,
            'total_questions': 3,
            'answered_questions': 1
        }
        
        response = self.client.get(reverse('surveys:survey_form', kwargs={
            'category_slug': 'health'
        }) + '?session=test-session-123')
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.questions[1].question_text)
        
    @patch('surveys.views.SurveyFlowController')
    def test_survey_navigation_between_sections(self, mock_flow_controller):
        """Test user navigation between survey sections."""
        mock_instance = MagicMock()
        mock_instance.session_key = "test-session-123"
        mock_instance.category = self.category
        mock_instance.validate_session.return_value = True
        mock_flow_controller.return_value = mock_instance
        
        # Test navigation to specific section
        mock_instance.navigate_to_section.return_value = {
            'success': True,
            'question': self.questions[2],  # Health Status section
            'url': f'/surveys/health/?session=test-session-123&question={self.questions[2].id}'
        }
        
        response = self.client.get(reverse('surveys:survey_section', kwargs={
            'category_slug': 'health',
            'section_name': 'health-status'
        }) + '?session=test-session-123')
        
        self.assertEqual(response.status_code, 302)
        self.assertIn(f'question={self.questions[2].id}', response.url)
        
    @patch('surveys.views.SurveyFlowController')
    def test_survey_progress_tracking(self, mock_flow_controller):
        """Test survey progress tracking functionality."""
        session = ComparisonSession.objects.create(
            session_key="test-session-123",
            category=self.category
        )
        
        # Create some responses
        SurveyResponse.objects.create(
            session=session,
            question=self.questions[0],
            response_value=35,
            confidence_level=4
        )
        
        SurveyResponse.objects.create(
            session=session,
            question=self.questions[1],
            response_value="John Doe",
            confidence_level=5
        )
        
        response = self.client.get(reverse('surveys:survey_progress_view', kwargs={
            'session_key': 'test-session-123'
        }))
        
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.content)
        self.assertEqual(data['session_key'], 'test-session-123')
        self.assertEqual(data['total_responses'], 2)
        self.assertEqual(data['total_questions'], 3)
        self.assertAlmostEqual(data['completion_percentage'], 66.67, places=1)
        
    def test_survey_session_validation(self):
        """Test survey session validation."""
        # Test with invalid session
        response = self.client.get(reverse('surveys:survey_progress_view', kwargs={
            'session_key': 'invalid-session'
        }))
        
        self.assertEqual(response.status_code, 404)
        
    @patch('surveys.views.SurveyFlowController')
    def test_ajax_response_submission(self, mock_flow_controller):
        """Test AJAX response submission."""
        mock_instance = MagicMock()
        mock_instance.validate_session.return_value = True
        mock_instance.submit_response.return_value = {
            'success': True,
            'message': 'Response saved successfully'
        }
        mock_flow_controller.return_value = mock_instance
        
        response = self.client.post(reverse('surveys:submit_response_ajax'),
            json.dumps({
                'session_key': 'test-session-123',
                'category_slug': 'health',
                'question_id': self.questions[0].id,
                'response_value': 35,
                'confidence_level': 4
            }),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        self.assertEqual(data['message'], 'Response saved successfully')


class UserErrorHandlingTests(TestCase):
    """Test user error handling scenarios."""
    
    def setUp(self):
        self.client = Client()
        self.category = PolicyCategory.objects.create(
            name="Health Insurance",
            slug="health",
            description="Health insurance policies"
        )
        
    def test_invalid_category_handling(self):
        """Test handling of invalid category."""
        response = self.client.get(reverse('surveys:direct_survey', kwargs={
            'category_slug': 'nonexistent'
        }))
        
        # Should handle gracefully
        self.assertIn(response.status_code, [302, 404, 500])
        
    @patch('surveys.views.SurveyFlowController')
    def test_expired_session_handling(self, mock_flow_controller):
        """Test handling of expired sessions."""
        mock_instance = MagicMock()
        mock_instance.validate_session.return_value = False
        mock_flow_controller.return_value = mock_instance
        
        response = self.client.get(reverse('surveys:survey_form', kwargs={
            'category_slug': 'health'
        }) + '?session=expired-session')
        
        self.assertEqual(response.status_code, 302)
        
        # Check for error message
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any('expired' in str(message) for message in messages))
        
    def test_malformed_ajax_request(self):
        """Test handling of malformed AJAX requests."""
        response = self.client.post(reverse('surveys:submit_response_ajax'),
            'invalid json',
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
        
    def test_missing_ajax_parameters(self):
        """Test handling of missing AJAX parameters."""
        response = self.client.post(reverse('surveys:submit_response_ajax'),
            json.dumps({
                'session_key': 'test-session-123',
                # Missing required parameters
            }),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)


class UserAccessibilityTests(TestCase):
    """Test accessibility features for users."""
    
    def setUp(self):
        self.client = Client()
        self.category = PolicyCategory.objects.create(
            name="Health Insurance",
            slug="health",
            description="Health insurance policies"
        )
        
        self.question = SurveyQuestion.objects.create(
            category=self.category,
            section="Personal Info",
            question_text="What is your age?",
            question_type=SurveyQuestion.QuestionType.NUMBER,
            field_name="age",
            help_text="Enter your age in years",
            is_required=True
        )
        
    @patch('surveys.views.SurveyFlowController')
    def test_form_accessibility_attributes(self, mock_flow_controller):
        """Test that forms include proper accessibility attributes."""
        mock_instance = MagicMock()
        mock_instance.session_key = "test-session-123"
        mock_instance.category = self.category
        mock_instance.validate_session.return_value = True
        mock_instance.get_current_section_and_question.return_value = ("Personal Info", self.question)
        mock_instance.engine.get_survey_sections.return_value = []
        mock_instance.get_section_progress.return_value = {}
        mock_instance.get_survey_summary.return_value = {'completion_percentage': 25.0}
        mock_flow_controller.return_value = mock_instance
        
        response = self.client.get(reverse('surveys:survey_form', kwargs={
            'category_slug': 'health'
        }) + '?session=test-session-123')
        
        self.assertEqual(response.status_code, 200)
        
        # Check for accessibility attributes in form
        content = response.content.decode()
        self.assertIn('aria-', content)  # Should have ARIA attributes
        self.assertIn('role=', content)  # Should have role attributes
        
    @patch('surveys.views.SurveyFlowController')
    def test_keyboard_navigation_support(self, mock_flow_controller):
        """Test keyboard navigation support."""
        mock_instance = MagicMock()
        mock_instance.session_key = "test-session-123"
        mock_instance.category = self.category
        mock_instance.validate_session.return_value = True
        mock_instance.get_current_section_and_question.return_value = ("Personal Info", self.question)
        mock_instance.engine.get_survey_sections.return_value = []
        mock_instance.get_section_progress.return_value = {}
        mock_instance.get_survey_summary.return_value = {'completion_percentage': 25.0}
        mock_flow_controller.return_value = mock_instance
        
        response = self.client.get(reverse('surveys:survey_form', kwargs={
            'category_slug': 'health'
        }) + '?session=test-session-123')
        
        self.assertEqual(response.status_code, 200)
        
        # Check for keyboard navigation support
        content = response.content.decode()
        self.assertIn('tabindex', content)  # Should have tab order
        
    def test_screen_reader_support(self):
        """Test screen reader support features."""
        # This would typically test for proper heading structure,
        # alt text, and other screen reader features
        pass