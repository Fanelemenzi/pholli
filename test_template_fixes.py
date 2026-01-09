#!/usr/bin/env python
"""
Test the template fixes for survey rendering.
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
from simple_surveys.models import SimpleSurveyQuestion
from simple_surveys.engine import SimpleSurveyEngine


def test_template_fixes():
    """Test that the template fixes work correctly"""
    
    print("🔧 Testing Template Fixes")
    print("=" * 40)
    
    # 1. Test template tag loading
    print("\n1. Testing Template Tags:")
    try:
        from simple_surveys.templatetags.survey_extras import get_item, is_in_list, default_if_none
        print("   ✅ Template tags imported successfully")
        
        # Test get_item filter
        test_dict = {'key1': 'value1', 'key2': 'value2'}
        result = get_item(test_dict, 'key1')
        print(f"   ✅ get_item filter works: {result}")
        
    except Exception as e:
        print(f"   ❌ Template tags error: {e}")
    
    # 2. Test question serialization with correct field names
    print("\n2. Testing Question Serialization:")
    engine = SimpleSurveyEngine('health')
    questions = engine.get_questions()
    
    if questions:
        first_question = questions[0]
        print(f"   Question fields: {list(first_question.keys())}")
        
        # Check for correct field names
        required_fields = ['id', 'question_text', 'field_name', 'input_type', 'choices', 'is_required']
        missing_fields = [field for field in required_fields if field not in first_question]
        
        if missing_fields:
            print(f"   ❌ Missing fields: {missing_fields}")
        else:
            print("   ✅ All required fields present")
    
    # 3. Test template rendering with mock data
    print("\n3. Testing Template Rendering:")
    
    # Create comprehensive test data
    test_questions = [
        {
            'id': 1,
            'question_text': 'What is your age?',
            'field_name': 'age',
            'input_type': 'number',
            'choices': [],
            'is_required': True,
            'validation_rules': {'min': 18, 'max': 80}
        },
        {
            'id': 2,
            'question_text': 'Which province are you in?',
            'field_name': 'location',
            'input_type': 'select',
            'choices': [['gauteng', 'Gauteng'], ['western_cape', 'Western Cape']],
            'is_required': True,
            'validation_rules': {}
        },
        {
            'id': 3,
            'question_text': 'How is your health?',
            'field_name': 'health_status',
            'input_type': 'radio',
            'choices': [['excellent', 'Excellent'], ['good', 'Good'], ['fair', 'Fair']],
            'is_required': True,
            'validation_rules': {}
        },
        {
            'id': 4,
            'question_text': 'Any chronic conditions?',
            'field_name': 'chronic_conditions',
            'input_type': 'checkbox',
            'choices': [['diabetes', 'Diabetes'], ['hypertension', 'High Blood Pressure'], ['none', 'None']],
            'is_required': True,
            'validation_rules': {}
        }
    ]
    
    context = {
        'category': 'health',
        'category_display': 'Health Insurance',
        'questions': test_questions,
        'existing_responses': {
            'age': '35',
            'location': 'gauteng',
            'health_status': 'good',
            'chronic_conditions': ['diabetes']
        },
        'completion_status': {
            'completion_percentage': 75,
            'answered_required': 3,
            'required_questions': 4
        }
    }
    
    # Test individual input types
    input_type_tests = {
        'number': '''
            {% load survey_extras %}
            {% for question in questions %}
                {% if question.input_type == 'number' %}
                    <input type="number" 
                           name="{{ question.field_name }}" 
                           value="{{ existing_responses|get_item:question.field_name|default:'' }}"
                           min="{{ question.validation_rules.min }}"
                           max="{{ question.validation_rules.max }}">
                {% endif %}
            {% endfor %}
        ''',
        'select': '''
            {% load survey_extras %}
            {% for question in questions %}
                {% if question.input_type == 'select' %}
                    <select name="{{ question.field_name }}">
                        {% for choice in question.choices %}
                            <option value="{{ choice.0 }}" 
                                    {% if existing_responses|get_item:question.field_name == choice.0 %}selected{% endif %}>
                                {{ choice.1 }}
                            </option>
                        {% endfor %}
                    </select>
                {% endif %}
            {% endfor %}
        ''',
        'radio': '''
            {% load survey_extras %}
            {% for question in questions %}
                {% if question.input_type == 'radio' %}
                    {% for choice in question.choices %}
                        <input type="radio" 
                               name="{{ question.field_name }}" 
                               value="{{ choice.0 }}"
                               {% if existing_responses|get_item:question.field_name == choice.0 %}checked{% endif %}>
                        <label>{{ choice.1 }}</label>
                    {% endfor %}
                {% endif %}
            {% endfor %}
        ''',
        'checkbox': '''
            {% load survey_extras %}
            {% for question in questions %}
                {% if question.input_type == 'checkbox' %}
                    {% for choice in question.choices %}
                        <input type="checkbox" 
                               name="{{ question.field_name }}" 
                               value="{{ choice.0 }}"
                               {% if choice.0 in existing_responses|get_item:question.field_name|default_if_none:'' %}checked{% endif %}>
                        <label>{{ choice.1 }}</label>
                    {% endfor %}
                {% endif %}
            {% endfor %}
        '''
    }
    
    for input_type, template_str in input_type_tests.items():
        print(f"\n   Testing {input_type} input:")
        try:
            template = Template(template_str)
            rendered = template.render(Context(context))
            
            # Check if content was rendered
            if rendered.strip():
                print(f"     ✅ {input_type} rendered successfully")
                
                # Check for specific elements
                if input_type == 'number':
                    if 'type="number"' in rendered and 'min="18"' in rendered:
                        print("     ✅ Number input with validation rendered")
                    else:
                        print("     ❌ Number input validation missing")
                
                elif input_type == 'select':
                    if '<option' in rendered and 'Gauteng' in rendered and 'selected' in rendered:
                        print("     ✅ Select with options and selection rendered")
                    else:
                        print("     ❌ Select options or selection missing")
                
                elif input_type == 'radio':
                    if 'type="radio"' in rendered and 'Excellent' in rendered and 'checked' in rendered:
                        print("     ✅ Radio buttons with selection rendered")
                    else:
                        print("     ❌ Radio buttons or selection missing")
                
                elif input_type == 'checkbox':
                    if 'type="checkbox"' in rendered and 'Diabetes' in rendered and 'checked' in rendered:
                        print("     ✅ Checkboxes with selection rendered")
                    else:
                        print("     ❌ Checkboxes or selection missing")
                
            else:
                print(f"     ❌ {input_type} rendered empty")
                
        except Exception as e:
            print(f"     ❌ {input_type} template error: {e}")
    
    # 4. Test full template rendering
    print("\n4. Testing Full Template:")
    try:
        rendered_html = render_to_string('surveys/simple_survey_form.html', context)
        
        # Check for key elements
        checks = [
            ('Form tag', '<form' in rendered_html),
            ('Question cards', 'question-card' in rendered_html),
            ('Number input', 'type="number"' in rendered_html),
            ('Select dropdown', '<select' in rendered_html and '<option' in rendered_html),
            ('Radio buttons', 'type="radio"' in rendered_html),
            ('Checkboxes', 'type="checkbox"' in rendered_html),
            ('Progress bar', 'progress-bar' in rendered_html),
            ('Submit button', 'Get My Quotes' in rendered_html)
        ]
        
        all_passed = True
        for check_name, check_result in checks:
            status = "✅" if check_result else "❌"
            print(f"   {status} {check_name}")
            if not check_result:
                all_passed = False
        
        if all_passed:
            print("\n   🎉 All template elements rendered successfully!")
        else:
            print("\n   ⚠️  Some template elements missing")
        
        # Save for inspection
        with open('debug_fixed_template.html', 'w', encoding='utf-8') as f:
            f.write(rendered_html)
        print(f"\n   📄 Full rendered template saved to: debug_fixed_template.html")
        
    except Exception as e:
        print(f"   ❌ Full template rendering failed: {e}")
        import traceback
        traceback.print_exc()
    
    # 5. Test with real database data
    print("\n5. Testing with Real Database Data:")
    try:
        real_questions = engine.get_questions()
        if real_questions:
            real_context = {
                'category': 'health',
                'category_display': 'Health Insurance',
                'questions': real_questions,
                'existing_responses': {},
                'completion_status': {
                    'completion_percentage': 0,
                    'answered_required': 0,
                    'required_questions': len([q for q in real_questions if q.get('is_required')])
                }
            }
            
            real_rendered = render_to_string('surveys/simple_survey_form.html', real_context)
            
            # Count different input types in rendered output
            input_counts = {
                'number': real_rendered.count('type="number"'),
                'select': real_rendered.count('<select'),
                'radio': real_rendered.count('type="radio"'),
                'checkbox': real_rendered.count('type="checkbox"')
            }
            
            print(f"   Real data input counts: {input_counts}")
            
            # Check if we have the expected number of inputs
            expected_inputs = {
                'number': len([q for q in real_questions if q.get('input_type') == 'number']),
                'select': len([q for q in real_questions if q.get('input_type') == 'select']),
                'radio': len([q for q in real_questions if q.get('input_type') == 'radio']),
                'checkbox': len([q for q in real_questions if q.get('input_type') == 'checkbox'])
            }
            
            print(f"   Expected input counts: {expected_inputs}")
            
            matches = all(input_counts[k] >= expected_inputs[k] for k in expected_inputs)
            if matches:
                print("   ✅ Real data rendered correctly!")
            else:
                print("   ❌ Some real data inputs missing")
        
    except Exception as e:
        print(f"   ❌ Real data test failed: {e}")
    
    print("\n🏁 Template fix testing completed!")


if __name__ == '__main__':
    test_template_fixes()