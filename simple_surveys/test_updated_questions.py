"""
Test script to verify the updated survey questions work correctly.
"""
from django.test import TestCase
from simple_surveys.models import SimpleSurveyQuestion, SimpleSurveyResponse


class UpdatedSurveyQuestionsTest(TestCase):
    """Test the new survey questions added for policy features upgrade"""
    
    def setUp(self):
        """Set up test data"""
        # Get or create the new questions (they should exist from migration)
        self.annual_limit_question, _ = SimpleSurveyQuestion.objects.get_or_create(
            category='health',
            field_name='preferred_annual_limit_per_family',
            defaults={
                'question_text': 'What is your preferred annual limit per family?',
                'input_type': 'select',
                'choices': [
                    ['100000', 'R100,000'],
                    ['250000', 'R250,000'],
                    ['500000', 'R500,000'],
                    ['1000000', 'R1,000,000'],
                    ['2000000', 'R2,000,000'],
                    ['unlimited', 'Unlimited']
                ],
                'is_required': True,
                'display_order': 7
            }
        )
        
        self.medical_aid_question, _ = SimpleSurveyQuestion.objects.get_or_create(
            category='health',
            field_name='currently_on_medical_aid',
            defaults={
                'question_text': 'Are you currently on medical aid?',
                'input_type': 'radio',
                'choices': [
                    ['yes', 'Yes'],
                    ['no', 'No']
                ],
                'is_required': True,
                'display_order': 8
            }
        )
        
        self.ambulance_question, _ = SimpleSurveyQuestion.objects.get_or_create(
            category='health',
            field_name='wants_ambulance_coverage',
            defaults={
                'question_text': 'Do you want ambulance coverage included?',
                'input_type': 'radio',
                'choices': [
                    ['yes', 'Yes, include ambulance coverage'],
                    ['no', 'No, I don\'t need ambulance coverage']
                ],
                'is_required': True,
                'display_order': 9
            }
        )
        
        self.household_income_question, _ = SimpleSurveyQuestion.objects.get_or_create(
            category='health',
            field_name='household_income',
            defaults={
                'question_text': 'What is your monthly household income?',
                'input_type': 'select',
                'choices': [
                    ['0-5000', 'R0 - R5,000'],
                    ['5001-10000', 'R5,001 - R10,000'],
                    ['10001-20000', 'R10,001 - R20,000'],
                    ['20001-35000', 'R20,001 - R35,000'],
                    ['35001-50000', 'R35,001 - R50,000'],
                    ['50001+', 'R50,001+']
                ],
                'is_required': True,
                'display_order': 10
            }
        )
    
    def test_new_questions_exist(self):
        """Test that all new questions were created"""
        # Check annual limit question
        question = SimpleSurveyQuestion.objects.get(
            field_name='preferred_annual_limit_per_family'
        )
        self.assertEqual(question.category, 'health')
        self.assertEqual(question.input_type, 'select')
        self.assertTrue(question.is_required)
        self.assertEqual(len(question.choices), 6)
        
        # Check medical aid question
        question = SimpleSurveyQuestion.objects.get(
            field_name='currently_on_medical_aid'
        )
        self.assertEqual(question.category, 'health')
        self.assertEqual(question.input_type, 'radio')
        self.assertTrue(question.is_required)
        self.assertEqual(len(question.choices), 2)
        
        # Check ambulance coverage question
        question = SimpleSurveyQuestion.objects.get(
            field_name='wants_ambulance_coverage'
        )
        self.assertEqual(question.category, 'health')
        self.assertEqual(question.input_type, 'radio')
        self.assertTrue(question.is_required)
        self.assertEqual(len(question.choices), 2)
        
        # Check household income question
        question = SimpleSurveyQuestion.objects.get(
            field_name='household_income'
        )
        self.assertEqual(question.category, 'health')
        self.assertEqual(question.input_type, 'select')
        self.assertTrue(question.is_required)
        self.assertEqual(len(question.choices), 6)
    
    def test_question_validation(self):
        """Test that question validation works correctly"""
        # Test annual limit validation
        errors = self.annual_limit_question.validate_response('500000')
        self.assertEqual(len(errors), 0)
        
        errors = self.annual_limit_question.validate_response('invalid')
        self.assertGreater(len(errors), 0)
        
        # Test medical aid validation
        errors = self.medical_aid_question.validate_response('yes')
        self.assertEqual(len(errors), 0)
        
        errors = self.medical_aid_question.validate_response('maybe')
        self.assertGreater(len(errors), 0)
        
        # Test ambulance coverage validation
        errors = self.ambulance_question.validate_response('no')
        self.assertEqual(len(errors), 0)
        
        errors = self.ambulance_question.validate_response('sometimes')
        self.assertGreater(len(errors), 0)
        
        # Test household income validation
        errors = self.household_income_question.validate_response('20001-35000')
        self.assertEqual(len(errors), 0)
        
        errors = self.household_income_question.validate_response('invalid-range')
        self.assertGreater(len(errors), 0)
    
    def test_survey_responses(self):
        """Test that survey responses can be created for new questions"""
        session_key = 'test_session_123'
        
        # Create responses for new questions
        responses = [
            {
                'question': self.annual_limit_question,
                'response_value': '1000000'
            },
            {
                'question': self.medical_aid_question,
                'response_value': 'no'
            },
            {
                'question': self.ambulance_question,
                'response_value': 'yes'
            },
            {
                'question': self.household_income_question,
                'response_value': '35001-50000'
            }
        ]
        
        for response_data in responses:
            response = SimpleSurveyResponse.objects.create(
                session_key=session_key,
                category='health',
                question=response_data['question'],
                response_value=response_data['response_value']
            )
            self.assertIsNotNone(response.id)
            self.assertEqual(response.session_key, session_key)
            self.assertEqual(response.category, 'health')
    
    def test_question_ordering(self):
        """Test that questions are properly ordered"""
        health_questions = SimpleSurveyQuestion.objects.filter(
            category='health'
        ).order_by('display_order')
        
        # Check that our new questions are in the expected order
        field_names = [q.field_name for q in health_questions]
        
        # Annual limit should be at position 7 (index 6)
        if 'preferred_annual_limit_per_family' in field_names:
            index = field_names.index('preferred_annual_limit_per_family')
            question = health_questions[index]
            self.assertEqual(question.display_order, 7)
        
        # Medical aid should be at position 8 (index 7)
        if 'currently_on_medical_aid' in field_names:
            index = field_names.index('currently_on_medical_aid')
            question = health_questions[index]
            self.assertEqual(question.display_order, 8)
        
        # Ambulance coverage should be at position 9 (index 8)
        if 'wants_ambulance_coverage' in field_names:
            index = field_names.index('wants_ambulance_coverage')
            question = health_questions[index]
            self.assertEqual(question.display_order, 9)
        
        # Household income should be at position 10 (index 9)
        if 'household_income' in field_names:
            index = field_names.index('household_income')
            question = health_questions[index]
            self.assertEqual(question.display_order, 10)
    
    def test_choices_format(self):
        """Test that question choices are properly formatted"""
        # Test annual limit choices
        choices = self.annual_limit_question.get_choices_list()
        self.assertIsInstance(choices, list)
        self.assertGreater(len(choices), 0)
        
        # Each choice should be a list with [value, label]
        for choice in choices:
            self.assertIsInstance(choice, list)
            self.assertEqual(len(choice), 2)
            self.assertIsInstance(choice[0], str)  # value
            self.assertIsInstance(choice[1], str)  # label
        
        # Test medical aid choices
        choices = self.medical_aid_question.get_choices_list()
        expected_values = ['yes', 'no']
        actual_values = [choice[0] for choice in choices]
        self.assertEqual(set(actual_values), set(expected_values))
        
        # Test ambulance coverage choices
        choices = self.ambulance_question.get_choices_list()
        expected_values = ['yes', 'no']
        actual_values = [choice[0] for choice in choices]
        self.assertEqual(set(actual_values), set(expected_values))
        
        # Test household income choices
        choices = self.household_income_question.get_choices_list()
        self.assertEqual(len(choices), 6)
        # Check that all choices have proper format
        for choice in choices:
            self.assertIn('-', choice[0])  # Should contain range separator
            self.assertIn('R', choice[1])  # Should contain currency symbol