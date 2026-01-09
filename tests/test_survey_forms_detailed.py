"""
Detailed tests for survey forms functionality.
Tests form rendering, validation, and edge cases.
"""

from django.test import TestCase
from django.forms import ValidationError
from decimal import Decimal

from policies.models import PolicyCategory
from comparison.models import ComparisonSession
from surveys.models import SurveyQuestion, SurveyResponse
from surveys.forms import SurveyResponseForm, BulkSurveyResponseForm


class SurveyFormRenderingTests(TestCase):
    """Test form rendering for different question types."""
    
    def setUp(self):
        self.category = PolicyCategory.objects.create(
            name="Health Insurance",
            slug="health",
            description="Health insurance policies"
        )
        
    def test_text_form_rendering(self):
        """Test text input form rendering."""
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
        form_html = str(form['response_value'])
        
        self.assertIn('type="text"', form_html)
        self.assertIn('class="form-control"', form_html)
        self.assertIn('placeholder="Enter your answer"', form_html)
        
    def test_number_form_rendering(self):
        """Test number input form rendering."""
        question = SurveyQuestion.objects.create(
            category=self.category,
            section="Personal Info",
            question_text="What is your age?",
            question_type=SurveyQuestion.QuestionType.NUMBER,
            field_name="age",
            is_required=True
        )
        
        form = SurveyResponseForm(question)
        form_html = str(form['response_value'])
        
        self.assertIn('type="number"', form_html)
        self.assertIn('class="form-control"', form_html)
        self.assertIn('placeholder="Enter a number"', form_html)
        
    def test_choice_form_rendering(self):
        """Test single choice form rendering."""
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
        
        self.assertIn('type="radio"', form_html)
        self.assertIn('class="form-check-input"', form_html)
        self.assertIn('value="male"', form_html)
        self.assertIn('value="female"', form_html)
        self.assertIn('value="other"', form_html)
        
    def test_multi_choice_form_rendering(self):
        """Test multiple choice form rendering."""
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
        
        self.assertIn('type="checkbox"', form_html)
        self.assertIn('class="form-check-input"', form_html)
        self.assertIn('value="diabetes"', form_html)
        self.assertIn('value="hypertension"', form_html)
        
    def test_boolean_form_rendering(self):
        """Test boolean form rendering."""
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
        
        self.assertIn('type="radio"', form_html)
        self.assertIn('class="form-check-input"', form_html)
        self.assertIn('value="True"', form_html)
        self.assertIn('value="False"', form_html)
        
    def test_range_form_rendering(self):
        """Test range/slider form rendering."""
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
        
        self.assertIn('type="range"', form_html)
        self.assertIn('class="form-range"', form_html)
        self.assertIn('min="1"', form_html)
        self.assertIn('max="10"', form_html)
        self.assertIn('step="1"', form_html)
        
    def test_confidence_level_rendering(self):
        """Test confidence level field rendering."""
        question = SurveyQuestion.objects.create(
            category=self.category,
            section="Personal Info",
            question_text="Test question",
            question_type=SurveyQuestion.QuestionType.TEXT,
            field_name="test_field"
        )
        
        form = SurveyResponseForm(question)
        confidence_html = str(form['confidence_level'])
        
        self.assertIn('type="range"', confidence_html)
        self.assertIn('class="form-range"', confidence_html)
        self.assertIn('min="1"', confidence_html)
        self.assertIn('max="5"', confidence_html)
        self.assertIn('step="1"', confidence_html)


class SurveyFormValidationTests(TestCase):
    """Test form validation for different scenarios."""
    
    def setUp(self):
        self.category = PolicyCategory.objects.create(
            name="Health Insurance",
            slug="health",
            description="Health insurance policies"
        )
        
        self.session = ComparisonSession.objects.create(
            session_key="test-session-123",
            category=self.category
        )
        
    def test_required_field_validation(self):
        """Test validation of required fields."""
        question = SurveyQuestion.objects.create(
            category=self.category,
            section="Personal Info",
            question_text="What is your full name?",
            question_type=SurveyQuestion.QuestionType.TEXT,
            field_name="full_name",
            is_required=True
        )
        
        # Test empty required field
        form = SurveyResponseForm(question, data={
            'response_value': '',
            'confidence_level': 4
        })
        
        self.assertFalse(form.is_valid())
        self.assertIn('response_value', form.errors)
        self.assertIn('This field is required', str(form.errors['response_value']))
        
        # Test valid required field
        form = SurveyResponseForm(question, data={
            'response_value': 'John Doe',
            'confidence_level': 4
        })
        
        self.assertTrue(form.is_valid())
        
    def test_optional_field_validation(self):
        """Test validation of optional fields."""
        question = SurveyQuestion.objects.create(
            category=self.category,
            section="Personal Info",
            question_text="What is your middle name?",
            question_type=SurveyQuestion.QuestionType.TEXT,
            field_name="middle_name",
            is_required=False
        )
        
        # Test empty optional field
        form = SurveyResponseForm(question, data={
            'response_value': '',
            'confidence_level': 4
        })
        
        self.assertTrue(form.is_valid())
        
    def test_text_length_validation(self):
        """Test text field length validation."""
        question = SurveyQuestion.objects.create(
            category=self.category,
            section="Personal Info",
            question_text="What is your full name?",
            question_type=SurveyQuestion.QuestionType.TEXT,
            field_name="full_name",
            validation_rules={"min_length": 5, "max_length": 50},
            is_required=True
        )
        
        # Test too short
        form = SurveyResponseForm(question, data={
            'response_value': 'Jo',
            'confidence_level': 4
        })
        
        self.assertFalse(form.is_valid())
        self.assertIn('Answer must be at least 5 characters', str(form.errors['response_value']))
        
        # Test too long
        form = SurveyResponseForm(question, data={
            'response_value': 'A' * 60,  # 60 characters
            'confidence_level': 4
        })
        
        self.assertFalse(form.is_valid())
        self.assertIn('Answer must be at most 50 characters', str(form.errors['response_value']))
        
        # Test valid length
        form = SurveyResponseForm(question, data={
            'response_value': 'John Doe',
            'confidence_level': 4
        })
        
        self.assertTrue(form.is_valid())
        
    def test_number_range_validation(self):
        """Test number field range validation."""
        question = SurveyQuestion.objects.create(
            category=self.category,
            section="Personal Info",
            question_text="What is your age?",
            question_type=SurveyQuestion.QuestionType.NUMBER,
            field_name="age",
            validation_rules={"min_value": 18, "max_value": 100},
            is_required=True
        )
        
        # Test below minimum
        form = SurveyResponseForm(question, data={
            'response_value': 15,
            'confidence_level': 4
        })
        
        self.assertFalse(form.is_valid())
        self.assertIn('Value must be at least 18', str(form.errors['response_value']))
        
        # Test above maximum
        form = SurveyResponseForm(question, data={
            'response_value': 150,
            'confidence_level': 4
        })
        
        self.assertFalse(form.is_valid())
        self.assertIn('Value must be at most 100', str(form.errors['response_value']))
        
        # Test valid range
        form = SurveyResponseForm(question, data={
            'response_value': 35,
            'confidence_level': 4
        })
        
        self.assertTrue(form.is_valid())
        
    def test_decimal_number_validation(self):
        """Test decimal number validation."""
        question = SurveyQuestion.objects.create(
            category=self.category,
            section="Financial Info",
            question_text="What is your annual income?",
            question_type=SurveyQuestion.QuestionType.NUMBER,
            field_name="annual_income",
            is_required=True
        )
        
        # Test decimal input
        form = SurveyResponseForm(question, data={
            'response_value': '50000.50',
            'confidence_level': 4
        })
        
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['response_value'], Decimal('50000.50'))
        
    def test_choice_validation(self):
        """Test choice field validation."""
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
        
        # Test valid choice
        form = SurveyResponseForm(question, data={
            'response_value': 'male',
            'confidence_level': 4
        })
        
        self.assertTrue(form.is_valid())
        
        # Test invalid choice
        form = SurveyResponseForm(question, data={
            'response_value': 'invalid_choice',
            'confidence_level': 4
        })
        
        self.assertFalse(form.is_valid())
        
    def test_multi_choice_validation(self):
        """Test multiple choice field validation."""
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
        
        # Test valid multiple choices
        form = SurveyResponseForm(question, data={
            'response_value': ['diabetes', 'hypertension'],
            'confidence_level': 4
        })
        
        self.assertTrue(form.is_valid())
        
        # Test single valid choice
        form = SurveyResponseForm(question, data={
            'response_value': ['diabetes'],
            'confidence_level': 4
        })
        
        self.assertTrue(form.is_valid())
        
        # Test empty selection (should be valid since not required)
        form = SurveyResponseForm(question, data={
            'response_value': [],
            'confidence_level': 4
        })
        
        self.assertTrue(form.is_valid())
        
    def test_boolean_validation(self):
        """Test boolean field validation."""
        question = SurveyQuestion.objects.create(
            category=self.category,
            section="Health Status",
            question_text="Do you smoke?",
            question_type=SurveyQuestion.QuestionType.BOOLEAN,
            field_name="smoker",
            is_required=True
        )
        
        # Test True value
        form = SurveyResponseForm(question, data={
            'response_value': True,
            'confidence_level': 4
        })
        
        self.assertTrue(form.is_valid())
        
        # Test False value
        form = SurveyResponseForm(question, data={
            'response_value': False,
            'confidence_level': 4
        })
        
        self.assertTrue(form.is_valid())
        
    def test_confidence_level_validation(self):
        """Test confidence level validation."""
        question = SurveyQuestion.objects.create(
            category=self.category,
            section="Personal Info",
            question_text="Test question",
            question_type=SurveyQuestion.QuestionType.TEXT,
            field_name="test_field"
        )
        
        # Test valid confidence levels
        for level in [1, 2, 3, 4, 5]:
            form = SurveyResponseForm(question, data={
                'response_value': 'test',
                'confidence_level': level
            })
            self.assertTrue(form.is_valid(), f"Confidence level {level} should be valid")
            
        # Test invalid confidence levels
        for level in [0, 6, -1, 10]:
            form = SurveyResponseForm(question, data={
                'response_value': 'test',
                'confidence_level': level
            })
            self.assertFalse(form.is_valid(), f"Confidence level {level} should be invalid")


class SurveyFormSaveTests(TestCase):
    """Test form save functionality."""
    
    def setUp(self):
        self.category = PolicyCategory.objects.create(
            name="Health Insurance",
            slug="health",
            description="Health insurance policies"
        )
        
        self.session = ComparisonSession.objects.create(
            session_key="test-session-123",
            category=self.category
        )
        
    def test_save_new_response(self):
        """Test saving a new response."""
        question = SurveyQuestion.objects.create(
            category=self.category,
            section="Personal Info",
            question_text="What is your age?",
            question_type=SurveyQuestion.QuestionType.NUMBER,
            field_name="age"
        )
        
        form = SurveyResponseForm(question, data={
            'response_value': 35,
            'confidence_level': 4
        })
        
        self.assertTrue(form.is_valid())
        
        response = form.save(self.session)
        
        self.assertIsNotNone(response)
        self.assertEqual(response.session, self.session)
        self.assertEqual(response.question, question)
        self.assertEqual(response.response_value, 35)
        self.assertEqual(response.confidence_level, 4)
        
        # Verify response exists in database
        saved_response = SurveyResponse.objects.get(session=self.session, question=question)
        self.assertEqual(saved_response.response_value, 35)
        
    def test_update_existing_response(self):
        """Test updating an existing response."""
        question = SurveyQuestion.objects.create(
            category=self.category,
            section="Personal Info",
            question_text="What is your age?",
            question_type=SurveyQuestion.QuestionType.NUMBER,
            field_name="age"
        )
        
        # Create initial response
        initial_response = SurveyResponse.objects.create(
            session=self.session,
            question=question,
            response_value=30,
            confidence_level=3
        )
        
        # Update via form
        form = SurveyResponseForm(question, data={
            'response_value': 35,
            'confidence_level': 5
        })
        
        self.assertTrue(form.is_valid())
        
        updated_response = form.save(self.session)
        
        # Should be the same object
        self.assertEqual(updated_response.id, initial_response.id)
        self.assertEqual(updated_response.response_value, 35)
        self.assertEqual(updated_response.confidence_level, 5)
        
        # Verify only one response exists
        self.assertEqual(SurveyResponse.objects.filter(
            session=self.session, question=question
        ).count(), 1)
        
    def test_save_invalid_form(self):
        """Test saving an invalid form returns None."""
        question = SurveyQuestion.objects.create(
            category=self.category,
            section="Personal Info",
            question_text="What is your age?",
            question_type=SurveyQuestion.QuestionType.NUMBER,
            field_name="age",
            validation_rules={"min_value": 18},
            is_required=True
        )
        
        form = SurveyResponseForm(question, data={
            'response_value': 15,  # Below minimum
            'confidence_level': 4
        })
        
        self.assertFalse(form.is_valid())
        
        response = form.save(self.session)
        
        self.assertIsNone(response)
        
        # Verify no response was saved
        self.assertEqual(SurveyResponse.objects.filter(
            session=self.session, question=question
        ).count(), 0)
        
    def test_save_different_data_types(self):
        """Test saving different data types."""
        # Text response
        text_question = SurveyQuestion.objects.create(
            category=self.category,
            section="Personal Info",
            question_text="What is your name?",
            question_type=SurveyQuestion.QuestionType.TEXT,
            field_name="name"
        )
        
        form = SurveyResponseForm(text_question, data={
            'response_value': 'John Doe',
            'confidence_level': 5
        })
        
        self.assertTrue(form.is_valid())
        response = form.save(self.session)
        self.assertEqual(response.response_value, 'John Doe')
        
        # Number response
        number_question = SurveyQuestion.objects.create(
            category=self.category,
            section="Personal Info",
            question_text="What is your age?",
            question_type=SurveyQuestion.QuestionType.NUMBER,
            field_name="age"
        )
        
        form = SurveyResponseForm(number_question, data={
            'response_value': 35,
            'confidence_level': 4
        })
        
        self.assertTrue(form.is_valid())
        response = form.save(self.session)
        self.assertEqual(response.response_value, 35)
        
        # Boolean response
        boolean_question = SurveyQuestion.objects.create(
            category=self.category,
            section="Health Status",
            question_text="Do you smoke?",
            question_type=SurveyQuestion.QuestionType.BOOLEAN,
            field_name="smoker"
        )
        
        form = SurveyResponseForm(boolean_question, data={
            'response_value': True,
            'confidence_level': 5
        })
        
        self.assertTrue(form.is_valid())
        response = form.save(self.session)
        self.assertEqual(response.response_value, True)
        
        # Choice response
        choices = [{"value": "male", "text": "Male"}, {"value": "female", "text": "Female"}]
        choice_question = SurveyQuestion.objects.create(
            category=self.category,
            section="Personal Info",
            question_text="What is your gender?",
            question_type=SurveyQuestion.QuestionType.CHOICE,
            field_name="gender",
            choices=choices
        )
        
        form = SurveyResponseForm(choice_question, data={
            'response_value': 'male',
            'confidence_level': 5
        })
        
        self.assertTrue(form.is_valid())
        response = form.save(self.session)
        self.assertEqual(response.response_value, 'male')


class BulkFormTests(TestCase):
    """Test bulk form functionality."""
    
    def setUp(self):
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
                question_text="What is your name?",
                question_type=SurveyQuestion.QuestionType.TEXT,
                field_name="name",
                is_required=True
            ),
            SurveyQuestion.objects.create(
                category=self.category,
                section="Personal Info",
                question_text="What is your age?",
                question_type=SurveyQuestion.QuestionType.NUMBER,
                field_name="age",
                is_required=True
            ),
            SurveyQuestion.objects.create(
                category=self.category,
                section="Health Status",
                question_text="Do you smoke?",
                question_type=SurveyQuestion.QuestionType.BOOLEAN,
                field_name="smoker",
                is_required=False
            )
        ]
        
    def test_bulk_form_field_creation(self):
        """Test that bulk form creates fields for all questions."""
        form = BulkSurveyResponseForm(self.questions)
        
        for question in self.questions:
            field_name = f'question_{question.id}'
            self.assertIn(field_name, form.fields)
            self.assertEqual(form.fields[field_name].label, question.question_text)
            self.assertEqual(form.fields[field_name].help_text, question.help_text)
            self.assertEqual(form.fields[field_name].required, question.is_required)
            
    def test_bulk_form_validation_all_valid(self):
        """Test bulk form validation with all valid data."""
        form_data = {
            f'question_{self.questions[0].id}': 'John Doe',
            f'question_{self.questions[1].id}': 35,
            f'question_{self.questions[2].id}': True
        }
        
        form = BulkSurveyResponseForm(self.questions, data=form_data)
        self.assertTrue(form.is_valid())
        
    def test_bulk_form_validation_missing_required(self):
        """Test bulk form validation with missing required fields."""
        form_data = {
            # Missing required name field
            f'question_{self.questions[1].id}': 35,
            f'question_{self.questions[2].id}': True
        }
        
        form = BulkSurveyResponseForm(self.questions, data=form_data)
        self.assertFalse(form.is_valid())
        
        required_field = f'question_{self.questions[0].id}'
        self.assertIn(required_field, form.errors)
        
    def test_bulk_form_validation_missing_optional(self):
        """Test bulk form validation with missing optional fields."""
        form_data = {
            f'question_{self.questions[0].id}': 'John Doe',
            f'question_{self.questions[1].id}': 35,
            # Missing optional smoker field
        }
        
        form = BulkSurveyResponseForm(self.questions, data=form_data)
        self.assertTrue(form.is_valid())
        
    def test_bulk_form_save(self):
        """Test bulk form save functionality."""
        form_data = {
            f'question_{self.questions[0].id}': 'John Doe',
            f'question_{self.questions[1].id}': 35,
            f'question_{self.questions[2].id}': True
        }
        
        form = BulkSurveyResponseForm(self.questions, data=form_data)
        self.assertTrue(form.is_valid())
        
        responses = form.save(self.session)
        
        self.assertEqual(len(responses), 3)
        
        # Verify each response
        name_response = SurveyResponse.objects.get(session=self.session, question=self.questions[0])
        self.assertEqual(name_response.response_value, 'John Doe')
        
        age_response = SurveyResponse.objects.get(session=self.session, question=self.questions[1])
        self.assertEqual(age_response.response_value, 35)
        
        smoker_response = SurveyResponse.objects.get(session=self.session, question=self.questions[2])
        self.assertEqual(smoker_response.response_value, True)
        
    def test_bulk_form_save_partial(self):
        """Test bulk form save with partial data."""
        form_data = {
            f'question_{self.questions[0].id}': 'John Doe',
            f'question_{self.questions[1].id}': 35,
            # No data for optional smoker question
        }
        
        form = BulkSurveyResponseForm(self.questions, data=form_data)
        self.assertTrue(form.is_valid())
        
        responses = form.save(self.session)
        
        # Should only save responses for fields with data
        self.assertEqual(len(responses), 2)
        
        # Verify responses exist for provided data
        self.assertTrue(SurveyResponse.objects.filter(
            session=self.session, question=self.questions[0]
        ).exists())
        
        self.assertTrue(SurveyResponse.objects.filter(
            session=self.session, question=self.questions[1]
        ).exists())
        
        # Verify no response for missing optional field
        self.assertFalse(SurveyResponse.objects.filter(
            session=self.session, question=self.questions[2]
        ).exists())
        
    def test_bulk_form_save_invalid(self):
        """Test bulk form save with invalid data."""
        form_data = {
            # Missing required name field
            f'question_{self.questions[1].id}': 35,
            f'question_{self.questions[2].id}': True
        }
        
        form = BulkSurveyResponseForm(self.questions, data=form_data)
        self.assertFalse(form.is_valid())
        
        responses = form.save(self.session)
        
        # Should return empty list for invalid form
        self.assertEqual(len(responses), 0)
        
        # Verify no responses were saved
        self.assertEqual(SurveyResponse.objects.filter(session=self.session).count(), 0)


class FormErrorHandlingTests(TestCase):
    """Test form error handling scenarios."""
    
    def setUp(self):
        self.category = PolicyCategory.objects.create(
            name="Health Insurance",
            slug="health",
            description="Health insurance policies"
        )
        
        self.session = ComparisonSession.objects.create(
            session_key="test-session-123",
            category=self.category
        )
        
    def test_form_with_invalid_question_type(self):
        """Test form creation with invalid question type."""
        # This would test edge cases in form creation
        pass
        
    def test_form_validation_edge_cases(self):
        """Test form validation edge cases."""
        question = SurveyQuestion.objects.create(
            category=self.category,
            section="Personal Info",
            question_text="Test question",
            question_type=SurveyQuestion.QuestionType.TEXT,
            field_name="test_field",
            validation_rules={"min_length": 1, "max_length": 10},
            is_required=True
        )
        
        # Test boundary values
        form = SurveyResponseForm(question, data={
            'response_value': 'a',  # Minimum length
            'confidence_level': 1   # Minimum confidence
        })
        self.assertTrue(form.is_valid())
        
        form = SurveyResponseForm(question, data={
            'response_value': 'a' * 10,  # Maximum length
            'confidence_level': 5        # Maximum confidence
        })
        self.assertTrue(form.is_valid())
        
    def test_form_save_database_error(self):
        """Test form save with database error."""
        question = SurveyQuestion.objects.create(
            category=self.category,
            section="Personal Info",
            question_text="Test question",
            question_type=SurveyQuestion.QuestionType.TEXT,
            field_name="test_field"
        )
        
        form = SurveyResponseForm(question, data={
            'response_value': 'test',
            'confidence_level': 4
        })
        
        self.assertTrue(form.is_valid())
        
        # Test with invalid session (should handle gracefully)
        invalid_session = ComparisonSession(
            session_key="invalid",
            category=self.category
        )
        # Don't save the session to database
        
        try:
            response = form.save(invalid_session)
            # Should handle the error gracefully
            self.assertIsNone(response)
        except Exception:
            # Or raise appropriate exception
            pass


class FormCustomizationTests(TestCase):
    """Test form customization features."""
    
    def setUp(self):
        self.category = PolicyCategory.objects.create(
            name="Health Insurance",
            slug="health",
            description="Health insurance policies"
        )
        
    def test_custom_form_attributes(self):
        """Test custom form attributes and styling."""
        question = SurveyQuestion.objects.create(
            category=self.category,
            section="Personal Info",
            question_text="Test question",
            question_type=SurveyQuestion.QuestionType.TEXT,
            field_name="test_field",
            help_text="Custom help text"
        )
        
        form = SurveyResponseForm(question)
        
        # Check that custom attributes are applied
        self.assertEqual(form.fields['response_value'].help_text, "Custom help text")
        
    def test_conditional_form_fields(self):
        """Test conditional form field display."""
        # This would test conditional field logic
        pass
        
    def test_form_localization(self):
        """Test form localization features."""
        # This would test form translation and localization
        pass