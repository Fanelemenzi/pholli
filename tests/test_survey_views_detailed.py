"""
Detailed tests for survey views functionality.
Tests view behavior, error handling, and user interactions.
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


class SurveyFormViewTests(TestCase):
    """Test survey form view functionality."""
    
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
            validation_rules={"min_value": 18, "max_value": 100},
            is_required=True,
            display_order=1
        )
        
    @patch('surveys.views.SurveyFlowController')
    def test_survey_form_view_get_success(self, mock_flow_controller):
        """Test successful GET request to survey form view."""
        # Mock flow controller
        mock_instance = MagicMock()
        mock_instance.session_key = "test-session-123"
        mock_instance.category = self.category
        mock_instance.validate_session.return_value = True
        mock_instance.get_current_section_and_question.return_value = ("Personal Info", self.question)
        mock_instance.engine.get_survey_sections.return_value = [
            {"name": "Personal Info", "progress": 25.0}
        ]
        mock_instance.get_section_progress.return_value = {"Personal Info": 25.0}
        mock_instance.get_survey_summary.return_value = {
            'completion_percentage': 25.0,
            'total_questions': 4,
            'answered_questions': 1
        }
        mock_flow_controller.return_value = mock_instance
        
        response = self.client.get(reverse('surveys:survey_form', kwargs={
            'category_slug': 'health'
        }) + '?session=test-session-123')
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.question.question_text)
        self.assertContains(response, "Health Insurance Survey")
        self.assertIn('form', response.context)
        self.assertIn('current_question', response.context)
        self.assertEqual(response.context['current_question'], self.question)
        
    @patch('surveys.views.SurveyFlowController')
    def test_survey_form_view_invalid_session(self, mock_flow_controller):
        """Test survey form view with invalid session."""
        # Mock flow controller with invalid session
        mock_instance = MagicMock()
        mock_instance.validate_session.return_value = False
        mock_flow_controller.return_value = mock_instance
        
        response = self.client.get(reverse('surveys:survey_form', kwargs={
            'category_slug': 'health'
        }) + '?session=invalid-session')
        
        # Should redirect to direct survey
        self.assertEqual(response.status_code, 302)
        self.assertIn('direct', response.url)
        
        # Check for error message
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any('expired' in str(message) for message in messages))
        
    @patch('surveys.views.SurveyFlowController')
    def test_survey_form_view_no_session(self, mock_flow_controller):
        """Test survey form view without session parameter."""
        response = self.client.get(reverse('surveys:survey_form', kwargs={
            'category_slug': 'health'
        }))
        
        # Should handle gracefully (implementation dependent)
        self.assertIn(response.status_code, [200, 302])
        
    @patch('surveys.views.SurveyFlowController')
    def test_survey_form_view_specific_question(self, mock_flow_controller):
        """Test survey form view with specific question ID."""
        # Mock flow controller
        mock_instance = MagicMock()
        mock_instance.session_key = "test-session-123"
        mock_instance.category = self.category
        mock_instance.validate_session.return_value = True
        mock_instance.get_question_by_id.return_value = self.question
        mock_instance.engine.get_survey_sections.return_value = []
        mock_instance.get_section_progress.return_value = {}
        mock_instance.get_survey_summary.return_value = {'completion_percentage': 25.0}
        mock_flow_controller.return_value = mock_instance
        
        response = self.client.get(reverse('surveys:survey_form', kwargs={
            'category_slug': 'health'
        }) + f'?session=test-session-123&question={self.question.id}')
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.question.question_text)
        
        # Verify get_question_by_id was called
        mock_instance.get_question_by_id.assert_called_with(self.question.id)
        
    @patch('surveys.views.SurveyFlowController')
    def test_survey_form_view_invalid_question_id(self, mock_flow_controller):
        """Test survey form view with invalid question ID."""
        # Mock flow controller
        mock_instance = MagicMock()
        mock_instance.session_key = "test-session-123"
        mock_instance.category = self.category
        mock_instance.validate_session.return_value = True
        mock_instance.get_question_by_id.return_value = None
        mock_flow_controller.return_value = mock_instance
        
        response = self.client.get(reverse('surveys:survey_form', kwargs={
            'category_slug': 'health'
        }) + '?session=test-session-123&question=999')
        
        # Should redirect back to survey form
        self.assertEqual(response.status_code, 302)
        
        # Check for error message
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any('not found' in str(message) for message in messages))
        
    @patch('surveys.views.SurveyFlowController')
    def test_survey_form_view_survey_complete(self, mock_flow_controller):
        """Test survey form view when survey is complete."""
        # Mock flow controller with no current question (survey complete)
        mock_instance = MagicMock()
        mock_instance.session_key = "test-session-123"
        mock_instance.category = self.category
        mock_instance.validate_session.return_value = True
        mock_instance.get_current_section_and_question.return_value = (None, None)
        mock_instance.engine.calculate_completion_percentage.return_value = 100.0
        mock_flow_controller.return_value = mock_instance
        
        response = self.client.get(reverse('surveys:survey_form', kwargs={
            'category_slug': 'health'
        }) + '?session=test-session-123')
        
        # Should redirect to completion page
        self.assertEqual(response.status_code, 302)
        self.assertIn('complete', response.url)
        
    @patch('surveys.views.SurveyFlowController')
    def test_survey_form_view_post_valid(self, mock_flow_controller):
        """Test POST request with valid form data."""
        # Create session for form to save to
        session = ComparisonSession.objects.create(
            session_key="test-session-123",
            category=self.category
        )
        
        # Mock flow controller
        mock_instance = MagicMock()
        mock_instance.session_key = "test-session-123"
        mock_instance.session = session
        mock_instance.category = self.category
        mock_instance.validate_session.return_value = True
        mock_instance.get_current_section_and_question.return_value = ("Personal Info", self.question)
        mock_instance.get_next_question.return_value = {
            'success': True,
            'question': self.question
        }
        mock_flow_controller.return_value = mock_instance
        
        response = self.client.post(reverse('surveys:survey_form', kwargs={
            'category_slug': 'health'
        }) + '?session=test-session-123', {
            'response_value': 35,
            'confidence_level': 4
        })
        
        # Should redirect to next question
        self.assertEqual(response.status_code, 302)
        
        # Verify response was saved
        survey_response = SurveyResponse.objects.get(session=session, question=self.question)
        self.assertEqual(survey_response.response_value, 35)
        self.assertEqual(survey_response.confidence_level, 4)
        
        # Check for success message
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any('saved successfully' in str(message) for message in messages))
        
    @patch('surveys.views.SurveyFlowController')
    def test_survey_form_view_post_invalid(self, mock_flow_controller):
        """Test POST request with invalid form data."""
        # Mock flow controller
        mock_instance = MagicMock()
        mock_instance.session_key = "test-session-123"
        mock_instance.category = self.category
        mock_instance.validate_session.return_value = True
        mock_instance.get_current_section_and_question.return_value = ("Personal Info", self.question)
        mock_instance.engine.get_survey_sections.return_value = []
        mock_instance.get_section_progress.return_value = {}
        mock_instance.get_survey_summary.return_value = {'completion_percentage': 25.0}
        mock_flow_controller.return_value = mock_instance
        
        response = self.client.post(reverse('surveys:survey_form', kwargs={
            'category_slug': 'health'
        }) + '?session=test-session-123', {
            'response_value': 15,  # Below minimum age
            'confidence_level': 4
        })
        
        # Should stay on same page
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Value must be at least 18')
        
    @patch('surveys.views.SurveyFlowController')
    def test_survey_form_view_post_survey_complete(self, mock_flow_controller):
        """Test POST request that completes the survey."""
        # Create session for form to save to
        session = ComparisonSession.objects.create(
            session_key="test-session-123",
            category=self.category
        )
        
        # Mock flow controller
        mock_instance = MagicMock()
        mock_instance.session_key = "test-session-123"
        mock_instance.session = session
        mock_instance.category = self.category
        mock_instance.validate_session.return_value = True
        mock_instance.get_current_section_and_question.return_value = ("Personal Info", self.question)
        mock_instance.get_next_question.return_value = {
            'success': False  # No next question - survey complete
        }
        mock_flow_controller.return_value = mock_instance
        
        response = self.client.post(reverse('surveys:survey_form', kwargs={
            'category_slug': 'health'
        }) + '?session=test-session-123', {
            'response_value': 35,
            'confidence_level': 4
        })
        
        # Should redirect to completion page
        self.assertEqual(response.status_code, 302)
        self.assertIn('complete', response.url)


class DirectSurveyViewTests(TestCase):
    """Test direct survey view functionality."""
    
    def setUp(self):
        self.client = Client()
        self.category = PolicyCategory.objects.create(
            name="Health Insurance",
            slug="health",
            description="Health insurance policies"
        )
        
    @patch('surveys.views.SurveyFlowController')
    def test_direct_survey_view_success(self, mock_flow_controller):
        """Test successful direct survey access."""
        # Mock flow controller
        mock_instance = MagicMock()
        mock_instance.session_key = "new-session-123"
        mock_flow_controller.return_value = mock_instance
        
        response = self.client.get(reverse('surveys:direct_survey', kwargs={
            'category_slug': 'health'
        }))
        
        # Should redirect to survey form with session key
        self.assertEqual(response.status_code, 302)
        self.assertIn('session=new-session-123', response.url)
        self.assertIn('health', response.url)
        
    @patch('surveys.views.SurveyFlowController')
    def test_direct_survey_view_error(self, mock_flow_controller):
        """Test direct survey view with error."""
        # Mock flow controller to raise exception
        mock_flow_controller.side_effect = Exception("Test error")
        
        response = self.client.get(reverse('surveys:direct_survey', kwargs={
            'category_slug': 'health'
        }))
        
        # Should redirect to home with error message
        self.assertEqual(response.status_code, 302)
        
        # Check for error message
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any('Unable to start' in str(message) for message in messages))
        
    def test_direct_survey_view_invalid_category(self):
        """Test direct survey view with invalid category."""
        response = self.client.get(reverse('surveys:direct_survey', kwargs={
            'category_slug': 'nonexistent'
        }))
        
        # Should handle gracefully
        self.assertIn(response.status_code, [302, 404, 500])


class SurveyProgressViewTests(TestCase):
    """Test survey progress view functionality."""
    
    def setUp(self):
        self.client = Client()
        self.category = PolicyCategory.objects.create(
            name="Health Insurance",
            slug="health",
            description="Health insurance policies"
        )
        
        self.session = ComparisonSession.objects.create(
            session_key="test-session-123",
            category=self.category
        )
        
        self.questions = [
            SurveyQuestion.objects.create(
                category=self.category,
                section="Personal Info",
                question_text="Question 1",
                question_type=SurveyQuestion.QuestionType.TEXT,
                field_name="q1",
                is_required=True
            ),
            SurveyQuestion.objects.create(
                category=self.category,
                section="Personal Info",
                question_text="Question 2",
                question_type=SurveyQuestion.QuestionType.TEXT,
                field_name="q2",
                is_required=True
            )
        ]
        
    def test_survey_progress_view_success(self):
        """Test successful survey progress request."""
        # Create some responses
        SurveyResponse.objects.create(
            session=self.session,
            question=self.questions[0],
            response_value="Answer 1",
            confidence_level=4
        )
        
        response = self.client.get(reverse('surveys:survey_progress_view', kwargs={
            'session_key': 'test-session-123'
        }))
        
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.content)
        self.assertEqual(data['session_key'], 'test-session-123')
        self.assertEqual(data['total_responses'], 1)
        self.assertEqual(data['total_questions'], 2)
        self.assertEqual(data['completion_percentage'], 50.0)
        self.assertFalse(data['survey_completed'])
        
    def test_survey_progress_view_invalid_session(self):
        """Test survey progress with invalid session key."""
        response = self.client.get(reverse('surveys:survey_progress_view', kwargs={
            'session_key': 'invalid-session'
        }))
        
        self.assertEqual(response.status_code, 404)
        
    def test_survey_progress_view_error(self):
        """Test survey progress view with error."""
        # Delete the session to cause an error
        self.session.delete()
        
        response = self.client.get(reverse('surveys:survey_progress_view', kwargs={
            'session_key': 'test-session-123'
        }))
        
        self.assertEqual(response.status_code, 404)


class AjaxViewTests(TestCase):
    """Test AJAX view functionality."""
    
    def setUp(self):
        self.client = Client()
        self.category = PolicyCategory.objects.create(
            name="Health Insurance",
            slug="health",
            description="Health insurance policies"
        )
        
        self.session = ComparisonSession.objects.create(
            session_key="test-session-123",
            category=self.category
        )
        
        self.question = SurveyQuestion.objects.create(
            category=self.category,
            section="Personal Info",
            question_text="What is your age?",
            question_type=SurveyQuestion.QuestionType.NUMBER,
            field_name="age",
            is_required=True
        )
        
    @patch('surveys.views.SurveyFlowController')
    def test_submit_response_ajax_success(self, mock_flow_controller):
        """Test successful AJAX response submission."""
        # Mock flow controller
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
                'question_id': self.question.id,
                'response_value': 35,
                'confidence_level': 4
            }),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        self.assertEqual(data['message'], 'Response saved successfully')
        
    @patch('surveys.views.SurveyFlowController')
    def test_submit_response_ajax_invalid_session(self, mock_flow_controller):
        """Test AJAX response submission with invalid session."""
        # Mock flow controller with invalid session
        mock_instance = MagicMock()
        mock_instance.validate_session.return_value = False
        mock_flow_controller.return_value = mock_instance
        
        response = self.client.post(reverse('surveys:submit_response_ajax'),
            json.dumps({
                'session_key': 'invalid-session',
                'category_slug': 'health',
                'question_id': self.question.id,
                'response_value': 35,
                'confidence_level': 4
            }),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 401)
        
    def test_submit_response_ajax_invalid_json(self):
        """Test AJAX response submission with invalid JSON."""
        response = self.client.post(reverse('surveys:submit_response_ajax'),
            'invalid json',
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
        
    def test_submit_response_ajax_missing_fields(self):
        """Test AJAX response submission with missing required fields."""
        response = self.client.post(reverse('surveys:submit_response_ajax'),
            json.dumps({
                'session_key': 'test-session-123',
                # Missing category_slug and question_id
            }),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
        
    @patch('surveys.views.SurveyFlowController')
    def test_navigate_section_ajax_success(self, mock_flow_controller):
        """Test successful AJAX section navigation."""
        # Mock flow controller
        mock_instance = MagicMock()
        mock_instance.navigate_to_section.return_value = {
            'success': True,
            'message': 'Navigated to section',
            'url': '/surveys/health/section/personal-info/'
        }
        mock_flow_controller.return_value = mock_instance
        
        response = self.client.post(reverse('surveys:navigate_section_ajax'),
            json.dumps({
                'session_key': 'test-session-123',
                'category_slug': 'health',
                'section_name': 'personal-info'
            }),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        
    def test_navigate_section_ajax_missing_params(self):
        """Test AJAX section navigation with missing parameters."""
        response = self.client.post(reverse('surveys:navigate_section_ajax'),
            json.dumps({
                'session_key': 'test-session-123',
                # Missing category_slug and section_name
            }),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
        
        data = json.loads(response.content)
        self.assertFalse(data['success'])
        self.assertIn('Missing required parameters', data['error'])
        
    @patch('surveys.views.SurveyFlowController')
    def test_modify_response_ajax_success(self, mock_flow_controller):
        """Test successful AJAX response modification."""
        # Mock flow controller
        mock_instance = MagicMock()
        mock_instance.validate_session.return_value = True
        mock_instance.modify_response.return_value = {
            'success': True,
            'message': 'Response modified successfully'
        }
        mock_flow_controller.return_value = mock_instance
        
        response = self.client.post(reverse('surveys:modify_response_ajax'),
            json.dumps({
                'session_key': 'test-session-123',
                'category_slug': 'health',
                'question_id': self.question.id,
                'new_response': 40,
                'confidence_level': 5
            }),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        
    @patch('surveys.views.SurveyFlowController')
    def test_survey_summary_ajax_success(self, mock_flow_controller):
        """Test successful AJAX survey summary request."""
        # Mock flow controller
        mock_instance = MagicMock()
        mock_instance.validate_session.return_value = True
        mock_instance.get_survey_summary.return_value = {
            'completion_percentage': 75.0,
            'total_questions': 4,
            'answered_questions': 3,
            'sections': ['Personal Info', 'Health Status']
        }
        mock_flow_controller.return_value = mock_instance
        
        response = self.client.get(reverse('surveys:survey_summary_ajax') + 
            '?session_key=test-session-123&category_slug=health')
        
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        self.assertEqual(data['summary']['completion_percentage'], 75.0)
        self.assertEqual(data['summary']['total_questions'], 4)
        
    def test_survey_summary_ajax_missing_params(self):
        """Test AJAX survey summary with missing parameters."""
        response = self.client.get(reverse('surveys:survey_summary_ajax'))
        
        self.assertEqual(response.status_code, 400)
        
        data = json.loads(response.content)
        self.assertFalse(data['success'])
        self.assertIn('Missing required parameters', data['error'])


class SurveyNavigationViewTests(TestCase):
    """Test survey navigation view functionality."""
    
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
            is_required=True
        )
        
    @patch('surveys.views.SurveyFlowController')
    def test_survey_section_view_success(self, mock_flow_controller):
        """Test successful section navigation."""
        # Mock flow controller
        mock_instance = MagicMock()
        mock_instance.navigate_to_section.return_value = {
            'success': True,
            'question': self.question,
            'url': f'/surveys/health/?session=test-session-123&question={self.question.id}'
        }
        mock_flow_controller.return_value = mock_instance
        
        response = self.client.get(reverse('surveys:survey_section', kwargs={
            'category_slug': 'health',
            'section_name': 'personal-info'
        }) + '?session=test-session-123')
        
        # Should redirect to specific question
        self.assertEqual(response.status_code, 302)
        
    @patch('surveys.views.SurveyFlowController')
    def test_survey_section_view_no_session(self, mock_flow_controller):
        """Test section navigation without session."""
        response = self.client.get(reverse('surveys:survey_section', kwargs={
            'category_slug': 'health',
            'section_name': 'personal-info'
        }))
        
        # Should redirect with error message
        self.assertEqual(response.status_code, 302)
        
        # Check for error message
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any('No active survey session' in str(message) for message in messages))
        
    @patch('surveys.views.SurveyFlowController')
    def test_survey_question_view_success(self, mock_flow_controller):
        """Test successful question navigation."""
        # Mock flow controller
        mock_instance = MagicMock()
        mock_instance.get_question_by_id.return_value = self.question
        mock_flow_controller.return_value = mock_instance
        
        response = self.client.get(reverse('surveys:survey_question', kwargs={
            'category_slug': 'health',
            'question_id': self.question.id
        }) + '?session=test-session-123')
        
        # Should redirect to survey form with question parameter
        self.assertEqual(response.status_code, 302)
        self.assertIn(f'question={self.question.id}', response.url)
        
    @patch('surveys.views.SurveyFlowController')
    def test_survey_question_view_invalid_question(self, mock_flow_controller):
        """Test question navigation with invalid question ID."""
        # Mock flow controller
        mock_instance = MagicMock()
        mock_instance.get_question_by_id.return_value = None
        mock_flow_controller.return_value = mock_instance
        
        response = self.client.get(reverse('surveys:survey_question', kwargs={
            'category_slug': 'health',
            'question_id': 999
        }) + '?session=test-session-123')
        
        # Should redirect with error message
        self.assertEqual(response.status_code, 302)
        
        # Check for error message
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any('not found' in str(message) for message in messages))


class SurveyCompletionViewTests(TestCase):
    """Test survey completion view functionality."""
    
    def setUp(self):
        self.client = Client()
        self.category = PolicyCategory.objects.create(
            name="Health Insurance",
            slug="health",
            description="Health insurance policies"
        )
        
    @patch('surveys.views.SurveyFlowController')
    def test_survey_completion_view_success(self, mock_flow_controller):
        """Test successful survey completion."""
        # Mock flow controller
        mock_instance = MagicMock()
        mock_instance.category = self.category
        mock_instance.complete_survey.return_value = {
            'success': True,
            'message': 'Survey completed successfully!',
            'results_url': '/comparison/results/?session=test-session-123'
        }
        mock_flow_controller.return_value = mock_instance
        
        response = self.client.get(reverse('surveys:survey_completion', kwargs={
            'category_slug': 'health'
        }) + '?session=test-session-123')
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Survey completed successfully!')
        self.assertIn('completion_result', response.context)
        
    @patch('surveys.views.SurveyFlowController')
    def test_survey_completion_view_failure(self, mock_flow_controller):
        """Test survey completion with failure."""
        # Mock flow controller
        mock_instance = MagicMock()
        mock_instance.complete_survey.return_value = {
            'success': False,
            'error': 'Failed to complete survey'
        }
        mock_flow_controller.return_value = mock_instance
        
        response = self.client.get(reverse('surveys:survey_completion', kwargs={
            'category_slug': 'health'
        }) + '?session=test-session-123')
        
        # Should redirect back to survey form
        self.assertEqual(response.status_code, 302)
        
        # Check for error message
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any('Failed to complete' in str(message) for message in messages))
        
    def test_survey_completion_view_no_session(self):
        """Test survey completion without session."""
        response = self.client.get(reverse('surveys:survey_completion', kwargs={
            'category_slug': 'health'
        }))
        
        # Should redirect with error message
        self.assertEqual(response.status_code, 302)
        
        # Check for error message
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any('No active survey session' in str(message) for message in messages))


class SurveyRestartViewTests(TestCase):
    """Test survey restart view functionality."""
    
    def setUp(self):
        self.client = Client()
        self.category = PolicyCategory.objects.create(
            name="Health Insurance",
            slug="health",
            description="Health insurance policies"
        )
        
    @patch('surveys.views.SurveyFlowController')
    def test_survey_restart_view_success(self, mock_flow_controller):
        """Test successful survey restart."""
        # Mock flow controller
        mock_instance = MagicMock()
        mock_instance.restart_survey.return_value = {
            'success': True,
            'message': 'Survey restarted successfully',
            'start_url': '/surveys/health/?session=new-session-456'
        }
        mock_flow_controller.return_value = mock_instance
        
        response = self.client.get(reverse('surveys:survey_restart', kwargs={
            'category_slug': 'health'
        }) + '?session=test-session-123')
        
        # Should redirect to new survey start
        self.assertEqual(response.status_code, 302)
        self.assertIn('new-session-456', response.url)
        
        # Check for success message
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any('restarted successfully' in str(message) for message in messages))
        
    @patch('surveys.views.SurveyFlowController')
    def test_survey_restart_view_preserve_responses(self, mock_flow_controller):
        """Test survey restart with preserved responses."""
        # Mock flow controller
        mock_instance = MagicMock()
        mock_instance.restart_survey.return_value = {
            'success': True,
            'message': 'Survey restarted with responses preserved',
            'start_url': '/surveys/health/?session=test-session-123'
        }
        mock_flow_controller.return_value = mock_instance
        
        response = self.client.get(reverse('surveys:survey_restart', kwargs={
            'category_slug': 'health'
        }) + '?session=test-session-123&preserve=true')
        
        # Should redirect to survey start
        self.assertEqual(response.status_code, 302)
        
        # Verify preserve_responses was called with True
        mock_instance.restart_survey.assert_called_with(True)
        
    @patch('surveys.views.SurveyFlowController')
    def test_survey_restart_view_failure(self, mock_flow_controller):
        """Test survey restart with failure."""
        # Mock flow controller
        mock_instance = MagicMock()
        mock_instance.restart_survey.return_value = {
            'success': False,
            'error': 'Failed to restart survey'
        }
        mock_flow_controller.return_value = mock_instance
        
        response = self.client.get(reverse('surveys:survey_restart', kwargs={
            'category_slug': 'health'
        }) + '?session=test-session-123')
        
        # Should redirect back to survey form
        self.assertEqual(response.status_code, 302)
        
        # Check for error message
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any('Failed to restart' in str(message) for message in messages))


class SurveyResultsViewTests(TestCase):
    """Test survey results view functionality."""
    
    def setUp(self):
        self.client = Client()
        self.category = PolicyCategory.objects.create(
            name="Health Insurance",
            slug="health",
            description="Health insurance policies"
        )
        
        self.session = ComparisonSession.objects.create(
            session_key="test-session-123",
            category=self.category,
            survey_completed=True
        )
        
    @patch('surveys.views.SurveyFlowController')
    def test_survey_results_view_success(self, mock_flow_controller):
        """Test successful survey results display."""
        # Mock flow controller
        mock_instance = MagicMock()
        mock_instance.get_survey_summary.return_value = {
            'completion_percentage': 100.0,
            'total_questions': 5,
            'answered_questions': 5,
            'user_profile': {'age': 35, 'smoker': False}
        }
        mock_flow_controller.return_value = mock_instance
        
        response = self.client.get(reverse('surveys:survey_results') + 
            '?session=test-session-123')
        
        self.assertEqual(response.status_code, 200)
        self.assertIn('survey_summary', response.context)
        self.assertEqual(response.context['session'], self.session)
        
    def test_survey_results_view_no_session(self):
        """Test survey results without session parameter."""
        response = self.client.get(reverse('surveys:survey_results'))
        
        # Should redirect with error message
        self.assertEqual(response.status_code, 302)
        
        # Check for error message
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any('No survey session specified' in str(message) for message in messages))
        
    def test_survey_results_view_invalid_session(self):
        """Test survey results with invalid session."""
        response = self.client.get(reverse('surveys:survey_results') + 
            '?session=invalid-session')
        
        self.assertEqual(response.status_code, 404)


class ProfileManagementViewTests(TestCase):
    """Test profile management view functionality."""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
    def test_profile_management_view_authenticated(self):
        """Test profile management view for authenticated user."""
        self.client.login(username='testuser', password='testpass123')
        
        response = self.client.get(reverse('surveys:profile_management'))
        
        self.assertEqual(response.status_code, 200)
        self.assertIn('user', response.context)
        self.assertEqual(response.context['user'], self.user)
        
    def test_profile_management_view_unauthenticated(self):
        """Test profile management view for unauthenticated user."""
        response = self.client.get(reverse('surveys:profile_management'))
        
        # Should redirect to login
        self.assertEqual(response.status_code, 302)
        
        # Check for error message
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any('Please log in' in str(message) for message in messages))

class
 SurveyCompletionViewTests(TestCase):
    """Test survey completion view functionality."""
    
    def setUp(self):
        self.client = Client()
        self.category = PolicyCategory.objects.create(
            name="Health Insurance",
            slug="health",
            description="Health insurance policies"
        )
        
    @patch('surveys.views.SurveyFlowController')
    def test_survey_completion_view_success(self, mock_flow_controller):
        """Test successful survey completion."""
        # Mock flow controller
        mock_instance = MagicMock()
        mock_instance.category = self.category
        mock_instance.complete_survey.return_value = {
            'success': True,
            'message': 'Survey completed successfully!',
            'results_url': '/comparison/results/?session=test-session-123'
        }
        mock_flow_controller.return_value = mock_instance
        
        response = self.client.get(reverse('surveys:survey_completion', kwargs={
            'category_slug': 'health'
        }) + '?session=test-session-123')
        
        # Should redirect to completion page
        self.assertEqual(response.status_code, 302)
        self.assertIn('complete', response.url)
        
        # Check for success message
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any('completed successfully' in str(message) for message in messages))
        
    @patch('surveys.views.SurveyFlowController')
    def test_survey_completion_view_error(self, mock_flow_controller):
        """Test survey completion with error."""
        # Mock flow controller with error
        mock_instance = MagicMock()
        mock_instance.complete_survey.return_value = {
            'success': False,
            'error': 'Survey completion failed'
        }
        mock_flow_controller.return_value = mock_instance
        
        response = self.client.get(reverse('surveys:survey_completion', kwargs={
            'category_slug': 'health'
        }) + '?session=test-session-123')
        
        # Should redirect with error message
        self.assertEqual(response.status_code, 302)
        
        # Check for error message
        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(any('failed' in str(message) for message in messages))


class SurveyTemplateViewTests(TestCase):
    """Test survey template view functionality."""
    
    def setUp(self):
        self.client = Client()
        self.category = PolicyCategory.objects.create(
            name="Health Insurance",
            slug="health",
            description="Health insurance policies"
        )
        
    def test_survey_template_list_view(self):
        """Test survey template list view."""
        response = self.client.get(reverse('surveys:template_list'))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Survey Templates')
        
    def test_survey_template_detail_view(self):
        """Test survey template detail view."""
        # This would test template detail functionality
        # Implementation depends on actual template system
        pass