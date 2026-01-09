"""
Simple tests to verify survey question rendering and input options.
"""

from django.test import TestCase
from policies.models import PolicyCategory
from surveys.models import SurveyQuestion
from surveys.forms import SurveyResponseForm


class SurveyQuestionRenderingTests(TestCase):
    """Test that survey questions and input options render correctly."""
    
    def setUp(self):
        self.category = PolicyCategory.objects.create(
            name="Health Insurance",
            slug="health",
            description="Health insurance policies"
        )
        
    def test_text_question_renders_input_field(self):
        """Test that text questions render with proper input field."""
        question = SurveyQuestion.objects.create(
            category=self.category,
            section="Personal Info",
            question_text="What is your full name?",
            question_type=SurveyQuestion.QuestionType.TEXT,
            field_name="full_name",
            is_required=True
        )
        
        form = SurveyResponseForm(question)
        form_html = str(form['response_value'])
        
        # Verify text input is rendered
        self.assertIn('type="text"', form_html)
        self.assertIn('name="response_value"', form_html)
        
        # Verify form has the question as label
        self.assertEqual(form.fields['response_value'].label, question.question_text)
        
    def test_number_question_renders_number_input(self):
        """Test that number questions render with number input."""
        question = SurveyQuestion.objects.create(
            category=self.category,
            section="Personal Info",
            question_text="What is your age?",
            question_type=SurveyQuestion.QuestionType.NUMBER,
            field_name="age",
            validation_rules={"min_value": 18, "max_value": 100},
            is_required=True
        )
        
        form = SurveyResponseForm(question)
        form_html = str(form['response_value'])
        
        # Verify number input is rendered
        self.assertIn('type="number"', form_html)
        self.assertIn('name="response_value"', form_html)
        
        # Verify form has the question as label
        self.assertEqual(form.fields['response_value'].label, question.question_text)
        
    def test_choice_question_renders_radio_buttons(self):
        """Test that choice questions render with radio buttons."""
        choices = [
            {"value": "male", "text": "Male"},
            {"value": "female", "text": "Female"},
            {"value": "other", "text": "Other"}
        ]
        
        question = SurveyQuestion.objects.create(
            category=self.category,
            section="Personal Info",
            question_text="What is your gender?",
            question_type=SurveyQuestion.QuestionType.CHOICE,
            field_name="gender",
            choices=choices,
            is_required=True
        )
        
        form = SurveyResponseForm(question)
        form_html = str(form['response_value'])
        
        # Verify radio buttons are rendered
        self.assertIn('type="radio"', form_html)
        self.assertIn('name="response_value"', form_html)
        
        # Verify all choice options are present
        self.assertIn('value="male"', form_html)
        self.assertIn('value="female"', form_html)
        self.assertIn('value="other"', form_html)
        
        # Verify choice labels are rendered
        self.assertIn('Male', form_html)
        self.assertIn('Female', form_html)
        self.assertIn('Other', form_html)
        
    def test_multi_choice_question_renders_checkboxes(self):
        """Test that multi-choice questions render with checkboxes."""
        choices = [
            {"value": "diabetes", "text": "Diabetes"},
            {"value": "hypertension", "text": "High Blood Pressure"},
            {"value": "heart_disease", "text": "Heart Disease"}
        ]
        
        question = SurveyQuestion.objects.create(
            category=self.category,
            section="Health Status",
            question_text="Do you have any of the following conditions?",
            question_type=SurveyQuestion.QuestionType.MULTI_CHOICE,
            field_name="medical_conditions",
            choices=choices,
            is_required=False
        )
        
        form = SurveyResponseForm(question)
        form_html = str(form['response_value'])
        
        # Verify checkboxes are rendered
        self.assertIn('type="checkbox"', form_html)
        self.assertIn('name="response_value"', form_html)
        
        # Verify all choice options are present
        self.assertIn('value="diabetes"', form_html)
        self.assertIn('value="hypertension"', form_html)
        self.assertIn('value="heart_disease"', form_html)
        
        # Verify choice labels are rendered
        self.assertIn('Diabetes', form_html)
        self.assertIn('High Blood Pressure', form_html)
        self.assertIn('Heart Disease', form_html)
        
    def test_boolean_question_renders_yes_no_options(self):
        """Test that boolean questions render with yes/no options."""
        question = SurveyQuestion.objects.create(
            category=self.category,
            section="Health Status",
            question_text="Do you smoke?",
            question_type=SurveyQuestion.QuestionType.BOOLEAN,
            field_name="smoker",
            is_required=True
        )
        
        form = SurveyResponseForm(question)
        form_html = str(form['response_value'])
        
        # Verify radio buttons for boolean are rendered
        self.assertIn('type="radio"', form_html)
        self.assertIn('name="response_value"', form_html)
        
        # Verify True/False values are present
        self.assertIn('value="True"', form_html)
        self.assertIn('value="False"', form_html)
        
        # Verify Yes/No labels are rendered
        self.assertIn('Yes', form_html)
        self.assertIn('No', form_html)
        
    def test_range_question_renders_slider(self):
        """Test that range questions render with slider input."""
        question = SurveyQuestion.objects.create(
            category=self.category,
            section="Preferences",
            question_text="How important is cost to you? (1-10)",
            question_type=SurveyQuestion.QuestionType.RANGE,
            field_name="cost_importance",
            validation_rules={"min_value": 1, "max_value": 10, "step": 1},
            is_required=True
        )
        
        form = SurveyResponseForm(question)
        form_html = str(form['response_value'])
        
        # Verify range input is rendered
        self.assertIn('type="range"', form_html)
        self.assertIn('name="response_value"', form_html)
        
        # Verify range attributes
        self.assertIn('min="1"', form_html)
        self.assertIn('max="10"', form_html)
        self.assertIn('step="1"', form_html)
        
    def test_confidence_level_always_rendered(self):
        """Test that confidence level slider is always rendered."""
        question = SurveyQuestion.objects.create(
            category=self.category,
            section="Personal Info",
            question_text="Test question",
            question_type=SurveyQuestion.QuestionType.TEXT,
            field_name="test_field"
        )
        
        form = SurveyResponseForm(question)
        confidence_html = str(form['confidence_level'])
        
        # Verify confidence level range input is rendered
        self.assertIn('type="range"', confidence_html)
        self.assertIn('name="confidence_level"', confidence_html)
        
        # Verify confidence level range (1-5)
        self.assertIn('min="1"', confidence_html)
        self.assertIn('max="5"', confidence_html)
        self.assertIn('step="1"', confidence_html)
        
        # Verify confidence level has proper label
        self.assertEqual(form.fields['confidence_level'].label, "How confident are you in this answer?")
        
    def test_form_validation_works(self):
        """Test that form validation works correctly."""
        question = SurveyQuestion.objects.create(
            category=self.category,
            section="Personal Info",
            question_text="What is your age?",
            question_type=SurveyQuestion.QuestionType.NUMBER,
            field_name="age",
            validation_rules={"min_value": 18, "max_value": 100},
            is_required=True
        )
        
        # Test valid data
        form = SurveyResponseForm(question, data={
            'response_value': 35,
            'confidence_level': 4
        })
        self.assertTrue(form.is_valid())
        
        # Test invalid data (below minimum)
        form = SurveyResponseForm(question, data={
            'response_value': 15,
            'confidence_level': 4
        })
        self.assertFalse(form.is_valid())
        self.assertIn('response_value', form.errors)
        
        # Test missing required field
        form = SurveyResponseForm(question, data={
            'response_value': '',
            'confidence_level': 4
        })
        self.assertFalse(form.is_valid())
        self.assertIn('response_value', form.errors)
        
    def test_help_text_rendered(self):
        """Test that help text is properly rendered."""
        question = SurveyQuestion.objects.create(
            category=self.category,
            section="Personal Info",
            question_text="What is your age?",
            question_type=SurveyQuestion.QuestionType.NUMBER,
            field_name="age",
            help_text="Enter your age in years",
            is_required=True
        )
        
        form = SurveyResponseForm(question)
        
        # Verify help text is set on the form field
        self.assertEqual(form.fields['response_value'].help_text, question.help_text)
        
    def test_required_field_indicator(self):
        """Test that required fields are properly marked."""
        # Required field
        required_question = SurveyQuestion.objects.create(
            category=self.category,
            section="Personal Info",
            question_text="Required field",
            question_type=SurveyQuestion.QuestionType.TEXT,
            field_name="required_field",
            is_required=True
        )
        
        form = SurveyResponseForm(required_question)
        self.assertTrue(form.fields['response_value'].required)
        
        # Optional field
        optional_question = SurveyQuestion.objects.create(
            category=self.category,
            section="Personal Info",
            question_text="Optional field",
            question_type=SurveyQuestion.QuestionType.TEXT,
            field_name="optional_field",
            is_required=False
        )
        
        form = SurveyResponseForm(optional_question)
        self.assertFalse(form.fields['response_value'].required)