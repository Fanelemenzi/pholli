"""
Test views for simple_surveys app to verify task 5 implementation.
"""

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.sessions.models import Session
from django.utils import timezone
from datetime import timedelta
import json

from .models import SimpleSurveyQuestion, SimpleSurveyResponse, QuotationSession


class SurveyViewsTestCase(TestCase):
    """Test case for survey views and URL routing."""
    
    def setUp(self):
        """Set up test data."""
        self.client = Client()
        
        # Create test questions
        self.health_question = SimpleSurveyQuestion.objects.create(
            category='health',
            question_text='What is your age?',
            field_name='age',
            input_type='number',
            is_required=True,
            display_order=1,
            validation_rules={'min': 18, 'max': 80}
        )
        
        self.funeral_question = SimpleSurveyQuestion.objects.create(
            category='funeral',
            question_text='How many family members do you want to cover?',
            field_name='family_members_to_cover',
            input_type='number',
            is_required=True,
            display_order=1,
            validation_rules={'min': 1, 'max': 15}
        )
    
    def test_survey_home_view(self):
        """Test the survey home page displays correctly."""
        response = self.client.get(reverse('simple_surveys:home'))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Choose Your Insurance Type')
        self.assertContains(response, 'Health Insurance')
        self.assertContains(response, 'Funeral Insurance')
    
    def test_health_survey_view(self):
        """Test health insurance survey view."""
        response = self.client.get(reverse('simple_surveys:survey', args=['health']))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Health Insurance Survey')
        self.assertContains(response, self.health_question.question_text)
        self.assertContains(response, 'Generate Quotations')
    
    def test_funeral_survey_view(self):
        """Test funeral insurance survey view."""
        response = self.client.get(reverse('simple_surveys:survey', args=['funeral']))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Funeral Insurance Survey')
        self.assertContains(response, self.funeral_question.question_text)
    
    def test_invalid_category_survey_view(self):
        """Test survey view with invalid category returns 404."""
        response = self.client.get(reverse('simple_surveys:survey', args=['invalid']))
        
        self.assertEqual(response.status_code, 404)
    
    def test_save_response_ajax_valid(self):
        """Test AJAX response saving with valid data."""
        # First visit survey to create session
        self.client.get(reverse('simple_surveys:survey', args=['health']))
        
        # Test saving a response
        response = self.client.post(
            reverse('simple_surveys:save_response_ajax'),
            data=json.dumps({
                'question_id': self.health_question.id,
                'response_value': 30,
                'category': 'health'
            }),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertIsNotNone(data['response_id'])
        
        # Verify response was saved
        saved_response = SimpleSurveyResponse.objects.get(id=data['response_id'])
        self.assertEqual(saved_response.response_value, 30)
        self.assertEqual(saved_response.question, self.health_question)
    
    def test_save_response_ajax_invalid_data(self):
        """Test AJAX response saving with invalid data."""
        # First visit survey to create session
        self.client.get(reverse('simple_surveys:survey', args=['health']))
        
        # Test with missing question_id
        response = self.client.post(
            reverse('simple_surveys:save_response_ajax'),
            data=json.dumps({
                'response_value': 30,
                'category': 'health'
            }),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertFalse(data['success'])
        self.assertIn('Missing required fields', data['errors'][0])
    
    def test_save_response_ajax_validation_error(self):
        """Test AJAX response saving with validation error."""
        # First visit survey to create session
        self.client.get(reverse('simple_surveys:survey', args=['health']))
        
        # Test with age below minimum
        response = self.client.post(
            reverse('simple_surveys:save_response_ajax'),
            data=json.dumps({
                'question_id': self.health_question.id,
                'response_value': 15,  # Below minimum age of 18
                'category': 'health'
            }),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertFalse(data['success'])
        self.assertIn('Value must be at least 18', data['errors'][0])
    
    def test_survey_status_ajax(self):
        """Test AJAX survey status endpoint."""
        # First visit survey to create session
        self.client.get(reverse('simple_surveys:survey', args=['health']))
        
        response = self.client.get(
            reverse('simple_surveys:status_ajax', args=['health'])
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertIn('status', data)
        self.assertEqual(data['status']['category'], 'health')
    
    def test_process_survey_incomplete(self):
        """Test processing incomplete survey returns error."""
        # First visit survey to create session
        self.client.get(reverse('simple_surveys:survey', args=['health']))
        
        response = self.client.post(
            reverse('simple_surveys:process', args=['health'])
        )
        
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertFalse(data['success'])
        self.assertIn('not complete', data['error'])
    
    def test_results_view_no_quotations(self):
        """Test results view when no quotations exist."""
        response = self.client.get(
            reverse('simple_surveys:results', args=['health'])
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'No quotations found')
    
    def test_session_management(self):
        """Test that sessions are properly created and managed."""
        # Visit survey page
        response = self.client.get(reverse('simple_surveys:survey', args=['health']))
        
        # Check that session was created
        self.assertTrue(self.client.session.session_key)
        
        # Check that QuotationSession was created
        session_key = self.client.session.session_key
        quotation_session = QuotationSession.objects.get(session_key=session_key)
        self.assertEqual(quotation_session.category, 'health')
        self.assertFalse(quotation_session.is_completed)
    
    def test_url_patterns(self):
        """Test that all URL patterns are properly configured."""
        # Test home URL
        url = reverse('simple_surveys:home')
        self.assertEqual(url, '/simple-surveys/')
        
        # Test survey URLs
        health_url = reverse('simple_surveys:survey', args=['health'])
        self.assertEqual(health_url, '/simple-surveys/health/')
        
        funeral_url = reverse('simple_surveys:survey', args=['funeral'])
        self.assertEqual(funeral_url, '/simple-surveys/funeral/')
        
        # Test AJAX URLs
        ajax_save_url = reverse('simple_surveys:save_response_ajax')
        self.assertEqual(ajax_save_url, '/simple-surveys/ajax/save-response/')
        
        ajax_status_url = reverse('simple_surveys:status_ajax', args=['health'])
        self.assertEqual(ajax_status_url, '/simple-surveys/ajax/status/health/')
        
        # Test process URL
        process_url = reverse('simple_surveys:process', args=['health'])
        self.assertEqual(process_url, '/simple-surveys/health/process/')
        
        # Test results URL
        results_url = reverse('simple_surveys:results', args=['health'])
        self.assertEqual(results_url, '/simple-surveys/health/results/')


if __name__ == '__main__':
    import django
    from django.conf import settings
    from django.test.utils import get_runner
    
    django.setup()
    TestRunner = get_runner(settings)
    test_runner = TestRunner()
    failures = test_runner.run_tests(["simple_surveys.test_views"])