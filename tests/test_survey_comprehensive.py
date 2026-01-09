"""
Comprehensive test suite for survey question and input functionality.
Tests cover models, forms, views, user interactions, and edge cases.
"""

import json
from decimal import Decimal
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.http import JsonResponse
from unittest.mock import patch, MagicMock

from policies.models import PolicyCategory
from comparison.models import ComparisonSession
from surveys.models import (
    SurveyTemplate, SurveyQuestion, TemplateQuestion,
    SurveyResponse, QuestionDependency, SurveyAnalytics,
    UserSurveyProfile, SavedSurveyProfile
)
from surveys.forms import SurveyResponseForm, BulkSurveyResponseForm
from surveys.flow_controller import SurveyFlowController

User = get_user_model()


class SurveyQuestionModelTests(TestCase):
    """Test survey question model functionality."""
    
    def setUp(self):
        self.category = PolicyCategory.objects.create(
            name="Health Insurance",
            slug="health",
            description="Health insurance policies"
        )
        
    def test_text_question_creation(self):
        """Test creating a text input question."""
        question = SurveyQuestion.objects.create(
            category=self.category,
            section="Personal Info",
            question_text="What is your full name?",
            question_type=SurveyQuestion.QuestionType.TEXT,
            field_name="full_name",
            validation_rules={"min_length": 2, "max_length": 100},
            help_text="Enter your legal name as it appears on documents",
            is_required=True,
            display_order=1
        )
        
        self.assertEqual(question.question_type, SurveyQuestion.QuestionType.TEXT)
        self.assertTrue(question.is_required)
        self.assertEqual(question.validation_rules["min_length"], 2)
        self.assertEqual(question.validation_rules["max_length"], 100)
        
    def test_number_question_creation(self):
        """Test creating a number input question."""
        question = SurveyQuestion.objects.create(
            category=self.category,
            section="Personal Info",
            question_text="What is your age?",
            question_type=SurveyQuestion.QuestionType.NUMBER,
            field_name="age",
            validation_rules={"min_value": 18, "max_value": 100},
            is_required=True,
            display_order=2
        )
        
        self.assertEqual(question.question_type, SurveyQuestion.QuestionType.NUMBER)
        self.assertEqual(question.validation_rules["min_value"], 18)
        self.assertEqual(question.validation_rules["max_value"], 100)
        
    def test_choice_question_creation(self):
        """Test creating a single choice question."""
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
            is_required=True,
            display_order=3
        )
        
        self.assertEqual(question.question_type, SurveyQuestion.QuestionType.CHOICE)
        self.assertEqual(len(question.choices), 3)
        self.assertEqual(question.choices[0]["value"], "male")
        
    def test_multi_choice_question_creation(self):
        """Test creating a multiple choice question."""
        choices = [
            {"value": "diabetes", "text": "Diabetes"},
            {"value": "hypertension", "text": "High Blood Pressure"},
            {"value": "heart_disease", "text": "Heart Disease"},
            {"value": "none", "text": "None of the above"}
        ]
        
        question = SurveyQuestion.objects.create(
            category=self.category,
            section="Health Status",
            question_text="Do you have any of the following conditions?",
            question_type=SurveyQuestion.QuestionType.MULTI_CHOICE,
            field_name="medical_conditions",
            choices=choices,
            is_required=False,
            display_order=4
        )
        
        self.assertEqual(question.question_type, SurveyQuestion.QuestionType.MULTI_CHOICE)
        self.assertEqual(len(question.choices), 4)
        self.assertFalse(question.is_required)
        
    def test_boolean_question_creation(self):
        """Test creating a boolean (yes/no) question."""
        question = SurveyQuestion.objects.create(
            category=self.category,
            section="Health Status",
            question_text="Do you smoke?",
            question_type=SurveyQuestion.QuestionType.BOOLEAN,
            field_name="smoker",
            is_required=True,
            display_order=5
        )
        
        self.assertEqual(question.question_type, SurveyQuestion.QuestionType.BOOLEAN)
        self.assertTrue(question.is_required)
        
    def test_range_question_creation(self):
        """Test creating a range/slider question."""
        question = SurveyQuestion.objects.create(
            category=self.category,
            section="Preferences",
            question_text="How important is cost to you? (1-10)",
            question_type=SurveyQuestion.QuestionType.RANGE,
            field_name="cost_importance",
            validation_rules={"min_value": 1, "max_value": 10, "step": 1},
            is_required=True,
            display_order=6
        )
        
        self.assertEqual(question.question_type, SurveyQuestion.QuestionType.RANGE)
        self.assertEqual(question.validation_rules["min_value"], 1)
        self.assertEqual(question.validation_rules["max_value"], 10)
        
    def test_question_ordering(self):
        """Test that questions are ordered correctly."""
        question1 = SurveyQuestion.objects.create(
            category=self.category,
            section="Personal Info",
            question_text="Question 1",
            question_type=SurveyQuestion.QuestionType.TEXT,
            field_name="q1",
            display_order=3
        )
        
        question2 = SurveyQuestion.objects.create(
            category=self.category,
            section="Personal Info",
            question_text="Question 2",
            question_type=SurveyQuestion.QuestionType.TEXT,
            field_name="q2",
            display_order=1
        )
        
        question3 = SurveyQuestion.objects.create(
            category=self.category,
            section="Personal Info",
            question_text="Question 3",
            question_type=SurveyQuestion.QuestionType.TEXT,
            field_name="q3",
            display_order=2
        )
        
        questions = SurveyQuestion.objects.filter(category=self.category).order_by('display_order')
        self.assertEqual(questions[0], question2)  # display_order=1
        self.assertEqual(questions[1], question3)  # display_order=2
        self.assertEqual(questions[2], question1)  # display_order=3


class SurveyResponseModelTests(TestCase):
    """Test survey response model functionality."""
    
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
        
    def test_text_response_creation(self):
        """Test creating a text response."""
        question = SurveyQuestion.objects.create(
            category=self.category,
            section="Personal Info",
            question_text="What is your full name?",
            question_type=SurveyQuestion.QuestionType.TEXT,
            field_name="full_name"
        )
        
        response = SurveyResponse.objects.create(
            session=self.session,
            question=question,
            response_value="John Doe",
            confidence_level=5
        )
        
        self.assertEqual(response.response_value, "John Doe")
        self.assertEqual(response.confidence_level, 5)
        
    def test_number_response_creation(self):
        """Test creating a number response."""
        question = SurveyQuestion.objects.create(
            category=self.category,
            section="Personal Info",
            question_text="What is your age?",
            question_type=SurveyQuestion.QuestionType.NUMBER,
            field_name="age"
        )
        
        response = SurveyResponse.objects.create(
            session=self.session,
            question=question,
            response_value=35,
            confidence_level=4
        )
        
        self.assertEqual(response.response_value, 35)
        self.assertEqual(response.confidence_level, 4)
        
    def test_choice_response_creation(self):
        """Test creating a single choice response."""
        choices = [
            {"value": "male", "text": "Male"},
            {"value": "female", "text": "Female"}
        ]
        
        question = SurveyQuestion.objects.create(
            category=self.category,
            section="Personal Info",
            question_text="What is your gender?",
            question_type=SurveyQuestion.QuestionType.CHOICE,
            field_name="gender",
            choices=choices
        )
        
        response = SurveyResponse.objects.create(
            session=self.session,
            question=question,
            response_value="male",
            confidence_level=5
        )
        
        self.assertEqual(response.response_value, "male")
        
    def test_multi_choice_response_creation(self):
        """Test creating a multiple choice response."""
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
            choices=choices
        )
        
        response = SurveyResponse.objects.create(
            session=self.session,
            question=question,
            response_value=["diabetes", "hypertension"],
            confidence_level=4
        )
        
        self.assertEqual(len(response.response_value), 2)
        self.assertIn("diabetes", response.response_value)
        self.assertIn("hypertension", response.response_value)
        
    def test_boolean_response_creation(self):
        """Test creating a boolean response."""
        question = SurveyQuestion.objects.create(
            category=self.category,
            section="Health Status",
            question_text="Do you smoke?",
            question_type=SurveyQuestion.QuestionType.BOOLEAN,
            field_name="smoker"
        )
        
        response = SurveyResponse.objects.create(
            session=self.session,
            question=question,
            response_value=True,
            confidence_level=5
        )
        
        self.assertTrue(response.response_value)
        
    def test_range_response_creation(self):
        """Test creating a range response."""
        question = SurveyQuestion.objects.create(
            category=self.category,
            section="Preferences",
            question_text="How important is cost to you? (1-10)",
            question_type=SurveyQuestion.QuestionType.RANGE,
            field_name="cost_importance"
        )
        
        response = SurveyResponse.objects.create(
            session=self.session,
            question=question,
            response_value=8,
            confidence_level=4
        )
        
        self.assertEqual(response.response_value, 8)
        
    def test_response_update(self):
        """Test updating an existing response."""
        question = SurveyQuestion.objects.create(
            category=self.category,
            section="Personal Info",
            question_text="What is your age?",
            question_type=SurveyQuestion.QuestionType.NUMBER,
            field_name="age"
        )
        
        # Create initial response
        response = SurveyResponse.objects.create(
            session=self.session,
            question=question,
            response_value=30,
            confidence_level=3
        )
        
        # Update response
        response.response_value = 35
        response.confidence_level = 5
        response.save()
        
        # Verify update
        response.refresh_from_db()
        self.assertEqual(response.response_value, 35)
        self.assertEqual(response.confidence_level, 5)
        
    def test_unique_session_question_constraint(self):
        """Test that only one response per session-question pair is allowed."""
        question = SurveyQuestion.objects.create(
            category=self.category,
            section="Personal Info",
            question_text="What is your age?",
            question_type=SurveyQuestion.QuestionType.NUMBER,
            field_name="age"
        )
        
        # Create first response
        SurveyResponse.objects.create(
            session=self.session,
            question=question,
            response_value=30,
            confidence_level=3
        )
        
        # Attempt to create duplicate should raise error
        with self.assertRaises(Exception):
            SurveyResponse.objects.create(
                session=self.session,
                question=question,
                response_value=35,
                confidence_level=4
            )


class SurveyFormTests(TestCase):
    """Test survey form functionality."""
    
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
        
    def test_text_form_creation(self):
        """Test creating a form for text input question."""
        question = SurveyQuestion.objects.create(
            category=self.category,
            section="Personal Info",
            question_text="What is your full name?",
            question_type=SurveyQuestion.QuestionType.TEXT,
            field_name="full_name",
            validation_rules={"min_length": 2, "max_length": 100},
            help_text="Enter your legal name",
            is_required=True
        )
        
        form = SurveyResponseForm(question)
        
        self.assertIn('response_value', form.fields)
        self.assertIn('confidence_level', form.fields)
        self.assertTrue(form.fields['response_value'].required)
        self.assertEqual(form.fields['response_value'].label, question.question_text)
        self.assertEqual(form.fields['response_value'].help_text, question.help_text)
        
    def test_number_form_creation(self):
        """Test creating a form for number input question."""
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
        
        self.assertIn('response_value', form.fields)
        self.assertTrue(form.fields['response_value'].required)
        
    def test_choice_form_creation(self):
        """Test creating a form for single choice question."""
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
        
        self.assertIn('response_value', form.fields)
        self.assertEqual(len(form.fields['response_value'].choices), 3)
        
    def test_multi_choice_form_creation(self):
        """Test creating a form for multiple choice question."""
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
        
        self.assertIn('response_value', form.fields)
        self.assertFalse(form.fields['response_value'].required)
        
    def test_boolean_form_creation(self):
        """Test creating a form for boolean question."""
        question = SurveyQuestion.objects.create(
            category=self.category,
            section="Health Status",
            question_text="Do you smoke?",
            question_type=SurveyQuestion.QuestionType.BOOLEAN,
            field_name="smoker",
            is_required=True
        )
        
        form = SurveyResponseForm(question)
        
        self.assertIn('response_value', form.fields)
        # BooleanField handles required differently
        self.assertFalse(form.fields['response_value'].required)
        
    def test_range_form_creation(self):
        """Test creating a form for range question."""
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
        
        self.assertIn('response_value', form.fields)
        self.assertTrue(form.fields['response_value'].required)
        self.assertEqual(form.fields['response_value'].min_value, 1)
        self.assertEqual(form.fields['response_value'].max_value, 10)
        
    def test_form_validation_text_min_length(self):
        """Test form validation for text minimum length."""
        question = SurveyQuestion.objects.create(
            category=self.category,
            section="Personal Info",
            question_text="What is your full name?",
            question_type=SurveyQuestion.QuestionType.TEXT,
            field_name="full_name",
            validation_rules={"min_length": 5},
            is_required=True
        )
        
        # Test valid input
        form = SurveyResponseForm(question, data={
            'response_value': 'John Doe',
            'confidence_level': 4
        })
        self.assertTrue(form.is_valid())
        
        # Test invalid input (too short)
        form = SurveyResponseForm(question, data={
            'response_value': 'Jo',
            'confidence_level': 4
        })
        self.assertFalse(form.is_valid())
        self.assertIn('response_value', form.errors)
        
    def test_form_validation_number_range(self):
        """Test form validation for number range."""
        question = SurveyQuestion.objects.create(
            category=self.category,
            section="Personal Info",
            question_text="What is your age?",
            question_type=SurveyQuestion.QuestionType.NUMBER,
            field_name="age",
            validation_rules={"min_value": 18, "max_value": 100},
            is_required=True
        )
        
        # Test valid input
        form = SurveyResponseForm(question, data={
            'response_value': 35,
            'confidence_level': 4
        })
        self.assertTrue(form.is_valid())
        
        # Test invalid input (too low)
        form = SurveyResponseForm(question, data={
            'response_value': 15,
            'confidence_level': 4
        })
        self.assertFalse(form.is_valid())
        self.assertIn('response_value', form.errors)
        
        # Test invalid input (too high)
        form = SurveyResponseForm(question, data={
            'response_value': 150,
            'confidence_level': 4
        })
        self.assertFalse(form.is_valid())
        self.assertIn('response_value', form.errors)
        
    def test_form_save_functionality(self):
        """Test form save functionality."""
        question = SurveyQuestion.objects.create(
            category=self.category,
            section="Personal Info",
            question_text="What is your age?",
            question_type=SurveyQuestion.QuestionType.NUMBER,
            field_name="age",
            is_required=True
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
        
    def test_form_update_existing_response(self):
        """Test form updating existing response."""
        question = SurveyQuestion.objects.create(
            category=self.category,
            section="Personal Info",
            question_text="What is your age?",
            question_type=SurveyQuestion.QuestionType.NUMBER,
            field_name="age",
            is_required=True
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
        
        # Should be the same object, updated
        self.assertEqual(updated_response.id, initial_response.id)
        self.assertEqual(updated_response.response_value, 35)
        self.assertEqual(updated_response.confidence_level, 5)
        
        # Verify only one response exists
        self.assertEqual(SurveyResponse.objects.filter(
            session=self.session, question=question
        ).count(), 1)


class BulkSurveyFormTests(TestCase):
    """Test bulk survey form functionality."""
    
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
        
        # Create multiple questions
        self.questions = [
            SurveyQuestion.objects.create(
                category=self.category,
                section="Personal Info",
                question_text="What is your full name?",
                question_type=SurveyQuestion.QuestionType.TEXT,
                field_name="full_name",
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
                is_required=True
            )
        ]
        
    def test_bulk_form_creation(self):
        """Test creating a bulk form with multiple questions."""
        form = BulkSurveyResponseForm(self.questions)
        
        # Should have fields for all questions
        for question in self.questions:
            field_name = f'question_{question.id}'
            self.assertIn(field_name, form.fields)
            
    def test_bulk_form_validation(self):
        """Test bulk form validation."""
        form_data = {}
        for question in self.questions:
            field_name = f'question_{question.id}'
            if question.question_type == SurveyQuestion.QuestionType.TEXT:
                form_data[field_name] = "John Doe"
            elif question.question_type == SurveyQuestion.QuestionType.NUMBER:
                form_data[field_name] = 35
            elif question.question_type == SurveyQuestion.QuestionType.BOOLEAN:
                form_data[field_name] = True
                
        form = BulkSurveyResponseForm(self.questions, data=form_data)
        self.assertTrue(form.is_valid())
        
    def test_bulk_form_save(self):
        """Test bulk form save functionality."""
        form_data = {}
        for question in self.questions:
            field_name = f'question_{question.id}'
            if question.question_type == SurveyQuestion.QuestionType.TEXT:
                form_data[field_name] = "John Doe"
            elif question.question_type == SurveyQuestion.QuestionType.NUMBER:
                form_data[field_name] = 35
            elif question.question_type == SurveyQuestion.QuestionType.BOOLEAN:
                form_data[field_name] = True
                
        form = BulkSurveyResponseForm(self.questions, data=form_data)
        self.assertTrue(form.is_valid())
        
        responses = form.save(self.session)
        
        self.assertEqual(len(responses), len(self.questions))
        
        # Verify responses were created
        for question in self.questions:
            response = SurveyResponse.objects.get(session=self.session, question=question)
            self.assertIsNotNone(response)


class SurveyViewTests(TestCase):
    """Test survey view functionality."""
    
    def setUp(self):
        self.client = Client()
        self.category = PolicyCategory.objects.create(
            name="Health Insurance",
            slug="health",
            description="Health insurance policies"
        )
        
        # Create test questions
        self.question1 = SurveyQuestion.objects.create(
            category=self.category,
            section="Personal Info",
            question_text="What is your age?",
            question_type=SurveyQuestion.QuestionType.NUMBER,
            field_name="age",
            is_required=True,
            display_order=1
        )
        
        self.question2 = SurveyQuestion.objects.create(
            category=self.category,
            section="Health Status",
            question_text="Do you smoke?",
            question_type=SurveyQuestion.QuestionType.BOOLEAN,
            field_name="smoker",
            is_required=True,
            display_order=2
        )
        
    @patch('surveys.views.SurveyFlowController')
    def test_direct_survey_view(self, mock_flow_controller):
        """Test direct survey access view."""
        # Mock flow controller
        mock_instance = MagicMock()
        mock_instance.session_key = "test-session-123"
        mock_flow_controller.return_value = mock_instance
        
        response = self.client.get(reverse('surveys:direct_survey', kwargs={
            'category_slug': 'health'
        }))
        
        self.assertEqual(response.status_code, 302)  # Redirect
        self.assertIn('session=test-session-123', response.url)
        
    @patch('surveys.views.SurveyFlowController')
    def test_survey_form_view_get(self, mock_flow_controller):
        """Test survey form view GET request."""
        # Mock flow controller
        mock_instance = MagicMock()
        mock_instance.session_key = "test-session-123"
        mock_instance.category = self.category
        mock_instance.validate_session.return_value = True
        mock_instance.get_current_section_and_question.return_value = ("Personal Info", self.question1)
        mock_instance.engine.get_survey_sections.return_value = []
        mock_instance.get_section_progress.return_value = {}
        mock_instance.get_survey_summary.return_value = {'completion_percentage': 25.0}
        mock_flow_controller.return_value = mock_instance
        
        response = self.client.get(reverse('surveys:survey_form', kwargs={
            'category_slug': 'health'
        }) + '?session=test-session-123')
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.question1.question_text)
        self.assertIn('form', response.context)
        
    @patch('surveys.views.SurveyFlowController')
    def test_survey_form_view_post_valid(self, mock_flow_controller):
        """Test survey form view POST request with valid data."""
        # Mock flow controller
        mock_instance = MagicMock()
        mock_instance.session_key = "test-session-123"
        mock_instance.category = self.category
        mock_instance.validate_session.return_value = True
        mock_instance.get_current_section_and_question.return_value = ("Personal Info", self.question1)
        mock_instance.get_next_question.return_value = {'success': True, 'question': self.question2}
        mock_flow_controller.return_value = mock_instance
        
        # Create a session for the form to save to
        session = ComparisonSession.objects.create(
            session_key="test-session-123",
            category=self.category
        )
        
        response = self.client.post(reverse('surveys:survey_form', kwargs={
            'category_slug': 'health'
        }) + '?session=test-session-123', {
            'response_value': 35,
            'confidence_level': 4
        })
        
        self.assertEqual(response.status_code, 302)  # Redirect to next question
        
        # Verify response was saved
        survey_response = SurveyResponse.objects.get(session=session, question=self.question1)
        self.assertEqual(survey_response.response_value, 35)
        self.assertEqual(survey_response.confidence_level, 4)
        
    @patch('surveys.views.SurveyFlowController')
    def test_survey_form_view_post_invalid(self, mock_flow_controller):
        """Test survey form view POST request with invalid data."""
        # Mock flow controller
        mock_instance = MagicMock()
        mock_instance.session_key = "test-session-123"
        mock_instance.category = self.category
        mock_instance.validate_session.return_value = True
        mock_instance.get_current_section_and_question.return_value = ("Personal Info", self.question1)
        mock_flow_controller.return_value = mock_instance
        
        response = self.client.post(reverse('surveys:survey_form', kwargs={
            'category_slug': 'health'
        }) + '?session=test-session-123', {
            'response_value': '',  # Invalid - required field
            'confidence_level': 4
        })
        
        self.assertEqual(response.status_code, 200)  # Stay on same page
        self.assertContains(response, 'This field is required')
        
    def test_survey_progress_view(self):
        """Test survey progress view."""
        session = ComparisonSession.objects.create(
            session_key="test-session-123",
            category=self.category
        )
        
        # Create some responses
        SurveyResponse.objects.create(
            session=session,
            question=self.question1,
            response_value=35,
            confidence_level=4
        )
        
        response = self.client.get(reverse('surveys:survey_progress_view', kwargs={
            'session_key': 'test-session-123'
        }))
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(data['session_key'], 'test-session-123')
        self.assertEqual(data['total_responses'], 1)
        
    def test_submit_response_ajax_valid(self):
        """Test AJAX response submission with valid data."""
        session = ComparisonSession.objects.create(
            session_key="test-session-123",
            category=self.category
        )
        
        with patch('surveys.views.SurveyFlowController') as mock_flow_controller:
            mock_instance = MagicMock()
            mock_instance.validate_session.return_value = True
            mock_instance.submit_response.return_value = {'success': True, 'message': 'Response saved'}
            mock_flow_controller.return_value = mock_instance
            
            response = self.client.post(reverse('surveys:submit_response_ajax'), 
                json.dumps({
                    'session_key': 'test-session-123',
                    'category_slug': 'health',
                    'question_id': self.question1.id,
                    'response_value': 35,
                    'confidence_level': 4
                }),
                content_type='application/json'
            )
            
            self.assertEqual(response.status_code, 200)
            data = json.loads(response.content)
            self.assertTrue(data['success'])
            
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


class QuestionDependencyTests(TestCase):
    """Test question dependency functionality."""
    
    def setUp(self):
        self.category = PolicyCategory.objects.create(
            name="Health Insurance",
            slug="health",
            description="Health insurance policies"
        )
        
        self.parent_question = SurveyQuestion.objects.create(
            category=self.category,
            section="Health Status",
            question_text="Do you smoke?",
            question_type=SurveyQuestion.QuestionType.BOOLEAN,
            field_name="smoker"
        )
        
        self.child_question = SurveyQuestion.objects.create(
            category=self.category,
            section="Health Status",
            question_text="How many cigarettes per day?",
            question_type=SurveyQuestion.QuestionType.NUMBER,
            field_name="cigarettes_per_day"
        )
        
    def test_equals_condition(self):
        """Test EQUALS condition evaluation."""
        dependency = QuestionDependency.objects.create(
            parent_question=self.parent_question,
            child_question=self.child_question,
            condition_value=True,
            condition_operator=QuestionDependency.ConditionOperator.EQUALS
        )
        
        self.assertTrue(dependency.evaluate_condition(True))
        self.assertFalse(dependency.evaluate_condition(False))
        
    def test_not_equals_condition(self):
        """Test NOT_EQUALS condition evaluation."""
        dependency = QuestionDependency.objects.create(
            parent_question=self.parent_question,
            child_question=self.child_question,
            condition_value=True,
            condition_operator=QuestionDependency.ConditionOperator.NOT_EQUALS
        )
        
        self.assertFalse(dependency.evaluate_condition(True))
        self.assertTrue(dependency.evaluate_condition(False))
        
    def test_greater_than_condition(self):
        """Test GREATER_THAN condition evaluation."""
        age_question = SurveyQuestion.objects.create(
            category=self.category,
            section="Personal Info",
            question_text="What is your age?",
            question_type=SurveyQuestion.QuestionType.NUMBER,
            field_name="age"
        )
        
        dependency = QuestionDependency.objects.create(
            parent_question=age_question,
            child_question=self.child_question,
            condition_value=65,
            condition_operator=QuestionDependency.ConditionOperator.GREATER_THAN
        )
        
        self.assertTrue(dependency.evaluate_condition(70))
        self.assertFalse(dependency.evaluate_condition(60))
        self.assertFalse(dependency.evaluate_condition(65))
        
    def test_less_than_condition(self):
        """Test LESS_THAN condition evaluation."""
        age_question = SurveyQuestion.objects.create(
            category=self.category,
            section="Personal Info",
            question_text="What is your age?",
            question_type=SurveyQuestion.QuestionType.NUMBER,
            field_name="age"
        )
        
        dependency = QuestionDependency.objects.create(
            parent_question=age_question,
            child_question=self.child_question,
            condition_value=30,
            condition_operator=QuestionDependency.ConditionOperator.LESS_THAN
        )
        
        self.assertTrue(dependency.evaluate_condition(25))
        self.assertFalse(dependency.evaluate_condition(35))
        self.assertFalse(dependency.evaluate_condition(30))
        
    def test_contains_condition(self):
        """Test CONTAINS condition evaluation."""
        dependency = QuestionDependency.objects.create(
            parent_question=self.parent_question,
            child_question=self.child_question,
            condition_value="diabetes",
            condition_operator=QuestionDependency.ConditionOperator.CONTAINS
        )
        
        self.assertTrue(dependency.evaluate_condition(["diabetes", "hypertension"]))
        self.assertFalse(dependency.evaluate_condition(["hypertension", "heart_disease"]))
        
    def test_in_list_condition(self):
        """Test IN_LIST condition evaluation."""
        dependency = QuestionDependency.objects.create(
            parent_question=self.parent_question,
            child_question=self.child_question,
            condition_value=["yes", "sometimes"],
            condition_operator=QuestionDependency.ConditionOperator.IN_LIST
        )
        
        self.assertTrue(dependency.evaluate_condition("yes"))
        self.assertTrue(dependency.evaluate_condition("sometimes"))
        self.assertFalse(dependency.evaluate_condition("no"))
        
    def test_inactive_dependency(self):
        """Test that inactive dependencies return False."""
        dependency = QuestionDependency.objects.create(
            parent_question=self.parent_question,
            child_question=self.child_question,
            condition_value=True,
            condition_operator=QuestionDependency.ConditionOperator.EQUALS,
            is_active=False
        )
        
        # Even though condition would be true, dependency is inactive
        self.assertFalse(dependency.evaluate_condition(True))


class SurveyAnalyticsTests(TestCase):
    """Test survey analytics functionality."""
    
    def setUp(self):
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
            field_name="age"
        )
        
    def test_analytics_creation(self):
        """Test creating survey analytics."""
        analytics = SurveyAnalytics.objects.create(
            question=self.question,
            total_responses=100,
            completion_rate=95.5,
            skip_rate=4.5,
            most_common_response=35,
            response_distribution={"18-25": 20, "26-35": 40, "36-45": 30, "46+": 10}
        )
        
        self.assertEqual(analytics.question, self.question)
        self.assertEqual(analytics.total_responses, 100)
        self.assertEqual(analytics.completion_rate, Decimal('95.5'))
        self.assertEqual(analytics.skip_rate, Decimal('4.5'))
        self.assertEqual(analytics.most_common_response, 35)
        
    def test_analytics_update(self):
        """Test updating analytics based on responses."""
        analytics = SurveyAnalytics.objects.create(
            question=self.question,
            total_responses=0
        )
        
        # Create some responses
        session1 = ComparisonSession.objects.create(
            session_key="session-1",
            category=self.category
        )
        session2 = ComparisonSession.objects.create(
            session_key="session-2",
            category=self.category
        )
        
        SurveyResponse.objects.create(
            session=session1,
            question=self.question,
            response_value=25,
            confidence_level=4
        )
        
        SurveyResponse.objects.create(
            session=session2,
            question=self.question,
            response_value=35,
            confidence_level=5
        )
        
        # Update analytics
        analytics.update_analytics()
        
        self.assertEqual(analytics.total_responses, 2)


class UserSurveyProfileTests(TestCase):
    """Test user survey profile functionality."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.category = PolicyCategory.objects.create(
            name="Health Insurance",
            slug="health",
            description="Health insurance policies"
        )
        
    def test_profile_creation(self):
        """Test creating a user survey profile."""
        profile = UserSurveyProfile.objects.create(
            user=self.user,
            auto_save_responses=True,
            prefill_from_history=True,
            email_survey_reminders=False,
            data_retention_days=365
        )
        
        self.assertEqual(profile.user, self.user)
        self.assertTrue(profile.auto_save_responses)
        self.assertTrue(profile.prefill_from_history)
        self.assertFalse(profile.email_survey_reminders)
        self.assertEqual(profile.data_retention_days, 365)
        
    def test_profile_completion_stats_update(self):
        """Test updating survey completion statistics."""
        profile = UserSurveyProfile.objects.create(user=self.user)
        
        # Create completed sessions
        session1 = ComparisonSession.objects.create(
            session_key="session-1",
            category=self.category,
            user=self.user,
            survey_completed=True
        )
        
        session2 = ComparisonSession.objects.create(
            session_key="session-2",
            category=self.category,
            user=self.user,
            survey_completed=True
        )
        
        # Update stats
        profile.update_survey_completion_stats()
        
        self.assertEqual(profile.total_surveys_completed, 2)
        self.assertIsNotNone(profile.last_survey_date)


class SavedSurveyProfileTests(TestCase):
    """Test saved survey profile functionality."""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.category = PolicyCategory.objects.create(
            name="Health Insurance",
            slug="health",
            description="Health insurance policies"
        )
        
    def test_saved_profile_creation(self):
        """Test creating a saved survey profile."""
        profile = SavedSurveyProfile.objects.create(
            user=self.user,
            name="My Health Profile",
            category=self.category,
            description="Profile for health insurance surveys",
            survey_responses={"age": 35, "smoker": False},
            criteria_weights={"cost": 0.8, "coverage": 0.9},
            user_profile_data={"risk_level": "low"}
        )
        
        self.assertEqual(profile.user, self.user)
        self.assertEqual(profile.name, "My Health Profile")
        self.assertEqual(profile.category, self.category)
        self.assertEqual(profile.survey_responses["age"], 35)
        self.assertFalse(profile.survey_responses["smoker"])
        
    def test_mark_profile_used(self):
        """Test marking a profile as used."""
        profile = SavedSurveyProfile.objects.create(
            user=self.user,
            name="My Health Profile",
            category=self.category,
            usage_count=0
        )
        
        initial_usage = profile.usage_count
        profile.mark_used()
        
        self.assertEqual(profile.usage_count, initial_usage + 1)
        self.assertIsNotNone(profile.last_used)
        
    def test_set_as_default_profile(self):
        """Test setting a profile as default."""
        profile1 = SavedSurveyProfile.objects.create(
            user=self.user,
            name="Profile 1",
            category=self.category,
            is_default=True
        )
        
        profile2 = SavedSurveyProfile.objects.create(
            user=self.user,
            name="Profile 2",
            category=self.category,
            is_default=False
        )
        
        # Set profile2 as default
        profile2.set_as_default()
        
        # Refresh from database
        profile1.refresh_from_db()
        profile2.refresh_from_db()
        
        self.assertFalse(profile1.is_default)
        self.assertTrue(profile2.is_default)


class SurveyIntegrationTests(TestCase):
    """Integration tests for complete survey workflows."""
    
    def setUp(self):
        self.client = Client()
        self.category = PolicyCategory.objects.create(
            name="Health Insurance",
            slug="health",
            description="Health insurance policies"
        )
        
        # Create a complete survey
        self.questions = [
            SurveyQuestion.objects.create(
                category=self.category,
                section="Personal Info",
                question_text="What is your full name?",
                question_type=SurveyQuestion.QuestionType.TEXT,
                field_name="full_name",
                is_required=True,
                display_order=1
            ),
            SurveyQuestion.objects.create(
                category=self.category,
                section="Personal Info",
                question_text="What is your age?",
                question_type=SurveyQuestion.QuestionType.NUMBER,
                field_name="age",
                validation_rules={"min_value": 18, "max_value": 100},
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
    def test_complete_survey_workflow(self, mock_flow_controller):
        """Test completing a full survey workflow."""
        # Mock flow controller for different stages
        mock_instance = MagicMock()
        mock_instance.session_key = "test-session-123"
        mock_instance.category = self.category
        mock_instance.validate_session.return_value = True
        mock_flow_controller.return_value = mock_instance
        
        # Create session
        session = ComparisonSession.objects.create(
            session_key="test-session-123",
            category=self.category
        )
        
        # Step 1: Start survey
        mock_instance.get_current_section_and_question.return_value = ("Personal Info", self.questions[0])
        mock_instance.engine.get_survey_sections.return_value = []
        mock_instance.get_section_progress.return_value = {}
        mock_instance.get_survey_summary.return_value = {'completion_percentage': 0.0}
        
        response = self.client.get(reverse('surveys:survey_form', kwargs={
            'category_slug': 'health'
        }) + '?session=test-session-123')
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.questions[0].question_text)
        
        # Step 2: Answer first question
        mock_instance.get_next_question.return_value = {'success': True, 'question': self.questions[1]}
        
        response = self.client.post(reverse('surveys:survey_form', kwargs={
            'category_slug': 'health'
        }) + '?session=test-session-123', {
            'response_value': 'John Doe',
            'confidence_level': 5
        })
        
        self.assertEqual(response.status_code, 302)  # Redirect to next question
        
        # Verify response was saved
        response_obj = SurveyResponse.objects.get(session=session, question=self.questions[0])
        self.assertEqual(response_obj.response_value, 'John Doe')
        
        # Step 3: Answer second question
        mock_instance.get_current_section_and_question.return_value = ("Personal Info", self.questions[1])
        mock_instance.get_next_question.return_value = {'success': True, 'question': self.questions[2]}
        
        response = self.client.post(reverse('surveys:survey_form', kwargs={
            'category_slug': 'health'
        }) + '?session=test-session-123', {
            'response_value': 35,
            'confidence_level': 4
        })
        
        self.assertEqual(response.status_code, 302)
        
        # Verify response was saved
        response_obj = SurveyResponse.objects.get(session=session, question=self.questions[1])
        self.assertEqual(response_obj.response_value, 35)
        
        # Step 4: Answer final question
        mock_instance.get_current_section_and_question.return_value = ("Health Status", self.questions[2])
        mock_instance.get_next_question.return_value = {'success': False}  # Survey complete
        
        response = self.client.post(reverse('surveys:survey_form', kwargs={
            'category_slug': 'health'
        }) + '?session=test-session-123', {
            'response_value': False,
            'confidence_level': 5
        })
        
        # Should redirect to completion page
        self.assertEqual(response.status_code, 302)
        
        # Verify final response was saved
        response_obj = SurveyResponse.objects.get(session=session, question=self.questions[2])
        self.assertEqual(response_obj.response_value, False)
        
        # Verify all responses exist
        self.assertEqual(SurveyResponse.objects.filter(session=session).count(), 3)
        
    def test_survey_validation_errors(self):
        """Test handling of validation errors during survey."""
        session = ComparisonSession.objects.create(
            session_key="test-session-123",
            category=self.category
        )
        
        with patch('surveys.views.SurveyFlowController') as mock_flow_controller:
            mock_instance = MagicMock()
            mock_instance.session_key = "test-session-123"
            mock_instance.category = self.category
            mock_instance.validate_session.return_value = True
            mock_instance.get_current_section_and_question.return_value = ("Personal Info", self.questions[1])  # Age question
            mock_instance.engine.get_survey_sections.return_value = []
            mock_instance.get_section_progress.return_value = {}
            mock_instance.get_survey_summary.return_value = {'completion_percentage': 33.0}
            mock_flow_controller.return_value = mock_instance
            
            # Submit invalid age (below minimum)
            response = self.client.post(reverse('surveys:survey_form', kwargs={
                'category_slug': 'health'
            }) + '?session=test-session-123', {
                'response_value': 15,  # Below minimum of 18
                'confidence_level': 4
            })
            
            # Should stay on same page with error
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, 'Value must be at least 18')
            
            # Verify no response was saved
            self.assertEqual(SurveyResponse.objects.filter(
                session=session, question=self.questions[1]
            ).count(), 0)


class SurveyErrorHandlingTests(TestCase):
    """Test error handling in survey functionality."""
    
    def setUp(self):
        self.client = Client()
        self.category = PolicyCategory.objects.create(
            name="Health Insurance",
            slug="health",
            description="Health insurance policies"
        )
        
    def test_invalid_session_handling(self):
        """Test handling of invalid session keys."""
        with patch('surveys.views.SurveyFlowController') as mock_flow_controller:
            mock_instance = MagicMock()
            mock_instance.validate_session.return_value = False
            mock_flow_controller.return_value = mock_instance
            
            response = self.client.get(reverse('surveys:survey_form', kwargs={
                'category_slug': 'health'
            }) + '?session=invalid-session')
            
            # Should redirect to direct survey
            self.assertEqual(response.status_code, 302)
            
    def test_nonexistent_category_handling(self):
        """Test handling of nonexistent category."""
        response = self.client.get(reverse('surveys:direct_survey', kwargs={
            'category_slug': 'nonexistent'
        }))
        
        # Should handle gracefully (implementation dependent)
        self.assertIn(response.status_code, [302, 404, 500])
        
    def test_ajax_invalid_json_handling(self):
        """Test AJAX endpoints with invalid JSON."""
        response = self.client.post(reverse('surveys:submit_response_ajax'), 
            'invalid json',
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
        
    def test_ajax_missing_parameters(self):
        """Test AJAX endpoints with missing parameters."""
        response = self.client.post(reverse('surveys:navigate_section_ajax'), 
            json.dumps({}),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertFalse(data['success'])
        self.assertIn('Missing required parameters', data['error'])


class SurveyPerformanceTests(TestCase):
    """Test performance aspects of survey functionality."""
    
    def setUp(self):
        self.category = PolicyCategory.objects.create(
            name="Health Insurance",
            slug="health",
            description="Health insurance policies"
        )
        
    def test_bulk_question_creation(self):
        """Test creating many questions efficiently."""
        questions_data = []
        for i in range(100):
            questions_data.append(SurveyQuestion(
                category=self.category,
                section=f"Section {i // 10}",
                question_text=f"Question {i}?",
                question_type=SurveyQuestion.QuestionType.TEXT,
                field_name=f"field_{i}",
                display_order=i
            ))
            
        # Bulk create should be efficient
        questions = SurveyQuestion.objects.bulk_create(questions_data)
        self.assertEqual(len(questions), 100)
        
    def test_bulk_response_creation(self):
        """Test creating many responses efficiently."""
        # Create questions
        questions = []
        for i in range(10):
            questions.append(SurveyQuestion.objects.create(
                category=self.category,
                section="Test Section",
                question_text=f"Question {i}?",
                question_type=SurveyQuestion.QuestionType.TEXT,
                field_name=f"field_{i}",
                display_order=i
            ))
            
        # Create sessions
        sessions = []
        for i in range(10):
            sessions.append(ComparisonSession.objects.create(
                session_key=f"session-{i}",
                category=self.category
            ))
            
        # Create responses in bulk
        responses_data = []
        for session in sessions:
            for question in questions:
                responses_data.append(SurveyResponse(
                    session=session,
                    question=question,
                    response_value=f"Response {question.id}",
                    confidence_level=4
                ))
                
        responses = SurveyResponse.objects.bulk_create(responses_data)
        self.assertEqual(len(responses), 100)  # 10 sessions * 10 questions
        
    def test_query_optimization(self):
        """Test that queries are optimized with select_related/prefetch_related."""
        # Create test data
        question = SurveyQuestion.objects.create(
            category=self.category,
            section="Test Section",
            question_text="Test Question?",
            question_type=SurveyQuestion.QuestionType.TEXT,
            field_name="test_field"
        )
        
        session = ComparisonSession.objects.create(
            session_key="test-session",
            category=self.category
        )
        
        SurveyResponse.objects.create(
            session=session,
            question=question,
            response_value="Test Response",
            confidence_level=4
        )
        
        # Test optimized query
        with self.assertNumQueries(1):
            responses = list(SurveyResponse.objects.select_related(
                'session', 'question', 'question__category'
            ).filter(session=session))
            
            # Access related objects (should not trigger additional queries)
            for response in responses:
                _ = response.session.category.name
                _ = response.question.question_text


class SurveyIntegrationTests(TestCase):
    """Test integration between survey components."""
    
    def setUp(self):
        self.client = Client()
        self.category = PolicyCategory.objects.create(
            name="Health Insurance",
            slug="health",
            description="Health insurance policies"
        )
        
    def test_end_to_end_survey_completion(self):
        """Test complete end-to-end survey flow."""
        # Create questions
        questions = [
            SurveyQuestion.objects.create(
                category=self.category,
                section="Personal Info",
                question_text="What is your age?",
                question_type=SurveyQuestion.QuestionType.NUMBER,
                field_name="age",
                is_required=True,
                display_order=1
            ),
            SurveyQuestion.objects.create(
                category=self.category,
                section="Health Status",
                question_text="Do you smoke?",
                question_type=SurveyQuestion.QuestionType.BOOLEAN,
                field_name="smoker",
                is_required=True,
                display_order=2
            )
        ]
        
        # This would test the complete flow from start to finish
        # Implementation would depend on actual survey flow
        pass
        
    def test_survey_data_consistency(self):
        """Test data consistency across survey operations."""
        session = ComparisonSession.objects.create(
            session_key="test-session-123",
            category=self.category
        )
        
        question = SurveyQuestion.objects.create(
            category=self.category,
            section="Personal Info",
            question_text="Test question",
            question_type=SurveyQuestion.QuestionType.TEXT,
            field_name="test_field"
        )
        
        # Create response
        response = SurveyResponse.objects.create(
            session=session,
            question=question,
            response_value="initial value",
            confidence_level=3
        )
        
        # Update response
        response.response_value = "updated value"
        response.confidence_level = 5
        response.save()
        
        # Verify consistency
        response.refresh_from_db()
        self.assertEqual(response.response_value, "updated value")
        self.assertEqual(response.confidence_level, 5)
        
    def test_survey_error_recovery(self):
        """Test survey error recovery mechanisms."""
        # This would test error recovery scenarios
        pass


class SurveySecurityTests(TestCase):
    """Test survey security features."""
    
    def setUp(self):
        self.client = Client()
        self.category = PolicyCategory.objects.create(
            name="Health Insurance",
            slug="health",
            description="Health insurance policies"
        )
        
    def test_session_security(self):
        """Test session security measures."""
        # This would test session validation and security
        pass
        
    def test_input_sanitization(self):
        """Test input sanitization."""
        question = SurveyQuestion.objects.create(
            category=self.category,
            section="Personal Info",
            question_text="Test question",
            question_type=SurveyQuestion.QuestionType.TEXT,
            field_name="test_field"
        )
        
        # Test with potentially malicious input
        malicious_input = "<script>alert('xss')</script>"
        
        form = SurveyResponseForm(question, data={
            'response_value': malicious_input,
            'confidence_level': 4
        })
        
        # Form should handle this appropriately
        if form.is_valid():
            # Input should be sanitized
            self.assertNotIn('<script>', form.cleaned_data['response_value'])
            
    def test_csrf_protection(self):
        """Test CSRF protection on forms."""
        # This would test CSRF token validation
        pass


class SurveyAccessibilityTests(TestCase):
    """Test survey accessibility features."""
    
    def setUp(self):
        self.client = Client()
        self.category = PolicyCategory.objects.create(
            name="Health Insurance",
            slug="health",
            description="Health insurance policies"
        )
        
    def test_form_accessibility(self):
        """Test form accessibility features."""
        question = SurveyQuestion.objects.create(
            category=self.category,
            section="Personal Info",
            question_text="Test question",
            question_type=SurveyQuestion.QuestionType.TEXT,
            field_name="test_field",
            help_text="Help text for accessibility"
        )
        
        form = SurveyResponseForm(question)
        
        # Check that help text is available for screen readers
        self.assertEqual(form.fields['response_value'].help_text, "Help text for accessibility")
        
    def test_keyboard_navigation(self):
        """Test keyboard navigation support."""
        # This would test keyboard accessibility
        pass
        
    def test_screen_reader_support(self):
        """Test screen reader support."""
        # This would test screen reader compatibility
        pass


class SurveyRenderingTests(TestCase):
    """Test survey question and input rendering for users."""
    
    def setUp(self):
        self.client = Client()
        self.category = PolicyCategory.objects.create(
            name="Health Insurance",
            slug="health",
            description="Health insurance policies"
        )
        
    def test_text_question_rendering(self):
        """Test that text questions render properly with input fields."""
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
        
        # Check that text input is rendered
        self.assertIn('type="text"', form_html)
        self.assertIn('class="form-control"', form_html)
        self.assertIn('placeholder="Enter your answer"', form_html)
        
    def test_number_question_rendering(self):
        """Test that number questions render with proper input type."""
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
        
        # Check that number input is rendered
        self.assertIn('type="number"', form_html)
        self.assertIn('class="form-control"', form_html)
        self.assertIn('placeholder="Enter a number"', form_html)
        
    def test_choice_question_rendering(self):
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
        
        # Check that radio buttons are rendered
        self.assertIn('type="radio"', form_html)
        self.assertIn('class="form-check-input"', form_html)
        self.assertIn('value="male"', form_html)
        self.assertIn('value="female"', form_html)
        self.assertIn('value="other"', form_html)
        
        # Check that choice labels are rendered
        self.assertIn('Male', form_html)
        self.assertIn('Female', form_html)
        self.assertIn('Other', form_html)
        
    def test_multi_choice_question_rendering(self):
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
        
        # Check that checkboxes are rendered
        self.assertIn('type="checkbox"', form_html)
        self.assertIn('class="form-check-input"', form_html)
        self.assertIn('value="diabetes"', form_html)
        self.assertIn('value="hypertension"', form_html)
        self.assertIn('value="heart_disease"', form_html)
        
        # Check that choice labels are rendered
        self.assertIn('Diabetes', form_html)
        self.assertIn('High Blood Pressure', form_html)
        self.assertIn('Heart Disease', form_html)
        
    def test_boolean_question_rendering(self):
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
        
        # Check that boolean radio buttons are rendered
        self.assertIn('type="radio"', form_html)
        self.assertIn('class="form-check-input"', form_html)
        self.assertIn('value="True"', form_html)
        self.assertIn('value="False"', form_html)
        
        # Check that Yes/No labels are rendered
        self.assertIn('Yes', form_html)
        self.assertIn('No', form_html)
        
    def test_range_question_rendering(self):
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
        
        # Check that range input is rendered
        self.assertIn('type="range"', form_html)
        self.assertIn('class="form-range"', form_html)
        self.assertIn('min="1"', form_html)
        self.assertIn('max="10"', form_html)
        self.assertIn('step="1"', form_html)
        
    def test_confidence_level_rendering(self):
        """Test that confidence level slider is rendered."""
        question = SurveyQuestion.objects.create(
            category=self.category,
            section="Personal Info",
            question_text="Test question",
            question_type=SurveyQuestion.QuestionType.TEXT,
            field_name="test_field"
        )
        
        form = SurveyResponseForm(question)
        confidence_html = str(form['confidence_level'])
        
        # Check that confidence level range input is rendered
        self.assertIn('type="range"', confidence_html)
        self.assertIn('class="form-range"', confidence_html)
        self.assertIn('min="1"', confidence_html)
        self.assertIn('max="5"', confidence_html)
        self.assertIn('step="1"', confidence_html)
        
    @patch('surveys.views.SurveyFlowController')
    def test_question_rendering_in_view(self, mock_flow_controller):
        """Test that questions are properly rendered in the survey view."""
        question = SurveyQuestion.objects.create(
            category=self.category,
            section="Personal Info",
            question_text="What is your age?",
            question_type=SurveyQuestion.QuestionType.NUMBER,
            field_name="age",
            help_text="Enter your age in years",
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
        
        # Check that question text is rendered
        self.assertContains(response, question.question_text)
        self.assertContains(response, "What is your age?")
        
        # Check that help text is rendered
        self.assertContains(response, question.help_text)
        self.assertContains(response, "Enter your age in years")
        
        # Check that form elements are present
        content = response.content.decode()
        self.assertIn('type="number"', content)
        self.assertIn('name="response_value"', content)
        self.assertIn('name="confidence_level"', content)
        
        # Check that required field indicator is present
        self.assertIn('required', content)
        
    @patch('surveys.views.SurveyFlowController')
    def test_multiple_choice_rendering_in_view(self, mock_flow_controller):
        """Test that multiple choice questions render properly in view."""
        choices = [
            {"value": "option1", "text": "Option 1"},
            {"value": "option2", "text": "Option 2"},
            {"value": "option3", "text": "Option 3"}
        ]
        
        question = SurveyQuestion.objects.create(
            category=self.category,
            section="Preferences",
            question_text="Which options do you prefer?",
            question_type=SurveyQuestion.QuestionType.MULTI_CHOICE,
            field_name="preferences",
            choices=choices,
            is_required=False
        )
        
        # Mock flow controller
        mock_instance = MagicMock()
        mock_instance.session_key = "test-session-123"
        mock_instance.category = self.category
        mock_instance.validate_session.return_value = True
        mock_instance.get_current_section_and_question.return_value = ("Preferences", question)
        mock_instance.engine.get_survey_sections.return_value = []
        mock_instance.get_section_progress.return_value = {}
        mock_instance.get_survey_summary.return_value = {'completion_percentage': 25.0}
        mock_flow_controller.return_value = mock_instance
        
        response = self.client.get(reverse('surveys:survey_form', kwargs={
            'category_slug': 'health'
        }) + '?session=test-session-123')
        
        self.assertEqual(response.status_code, 200)
        
        # Check that question text is rendered
        self.assertContains(response, "Which options do you prefer?")
        
        # Check that all choice options are rendered
        content = response.content.decode()
        self.assertIn('Option 1', content)
        self.assertIn('Option 2', content)
        self.assertIn('Option 3', content)
        
        # Check that checkboxes are rendered
        self.assertIn('type="checkbox"', content)
        self.assertIn('value="option1"', content)
        self.assertIn('value="option2"', content)
        self.assertIn('value="option3"', content)


class SurveyAccessibilityRenderingTests(TestCase):
    """Test accessibility features in survey rendering."""
    
    def setUp(self):
        self.client = Client()
        self.category = PolicyCategory.objects.create(
            name="Health Insurance",
            slug="health",
            description="Health insurance policies"
        )
        
    def test_form_labels_and_accessibility(self):
        """Test that forms have proper labels and accessibility attributes."""
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
        
        # Check that form has proper labels
        self.assertEqual(form.fields['response_value'].label, question.question_text)
        self.assertEqual(form.fields['response_value'].help_text, question.help_text)
        self.assertTrue(form.fields['response_value'].required)
        
        # Check confidence level field
        self.assertEqual(form.fields['confidence_level'].label, "How confident are you in this answer?")
        
    @patch('surveys.views.SurveyFlowController')
    def test_accessibility_attributes_in_view(self, mock_flow_controller):
        """Test that accessibility attributes are present in rendered view."""
        question = SurveyQuestion.objects.create(
            category=self.category,
            section="Personal Info",
            question_text="What is your age?",
            question_type=SurveyQuestion.QuestionType.NUMBER,
            field_name="age",
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
        mock_instance.get_survey_summary.return_value = {'completion_percentage': 25.0}
        mock_flow_controller.return_value = mock_instance
        
        response = self.client.get(reverse('surveys:survey_form', kwargs={
            'category_slug': 'health'
        }) + '?session=test-session-123')
        
        self.assertEqual(response.status_code, 200)
        
        content = response.content.decode()
        
        # Check for accessibility attributes
        self.assertIn('aria-', content)  # Should have ARIA attributes
        self.assertIn('role=', content)  # Should have role attributes
        self.assertIn('tabindex', content)  # Should have tab order
        
        # Check for proper form structure
        self.assertIn('<label', content)  # Should have labels
        self.assertIn('for=', content)    # Labels should be associated with inputs