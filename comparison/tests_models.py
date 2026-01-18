"""
Unit tests for comparison models.
Tests FeatureComparisonResult and related comparison functionality.
"""

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from decimal import Decimal
from datetime import date

from .models import (
    ComparisonSession, ComparisonCriteria, ComparisonResult,
    FeatureComparisonResult, UserPreferenceProfile
)
from policies.models import BasePolicy, PolicyCategory, PolicyType, PolicyFeatures
from simple_surveys.models import SimpleSurvey
from organizations.models import Organization

User = get_user_model()


class ComparisonSessionModelTest(TestCase):
    """Test ComparisonSession model functionality."""
    
    def setUp(self):
        """Set up test data."""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
   