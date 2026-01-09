from django.test import TestCase
from django.core.exceptions import ValidationError
from policies.models import PolicyCategory
from comparison.models import ComparisonSession
from .models import (
    SurveyTemplate, SurveyQuestion, TemplateQuestion,
    SurveyResponse, QuestionDependency, SurveyAnalytics
)


class SurveyModelsTestCase(TestCase):
    """Test cases for survey models."""
    
    def setUp(self):
        """Set up test data."""
        # Create a policy category
        self.category = PolicyCategory.objects.create(
            name="Health Insurance",
            slug="health",
            description="Health insurance policies"
        )
        
        # Create a comparison session
        self.session = ComparisonSession.objects.create(
            session_key="test-session-123",
            category=self.category
        )
        
        # Create a survey template
        self.template = SurveyTemplate.objects.create(
            category=self.category,
            name="Health Insurance Survey",
            description="Survey for health insurance needs",
            version="1.0"
        )
    
    def test_survey_question_creation(self):
        """Test creating a survey question."""
        question = SurveyQuestion.objects.create(
            category=self.category,
            section="Personal Info",
            question_text="What is your age?",
            question_type=SurveyQuestion.QuestionType.NUMBER,
            field_name="age",
            validation_rules={"min": 18, "max": 100},
            weight_impact=1.5,
            help_text="Please enter your current age",
            is_required=True,
            display_order=1
        )
        
        self.assertEqual(question.category, self.category)
        self.assertEqual(question.question_type, SurveyQuestion.QuestionType.NUMBER)
        self.assertTrue(question.is_required)
        self.assertEqual(question.validation_rules["min"], 18)
    
    def test_survey_response_creation(self):
        """Test creating a survey response."""
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
            response_value={"value": 35},
            confidence_level=4
        )
        
        self.assertEqual(response.session, self.session)
        self.assertEqual(response.question, question)
        self.assertEqual(response.response_value["value"], 35)
        self.assertEqual(response.confidence_level, 4)
    
    def test_template_question_relationship(self):
        """Test the many-to-many relationship between templates and questions."""
        question1 = SurveyQuestion.objects.create(
            category=self.category,
            section="Personal Info",
            question_text="What is your age?",
            question_type=SurveyQuestion.QuestionType.NUMBER,
            field_name="age"
        )
        
        question2 = SurveyQuestion.objects.create(
            category=self.category,
            section="Personal Info",
            question_text="What is your gender?",
            question_type=SurveyQuestion.QuestionType.CHOICE,
            field_name="gender",
            choices=["Male", "Female", "Other"]
        )
        
        # Add questions to template
        TemplateQuestion.objects.create(
            template=self.template,
            question=question1,
            display_order=1
        )
        
        TemplateQuestion.objects.create(
            template=self.template,
            question=question2,
            display_order=2,
            is_required_override=False
        )
        
        # Test relationships
        self.assertEqual(self.template.template_questions.count(), 2)
        self.assertEqual(question1.template_questions.count(), 1)
        
        # Test ordering
        template_questions = self.template.template_questions.order_by('display_order')
        self.assertEqual(template_questions.first().question, question1)
        self.assertEqual(template_questions.last().question, question2)
    
    def test_question_dependency_evaluation(self):
        """Test question dependency logic."""
        parent_question = SurveyQuestion.objects.create(
            category=self.category,
            section="Health Status",
            question_text="Do you smoke?",
            question_type=SurveyQuestion.QuestionType.BOOLEAN,
            field_name="smoker"
        )
        
        child_question = SurveyQuestion.objects.create(
            category=self.category,
            section="Health Status",
            question_text="How many cigarettes per day?",
            question_type=SurveyQuestion.QuestionType.NUMBER,
            field_name="cigarettes_per_day"
        )
        
        dependency = QuestionDependency.objects.create(
            parent_question=parent_question,
            child_question=child_question,
            condition_value=True,
            condition_operator=QuestionDependency.ConditionOperator.EQUALS
        )
        
        # Test condition evaluation
        self.assertTrue(dependency.evaluate_condition(True))
        self.assertFalse(dependency.evaluate_condition(False))
    
    def test_survey_analytics_creation(self):
        """Test creating survey analytics."""
        question = SurveyQuestion.objects.create(
            category=self.category,
            section="Personal Info",
            question_text="What is your age?",
            question_type=SurveyQuestion.QuestionType.NUMBER,
            field_name="age"
        )
        
        analytics = SurveyAnalytics.objects.create(
            question=question,
            total_responses=100,
            completion_rate=95.5,
            skip_rate=4.5,
            most_common_response={"value": 35},
            response_distribution={"18-25": 20, "26-35": 40, "36-45": 30, "46+": 10}
        )
        
        self.assertEqual(analytics.question, question)
        self.assertEqual(analytics.total_responses, 100)
        self.assertEqual(analytics.completion_rate, 95.5)
        self.assertEqual(analytics.most_common_response["value"], 35)
    
    def test_comparison_session_survey_fields(self):
        """Test the survey-related fields added to ComparisonSession."""
        self.session.survey_completed = True
        self.session.survey_completion_percentage = 85.5
        self.session.survey_responses_count = 12
        self.session.user_profile = {"age": 35, "smoker": False}
        self.session.save()
        
        # Refresh from database
        self.session.refresh_from_db()
        
        self.assertTrue(self.session.survey_completed)
        self.assertEqual(self.session.survey_completion_percentage, 85.5)
        self.assertEqual(self.session.survey_responses_count, 12)
        self.assertEqual(self.session.user_profile["age"], 35)
        self.assertFalse(self.session.user_profile["smoker"])
    
    def test_question_type_choices(self):
        """Test that all question types are available."""
        expected_types = ['TEXT', 'NUMBER', 'CHOICE', 'MULTI_CHOICE', 'RANGE', 'BOOLEAN']
        actual_types = [choice[0] for choice in SurveyQuestion.QuestionType.choices]
        
        for expected_type in expected_types:
            self.assertIn(expected_type, actual_types)
    
    def test_condition_operator_choices(self):
        """Test that all condition operators are available."""
        expected_operators = ['EQUALS', 'NOT_EQUALS', 'GREATER_THAN', 'LESS_THAN', 'CONTAINS', 'IN_LIST']
        actual_operators = [choice[0] for choice in QuestionDependency.ConditionOperator.choices]
        
        for expected_operator in expected_operators:
            self.assertIn(expected_operator, actual_operators)
    
    def test_unique_constraints(self):
        """Test unique constraints on models."""
        # Test SurveyQuestion unique constraint (category, field_name)
        question1 = SurveyQuestion.objects.create(
            category=self.category,
            section="Personal Info",
            question_text="What is your age?",
            question_type=SurveyQuestion.QuestionType.NUMBER,
            field_name="age"
        )
        
        # This should raise an IntegrityError due to unique constraint
        with self.assertRaises(Exception):
            SurveyQuestion.objects.create(
                category=self.category,
                section="Health Status",  # Different section
                question_text="How old are you?",  # Different text
                question_type=SurveyQuestion.QuestionType.NUMBER,
                field_name="age"  # Same field_name and category
            )
    
    def test_string_representations(self):
        """Test string representations of models."""
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
            response_value={"value": 35},
            confidence_level=4
        )
        
        # Test string representations
        self.assertIn("Personal Info", str(question))
        self.assertIn("What is your age", str(question))
        self.assertIn("Response to", str(response))
        self.assertIn("Health Insurance Survey", str(self.template))