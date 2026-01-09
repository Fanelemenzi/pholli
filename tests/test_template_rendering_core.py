"""
Core tests to verify that survey questions and input options render in HTML templates.
"""

from django.test import TestCase
from django.template.loader import render_to_string
from policies.models import PolicyCategory
from comparison.models import ComparisonSession
from surveys.models import SurveyQuestion
from surveys.forms import SurveyResponseForm


class CoreTemplateRenderingTests(TestCase):
    """Core tests for template rendering of survey questions and inputs."""
    
    def setUp(self):
        self.category = PolicyCategory.objects.create(
            name="Health Insurance",
            slug="health",
            description="Health insurance policies"
        )
        
    def test_text_question_renders_correctly_in_template(self):
        """Test that text questions render with proper input elements in HTML."""
        question = SurveyQuestion.objects.create(
            category=self.category,
            section="Personal Info",
            question_text="What is your full name?",
            question_type=SurveyQuestion.QuestionType.TEXT,
            field_name="full_name",
            help_text="Enter your legal name",
            is_required=True
        )
        
        form = SurveyResponseForm(question)
        
        context = {
            'category': self.category,
            'current_question': question,
            'form': form,
            'completion_percentage': 25.0,
            'session_key': 'test-session-123'
        }
        
        rendered = render_to_string('surveys/survey_form.html', context)
        
        # Verify question text is rendered
        self.assertIn("What is your full name?", rendered)
        
        # Verify help text is rendered
        self.assertIn("Enter your legal name", rendered)
        
        # Verify text input is rendered
        self.assertIn('type="text"', rendered)
        self.assertIn('name="response_value"', rendered)
        
        # Verify form structure
        self.assertIn('<form method="post">', rendered)
        self.assertIn('class="form-control"', rendered)
        
    def test_choice_question_renders_all_options_in_template(self):
        """Test that choice questions render all radio button options in HTML."""
        choices = [
            {"value": "option1", "text": "Option One"},
            {"value": "option2", "text": "Option Two"},
            {"value": "option3", "text": "Option Three"}
        ]
        
        question = SurveyQuestion.objects.create(
            category=self.category,
            section="Preferences",
            question_text="Which option do you prefer?",
            question_type=SurveyQuestion.QuestionType.CHOICE,
            field_name="preference",
            choices=choices,
            help_text="Select one option",
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
        
        # Verify question text is rendered
        self.assertIn("Which option do you prefer?", rendered)
        
        # Verify help text is rendered
        self.assertIn("Select one option", rendered)
        
        # Verify radio buttons are rendered
        self.assertIn('type="radio"', rendered)
        self.assertIn('name="response_value"', rendered)
        
        # Verify all choice values are rendered
        self.assertIn('value="option1"', rendered)
        self.assertIn('value="option2"', rendered)
        self.assertIn('value="option3"', rendered)
        
        # Verify all choice labels are rendered
        self.assertIn('Option One', rendered)
        self.assertIn('Option Two', rendered)
        self.assertIn('Option Three', rendered)
        
    def test_multi_choice_question_renders_checkboxes_in_template(self):
        """Test that multi-choice questions render checkbox options in HTML."""
        choices = [
            {"value": "feature1", "text": "Feature One"},
            {"value": "feature2", "text": "Feature Two"},
            {"value": "feature3", "text": "Feature Three"}
        ]
        
        question = SurveyQuestion.objects.create(
            category=self.category,
            section="Features",
            question_text="Which features do you want?",
            question_type=SurveyQuestion.QuestionType.MULTI_CHOICE,
            field_name="features",
            choices=choices,
            help_text="Select all that apply",
            is_required=False
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
        
        # Verify question text is rendered
        self.assertIn("Which features do you want?", rendered)
        
        # Verify help text is rendered
        self.assertIn("Select all that apply", rendered)
        
        # Verify checkboxes are rendered
        self.assertIn('type="checkbox"', rendered)
        self.assertIn('name="response_value"', rendered)
        
        # Verify all choice values are rendered
        self.assertIn('value="feature1"', rendered)
        self.assertIn('value="feature2"', rendered)
        self.assertIn('value="feature3"', rendered)
        
        # Verify all choice labels are rendered
        self.assertIn('Feature One', rendered)
        self.assertIn('Feature Two', rendered)
        self.assertIn('Feature Three', rendered)
        
    def test_number_question_renders_number_input_in_template(self):
        """Test that number questions render number input in HTML."""
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
            'completion_percentage': 40.0,
            'session_key': 'test-session-123'
        }
        
        rendered = render_to_string('surveys/survey_form.html', context)
        
        # Verify question text is rendered
        self.assertIn("What is your age?", rendered)
        
        # Verify help text is rendered
        self.assertIn("Enter your age in years", rendered)
        
        # Verify number input is rendered
        self.assertIn('type="number"', rendered)
        self.assertIn('name="response_value"', rendered)
        self.assertIn('class="form-control"', rendered)
        
    def test_boolean_question_renders_yes_no_options_in_template(self):
        """Test that boolean questions render Yes/No radio options in HTML."""
        question = SurveyQuestion.objects.create(
            category=self.category,
            section="Health Status",
            question_text="Do you smoke?",
            question_type=SurveyQuestion.QuestionType.BOOLEAN,
            field_name="smoker",
            help_text="This affects your premium",
            is_required=True
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
        
        # Verify question text is rendered
        self.assertIn("Do you smoke?", rendered)
        
        # Verify help text is rendered
        self.assertIn("This affects your premium", rendered)
        
        # Verify radio buttons are rendered
        self.assertIn('type="radio"', rendered)
        self.assertIn('name="response_value"', rendered)
        
        # Verify Yes/No values are rendered
        self.assertIn('value="True"', rendered)
        self.assertIn('value="False"', rendered)
        
        # Verify Yes/No labels are rendered
        self.assertIn('Yes', rendered)
        self.assertIn('No', rendered)
        
    def test_range_question_renders_slider_in_template(self):
        """Test that range questions render slider input in HTML."""
        question = SurveyQuestion.objects.create(
            category=self.category,
            section="Preferences",
            question_text="Rate importance (1-10)",
            question_type=SurveyQuestion.QuestionType.RANGE,
            field_name="importance",
            validation_rules={"min_value": 1, "max_value": 10, "step": 1},
            help_text="1 = Not important, 10 = Very important",
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
        
        # Verify question text is rendered
        self.assertIn("Rate importance (1-10)", rendered)
        
        # Verify help text is rendered
        self.assertIn("1 = Not important, 10 = Very important", rendered)
        
        # Verify range input is rendered
        self.assertIn('type="range"', rendered)
        self.assertIn('name="response_value"', rendered)
        self.assertIn('class="form-range"', rendered)
        
        # Verify range attributes
        self.assertIn('min="1"', rendered)
        self.assertIn('max="10"', rendered)
        self.assertIn('step="1"', rendered)
        
    def test_confidence_level_always_rendered_in_template(self):
        """Test that confidence level is always rendered regardless of question type."""
        question = SurveyQuestion.objects.create(
            category=self.category,
            section="Test",
            question_text="Test question",
            question_type=SurveyQuestion.QuestionType.TEXT,
            field_name="test"
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
        
        # Verify confidence level label is rendered
        self.assertIn("How confident are you in this answer?", rendered)
        
        # Verify confidence level range input is rendered
        self.assertIn('name="confidence_level"', rendered)
        
        # Verify confidence level labels
        self.assertIn("Not confident", rendered)
        self.assertIn("Very confident", rendered)
        
    def test_form_validation_errors_display_in_template(self):
        """Test that form validation errors are displayed in HTML."""
        question = SurveyQuestion.objects.create(
            category=self.category,
            section="Personal Info",
            question_text="What is your age?",
            question_type=SurveyQuestion.QuestionType.NUMBER,
            field_name="age",
            validation_rules={"min_value": 18, "max_value": 100},
            is_required=True
        )
        
        # Create form with invalid data
        form = SurveyResponseForm(question, data={
            'response_value': 15,  # Below minimum
            'confidence_level': 4
        })
        
        # Ensure form is invalid
        self.assertFalse(form.is_valid())
        
        context = {
            'category': self.category,
            'current_question': question,
            'form': form,
            'completion_percentage': 25.0,
            'session_key': 'test-session-123'
        }
        
        rendered = render_to_string('surveys/survey_form.html', context)
        
        # Verify error message is displayed
        self.assertIn("Value must be at least 18", rendered)
        self.assertIn('text-danger', rendered)
        
    def test_progress_bar_renders_in_template(self):
        """Test that progress bar is rendered in HTML."""
        question = SurveyQuestion.objects.create(
            category=self.category,
            section="Test",
            question_text="Test question",
            question_type=SurveyQuestion.QuestionType.TEXT,
            field_name="test"
        )
        
        form = SurveyResponseForm(question)
        
        context = {
            'category': self.category,
            'current_question': question,
            'form': form,
            'completion_percentage': 67.5,
            'session_key': 'test-session-123'
        }
        
        rendered = render_to_string('surveys/survey_form.html', context)
        
        # Verify progress bar is rendered
        self.assertIn('progress-bar', rendered)
        self.assertIn('68%', rendered)  # Rounded percentage (67.5 rounds to 68)
        
    def test_survey_navigation_buttons_render_in_template(self):
        """Test that navigation buttons are rendered in HTML."""
        question = SurveyQuestion.objects.create(
            category=self.category,
            section="Test",
            question_text="Test question",
            question_type=SurveyQuestion.QuestionType.TEXT,
            field_name="test"
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
        
        # Verify navigation buttons are rendered
        self.assertIn('Previous', rendered)
        self.assertIn('Next Question', rendered)
        self.assertIn('btn btn-secondary', rendered)
        self.assertIn('btn btn-primary', rendered)
        
    def test_survey_completion_template_renders_correctly(self):
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
        
        # Verify completion message
        self.assertIn('Survey Complete!', rendered)
        self.assertIn('Thank you for completing the Health Insurance survey!', rendered)
        
        # Verify session information
        self.assertIn('test-session-123', rendered)
        
        # Verify next steps
        self.assertIn("What's Next?", rendered)
        self.assertIn('Analyzing your responses', rendered)
        
    def test_survey_results_template_renders_correctly(self):
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
        
        # Verify results header
        self.assertIn('Your Health Insurance Insurance Recommendations', rendered)
        
        # Verify survey summary
        self.assertIn('100%', rendered)
        self.assertIn('test-session-123', rendered)
        
        # Verify analysis information
        self.assertIn('Your coverage needs', rendered)
        self.assertIn('Budget preferences', rendered)