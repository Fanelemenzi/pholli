from django import forms
from django.core.exceptions import ValidationError
from .models import SurveyQuestion, SurveyResponse
import json


class SurveyResponseForm(forms.Form):
    """
    Dynamic form for survey responses that adapts to different question types.
    """
    
    def __init__(self, question, *args, **kwargs):
        self.question = question
        super().__init__(*args, **kwargs)
        
        # Create the appropriate field based on question type
        field_name = 'response_value'
        
        if question.question_type == SurveyQuestion.QuestionType.TEXT:
            self.fields[field_name] = forms.CharField(
                label=question.question_text,
                help_text=question.help_text,
                required=question.is_required,
                widget=forms.TextInput(attrs={
                    'class': 'form-control',
                    'placeholder': 'Enter your answer'
                })
            )
            
        elif question.question_type == SurveyQuestion.QuestionType.NUMBER:
            self.fields[field_name] = forms.DecimalField(
                label=question.question_text,
                help_text=question.help_text,
                required=question.is_required,
                widget=forms.NumberInput(attrs={
                    'class': 'form-control',
                    'placeholder': 'Enter a number'
                })
            )
            
        elif question.question_type == SurveyQuestion.QuestionType.CHOICE:
            choices = [(choice['value'], choice['text']) for choice in question.choices]
            self.fields[field_name] = forms.ChoiceField(
                label=question.question_text,
                help_text=question.help_text,
                required=question.is_required,
                choices=choices,
                widget=forms.RadioSelect(attrs={'class': 'form-check-input'})
            )
            
        elif question.question_type == SurveyQuestion.QuestionType.MULTI_CHOICE:
            choices = [(choice['value'], choice['text']) for choice in question.choices]
            self.fields[field_name] = forms.MultipleChoiceField(
                label=question.question_text,
                help_text=question.help_text,
                required=question.is_required,
                choices=choices,
                widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'})
            )
            
        elif question.question_type == SurveyQuestion.QuestionType.BOOLEAN:
            self.fields[field_name] = forms.BooleanField(
                label=question.question_text,
                help_text=question.help_text,
                required=False,  # BooleanField handles required differently
                widget=forms.RadioSelect(
                    choices=[(True, 'Yes'), (False, 'No')],
                    attrs={'class': 'form-check-input'}
                )
            )
            
        elif question.question_type == SurveyQuestion.QuestionType.RANGE:
            validation_rules = question.validation_rules or {}
            min_val = validation_rules.get('min_value', 0)
            max_val = validation_rules.get('max_value', 100)
            
            self.fields[field_name] = forms.IntegerField(
                label=question.question_text,
                help_text=question.help_text,
                required=question.is_required,
                min_value=min_val,
                max_value=max_val,
                widget=forms.NumberInput(attrs={
                    'type': 'range',
                    'class': 'form-range',
                    'min': min_val,
                    'max': max_val,
                    'step': validation_rules.get('step', 1)
                })
            )
        
        # Add confidence level field
        self.fields['confidence_level'] = forms.IntegerField(
            label='How confident are you in this answer?',
            required=False,
            initial=3,
            min_value=1,
            max_value=5,
            widget=forms.NumberInput(attrs={
                'type': 'range',
                'class': 'form-range',
                'min': 1,
                'max': 5,
                'step': 1
            })
        )
    
    def clean_response_value(self):
        """Custom validation for response value based on question type."""
        value = self.cleaned_data.get('response_value')
        
        if self.question.is_required and not value:
            raise ValidationError('This field is required.')
        
        # Apply validation rules if they exist
        validation_rules = self.question.validation_rules or {}
        
        if self.question.question_type == SurveyQuestion.QuestionType.NUMBER:
            if 'min_value' in validation_rules and value < validation_rules['min_value']:
                raise ValidationError(f'Value must be at least {validation_rules["min_value"]}')
            if 'max_value' in validation_rules and value > validation_rules['max_value']:
                raise ValidationError(f'Value must be at most {validation_rules["max_value"]}')
        
        elif self.question.question_type == SurveyQuestion.QuestionType.TEXT:
            if 'min_length' in validation_rules and len(str(value)) < validation_rules['min_length']:
                raise ValidationError(f'Answer must be at least {validation_rules["min_length"]} characters')
            if 'max_length' in validation_rules and len(str(value)) > validation_rules['max_length']:
                raise ValidationError(f'Answer must be at most {validation_rules["max_length"]} characters')
        
        return value
    
    def save(self, session):
        """Save the response to the database."""
        if not self.is_valid():
            return None
        
        response_value = self.cleaned_data['response_value']
        confidence_level = self.cleaned_data.get('confidence_level', 3)
        
        # Update or create the response
        response, created = SurveyResponse.objects.update_or_create(
            session=session,
            question=self.question,
            defaults={
                'response_value': response_value,
                'confidence_level': confidence_level
            }
        )
        
        return response


class BulkSurveyResponseForm(forms.Form):
    """
    Form for handling multiple survey responses at once.
    """
    
    def __init__(self, questions, *args, **kwargs):
        self.questions = questions
        super().__init__(*args, **kwargs)
        
        for question in questions:
            field_name = f'question_{question.id}'
            
            if question.question_type == SurveyQuestion.QuestionType.TEXT:
                self.fields[field_name] = forms.CharField(
                    label=question.question_text,
                    help_text=question.help_text,
                    required=question.is_required,
                    widget=forms.TextInput(attrs={'class': 'form-control'})
                )
                
            elif question.question_type == SurveyQuestion.QuestionType.NUMBER:
                self.fields[field_name] = forms.DecimalField(
                    label=question.question_text,
                    help_text=question.help_text,
                    required=question.is_required,
                    widget=forms.NumberInput(attrs={'class': 'form-control'})
                )
                
            elif question.question_type == SurveyQuestion.QuestionType.CHOICE:
                choices = [(choice['value'], choice['text']) for choice in question.choices]
                self.fields[field_name] = forms.ChoiceField(
                    label=question.question_text,
                    help_text=question.help_text,
                    required=question.is_required,
                    choices=choices,
                    widget=forms.RadioSelect()
                )
                
            elif question.question_type == SurveyQuestion.QuestionType.BOOLEAN:
                self.fields[field_name] = forms.BooleanField(
                    label=question.question_text,
                    help_text=question.help_text,
                    required=False,
                    widget=forms.RadioSelect(choices=[(True, 'Yes'), (False, 'No')])
                )
    
    def save(self, session):
        """Save all responses to the database."""
        if not self.is_valid():
            return []
        
        responses = []
        for question in self.questions:
            field_name = f'question_{question.id}'
            if field_name in self.cleaned_data:
                response_value = self.cleaned_data[field_name]
                
                response, created = SurveyResponse.objects.update_or_create(
                    session=session,
                    question=question,
                    defaults={
                        'response_value': response_value,
                        'confidence_level': 3  # Default confidence
                    }
                )
                responses.append(response)
        
        return responses