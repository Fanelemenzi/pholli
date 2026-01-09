#!/usr/bin/env python
"""
Debug tests for Simple Survey rendering issues.
Tests why only questions are rendered without input options.
"""
import os
import sys
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pholli.settings')
django.setup()

from django.test import TestCase, Client
from django.template import Template, Context
from django.template.loader import render_to_string
from django.contrib.sessions.middleware import SessionMiddleware
from django.http import HttpRequest
from simple_surveys.models import SimpleSurveyQuestion, QuotationSession
from simple_surveys.views import SurveyView
from simple_surveys.engine import SimpleSurveyEngine
import json


class SurveyRenderingDebugTests(TestCase):
    """Test suite to debug survey rendering issues"""
    
    def setUp(self):
        """Set up test data"""
        # Create test questions for health category
        self.health_questions = [
            SimpleSurveyQuestion.objects.create(
                category='health',
                question_text='What is your age?',
                field_name='age',
                input_type='number',
                choices=[],
                is_required=True,
                display_order=1,
                validation_rules={'min': 18, 'max': 80}
            ),
            SimpleSurveyQuestion.objects.create(
                category='health',
                question_text='Which province are you located in?',
                field_name='location',
                input_type='select',
                choices=[
                    ['gauteng', 'Gauteng'],
                    ['western_cape', 'Western Cape'],
                    ['kwazulu_natal', 'KwaZulu-Natal']
                ],
                is_required=True,
                display_order=2,
                validation_rules={}
            ),
            SimpleSurveyQuestion.objects.create(
                category='health',
                question_text='How would you describe your health?',
                field_name='health_status',
                input_type='radio',
                choices=[
                    ['excellent', 'Excellent'],
                    ['good', 'Good'],
                    ['fair', 'Fair'],
                    ['poor', 'Poor']
                ],
                is_required=True,
                display_order=3,
                validation_rules={}
            ),
            SimpleSurveyQuestion.objects.create(
                category='health',
                question_text='Do you have chronic conditions?',
                field_name='chronic_conditions',
                input_type='checkbox',
                choices=[
                    ['diabetes', 'Diabetes'],
                    ['hypertension', 'High Blood Pressure'],
                    ['none', 'None of the above']
                ],
                is_required=True,
                display_order=4,
                validation_rules={}
            )
        ]
        
        self.client = Client()
    
    def test_question_model_serialization(self):
        """Test if questions are properly serialized by the engine"""
        print("\n=== Testing Question Model Serialization ===")
        
        engine = SimpleSurveyEngine('health')
        questions = engine.get_questions()
        
        print(f"Found {len(questions)} questions")
        
        for i, question in enumerate(questions):
            print(f"\nQuestion {i+1}:")
            print(f"  ID: {question.get('id')}")
            print(f"  Text: {question.get('question_text')}")
            print(f"  Field: {question.get('field_name')}")
            print(f"  Type: {question.get('input_type')}")
            print(f"  Choices: {question.get('choices')}")
            print(f"  Required: {question.get('is_required')}")
            
            # Check if choices are properly formatted
            if question.get('input_type') in ['select', 'radio', 'checkbox']:
                choices = question.get('choices', [])
                if not choices:
                    print(f"  ❌ ERROR: No choices found for {question.get('input_type')} question!")
                else:
                    print(f"  ✅ Choices properly loaded: {len(choices)} options")
                    for choice in choices:
                        if isinstance(choice, list) and len(choice) == 2:
                            print(f"    - {choice[0]}: {choice[1]}")
                        else:
                            print(f"    ❌ Invalid choice format: {choice}")
        
        self.assertGreater(len(questions), 0, "No questions found")
        
        # Test specific question types
        select_question = next((q for q in questions if q['input_type'] == 'select'), None)
        self.assertIsNotNone(select_question, "No select question found")
        self.assertGreater(len(select_question['choices']), 0, "Select question has no choices")
        
        radio_question = next((q for q in questions if q['input_type'] == 'radio'), None)
        self.assertIsNotNone(radio_question, "No radio question found")
        self.assertGreater(len(radio_question['choices']), 0, "Radio question has no choices")
    
    def test_template_context_data(self):
        """Test the context data passed to the template"""
        print("\n=== Testing Template Context Data ===")
        
        # Create a request with session
        request = HttpRequest()
        request.method = 'GET'
        request.path = '/survey/health/'
        
        # Add session middleware
        middleware = SessionMiddleware(lambda req: None)
        middleware.process_request(request)
        request.session.save()
        
        # Create survey view and get context
        view = SurveyView()
        view.request = request
        
        try:
            response = view.get(request, 'health')
            
            # Check if response is successful
            if hasattr(response, 'context_data'):
                context = response.context_data
            else:
                # Extract context from rendered response
                context = response.context_data if hasattr(response, 'context_data') else {}
            
            print(f"Context keys: {list(context.keys()) if context else 'No context'}")
            
            if 'questions' in context:
                questions = context['questions']
                print(f"Questions in context: {len(questions)}")
                
                for i, question in enumerate(questions):
                    print(f"\nContext Question {i+1}:")
                    print(f"  Type: {type(question)}")
                    if isinstance(question, dict):
                        print(f"  Keys: {list(question.keys())}")
                        print(f"  Input Type: {question.get('input_type')}")
                        print(f"  Choices: {question.get('choices')}")
                    else:
                        print(f"  Object: {question}")
                        if hasattr(question, 'input_type'):
                            print(f"  Input Type: {question.input_type}")
                        if hasattr(question, 'choices'):
                            print(f"  Choices: {question.choices}")
                        if hasattr(question, 'get_choices_list'):
                            print(f"  Choices List: {question.get_choices_list()}")
            else:
                print("❌ No 'questions' key in context!")
                
        except Exception as e:
            print(f"❌ Error getting view response: {e}")
            import traceback
            traceback.print_exc()
    
    def test_template_rendering_isolated(self):
        """Test template rendering in isolation"""
        print("\n=== Testing Template Rendering (Isolated) ===")
        
        # Create mock context data
        mock_questions = [
            {
                'id': 1,
                'question_text': 'Test Select Question',
                'field_name': 'test_select',
                'input_type': 'select',
                'choices': [['option1', 'Option 1'], ['option2', 'Option 2']],
                'is_required': True
            },
            {
                'id': 2,
                'question_text': 'Test Radio Question',
                'field_name': 'test_radio',
                'input_type': 'radio',
                'choices': [['yes', 'Yes'], ['no', 'No']],
                'is_required': True
            },
            {
                'id': 3,
                'question_text': 'Test Number Question',
                'field_name': 'test_number',
                'input_type': 'number',
                'choices': [],
                'is_required': True
            }
        ]
        
        context = {
            'category': 'health',
            'category_display': 'Health Insurance',
            'questions': mock_questions,
            'existing_responses': {},
            'completion_status': {
                'percentage': 0,
                'completed_questions': 0,
                'total_questions': 3
            }
        }
        
        # Test individual template parts
        template_parts = {
            'select': '''
                {% if question.input_type == 'select' %}
                    <select name="{{ question.field_name }}">
                        <option value="">Select...</option>
                        {% for choice in question.choices %}
                            <option value="{{ choice.0 }}">{{ choice.1 }}</option>
                        {% endfor %}
                    </select>
                {% endif %}
            ''',
            'radio': '''
                {% if question.input_type == 'radio' %}
                    {% for choice in question.choices %}
                        <input type="radio" name="{{ question.field_name }}" value="{{ choice.0 }}">
                        <label>{{ choice.1 }}</label>
                    {% endfor %}
                {% endif %}
            ''',
            'number': '''
                {% if question.input_type == 'number' %}
                    <input type="number" name="{{ question.field_name }}">
                {% endif %}
            '''
        }
        
        for question in mock_questions:
            print(f"\nTesting {question['input_type']} question:")
            print(f"  Question: {question['question_text']}")
            print(f"  Choices: {question['choices']}")
            
            template_str = template_parts.get(question['input_type'], '')
            if template_str:
                try:
                    template = Template(template_str)
                    rendered = template.render(Context({'question': question}))
                    print(f"  Rendered HTML: {rendered.strip()}")
                    
                    # Check if choices are rendered
                    if question['input_type'] in ['select', 'radio'] and question['choices']:
                        for choice in question['choices']:
                            if choice[0] in rendered and choice[1] in rendered:
                                print(f"    ✅ Choice '{choice[1]}' rendered correctly")
                            else:
                                print(f"    ❌ Choice '{choice[1]}' NOT found in rendered HTML")
                    
                except Exception as e:
                    print(f"  ❌ Template rendering error: {e}")
    
    def test_actual_template_file(self):
        """Test the actual template file with mock data"""
        print("\n=== Testing Actual Template File ===")
        
        # Create realistic mock data
        engine = SimpleSurveyEngine('health')
        questions = engine.get_questions()
        
        context = {
            'category': 'health',
            'category_display': 'Health Insurance',
            'questions': questions,
            'existing_responses': {},
            'completion_status': {
                'percentage': 0,
                'completed_questions': 0,
                'total_questions': len(questions)
            }
        }
        
        try:
            rendered_html = render_to_string('surveys/simple_survey_form.html', context)
            
            print(f"Template rendered successfully. Length: {len(rendered_html)} characters")
            
            # Check for specific elements
            checks = [
                ('form tag', '<form' in rendered_html),
                ('question cards', 'question-card' in rendered_html),
                ('select elements', '<select' in rendered_html),
                ('radio inputs', 'type="radio"' in rendered_html),
                ('number inputs', 'type="number"' in rendered_html),
                ('option elements', '<option' in rendered_html)
            ]
            
            for check_name, check_result in checks:
                status = "✅" if check_result else "❌"
                print(f"  {status} {check_name}: {check_result}")
            
            # Look for specific question content
            for question in questions:
                question_text = question.get('question_text', '')
                if question_text in rendered_html:
                    print(f"  ✅ Question found: {question_text[:50]}...")
                    
                    # Check for choices if applicable
                    if question.get('input_type') in ['select', 'radio', 'checkbox']:
                        choices = question.get('choices', [])
                        choices_found = 0
                        for choice in choices:
                            if isinstance(choice, list) and len(choice) >= 2:
                                if choice[1] in rendered_html:
                                    choices_found += 1
                        
                        print(f"    Choices found: {choices_found}/{len(choices)}")
                        if choices_found == 0 and len(choices) > 0:
                            print(f"    ❌ No choices rendered for {question.get('input_type')} question!")
                else:
                    print(f"  ❌ Question NOT found: {question_text[:50]}...")
            
            # Save rendered HTML for manual inspection
            with open('debug_rendered_template.html', 'w', encoding='utf-8') as f:
                f.write(rendered_html)
            print(f"\n📄 Rendered HTML saved to: debug_rendered_template.html")
            
        except Exception as e:
            print(f"❌ Template rendering failed: {e}")
            import traceback
            traceback.print_exc()
    
    def test_template_variable_access(self):
        """Test how template variables are accessed"""
        print("\n=== Testing Template Variable Access ===")
        
        # Test different ways to access question data
        test_question = {
            'id': 1,
            'question_text': 'Test Question',
            'field_name': 'test_field',
            'input_type': 'select',
            'choices': [['val1', 'Label 1'], ['val2', 'Label 2']],
            'is_required': True
        }
        
        # Test various template syntaxes
        template_tests = [
            ('Direct access', '{{ question.choices }}'),
            ('Loop test', '{% for choice in question.choices %}{{ choice }}{% endfor %}'),
            ('Choice access', '{% for choice in question.choices %}{{ choice.0 }}-{{ choice.1 }}{% endfor %}'),
            ('Input type check', '{% if question.input_type == "select" %}SELECT{% endif %}'),
            ('Field name', '{{ question.field_name }}'),
        ]
        
        for test_name, template_str in template_tests:
            try:
                template = Template(template_str)
                result = template.render(Context({'question': test_question}))
                print(f"  {test_name}: '{result}'")
            except Exception as e:
                print(f"  ❌ {test_name} failed: {e}")
    
    def test_model_method_calls(self):
        """Test if model methods are being called correctly"""
        print("\n=== Testing Model Method Calls ===")
        
        for question in self.health_questions:
            print(f"\nTesting question: {question.question_text}")
            print(f"  Input type: {question.input_type}")
            print(f"  Raw choices: {question.choices}")
            
            # Test get_choices_list method
            try:
                choices_list = question.get_choices_list()
                print(f"  get_choices_list(): {choices_list}")
                print(f"  Type: {type(choices_list)}")
                
                if question.input_type in ['select', 'radio', 'checkbox']:
                    if not choices_list:
                        print(f"  ❌ Empty choices list for {question.input_type} question!")
                    else:
                        print(f"  ✅ Choices list has {len(choices_list)} items")
                        for i, choice in enumerate(choices_list):
                            print(f"    {i}: {choice} (type: {type(choice)})")
                
            except Exception as e:
                print(f"  ❌ get_choices_list() failed: {e}")
    
    def test_view_response_structure(self):
        """Test the actual view response structure"""
        print("\n=== Testing View Response Structure ===")
        
        try:
            response = self.client.get('/simple-surveys/survey/health/')
            
            print(f"Response status: {response.status_code}")
            
            if response.status_code == 200:
                # Check if it's a TemplateResponse
                if hasattr(response, 'context_data'):
                    context = response.context_data
                    print(f"Context data keys: {list(context.keys())}")
                    
                    if 'questions' in context:
                        questions = context['questions']
                        print(f"Questions type: {type(questions)}")
                        print(f"Questions count: {len(questions) if hasattr(questions, '__len__') else 'Unknown'}")
                        
                        if questions:
                            first_question = questions[0]
                            print(f"First question type: {type(first_question)}")
                            print(f"First question data: {first_question}")
                
                # Check rendered content
                content = response.content.decode('utf-8')
                print(f"Response content length: {len(content)}")
                
                # Look for form elements
                form_elements = [
                    ('<form', 'Form tag'),
                    ('<select', 'Select elements'),
                    ('<option', 'Option elements'),
                    ('type="radio"', 'Radio inputs'),
                    ('type="number"', 'Number inputs'),
                    ('question-card', 'Question cards')
                ]
                
                for element, description in form_elements:
                    count = content.count(element)
                    print(f"  {description}: {count} found")
            
            elif response.status_code == 302:
                print(f"Redirect to: {response.url}")
            else:
                print(f"Error response: {response.status_code}")
                print(f"Content: {response.content.decode('utf-8')[:500]}")
                
        except Exception as e:
            print(f"❌ View test failed: {e}")
            import traceback
            traceback.print_exc()


def run_debug_tests():
    """Run all debug tests"""
    print("🔍 Starting Simple Survey Rendering Debug Tests")
    print("=" * 60)
    
    # Create test instance
    test_instance = SurveyRenderingDebugTests()
    test_instance.setUp()
    
    # Run individual tests
    tests = [
        test_instance.test_question_model_serialization,
        test_instance.test_template_context_data,
        test_instance.test_template_rendering_isolated,
        test_instance.test_actual_template_file,
        test_instance.test_template_variable_access,
        test_instance.test_model_method_calls,
        test_instance.test_view_response_structure,
    ]
    
    for test in tests:
        try:
            test()
        except Exception as e:
            print(f"\n❌ Test {test.__name__} failed with error: {e}")
            import traceback
            traceback.print_exc()
        
        print("\n" + "-" * 40)
    
    print("\n🏁 Debug tests completed!")
    print("\nCheck the following files for detailed output:")
    print("- debug_rendered_template.html (if generated)")


if __name__ == '__main__':
    run_debug_tests()