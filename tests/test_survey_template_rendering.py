"""
Tests to verify that survey questions and input options are properly rendered in HTML templates.
"""

import json
from unittest.mock import patch, MagicMock
from django.test import TestCase, Client
from django.urls import reverse
from django.template.loader import render_to_string
from django.template import Context, Template
from django.contrib.auth import get_user_model

from policies.models import PolicyCategory
from comparison.models import ComparisonSession
from surveys.models import SurveyQuestion, SurveyResponse
from surveys.forms import SurveyResponseForm

User = get_user_model()


class SurveyTemplateRenderingTests(TestCase):
    """Test that survey questions and inputs are properly rendered in HTML templates."""
    
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
        
    def test_text_question_renders_in_template(self):
        """Test that text questions render properly in survey form template."""
        question = SurveyQuestion.objects.create(
            category=self.category,
            section="Personal Info",
            question_text="What is your full name?",
            question_type=SurveyQuestion.QuestionType.TEXT,
            field_name="full_name",
            help_text="Enter your legal name as it appears on documents",
            is_required=True
        )
        
        form = SurveyResponseForm(question)
        
        # Render the template with context
        context = {
            'category': self.category,
            'current_question': question,
            'form': form,
            'completion_percentage': 25.0,
            'session_key': 'test-session-123'
        }
        
        rendered = render_to_string('surveys/survey_form.html', context)
        
        # Check that question text is rendered
        self.assertIn(question.question_text, rendered)
        self.assertIn("What is your full name?", rendered)
        
        # Check that help text is rendered
        self.assertIn(question.help_text, rendered)
        self.assertIn("Enter your legal name as it appears on documents", rendered)
        
        # Check that text input is rendered
        self.assertIn('type="text"', rendered)
        self.assertIn('name="response_value"', rendered)
        
        # Check that form structure is present
        self.assertIn('<form method="post">', rendered)
        self.assertIn('{% csrf_token %}', rendered)
        
    def test_number_question_renders_in_template(self):
        """Test that number questions render properly in survey form template."""
        question = SurveyQuestion.objects.create(
            category=self.category,
            section="Personal Info",
            question_text="What is your age?",
            question_type=SurveyQuestion.QuestionType.NUMBER,
            field_name="age",
            validation_rules={"min_value": 18, "max_value": 100},
            help_text="Enter your age in years",
            is_required=True
        )
        
        form = SurveyResponseForm(question)
        
        context = {
            'category': self.category,
            'current_question': question,
            'form': form,
            'completion_percentage': 50.0,
            'session_key': 'test-session-123'
        }
        
        rendered = render_to_string('surveys/survey_form.html', context)
        
        # Check that question text is rendered
        self.assertIn("What is your age?", rendered)
        
        # Check that help text is rendered
        self.assertIn("Enter your age in years", rendered)
        
        # Check that number input is rendered
        self.assertIn('type="number"', rendered)
        self.assertIn('name="response_value"', rendered)
        
    def test_choice_question_renders_in_template(self):
        """Test that choice questions render properly with all options in template."""
        choices = [
            {"value": "male", "text": "Male"},
            {"value": "female", "text": "Female"},
            {"value": "other", "text": "Other"},
            {"value": "prefer_not_to_say", "text": "Prefer not to say"}
        ]
        
        question = SurveyQuestion.objects.create(
            category=self.category,
            section="Personal Info",
            question_text="What is your gender?",
            question_type=SurveyQuestion.QuestionType.CHOICE,
            field_name="gender",
            choices=choices,
            help_text="Select the option that best describes you",
            is_required=True
        )
        
        form = SurveyResponseForm(question)
        
        context = {
            'category': self.category,
            'current_question': question,
            'form': form,
            'completion_percentage': 75.0,
            'session_key': 'test-session-123'
        }
        
        rendered = render_to_string('surveys/survey_form.html', context)
        
        # Check that question text is rendered
        self.assertIn("What is your gender?", rendered)
        
        # Check that help text is rendered
        self.assertIn("Select the option that best describes you", rendered)
        
        # Check that radio buttons are rendered
        self.assertIn('type="radio"', rendered)
        self.assertIn('name="response_value"', rendered)
        
        # Check that all choice options are rendered
        self.assertIn('value="male"', rendered)
        self.assertIn('value="female"', rendered)
        self.assertIn('value="other"', rendered)
        self.assertIn('value="prefer_not_to_say"', rendered)
        
        # Check that choice labels are rendered
        self.assertIn('Male', rendered)
        self.assertIn('Female', rendered)
        self.assertIn('Other', rendered)
        self.assertIn('Prefer not to say', rendered)
        
    def test_multi_choice_question_renders_in_template(self):
        """Test that multi-choice questions render properly with checkboxes in template."""
        choices = [
            {"value": "diabetes", "text": "Diabetes"},
            {"value": "hypertension", "text": "High Blood Pressure"},
            {"value": "heart_disease", "text": "Heart Disease"},
            {"value": "asthma", "text": "Asthma"},
            {"value": "none", "text": "None of the above"}
        ]
        
        question = SurveyQuestion.objects.create(
            category=self.category,
            section="Health Status",
            question_text="Do you have any of the following medical conditions?",
            question_type=SurveyQuestion.QuestionType.MULTI_CHOICE,
            field_name="medical_conditions",
            choices=choices,
            help_text="Select all that apply to you",
            is_required=False
        )
        
        form = SurveyResponseForm(question)
        
        context = {
            'category': self.category,
            'current_question': question,
            'form': form,
            'completion_percentage': 60.0,
            'session_key': 'test-session-123'
        }
        
        rendered = render_to_string('surveys/survey_form.html', context)
        
        # Check that question text is rendered
        self.assertIn("Do you have any of the following medical conditions?", rendered)
        
        # Check that help text is rendered
        self.assertIn("Select all that apply to you", rendered)
        
        # Check that checkboxes are rendered
        self.assertIn('type="checkbox"', rendered)
        self.assertIn('name="response_value"', rendered)
        
        # Check that all choice options are rendered
        self.assertIn('value="diabetes"', rendered)
        self.assertIn('value="hypertension"', rendered)
        self.assertIn('value="heart_disease"', rendered)
        self.assertIn('value="asthma"', rendered)
        self.assertIn('value="none"', rendered)
        
        # Check that choice labels are rendered
        self.assertIn('Diabetes', rendered)
        self.assertIn('High Blood Pressure', rendered)
        self.assertIn('Heart Disease', rendered)
        self.assertIn('Asthma', rendered)
        self.assertIn('None of the above', rendered)
        
    def test_boolean_question_renders_in_template(self):
        """Test that boolean questions render properly with Yes/No options in template."""
        question = SurveyQuestion.objects.create(
            category=self.category,
            section="Health Status",
            question_text="Do you currently smoke tobacco?",
            question_type=SurveyQuestion.QuestionType.BOOLEAN,
            field_name="smoker",
            help_text="This affects your insurance premiums",
            is_required=True
        )
        
        form = SurveyResponseForm(question)
        
        context = {
            'category': self.category,
            'current_question': question,
            'form': form,
            'completion_percentage': 80.0,
            'session_key': 'test-session-123'
        }
        
        rendered = render_to_string('surveys/survey_form.html', context)
        
        # Check that question text is rendered
        self.assertIn("Do you currently smoke tobacco?", rendered)
        
        # Check that help text is rendered
        self.assertIn("This affects your insurance premiums", rendered)
        
        # Check that radio buttons are rendered
        self.assertIn('type="radio"', rendered)
        self.assertIn('name="response_value"', rendered)
        
        # Check that Yes/No options are rendered
        self.assertIn('value="True"', rendered)
        self.assertIn('value="False"', rendered)
        self.assertIn('Yes', rendered)
        self.assertIn('No', rendered)
        
    def test_range_question_renders_in_template(self):
        """Test that range questions render properly with slider in template."""
        question = SurveyQuestion.objects.create(
            category=self.category,
            section="Preferences",
            question_text="How important is cost to you when choosing insurance? (1-10)",
            question_type=SurveyQuestion.QuestionType.RANGE,
            field_name="cost_importance",
            validation_rules={"min_value": 1, "max_value": 10, "step": 1},
            help_text="1 = Not important, 10 = Very important",
            is_required=True
        )
        
        form = SurveyResponseForm(question)
        
        context = {
            'category': self.category,
            'current_question': question,
            'form': form,
            'completion_percentage': 90.0,
            'session_key': 'test-session-123'
        }
        
        rendered = render_to_string('surveys/survey_form.html', context)
        
        # Check that question text is rendered
        self.assertIn("How important is cost to you when choosing insurance?", rendered)
        
        # Check that help text is rendered
        self.assertIn("1 = Not important, 10 = Very important", rendered)
        
        # Check that range input is rendered
        self.assertIn('type="range"', rendered)
        self.assertIn('name="response_value"', rendered)
        
        # Check that range attributes are rendered
        self.assertIn('min="1"', rendered)
        self.assertIn('max="10"', rendered)
        self.assertIn('step="1"', rendered)
        
    def test_confidence_level_renders_in_template(self):
        """Test that confidence level slider is always rendered in template."""
        question = SurveyQuestion.objects.create(
            category=self.category,
            section="Personal Info",
            question_text="Test question for confidence level",
            question_type=SurveyQuestion.QuestionType.TEXT,
            field_name="test_field"
        )
        
        form = SurveyResponseForm(question)
        
        context = {
            'category': self.category,
            'current_question': question,
            'form': form,
            'completion_percentage': 50.0,
            'session_key': 'test-session-123'
        }
        
        rendered = render_to_string('surveys/survey_form.html', context)
        
        # Check that confidence level label is rendered
        self.assertIn("How confident are you in this answer?", rendered)
        
        # Check that confidence level range input is rendered
        confidence_field_found = False
        if 'name="confidence_level"' in rendered and 'type="range"' in rendered:
            confidence_field_found = True
        self.assertTrue(confidence_field_found, "Confidence level field not found in rendered template")
        
        # Check that confidence level labels are rendered
        self.assertIn("Not confident", rendered)
        self.assertIn("Very confident", rendered)
        
    def test_form_validation_errors_render_in_template(self):
        """Test that form validation errors are properly displayed in template."""
        question = SurveyQuestion.objects.create(
            category=self.category,
            section="Personal Info",
            question_text="What is your age?",
            question_type=SurveyQuestion.QuestionType.NUMBER,
            field_name="age",
            validation_rules={"min_value": 18, "max_value": 100},
            is_required=True
        )
        
        # Create form with invalid data to trigger errors
        form = SurveyResponseForm(question, data={
            'response_value': 15,  # Below minimum
            'confidence_level': 4
        })
        
        # Form should be invalid
        self.assertFalse(form.is_valid())
        
        context = {
            'category': self.category,
            'current_question': question,
            'form': form,
            'completion_percentage': 25.0,
            'session_key': 'test-session-123'
        }
        
        rendered = render_to_string('surveys/survey_form.html', context)
        
        # Check that error display structure is present
        self.assertIn('text-danger', rendered)
        self.assertIn('field.errors', rendered)
        
    def test_progress_bar_renders_in_template(self):
        """Test that progress bar is properly rendered in template."""
        question = SurveyQuestion.objects.create(
            category=self.category,
            section="Personal Info",
            question_text="Test question",
            question_type=SurveyQuestion.QuestionType.TEXT,
            field_name="test_field"
        )
        
        form = SurveyResponseForm(question)
        
        context = {
            'category': self.category,
            'current_question': question,
            'form': form,
            'completion_percentage': 65.5,
            'session_key': 'test-session-123',
            'sections': [
                {'name': 'Personal Info', 'progress': 80.0},
                {'name': 'Health Status', 'progress': 50.0}
            ]
        }
        
        rendered = render_to_string('surveys/survey_form.html', context)
        
        # Check that progress bar is rendered
        self.assertIn('progress-bar', rendered)
        self.assertIn('65%', rendered)  # Rounded percentage
        
        # Check that section progress is rendered
        self.assertIn('Personal Info', rendered)
        self.assertIn('Health Status', rendered)
        self.assertIn('80%', rendered)
        self.assertIn('50%', rendered)
        
    def test_survey_completion_template_renders(self):
        """Test that survey completion template renders properly."""
        context = {
            'category': self.category,
            'session_key': 'test-session-123',
            'completion_result': {
                'completion_time': 'Just now',
                'results_url': '/comparison/results/?session=test-session-123'
            }
        }
        
        rendered = render_to_string('surveys/survey_completion.html', context)
        
        # Check that completion message is rendered
        self.assertIn('Survey Complete!', rendered)
        self.assertIn('Thank you for completing the Health Insurance survey!', rendered)
        
        # Check that session information is rendered
        self.assertIn('test-session-123', rendered)
        self.assertIn('Health Insurance', rendered)
        
        # Check that next steps are rendered
        self.assertIn("What's Next?", rendered)
        self.assertIn('Analyzing your responses', rendered)
        self.assertIn('Comparing policies', rendered)
        
    def test_survey_results_template_renders(self):
        """Test that survey results template renders properly."""
        context = {
            'category': self.category,
            'session_key': 'test-session-123',
            'survey_summary': {
                'completion_percentage': 100.0,
                'total_responses': 5
            }
        }
        
        rendered = render_to_string('surveys/survey_results.html', context)
        
        # Check that results header is rendered
        self.assertIn('Your Health Insurance Insurance Recommendations', rendered)
        
        # Check that survey summary is rendered
        self.assertIn('100%', rendered)
        self.assertIn('test-session-123', rendered)
        
        # Check that analysis information is rendered
        self.assertIn('What we\'re analyzing:', rendered)
        self.assertIn('Your coverage needs', rendered)
        self.assertIn('Budget preferences', rendered)


class SurveyTemplateIntegrationTests(TestCase):
    """Integration tests for survey templates with actual view rendering."""
    
    def setUp(self):
        self.client = Client()
        self.category = PolicyCategory.objects.create(
            name="Health Insurance",
            slug="health",
            description="Health insurance policies"
        )
        
    @patch('surveys.views.SurveyFlowController')
    def test_survey_form_view_renders_question_in_template(self, mock_flow_controller):
        """Test that survey form view properly renders questions in HTML template."""
        question = SurveyQuestion.objects.create(
            category=self.category,
            section="Personal Info",
            question_text="What is your annual income?",
            question_type=SurveyQuestion.QuestionType.NUMBER,
            field_name="annual_income",
            help_text="Enter your gross annual income in dollars",
            validation_rules={"min_value": 0, "max_value": 1000000},
            is_required=True
        )
        
        # Mock flow controller
        mock_instance = MagicMock()
        mock_instance.session_key = "test-session-123"
        mock_instance.category = self.category
        mock_instance.validate_session.return_value = True
        mock_instance.get_current_section_and_question.return_value = ("Personal Info", question)
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
        
        # Get the rendered content
        content = response.content.decode()
        
        # Check that question is rendered in HTML
        self.assertIn("What is your annual income?", content)
        self.assertIn("Enter your gross annual income in dollars", content)
        
        # Check that number input is rendered
        self.assertIn('type="number"', content)
        self.assertIn('name="response_value"', content)
        
        # Check that confidence level is rendered
        self.assertIn("How confident are you in this answer?", content)
        self.assertIn('name="confidence_level"', content)
        
        # Check that form structure is present
        self.assertIn('<form method="post">', content)
        self.assertIn('csrf', content)
        
        # Check that progress bar is rendered
        self.assertIn('progress-bar', content)
        self.assertIn('25%', content)
        
        # Check that navigation buttons are rendered
        self.assertIn('Previous', content)
        self.assertIn('Next Question', content)
        
    @patch('surveys.views.SurveyFlowController')
    def test_choice_question_renders_all_options_in_view(self, mock_flow_controller):
        """Test that choice questions render all options when accessed through view."""
        choices = [
            {"value": "single", "text": "Single"},
            {"value": "married", "text": "Married"},
            {"value": "divorced", "text": "Divorced"},
            {"value": "widowed", "text": "Widowed"}
        ]
        
        question = SurveyQuestion.objects.create(
            category=self.category,
            section="Personal Info",
            question_text="What is your marital status?",
            question_type=SurveyQuestion.QuestionType.CHOICE,
            field_name="marital_status",
            choices=choices,
            help_text="Select your current marital status",
            is_required=True
        )
        
        # Mock flow controller
        mock_instance = MagicMock()
        mock_instance.session_key = "test-session-123"
        mock_instance.category = self.category
        mock_instance.validate_session.return_value = True
        mock_instance.get_current_section_and_question.return_value = ("Personal Info", question)
        mock_instance.engine.get_survey_sections.return_value = []
        mock_instance.get_section_progress.return_value = {}
        mock_instance.get_survey_summary.return_value = {'completion_percentage': 50.0}
        mock_flow_controller.return_value = mock_instance
        
        response = self.client.get(reverse('surveys:survey_form', kwargs={
            'category_slug': 'health'
        }) + '?session=test-session-123')
        
        self.assertEqual(response.status_code, 200)
        
        content = response.content.decode()
        
        # Check that question is rendered
        self.assertIn("What is your marital status?", content)
        self.assertIn("Select your current marital status", content)
        
        # Check that all choice options are rendered
        self.assertIn('value="single"', content)
        self.assertIn('value="married"', content)
        self.assertIn('value="divorced"', content)
        self.assertIn('value="widowed"', content)
        
        # Check that choice labels are rendered
        self.assertIn('Single', content)
        self.assertIn('Married', content)
        self.assertIn('Divorced', content)
        self.assertIn('Widowed', content)
        
        # Check that radio buttons are rendered
        self.assertIn('type="radio"', content)
        self.assertIn('name="response_value"', content)