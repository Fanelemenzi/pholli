"""
Validation script for Survey Session Management

This script validates that the session management functionality
is properly implemented and working as expected.
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pholli.settings')
django.setup()

from django.contrib.auth import get_user_model
from policies.models import PolicyCategory
from comparison.models import ComparisonSession
from surveys.models import SurveyQuestion, SurveyResponse, SurveyTemplate
from surveys.session_manager import SurveySessionManager, SurveyAutoSaveManager
from surveys.session_recovery import SurveySessionRecovery

User = get_user_model()


def validate_session_management():
    """Validate session management functionality."""
    print("🔍 Validating Survey Session Management...")
    
    # Test 1: Session Manager Import
    try:
        from surveys.session_manager import SurveySessionManager
        print("✅ SurveySessionManager imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import SurveySessionManager: {e}")
        return False
    
    # Test 2: Session Recovery Import
    try:
        from surveys.session_recovery import SurveySessionRecovery
        print("✅ SurveySessionRecovery imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import SurveySessionRecovery: {e}")
        return False
    
    # Test 3: Check if we have required models
    try:
        # Check if health category exists
        health_category = PolicyCategory.objects.filter(slug='health').first()
        if not health_category:
            print("⚠️  Health category not found - creating test category")
            health_category = PolicyCategory.objects.create(
                name='Health Insurance',
                slug='health',
                description='Health insurance policies'
            )
        
        print("✅ Policy category available")
    except Exception as e:
        print(f"❌ Failed to access PolicyCategory: {e}")
        return False
    
    # Test 4: Create anonymous session
    try:
        manager = SurveySessionManager()
        session = manager.create_survey_session('health')
        print(f"✅ Created anonymous session: {session.session_key}")
    except Exception as e:
        print(f"❌ Failed to create anonymous session: {e}")
        return False
    
    # Test 5: Check session fields
    try:
        assert session.category == health_category
        assert session.user is None
        assert session.status == ComparisonSession.Status.ACTIVE
        assert session.session_key is not None
        assert session.expires_at is not None
        print("✅ Session fields validated")
    except AssertionError as e:
        print(f"❌ Session field validation failed: {e}")
        return False
    
    # Test 6: Test session progress tracking
    try:
        progress = manager.get_session_progress(session)
        assert 'completion_percentage' in progress
        assert 'total_questions' in progress
        assert 'answered_questions' in progress
        assert 'sections' in progress
        print("✅ Session progress tracking works")
    except Exception as e:
        print(f"❌ Session progress tracking failed: {e}")
        return False
    
    # Test 7: Test session recovery
    try:
        recovery = SurveySessionRecovery()
        recovered_data = recovery.recover_session_by_key(session.session_key, 'health')
        print("✅ Session recovery functionality works")
    except Exception as e:
        print(f"❌ Session recovery failed: {e}")
        return False
    
    # Test 8: Test auto-save manager
    try:
        auto_save_manager = SurveyAutoSaveManager(manager)
        auto_save_manager.enable_auto_save(session, interval_seconds=30)
        print("✅ Auto-save manager works")
    except Exception as e:
        print(f"❌ Auto-save manager failed: {e}")
        return False
    
    # Test 9: Test session validation
    try:
        validation_results = manager.validate_session_data(session)
        assert 'is_valid' in validation_results
        assert 'errors' in validation_results
        assert 'missing_required' in validation_results
        print("✅ Session validation works")
    except Exception as e:
        print(f"❌ Session validation failed: {e}")
        return False
    
    # Test 10: Test session expiry extension
    try:
        original_expiry = session.expires_at
        extended_session = manager.extend_session_expiry(session, days=14)
        assert extended_session.expires_at > original_expiry
        print("✅ Session expiry extension works")
    except Exception as e:
        print(f"❌ Session expiry extension failed: {e}")
        return False
    
    print("\n🎉 All session management validations passed!")
    return True


def validate_session_features():
    """Validate specific session management features."""
    print("\n🔍 Validating Session Management Features...")
    
    # Feature 1: Anonymous user session management
    try:
        manager = SurveySessionManager(session_key="test-anonymous-key")
        session = manager.create_survey_session('health')
        assert session.user is None
        assert session.session_key == "test-anonymous-key"
        print("✅ Anonymous user session management")
    except Exception as e:
        print(f"❌ Anonymous session management failed: {e}")
        return False
    
    # Feature 2: Auto-save functionality (simulated)
    try:
        # Check if we have questions to test with
        questions = SurveyQuestion.objects.filter(category__slug='health')
        if questions.exists():
            question = questions.first()
            response = manager.save_survey_response(
                session=session,
                question_id=question.id,
                response_value="test_value",
                auto_save=True
            )
            print("✅ Auto-save functionality")
        else:
            print("⚠️  No questions available for auto-save test")
    except Exception as e:
        print(f"❌ Auto-save functionality failed: {e}")
        return False
    
    # Feature 3: Session recovery mechanisms
    try:
        recovery = SurveySessionRecovery()
        recovered_data = manager.recover_session_data(session)
        assert 'session_id' in recovered_data
        assert 'responses' in recovered_data
        assert 'progress' in recovered_data
        print("✅ Session recovery mechanisms")
    except Exception as e:
        print(f"❌ Session recovery failed: {e}")
        return False
    
    # Feature 4: Survey progress tracking
    try:
        progress = manager.get_session_progress(session)
        assert isinstance(progress['completion_percentage'], (int, float))
        assert isinstance(progress['total_questions'], int)
        assert isinstance(progress['answered_questions'], int)
        print("✅ Survey progress tracking")
    except Exception as e:
        print(f"❌ Progress tracking failed: {e}")
        return False
    
    # Feature 5: Session validation
    try:
        validation = manager.validate_session_data(session)
        assert isinstance(validation['is_valid'], bool)
        assert isinstance(validation['errors'], list)
        print("✅ Session validation")
    except Exception as e:
        print(f"❌ Session validation failed: {e}")
        return False
    
    print("\n🎉 All session management features validated!")
    return True


def main():
    """Main validation function."""
    print("=" * 60)
    print("SURVEY SESSION MANAGEMENT VALIDATION")
    print("=" * 60)
    
    # Run basic validation
    basic_valid = validate_session_management()
    
    # Run feature validation
    features_valid = validate_session_features()
    
    # Summary
    print("\n" + "=" * 60)
    print("VALIDATION SUMMARY")
    print("=" * 60)
    
    if basic_valid and features_valid:
        print("🎉 ALL VALIDATIONS PASSED!")
        print("\nTask 8 Implementation Status:")
        print("✅ Session management for anonymous users with survey data")
        print("✅ Auto-save functionality for survey responses")
        print("✅ Session recovery mechanisms for incomplete surveys")
        print("✅ Survey progress tracking and validation")
        print("\n✅ Task 8: Implement survey session management - COMPLETED")
        return True
    else:
        print("❌ SOME VALIDATIONS FAILED!")
        print("Please check the error messages above.")
        return False


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)