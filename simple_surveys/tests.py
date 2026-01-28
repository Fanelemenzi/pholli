from django.test import TestCase
from django.utils import timezone
from datetime import timedelta
from .models import SimpleSurveyQuestion, SimpleSurveyResponse, QuotationSession, SimpleSurvey
from .engine import SimpleSurveyEngine


class SimpleSurveyQuestionModelTest(TestCase):
    """Test cases for SimpleSurveyQuestion model"""
    
    def setUp(self):
        """Set up test data"""
        self.question = SimpleSurveyQuestion.objects.create(
            category='health',
            question_text='What is your age?',
            field_name='age',
            input_type='number',
            display_order=1,
            validation_rules={'min': 18, 'max': 80}
        )
    
    def test_question_creation(self):
        """Test question creation and string representation"""
        self.assertEqual(self.question.category, 'health')
        self.assertEqual(self.question.field_name, 'age')
        self.assertTrue(self.question.is_required)
        self.assertIn('Health Insurance', str(self.question))
    
    def test_question_validation_valid_response(self):
        """Test validation with valid response"""
        errors = self.question.validate_response(25)
        self.assertEqual(len(errors), 0)
    
    def test_question_validation_invalid_response(self):
        """Test validation with invalid response"""
        errors = self.question.validate_response(15)  # Below minimum
        self.assertGreater(len(errors), 0)
        self.assertIn('at least', errors[0])
    
    def test_question_validation_required_field(self):
        """Test validation for required field"""
        errors = self.question.validate_response(None)
        self.assertGreater(len(errors), 0)
        self.assertIn('required', errors[0])
    
    def test_question_manager_for_category(self):
        """Test manager method for category filtering"""
        # Create another question for funeral category
        SimpleSurveyQuestion.objects.create(
            category='funeral',
            question_text='Coverage amount needed?',
            field_name='coverage_amount',
            input_type='radio',
            display_order=1,
            choices=['25000', '50000', '100000']
        )
        
        health_questions = SimpleSurveyQuestion.objects.for_category('health')
        self.assertEqual(health_questions.count(), 1)
        self.assertEqual(health_questions.first().category, 'health')


class SimpleSurveyResponseModelTest(TestCase):
    """Test cases for SimpleSurveyResponse model"""
    
    def setUp(self):
        """Set up test data"""
        self.question = SimpleSurveyQuestion.objects.create(
            category='health',
            question_text='What is your age?',
            field_name='age',
            input_type='number',
            display_order=1
        )
        
        self.response = SimpleSurveyResponse.objects.create(
            session_key='test_session_123',
            category='health',
            question=self.question,
            response_value=30
        )
    
    def test_response_creation(self):
        """Test response creation and string representation"""
        self.assertEqual(self.response.session_key, 'test_session_123')
        self.assertEqual(self.response.response_value, 30)
        self.assertIn('test_ses', str(self.response))  # Matches the 8-character truncation
    
    def test_response_display_value(self):
        """Test display value formatting"""
        self.assertEqual(self.response.get_display_value(), '30')
        
        # Test with checkbox response - need to create a checkbox question first
        checkbox_question = SimpleSurveyQuestion.objects.create(
            category='health',
            question_text='What conditions do you have?',
            field_name='conditions',
            input_type='checkbox',
            display_order=2,
            choices=['diabetes', 'hypertension', 'heart_disease']
        )
        
        checkbox_response = SimpleSurveyResponse.objects.create(
            session_key='test_session_456',
            category='health',
            question=checkbox_question,
            response_value=['option1', 'option2']
        )
        self.assertEqual(checkbox_response.get_display_value(), 'option1, option2')
    
    def test_response_manager_for_session(self):
        """Test manager method for session filtering"""
        responses = SimpleSurveyResponse.objects.for_session('test_session_123')
        self.assertEqual(responses.count(), 1)
        self.assertEqual(responses.first().session_key, 'test_session_123')


class QuotationSessionModelTest(TestCase):
    """Test cases for QuotationSession model"""
    
    def setUp(self):
        """Set up test data"""
        self.session = QuotationSession.objects.create_session(
            session_key='test_session_789',
            category='health'
        )
        
        # Create a question and response for completion testing
        self.question = SimpleSurveyQuestion.objects.create(
            category='health',
            question_text='What is your age?',
            field_name='age',
            input_type='number',
            display_order=1,
            is_required=True
        )
    
    def test_session_creation(self):
        """Test session creation with manager method"""
        self.assertEqual(self.session.session_key, 'test_session_789')
        self.assertEqual(self.session.category, 'health')
        self.assertFalse(self.session.is_completed)
        self.assertFalse(self.session.is_expired())
    
    def test_session_expiry(self):
        """Test session expiry functionality"""
        # Create an expired session
        expired_session = QuotationSession.objects.create(
            session_key='expired_session',
            category='health',
            expires_at=timezone.now() - timedelta(hours=1)
        )
        
        self.assertTrue(expired_session.is_expired())
        self.assertFalse(self.session.is_expired())
    
    def test_session_completion_percentage(self):
        """Test completion percentage calculation"""
        # Initially 0% complete (no responses)
        self.assertEqual(self.session.get_completion_percentage(), 0)
        
        # Add a response
        SimpleSurveyResponse.objects.create(
            session_key=self.session.session_key,
            category='health',
            question=self.question,
            response_value=25
        )
        
        # Should be 100% complete (1 required question answered)
        self.assertEqual(self.session.get_completion_percentage(), 100)
    
    def test_session_mark_completed(self):
        """Test marking session as completed"""
        self.assertFalse(self.session.is_completed)
        self.session.mark_completed()
        self.assertTrue(self.session.is_completed)
    
    def test_session_extend_expiry(self):
        """Test extending session expiry"""
        original_expiry = self.session.expires_at
        self.session.extend_expiry(48)  # Extend by 48 hours
        
        self.assertGreater(self.session.expires_at, original_expiry)
    
    def test_session_manager_active_sessions(self):
        """Test manager method for active sessions"""
        # Create an expired session
        QuotationSession.objects.create(
            session_key='expired_session',
            category='health',
            expires_at=timezone.now() - timedelta(hours=1)
        )
        
        active_sessions = QuotationSession.objects.active_sessions()
        self.assertEqual(active_sessions.count(), 1)
        self.assertEqual(active_sessions.first().session_key, 'test_session_789')


class ModelIntegrationTest(TestCase):
    """Integration tests for model interactions"""
    
    def setUp(self):
        """Set up test data for integration testing"""
        # Create questions
        self.age_question = SimpleSurveyQuestion.objects.create(
            category='health',
            question_text='What is your age?',
            field_name='age',
            input_type='number',
            display_order=1,
            is_required=True,
            validation_rules={'min': 18, 'max': 80}
        )
        
        self.location_question = SimpleSurveyQuestion.objects.create(
            category='health',
            question_text='What is your location?',
            field_name='location',
            input_type='select',
            display_order=2,
            is_required=True,
            choices=['Western Cape', 'Gauteng', 'KwaZulu-Natal']
        )
        
        # Create session
        self.session = QuotationSession.objects.create_session(
            session_key='integration_test_session',
            category='health'
        )
    
    def test_complete_survey_flow(self):
        """Test complete survey flow from questions to completion"""
        # Initially 0% complete
        self.assertEqual(self.session.get_completion_percentage(), 0)
        
        # Answer first question
        SimpleSurveyResponse.objects.create(
            session_key=self.session.session_key,
            category='health',
            question=self.age_question,
            response_value=30
        )
        
        # Should be 50% complete
        self.assertEqual(self.session.get_completion_percentage(), 50)
        
        # Answer second question
        SimpleSurveyResponse.objects.create(
            session_key=self.session.session_key,
            category='health',
            question=self.location_question,
            response_value='Western Cape'
        )
        
        # Should be 100% complete
        self.assertEqual(self.session.get_completion_percentage(), 100)
        
        # Mark as completed
        self.session.mark_completed()
        self.assertTrue(self.session.is_completed)
    
    def test_response_validation_integration(self):
        """Test response validation through the complete flow"""
        # Test valid response
        valid_errors = self.age_question.validate_response(25)
        self.assertEqual(len(valid_errors), 0)
        
        # Test invalid response
        invalid_errors = self.age_question.validate_response(15)
        self.assertGreater(len(invalid_errors), 0)
        
        # Test select question validation
        valid_location_errors = self.location_question.validate_response('Western Cape')
        self.assertEqual(len(valid_location_errors), 0)
        
        invalid_location_errors = self.location_question.validate_response('Invalid Province')
        self.assertGreater(len(invalid_location_errors), 0)


class QuestionValidationDetailedTest(TestCase):
    """Detailed tests for survey question validation rules covering all input types"""

    def setUp(self):
        """Set up test questions for each input type with comprehensive validation"""
        # Number question with min/max validation
        self.age_question = SimpleSurveyQuestion.objects.create(
            category='health',
            question_text='What is your age?',
            field_name='age',
            input_type='number',
            display_order=1,
            validation_rules={'min': 18, 'max': 80}
        )

        # Select question with choices
        self.location_question = SimpleSurveyQuestion.objects.create(
            category='health',
            question_text='Which province are you located in?',
            field_name='location',
            input_type='select',
            choices=[
                ['gauteng', 'Gauteng'],
                ['western_cape', 'Western Cape'],
                ['kwazulu_natal', 'KwaZulu-Natal']
            ],
            display_order=2
        )

        # Radio question with choices
        self.health_status_question = SimpleSurveyQuestion.objects.create(
            category='health',
            question_text='How would you describe your current health status?',
            field_name='health_status',
            input_type='radio',
            choices=[
                ['excellent', 'Excellent'],
                ['good', 'Good'],
                ['fair', 'Fair'],
                ['poor', 'Poor']
            ],
            display_order=3
        )

        # Checkbox question with multiple choices
        self.conditions_question = SimpleSurveyQuestion.objects.create(
            category='health',
            question_text='Do you have any chronic conditions?',
            field_name='chronic_conditions',
            input_type='checkbox',
            choices=[
                ['diabetes', 'Diabetes'],
                ['hypertension', 'High Blood Pressure'],
                ['heart_disease', 'Heart Disease'],
                ['none', 'None of the above']
            ],
            display_order=4
        )

        # Text question with max length
        self.text_question = SimpleSurveyQuestion.objects.create(
            category='health',
            question_text='Additional comments',
            field_name='comments',
            input_type='text',
            is_required=False,
            display_order=5,
            validation_rules={'max_length': 100}
        )

    def test_number_validation_comprehensive(self):
        """Test comprehensive number validation scenarios"""
        # Valid cases
        self.assertEqual(self.age_question.validate_response(25), [])
        self.assertEqual(self.age_question.validate_response('30'), [])
        self.assertEqual(self.age_question.validate_response(18), [])  # Min boundary
        self.assertEqual(self.age_question.validate_response(80), [])  # Max boundary
        self.assertEqual(self.age_question.validate_response(45.5), [])  # Float

        # Invalid cases
        errors = self.age_question.validate_response(17)
        self.assertIn('Value must be at least 18', errors)
        
        errors = self.age_question.validate_response(81)
        self.assertIn('Value must be at most 80', errors)
        
        errors = self.age_question.validate_response('not a number')
        self.assertIn('Please enter a valid number', errors)
        
        errors = self.age_question.validate_response('')
        self.assertIn('This field is required', errors)

    def test_select_validation_comprehensive(self):
        """Test comprehensive select validation scenarios"""
        # Valid cases
        self.assertEqual(self.location_question.validate_response('gauteng'), [])
        self.assertEqual(self.location_question.validate_response('western_cape'), [])

        # Invalid cases
        errors = self.location_question.validate_response('invalid_province')
        self.assertIn('Please select a valid option', errors)
        
        errors = self.location_question.validate_response('')
        self.assertIn('This field is required', errors)

    def test_radio_validation_comprehensive(self):
        """Test comprehensive radio validation scenarios"""
        # Valid cases
        self.assertEqual(self.health_status_question.validate_response('excellent'), [])
        self.assertEqual(self.health_status_question.validate_response('poor'), [])

        # Invalid cases
        errors = self.health_status_question.validate_response('invalid_status')
        self.assertIn('Please select a valid option', errors)

    def test_checkbox_validation_comprehensive(self):
        """Test comprehensive checkbox validation scenarios"""
        # Valid cases
        self.assertEqual(self.conditions_question.validate_response(['diabetes']), [])
        self.assertEqual(self.conditions_question.validate_response(['diabetes', 'hypertension']), [])
        self.assertEqual(self.conditions_question.validate_response(['none']), [])

        # Test non-required empty list
        self.conditions_question.is_required = False
        self.conditions_question.save()
        self.assertEqual(self.conditions_question.validate_response([]), [])

        # Invalid cases
        errors = self.conditions_question.validate_response(['invalid_condition'])
        self.assertIn('Invalid choice: invalid_condition', errors)
        
        errors = self.conditions_question.validate_response(['diabetes', 'invalid_condition'])
        self.assertIn('Invalid choice: invalid_condition', errors)
        
        errors = self.conditions_question.validate_response('diabetes')
        self.assertEqual(len(errors), 0)  # Should now be valid as it converts to ['diabetes']

    def test_text_validation_comprehensive(self):
        """Test comprehensive text validation scenarios"""
        # Valid cases
        self.assertEqual(self.text_question.validate_response('Short comment'), [])
        self.assertEqual(self.text_question.validate_response('x' * 100), [])  # At limit
        self.assertEqual(self.text_question.validate_response(''), [])  # Empty for non-required

        # Invalid cases
        errors = self.text_question.validate_response('x' * 101)
        self.assertIn('Text must be no more than 100 characters', errors)

    def test_required_field_validation_all_types(self):
        """Test required field validation across all input types"""
        # Number field
        errors = self.age_question.validate_response(None)
        self.assertIn('This field is required', errors)
        
        errors = self.age_question.validate_response('')
        self.assertIn('This field is required', errors)

        # Select field
        errors = self.location_question.validate_response(None)
        self.assertIn('This field is required', errors)

        # Radio field
        errors = self.health_status_question.validate_response('')
        self.assertIn('This field is required', errors)

        # Checkbox field
        errors = self.conditions_question.validate_response(None)
        self.assertIn('This field is required', errors)

        # Non-required field should pass
        self.text_question.is_required = False
        self.text_question.save()
        self.assertEqual(self.text_question.validate_response(''), [])

    def test_get_choices_list_helper(self):
        """Test the get_choices_list helper method with different formats"""
        # List format (standard)
        choices = self.location_question.get_choices_list()
        expected = [
            ['gauteng', 'Gauteng'],
            ['western_cape', 'Western Cape'],
            ['kwazulu_natal', 'KwaZulu-Natal']
        ]
        self.assertEqual(choices, expected)

        # Empty choices
        self.age_question.choices = []
        choices = self.age_question.get_choices_list()
        self.assertEqual(choices, [])

        # Dict format (should convert to list of items)
        self.location_question.choices = {'gauteng': 'Gauteng', 'western_cape': 'Western Cape'}
        choices = self.location_question.get_choices_list()
        self.assertIsInstance(choices, list)
        self.assertEqual(len(choices), 2)


class LoadedQuestionsTest(TestCase):
    """Test the loaded question fixtures"""
    
    def test_health_questions_loaded(self):
        """Test that health insurance questions are properly loaded"""
        # Load the questions using the management command
        from django.core.management import call_command
        call_command('load_survey_questions', '--category=health')
        
        health_questions = SimpleSurveyQuestion.objects.for_category('health')
        self.assertEqual(health_questions.count(), 8)
        
        # Test specific questions exist
        age_question = health_questions.filter(field_name='age').first()
        self.assertIsNotNone(age_question)
        self.assertEqual(age_question.input_type, 'number')
        self.assertEqual(age_question.validation_rules['min'], 18)
        self.assertEqual(age_question.validation_rules['max'], 80)
        
        location_question = health_questions.filter(field_name='location').first()
        self.assertIsNotNone(location_question)
        self.assertEqual(location_question.input_type, 'select')
        self.assertGreater(len(location_question.choices), 0)
    
    def test_funeral_questions_loaded(self):
        """Test that funeral insurance questions are properly loaded"""
        # Load the questions using the management command
        from django.core.management import call_command
        call_command('load_survey_questions', '--category=funeral')
        
        funeral_questions = SimpleSurveyQuestion.objects.for_category('funeral')
        self.assertEqual(funeral_questions.count(), 7)
        
        # Test specific questions exist
        age_question = funeral_questions.filter(field_name='age').first()
        self.assertIsNotNone(age_question)
        self.assertEqual(age_question.input_type, 'number')
        
        coverage_question = funeral_questions.filter(field_name='coverage_amount').first()
        self.assertIsNotNone(coverage_question)
        self.assertEqual(coverage_question.input_type, 'radio')
        self.assertGreater(len(coverage_question.choices), 0)
    
    def test_all_questions_loaded(self):
        """Test that all questions are loaded correctly"""
        # Load all questions
        from django.core.management import call_command
        call_command('load_survey_questions', '--category=all', '--clear')
        
        total_questions = SimpleSurveyQuestion.objects.count()
        self.assertEqual(total_questions, 15)  # 8 health + 7 funeral
        
        health_count = SimpleSurveyQuestion.objects.for_category('health').count()
        funeral_count = SimpleSurveyQuestion.objects.for_category('funeral').count()
        
        self.assertEqual(health_count, 8)
        self.assertEqual(funeral_count, 7)

class SimpleSurveyEngineTest(TestCase):
    """Test cases for SimpleSurveyEngine class"""
    
    def setUp(self):
        """Set up test data for engine testing"""
        # Create test questions for health category
        self.age_question = SimpleSurveyQuestion.objects.create(
            category='health',
            question_text='What is your age?',
            field_name='age',
            input_type='number',
            display_order=1,
            is_required=True,
            validation_rules={'min': 18, 'max': 80}
        )
        
        self.location_question = SimpleSurveyQuestion.objects.create(
            category='health',
            question_text='What is your location?',
            field_name='location',
            input_type='select',
            display_order=2,
            is_required=True,
            choices=[
                ['western_cape', 'Western Cape'],
                ['gauteng', 'Gauteng'],
                ['kwazulu_natal', 'KwaZulu-Natal']
            ]
        )
        
        self.conditions_question = SimpleSurveyQuestion.objects.create(
            category='health',
            question_text='Do you have any chronic conditions?',
            field_name='chronic_conditions',
            input_type='checkbox',
            display_order=3,
            is_required=False,
            choices=[
                ['diabetes', 'Diabetes'],
                ['hypertension', 'High Blood Pressure'],
                ['heart_disease', 'Heart Disease'],
                ['none', 'None of the above']
            ]
        )
        
        # Create funeral question for category testing
        self.funeral_question = SimpleSurveyQuestion.objects.create(
            category='funeral',
            question_text='What coverage amount do you need?',
            field_name='coverage_amount',
            input_type='radio',
            display_order=1,
            is_required=True,
            choices=[
                ['25000', 'R25,000'],
                ['50000', 'R50,000'],
                ['100000', 'R100,000']
            ]
        )
        
        self.engine = SimpleSurveyEngine('health')
        self.session_key = 'test_session_engine_123'
    
    def test_engine_initialization_valid_category(self):
        """Test engine initialization with valid category"""
        health_engine = SimpleSurveyEngine('health')
        self.assertEqual(health_engine.category, 'health')
        self.assertEqual(len(health_engine.questions), 3)  # 3 health questions
        
        funeral_engine = SimpleSurveyEngine('funeral')
        self.assertEqual(funeral_engine.category, 'funeral')
        self.assertEqual(len(funeral_engine.questions), 1)  # 1 funeral question
    
    def test_engine_initialization_invalid_category(self):
        """Test engine initialization with invalid category"""
        with self.assertRaises(ValueError) as context:
            SimpleSurveyEngine('invalid_category')
        
        self.assertIn('Invalid category', str(context.exception))
        self.assertIn('Must be \'health\' or \'funeral\'', str(context.exception))
    
    def test_get_questions_serialization(self):
        """Test question serialization for frontend consumption"""
        questions = self.engine.get_questions()
        
        self.assertEqual(len(questions), 3)
        
        # Test first question (age)
        age_q = questions[0]
        self.assertEqual(age_q['field_name'], 'age')
        self.assertEqual(age_q['input_type'], 'number')
        self.assertTrue(age_q['is_required'])
        self.assertEqual(age_q['validation_rules'], {'min': 18, 'max': 80})
        self.assertEqual(age_q['category'], 'health')
        
        # Test second question (location)
        location_q = questions[1]
        self.assertEqual(location_q['field_name'], 'location')
        self.assertEqual(location_q['input_type'], 'select')
        self.assertIsInstance(location_q['choices'], list)
        self.assertGreater(len(location_q['choices']), 0)
    
    def test_validate_response_valid_cases(self):
        """Test response validation with valid inputs"""
        # Valid number response
        result = self.engine.validate_response(self.age_question.id, 25)
        self.assertTrue(result['is_valid'])
        self.assertEqual(result['errors'], [])
        self.assertEqual(result['cleaned_value'], 25)
        
        # Valid select response
        result = self.engine.validate_response(self.location_question.id, 'western_cape')
        self.assertTrue(result['is_valid'])
        self.assertEqual(result['errors'], [])
        self.assertEqual(result['cleaned_value'], 'western_cape')
        
        # Valid checkbox response
        result = self.engine.validate_response(self.conditions_question.id, ['diabetes', 'hypertension'])
        self.assertTrue(result['is_valid'])
        self.assertEqual(result['errors'], [])
        self.assertEqual(result['cleaned_value'], ['diabetes', 'hypertension'])
    
    def test_validate_response_invalid_cases(self):
        """Test response validation with invalid inputs"""
        # Invalid number (below minimum)
        result = self.engine.validate_response(self.age_question.id, 15)
        self.assertFalse(result['is_valid'])
        self.assertIn('Value must be at least 18', result['errors'])
        
        # Invalid select option
        result = self.engine.validate_response(self.location_question.id, 'invalid_province')
        self.assertFalse(result['is_valid'])
        self.assertIn('Please select a valid option', result['errors'])
        
        # Invalid checkbox option
        result = self.engine.validate_response(self.conditions_question.id, ['invalid_condition'])
        self.assertFalse(result['is_valid'])
        self.assertIn('Invalid choice: invalid_condition', result['errors'])
    
    def test_validate_response_nonexistent_question(self):
        """Test validation with non-existent question ID"""
        result = self.engine.validate_response(99999, 'any_value')
        self.assertFalse(result['is_valid'])
        self.assertIn('Question not found', result['errors'])
        self.assertIsNone(result['cleaned_value'])
    
    def test_clean_response_value_number(self):
        """Test response value cleaning for number inputs"""
        # Integer
        cleaned = self.engine._clean_response_value(self.age_question, '25')
        self.assertEqual(cleaned, 25)
        self.assertIsInstance(cleaned, int)
        
        # Float
        cleaned = self.engine._clean_response_value(self.age_question, '25.5')
        self.assertEqual(cleaned, 25.5)
        self.assertIsInstance(cleaned, float)
        
        # None/empty
        cleaned = self.engine._clean_response_value(self.age_question, None)
        self.assertIsNone(cleaned)
    
    def test_clean_response_value_checkbox(self):
        """Test response value cleaning for checkbox inputs"""
        # List input (already correct format)
        cleaned = self.engine._clean_response_value(self.conditions_question, ['diabetes', 'hypertension'])
        self.assertEqual(cleaned, ['diabetes', 'hypertension'])
        
        # String input (comma-separated)
        cleaned = self.engine._clean_response_value(self.conditions_question, 'diabetes, hypertension')
        self.assertEqual(cleaned, ['diabetes', 'hypertension'])
        
        # Single value
        cleaned = self.engine._clean_response_value(self.conditions_question, 'diabetes')
        self.assertEqual(cleaned, ['diabetes'])
    
    def test_clean_response_value_text(self):
        """Test response value cleaning for text inputs"""
        # String with whitespace
        cleaned = self.engine._clean_response_value(self.location_question, '  western_cape  ')
        self.assertEqual(cleaned, 'western_cape')
    
    def test_save_response_success(self):
        """Test successful response saving"""
        result = self.engine.save_response(self.session_key, self.age_question.id, 30)
        
        self.assertTrue(result['success'])
        self.assertEqual(result['errors'], [])
        self.assertIsNotNone(result['response_id'])
        
        # Verify response was saved to database
        response = SimpleSurveyResponse.objects.get(id=result['response_id'])
        self.assertEqual(response.session_key, self.session_key)
        self.assertEqual(response.question_id, self.age_question.id)
        self.assertEqual(response.response_value, 30)
        self.assertEqual(response.category, 'health')
    
    def test_save_response_update_existing(self):
        """Test updating existing response"""
        # Save initial response
        result1 = self.engine.save_response(self.session_key, self.age_question.id, 25)
        self.assertTrue(result1['success'])
        
        # Update with new value
        result2 = self.engine.save_response(self.session_key, self.age_question.id, 30)
        self.assertTrue(result2['success'])
        
        # Should still be only one response in database
        responses = SimpleSurveyResponse.objects.filter(
            session_key=self.session_key,
            question_id=self.age_question.id
        )
        self.assertEqual(responses.count(), 1)
        self.assertEqual(responses.first().response_value, 30)
    
    def test_save_response_validation_failure(self):
        """Test response saving with validation failure"""
        result = self.engine.save_response(self.session_key, self.age_question.id, 15)  # Below minimum
        
        self.assertFalse(result['success'])
        self.assertGreater(len(result['errors']), 0)
        self.assertIsNone(result['response_id'])
        
        # Verify no response was saved
        responses = SimpleSurveyResponse.objects.filter(
            session_key=self.session_key,
            question_id=self.age_question.id
        )
        self.assertEqual(responses.count(), 0)
    
    def test_get_session_responses(self):
        """Test retrieving session responses"""
        # Save some responses
        self.engine.save_response(self.session_key, self.age_question.id, 30)
        self.engine.save_response(self.session_key, self.location_question.id, 'western_cape')
        
        session_data = self.engine.get_session_responses(self.session_key)
        
        self.assertEqual(session_data['session_key'], self.session_key)
        self.assertEqual(session_data['category'], 'health')
        self.assertEqual(session_data['total_responses'], 2)
        
        responses = session_data['responses']
        self.assertIn('age', responses)
        self.assertIn('location', responses)
        
        self.assertEqual(responses['age']['value'], 30)
        self.assertEqual(responses['location']['value'], 'western_cape')
    
    def test_process_responses(self):
        """Test processing responses into quotation criteria"""
        # Save responses
        self.engine.save_response(self.session_key, self.age_question.id, 30)
        self.engine.save_response(self.session_key, self.location_question.id, 'western_cape')
        self.engine.save_response(self.session_key, self.conditions_question.id, ['diabetes'])
        
        criteria = self.engine.process_responses(self.session_key)
        
        # Check criteria content
        self.assertEqual(criteria['age'], 30)
        self.assertEqual(criteria['location'], 'western_cape')
        self.assertEqual(criteria['chronic_conditions'], ['diabetes'])
        
        # Check metadata
        self.assertIn('_metadata', criteria)
        metadata = criteria['_metadata']
        self.assertEqual(metadata['category'], 'health')
        self.assertEqual(metadata['session_key'], self.session_key)
        self.assertEqual(metadata['total_responses'], 3)
        self.assertIn('processed_at', metadata)
    
    def test_is_survey_complete(self):
        """Test survey completion checking"""
        # Initially incomplete (no responses)
        self.assertFalse(self.engine.is_survey_complete(self.session_key))
        
        # Answer one required question (still incomplete)
        self.engine.save_response(self.session_key, self.age_question.id, 30)
        self.assertFalse(self.engine.is_survey_complete(self.session_key))
        
        # Answer second required question (now complete)
        self.engine.save_response(self.session_key, self.location_question.id, 'western_cape')
        self.assertTrue(self.engine.is_survey_complete(self.session_key))
        
        # Answer optional question (still complete)
        self.engine.save_response(self.session_key, self.conditions_question.id, ['none'])
        self.assertTrue(self.engine.is_survey_complete(self.session_key))
    
    def test_get_completion_status(self):
        """Test detailed completion status"""
        # Initial status
        status = self.engine.get_completion_status(self.session_key)
        
        self.assertEqual(status['session_key'], self.session_key)
        self.assertEqual(status['category'], 'health')
        self.assertFalse(status['is_complete'])
        self.assertEqual(status['total_questions'], 3)
        self.assertEqual(status['required_questions'], 2)  # age and location are required
        self.assertEqual(status['answered_total'], 0)
        self.assertEqual(status['answered_required'], 0)
        self.assertEqual(status['completion_percentage'], 0)
        
        # Answer one required question
        self.engine.save_response(self.session_key, self.age_question.id, 30)
        status = self.engine.get_completion_status(self.session_key)
        
        self.assertEqual(status['answered_total'], 1)
        self.assertEqual(status['answered_required'], 1)
        self.assertEqual(status['completion_percentage'], 50)
        self.assertFalse(status['is_complete'])
        
        # Answer second required question
        self.engine.save_response(self.session_key, self.location_question.id, 'western_cape')
        status = self.engine.get_completion_status(self.session_key)
        
        self.assertEqual(status['answered_total'], 2)
        self.assertEqual(status['answered_required'], 2)
        self.assertEqual(status['completion_percentage'], 100)
        self.assertTrue(status['is_complete'])


class SimpleSurveyEngineValidationTest(TestCase):
    """Detailed validation tests for SimpleSurveyEngine covering all input types"""
    
    def setUp(self):
        """Set up comprehensive test questions for validation testing"""
        # Text question with max length
        self.text_question = SimpleSurveyQuestion.objects.create(
            category='health',
            question_text='Additional comments',
            field_name='comments',
            input_type='text',
            display_order=1,
            is_required=False,
            validation_rules={'max_length': 50}
        )
        
        # Number question with min/max
        self.number_question = SimpleSurveyQuestion.objects.create(
            category='health',
            question_text='Monthly budget',
            field_name='budget',
            input_type='number',
            display_order=2,
            is_required=True,
            validation_rules={'min': 100, 'max': 5000}
        )
        
        # Select question
        self.select_question = SimpleSurveyQuestion.objects.create(
            category='health',
            question_text='Coverage priority',
            field_name='coverage_priority',
            input_type='select',
            display_order=3,
            is_required=True,
            choices=[
                ['hospital', 'Hospital Cover'],
                ['day_to_day', 'Day-to-day Cover'],
                ['comprehensive', 'Comprehensive Cover']
            ]
        )
        
        # Radio question
        self.radio_question = SimpleSurveyQuestion.objects.create(
            category='health',
            question_text='Health status',
            field_name='health_status',
            input_type='radio',
            display_order=4,
            is_required=True,
            choices=[
                ['excellent', 'Excellent'],
                ['good', 'Good'],
                ['fair', 'Fair'],
                ['poor', 'Poor']
            ]
        )
        
        # Checkbox question
        self.checkbox_question = SimpleSurveyQuestion.objects.create(
            category='health',
            question_text='Chronic conditions',
            field_name='conditions',
            input_type='checkbox',
            display_order=5,
            is_required=False,
            choices=[
                ['diabetes', 'Diabetes'],
                ['hypertension', 'Hypertension'],
                ['heart_disease', 'Heart Disease'],
                ['none', 'None']
            ]
        )
        
        self.engine = SimpleSurveyEngine('health')
    
    def test_text_validation_comprehensive(self):
        """Test comprehensive text input validation"""
        # Valid cases
        result = self.engine.validate_response(self.text_question.id, 'Short comment')
        self.assertTrue(result['is_valid'])
        self.assertEqual(result['cleaned_value'], 'Short comment')
        
        # Empty for non-required
        result = self.engine.validate_response(self.text_question.id, '')
        self.assertTrue(result['is_valid'])
        self.assertIsNone(result['cleaned_value'])
        
        # At max length
        result = self.engine.validate_response(self.text_question.id, 'x' * 50)
        self.assertTrue(result['is_valid'])
        
        # Over max length
        result = self.engine.validate_response(self.text_question.id, 'x' * 51)
        self.assertFalse(result['is_valid'])
        self.assertIn('Text must be no more than 50 characters', result['errors'])
        
        # Whitespace trimming
        result = self.engine.validate_response(self.text_question.id, '  trimmed  ')
        self.assertTrue(result['is_valid'])
        self.assertEqual(result['cleaned_value'], 'trimmed')
    
    def test_number_validation_comprehensive(self):
        """Test comprehensive number input validation"""
        # Valid integer
        result = self.engine.validate_response(self.number_question.id, 500)
        self.assertTrue(result['is_valid'])
        self.assertEqual(result['cleaned_value'], 500)
        self.assertIsInstance(result['cleaned_value'], int)
        
        # Valid float
        result = self.engine.validate_response(self.number_question.id, 500.50)
        self.assertTrue(result['is_valid'])
        self.assertEqual(result['cleaned_value'], 500.50)
        self.assertIsInstance(result['cleaned_value'], float)
        
        # String number (should convert)
        result = self.engine.validate_response(self.number_question.id, '750')
        self.assertTrue(result['is_valid'])
        self.assertEqual(result['cleaned_value'], 750)
        self.assertIsInstance(result['cleaned_value'], int)
        
        # String float (should convert)
        result = self.engine.validate_response(self.number_question.id, '750.25')
        self.assertTrue(result['is_valid'])
        self.assertEqual(result['cleaned_value'], 750.25)
        self.assertIsInstance(result['cleaned_value'], float)
        
        # Below minimum
        result = self.engine.validate_response(self.number_question.id, 50)
        self.assertFalse(result['is_valid'])
        self.assertIn('Value must be at least 100', result['errors'])
        
        # Above maximum
        result = self.engine.validate_response(self.number_question.id, 6000)
        self.assertFalse(result['is_valid'])
        self.assertIn('Value must be at most 5000', result['errors'])
        
        # Invalid number string
        result = self.engine.validate_response(self.number_question.id, 'not a number')
        self.assertFalse(result['is_valid'])
        self.assertIn('Please enter a valid number', result['errors'])
        
        # Required field empty
        result = self.engine.validate_response(self.number_question.id, '')
        self.assertFalse(result['is_valid'])
        self.assertIn('This field is required', result['errors'])
    
    def test_select_validation_comprehensive(self):
        """Test comprehensive select input validation"""
        # Valid option
        result = self.engine.validate_response(self.select_question.id, 'hospital')
        self.assertTrue(result['is_valid'])
        self.assertEqual(result['cleaned_value'], 'hospital')
        
        # Another valid option
        result = self.engine.validate_response(self.select_question.id, 'comprehensive')
        self.assertTrue(result['is_valid'])
        self.assertEqual(result['cleaned_value'], 'comprehensive')
        
        # Invalid option
        result = self.engine.validate_response(self.select_question.id, 'invalid_option')
        self.assertFalse(result['is_valid'])
        self.assertIn('Please select a valid option', result['errors'])
        
        # Empty for required field
        result = self.engine.validate_response(self.select_question.id, '')
        self.assertFalse(result['is_valid'])
        self.assertIn('This field is required', result['errors'])
        
        # None for required field
        result = self.engine.validate_response(self.select_question.id, None)
        self.assertFalse(result['is_valid'])
        self.assertIn('This field is required', result['errors'])
    
    def test_radio_validation_comprehensive(self):
        """Test comprehensive radio input validation"""
        # Valid option
        result = self.engine.validate_response(self.radio_question.id, 'excellent')
        self.assertTrue(result['is_valid'])
        self.assertEqual(result['cleaned_value'], 'excellent')
        
        # Another valid option
        result = self.engine.validate_response(self.radio_question.id, 'poor')
        self.assertTrue(result['is_valid'])
        self.assertEqual(result['cleaned_value'], 'poor')
        
        # Invalid option
        result = self.engine.validate_response(self.radio_question.id, 'invalid_status')
        self.assertFalse(result['is_valid'])
        self.assertIn('Please select a valid option', result['errors'])
        
        # Empty for required field
        result = self.engine.validate_response(self.radio_question.id, '')
        self.assertFalse(result['is_valid'])
        self.assertIn('This field is required', result['errors'])
    
    def test_checkbox_validation_comprehensive(self):
        """Test comprehensive checkbox input validation"""
        # Single valid option
        result = self.engine.validate_response(self.checkbox_question.id, ['diabetes'])
        self.assertTrue(result['is_valid'])
        self.assertEqual(result['cleaned_value'], ['diabetes'])
        
        # Multiple valid options
        result = self.engine.validate_response(self.checkbox_question.id, ['diabetes', 'hypertension'])
        self.assertTrue(result['is_valid'])
        self.assertEqual(result['cleaned_value'], ['diabetes', 'hypertension'])
        
        # Empty list for non-required
        result = self.engine.validate_response(self.checkbox_question.id, [])
        self.assertTrue(result['is_valid'])
        self.assertEqual(result['cleaned_value'], [])
        
        # String input (should convert to list)
        result = self.engine.validate_response(self.checkbox_question.id, 'diabetes')
        self.assertTrue(result['is_valid'])
        self.assertEqual(result['cleaned_value'], ['diabetes'])
        
        # Comma-separated string (should convert to list)
        result = self.engine.validate_response(self.checkbox_question.id, 'diabetes, hypertension')
        self.assertTrue(result['is_valid'])
        self.assertEqual(result['cleaned_value'], ['diabetes', 'hypertension'])
        
        # Invalid option in list
        result = self.engine.validate_response(self.checkbox_question.id, ['diabetes', 'invalid_condition'])
        self.assertFalse(result['is_valid'])
        self.assertIn('Invalid choice: invalid_condition', result['errors'])
        
        # Non-list input (invalid format)
        result = self.engine.validate_response(self.checkbox_question.id, 123)
        self.assertFalse(result['is_valid'])
        self.assertIn('Invalid checkbox response format', result['errors'])


class SimpleSurveyEngineIntegrationTest(TestCase):
    """Integration tests for SimpleSurveyEngine with complete workflows"""
    
    def setUp(self):
        """Set up complete survey scenarios"""
        # Load actual survey questions using management command
        from django.core.management import call_command
        call_command('load_survey_questions', '--category=health', '--clear')
        
        self.engine = SimpleSurveyEngine('health')
        self.session_key = 'integration_test_session'
    
    def test_complete_health_survey_workflow(self):
        """Test complete health survey workflow from start to finish"""
        # Get all questions
        questions = self.engine.get_questions()
        self.assertEqual(len(questions), 8)  # Should have 8 health questions
        
        # Simulate user completing survey
        responses = {
            'age': 35,
            'location': 'western_cape',
            'family_size': 2,
            'health_status': 'good',
            'chronic_conditions': ['none'],
            'coverage_priority': 'comprehensive',
            'monthly_budget': 1500,
            'preferred_deductible': '1000'
        }
        
        # Save each response
        for question in questions:
            field_name = question['field_name']
            if field_name in responses:
                result = self.engine.save_response(
                    self.session_key,
                    question['id'],
                    responses[field_name]
                )
                self.assertTrue(result['success'], f"Failed to save {field_name}: {result['errors']}")
        
        # Check completion status
        self.assertTrue(self.engine.is_survey_complete(self.session_key))
        
        status = self.engine.get_completion_status(self.session_key)
        self.assertTrue(status['is_complete'])
        self.assertEqual(status['completion_percentage'], 100)
        
        # Process responses into criteria
        criteria = self.engine.process_responses(self.session_key)
        
        # Verify criteria contains expected fields
        expected_fields = ['age', 'location', 'family_size', 'health_status', 
                          'chronic_conditions', 'coverage_priority', 'monthly_budget', 
                          'preferred_deductible']
        
        for field in expected_fields:
            self.assertIn(field, criteria, f"Missing field: {field}")
        
        # Verify metadata
        self.assertIn('_metadata', criteria)
        metadata = criteria['_metadata']
        self.assertEqual(metadata['category'], 'health')
        self.assertEqual(metadata['session_key'], self.session_key)
        self.assertGreater(metadata['total_responses'], 0)
    
    def test_partial_survey_completion(self):
        """Test partial survey completion scenarios"""
        questions = self.engine.get_questions()
        
        # Answer only required questions
        required_questions = [q for q in questions if q['is_required']]
        
        for question in required_questions[:2]:  # Answer only first 2 required questions
            result = self.engine.save_response(
                self.session_key,
                question['id'],
                self._get_valid_response_for_question(question)
            )
            self.assertTrue(result['success'])
        
        # Should not be complete yet
        self.assertFalse(self.engine.is_survey_complete(self.session_key))
        
        status = self.engine.get_completion_status(self.session_key)
        self.assertFalse(status['is_complete'])
        self.assertLess(status['completion_percentage'], 100)
        
        # Answer remaining required questions
        for question in required_questions[2:]:
            result = self.engine.save_response(
                self.session_key,
                question['id'],
                self._get_valid_response_for_question(question)
            )
            self.assertTrue(result['success'])
        
        # Should now be complete
        self.assertTrue(self.engine.is_survey_complete(self.session_key))
    
    def test_response_update_workflow(self):
        """Test updating responses in a survey"""
        questions = self.engine.get_questions()
        age_question = next(q for q in questions if q['field_name'] == 'age')
        
        # Save initial response
        result1 = self.engine.save_response(self.session_key, age_question['id'], 25)
        self.assertTrue(result1['success'])
        
        # Verify initial response
        session_data = self.engine.get_session_responses(self.session_key)
        self.assertEqual(session_data['responses']['age']['value'], 25)
        
        # Update response
        result2 = self.engine.save_response(self.session_key, age_question['id'], 30)
        self.assertTrue(result2['success'])
        
        # Verify updated response
        session_data = self.engine.get_session_responses(self.session_key)
        self.assertEqual(session_data['responses']['age']['value'], 30)
        
        # Should still have only one response in database
        responses = SimpleSurveyResponse.objects.filter(
            session_key=self.session_key,
            question_id=age_question['id']
        )
        self.assertEqual(responses.count(), 1)
    
    def _get_valid_response_for_question(self, question):
        """Helper method to get valid response for any question type"""
        if question['input_type'] == 'number':
            if question['field_name'] == 'age':
                return 30
            elif question['field_name'] == 'family_size':
                return 2
            elif question['field_name'] == 'monthly_budget':
                return 1000
            else:
                return 100
        
        elif question['input_type'] in ['select', 'radio']:
            if question['choices']:
                # Return first choice value
                first_choice = question['choices'][0]
                if isinstance(first_choice, list):
                    return first_choice[0]
                else:
                    return first_choice
            return 'default'
        
        elif question['input_type'] == 'checkbox':
            if question['choices']:
                # Return first choice as list
                first_choice = question['choices'][0]
                if isinstance(first_choice, list):
                    return [first_choice[0]]
                else:
                    return [first_choice]
            return ['default']
        
        elif question['input_type'] == 'text':
            return 'Test response'
        
        return 'default'


class SimpleSurveyModelTest(TestCase):
    """Test cases for SimpleSurvey model"""
    
    def setUp(self):
        """Set up test data"""
        self.health_survey_data = {
            'first_name': 'John',
            'last_name': 'Doe',
            'date_of_birth': '1990-01-01',
            'email': 'john.doe@example.com',
            'phone': '+27123456789',
            'insurance_type': SimpleSurvey.InsuranceType.HEALTH,
            'preferred_annual_limit': 50000.00,
            'household_income': 15000.00,
            'wants_in_hospital_benefit': True,
            'wants_out_hospital_benefit': True,
            'needs_chronic_medication': False,
        }
        
        self.funeral_survey_data = {
            'first_name': 'Jane',
            'last_name': 'Smith',
            'date_of_birth': '1985-05-15',
            'email': 'jane.smith@example.com',
            'phone': '+27987654321',
            'insurance_type': SimpleSurvey.InsuranceType.FUNERAL,
            'preferred_cover_amount': 25000.00,
            'marital_status': 'married',
            'gender': 'female',
            'net_income': 12000.00,
        }
    
    def test_health_survey_creation_valid(self):
        """Test creating a valid health survey"""
        survey = SimpleSurvey.objects.create(**self.health_survey_data)
        
        self.assertEqual(survey.first_name, 'John')
        self.assertEqual(survey.last_name, 'Doe')
        self.assertEqual(survey.insurance_type, SimpleSurvey.InsuranceType.HEALTH)
        self.assertEqual(survey.preferred_annual_limit, 50000.00)
        self.assertTrue(survey.wants_in_hospital_benefit)
        self.assertIsNone(survey.preferred_cover_amount)  # Funeral field should be None
        
        # Test string representation
        self.assertEqual(str(survey), 'John Doe - Health Policies')
    
    def test_funeral_survey_creation_valid(self):
        """Test creating a valid funeral survey"""
        survey = SimpleSurvey.objects.create(**self.funeral_survey_data)
        
        self.assertEqual(survey.first_name, 'Jane')
        self.assertEqual(survey.last_name, 'Smith')
        self.assertEqual(survey.insurance_type, SimpleSurvey.InsuranceType.FUNERAL)
        self.assertEqual(survey.preferred_cover_amount, 25000.00)
        self.assertEqual(survey.marital_status, 'married')
        self.assertIsNone(survey.preferred_annual_limit)  # Health field should be None
        
        # Test string representation
        self.assertEqual(str(survey), 'Jane Smith - Funeral Policies')
    
    def test_health_survey_validation_missing_fields(self):
        """Test health survey validation with missing required fields"""
        # Remove required health fields
        incomplete_data = self.health_survey_data.copy()
        del incomplete_data['preferred_annual_limit']
        del incomplete_data['wants_in_hospital_benefit']
        
        survey = SimpleSurvey(**incomplete_data)
        
        with self.assertRaises(ValidationError) as context:
            survey.clean()
        
        errors = context.exception.message_dict
        self.assertIn('preferred_annual_limit', errors)
        self.assertIn('wants_in_hospital_benefit', errors)
        self.assertIn('Annual limit preference is required', errors['preferred_annual_limit'][0])
    
    def test_funeral_survey_validation_missing_fields(self):
        """Test funeral survey validation with missing required fields"""
        # Remove required funeral fields
        incomplete_data = self.funeral_survey_data.copy()
        del incomplete_data['preferred_cover_amount']
        del incomplete_data['marital_status']
        
        survey = SimpleSurvey(**incomplete_data)
        
        with self.assertRaises(ValidationError) as context:
            survey.clean()
        
        errors = context.exception.message_dict
        self.assertIn('preferred_cover_amount', errors)
        self.assertIn('marital_status', errors)
        self.assertIn('Cover amount preference is required', errors['preferred_cover_amount'][0])
    
    def test_health_survey_validation_invalid_values(self):
        """Test health survey validation with invalid values"""
        invalid_data = self.health_survey_data.copy()
        invalid_data['preferred_annual_limit'] = -1000.00  # Negative value
        invalid_data['household_income'] = 0  # Zero value
        
        survey = SimpleSurvey(**invalid_data)
        
        with self.assertRaises(ValidationError) as context:
            survey.clean()
        
        errors = context.exception.message_dict
        self.assertIn('preferred_annual_limit', errors)
        self.assertIn('household_income', errors)
        self.assertIn('must be greater than 0', errors['preferred_annual_limit'][0])
    
    def test_funeral_survey_validation_invalid_values(self):
        """Test funeral survey validation with invalid values"""
        invalid_data = self.funeral_survey_data.copy()
        invalid_data['preferred_cover_amount'] = -5000.00  # Negative value
        invalid_data['net_income'] = 0  # Zero value
        
        survey = SimpleSurvey(**invalid_data)
        
        with self.assertRaises(ValidationError) as context:
            survey.clean()
        
        errors = context.exception.message_dict
        self.assertIn('preferred_cover_amount', errors)
        self.assertIn('net_income', errors)
        self.assertIn('must be greater than 0', errors['preferred_cover_amount'][0])
    
    def test_get_preferences_dict_health(self):
        """Test getting preferences dictionary for health survey"""
        survey = SimpleSurvey.objects.create(**self.health_survey_data)
        preferences = survey.get_preferences_dict()
        
        expected = {
            'annual_limit_per_member': 50000.00,
            'monthly_household_income': 15000.00,
            'in_hospital_benefit': True,
            'out_hospital_benefit': True,
            'chronic_medication_availability': False,
        }
        
        self.assertEqual(preferences, expected)
    
    def test_get_preferences_dict_funeral(self):
        """Test getting preferences dictionary for funeral survey"""
        survey = SimpleSurvey.objects.create(**self.funeral_survey_data)
        preferences = survey.get_preferences_dict()
        
        expected = {
            'cover_amount': 25000.00,
            'marital_status_requirement': 'married',
            'gender_requirement': 'female',
            'monthly_net_income': 12000.00,
        }
        
        self.assertEqual(preferences, expected)
    
    def test_is_complete_health_survey(self):
        """Test completion check for health survey"""
        # Complete survey
        complete_survey = SimpleSurvey.objects.create(**self.health_survey_data)
        self.assertTrue(complete_survey.is_complete())
        
        # Incomplete survey
        incomplete_data = self.health_survey_data.copy()
        del incomplete_data['preferred_annual_limit']
        incomplete_survey = SimpleSurvey(**incomplete_data)
        self.assertFalse(incomplete_survey.is_complete())
    
    def test_is_complete_funeral_survey(self):
        """Test completion check for funeral survey"""
        # Complete survey
        complete_survey = SimpleSurvey.objects.create(**self.funeral_survey_data)
        self.assertTrue(complete_survey.is_complete())
        
        # Incomplete survey
        incomplete_data = self.funeral_survey_data.copy()
        del incomplete_data['marital_status']
        incomplete_survey = SimpleSurvey(**incomplete_data)
        self.assertFalse(incomplete_survey.is_complete())
    
    def test_get_missing_fields_health(self):
        """Test getting missing fields for health survey"""
        incomplete_data = self.health_survey_data.copy()
        del incomplete_data['preferred_annual_limit']
        del incomplete_data['wants_in_hospital_benefit']
        
        survey = SimpleSurvey(**incomplete_data)
        missing_fields = survey.get_missing_fields()
        
        self.assertIn('preferred_annual_limit', missing_fields)
        self.assertIn('wants_in_hospital_benefit', missing_fields)
    
    def test_get_missing_fields_funeral(self):
        """Test getting missing fields for funeral survey"""
        incomplete_data = self.funeral_survey_data.copy()
        del incomplete_data['preferred_cover_amount']
        del incomplete_data['gender']
        
        survey = SimpleSurvey(**incomplete_data)
        missing_fields = survey.get_missing_fields()
        
        self.assertIn('preferred_cover_amount', missing_fields)
        self.assertIn('gender', missing_fields)
    
    def test_optional_contact_fields(self):
        """Test that email and phone are optional"""
        data = self.health_survey_data.copy()
        del data['email']
        del data['phone']
        
        survey = SimpleSurvey.objects.create(**data)
        self.assertEqual(survey.email, '')
        self.assertEqual(survey.phone, '')
        self.assertTrue(survey.is_complete())


class SimpleSurveyFormTest(TestCase):
    """Test cases for SimpleSurvey forms"""
    
    def setUp(self):
        """Set up test data"""
        self.health_form_data = {
            'first_name': 'John',
            'last_name': 'Doe',
            'date_of_birth': '1990-01-01',
            'email': 'john.doe@example.com',
            'phone': '+27123456789',
            'insurance_type': SimpleSurvey.InsuranceType.HEALTH,
            'preferred_annual_limit_per_family': '50000.00',
            'household_income': '15000.00',
            'wants_ambulance_coverage': True,
            'in_hospital_benefit_level': 'basic',
            'out_hospital_benefit_level': 'routine_care',
            'needs_chronic_medication': False,
            'annual_limit_family_range': '50k-100k',
            'annual_limit_member_range': '25k-50k',
        }
        
        self.funeral_form_data = {
            'first_name': 'Jane',
            'last_name': 'Smith',
            'date_of_birth': '1985-05-15',
            'email': 'jane.smith@example.com',
            'phone': '+27987654321',
            'insurance_type': SimpleSurvey.InsuranceType.FUNERAL,
            'preferred_cover_amount': '25000.00',
            'marital_status': 'married',
            'gender': 'female',
        }
    
    def test_health_survey_form_valid(self):
        """Test valid health survey form"""
        from .forms import HealthSurveyForm
        
        form = HealthSurveyForm(data=self.health_form_data)
        self.assertTrue(form.is_valid(), f"Form errors: {form.errors}")
        
        survey = form.save()
        self.assertEqual(survey.insurance_type, SimpleSurvey.InsuranceType.HEALTH)
        self.assertEqual(survey.preferred_annual_limit_per_family, 50000.00)
    
    def test_funeral_survey_form_valid(self):
        """Test valid funeral survey form"""
        from .forms import FuneralSurveyForm
        
        form = FuneralSurveyForm(data=self.funeral_form_data)
        self.assertTrue(form.is_valid(), f"Form errors: {form.errors}")
        
        survey = form.save()
        self.assertEqual(survey.insurance_type, SimpleSurvey.InsuranceType.FUNERAL)
        self.assertEqual(survey.preferred_cover_amount, 25000.00)
    
    def test_health_survey_form_invalid_missing_fields(self):
        """Test health survey form with missing required fields"""
        from .forms import HealthSurveyForm
        
        incomplete_data = self.health_form_data.copy()
        del incomplete_data['preferred_annual_limit_per_family']
        del incomplete_data['in_hospital_benefit_level']
        
        form = HealthSurveyForm(data=incomplete_data)
        self.assertFalse(form.is_valid())
        self.assertIn('preferred_annual_limit_per_family', form.errors)
        self.assertIn('in_hospital_benefit_level', form.errors)
    
    def test_funeral_survey_form_invalid_missing_fields(self):
        """Test funeral survey form with missing required fields"""
        from .forms import FuneralSurveyForm
        
        incomplete_data = self.funeral_form_data.copy()
        del incomplete_data['preferred_cover_amount']
        del incomplete_data['marital_status']
        
        form = FuneralSurveyForm(data=incomplete_data)
        self.assertFalse(form.is_valid())
        self.assertIn('preferred_cover_amount', form.errors)
        self.assertIn('marital_status', form.errors)
    
    def test_general_survey_form_insurance_type_validation(self):
        """Test general survey form with insurance type validation"""
        from .forms import SimpleSurveyForm
        
        # Test without insurance type
        data = self.health_form_data.copy()
        del data['insurance_type']
        
        form = SimpleSurveyForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('Please select an insurance type', str(form.errors))
    
    def test_form_field_widgets_and_attributes(self):
        """Test that form fields have correct widgets and attributes"""
        from .forms import SimpleSurveyForm
        
        form = SimpleSurveyForm()
        
        # Test CSS classes
        self.assertIn('form-control', form.fields['first_name'].widget.attrs['class'])
        self.assertIn('health-field', form.fields['preferred_annual_limit_per_family'].widget.attrs['class'])
        self.assertIn('funeral-field', form.fields['preferred_cover_amount'].widget.attrs['class'])
        
        # Test input types
        self.assertEqual(form.fields['date_of_birth'].widget.attrs['type'], 'date')
        self.assertEqual(form.fields['preferred_annual_limit_per_family'].widget.attrs['step'], '0.01')
        self.assertEqual(form.fields['preferred_annual_limit_per_family'].widget.attrs['min'], '0')
        
        # Test new benefit level fields have radio widgets
        self.assertTrue(hasattr(form.fields['in_hospital_benefit_level'].widget, 'choices'))
        self.assertTrue(hasattr(form.fields['out_hospital_benefit_level'].widget, 'choices'))
        
        # Test range fields have select widgets with choices
        self.assertIn('range-select', form.fields['annual_limit_family_range'].widget.attrs['class'])
        self.assertIn('range-select', form.fields['annual_limit_member_range'].widget.attrs['class'])