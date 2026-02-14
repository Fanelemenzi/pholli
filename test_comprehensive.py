#!/usr/bin/env python
"""
Comprehensive end-to-end test suite for the complete survey system.
This test validates all functionality from user entry to results display.
"""

import os
import sys
import django
import json
from django.test import Client
from django.urls import reverse

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pholli.settings')
django.setup()

class ComprehensiveTestSuite:
    def __init__(self):
        self.client = Client()
        self.test_results = {
            'passed': 0,
            'failed': 0,
            'errors': []
        }
    
    def log_test(self, test_name, success, message=""):
        """Log test results"""
        status = "✅" if success else "❌"
        print(f"   {status} {test_name}: {message}")
        
        if success:
            self.test_results['passed'] += 1
        else:
            self.test_results['failed'] += 1
            self.test_results['errors'].append(f"{test_name}: {message}")
    
    def test_url_resolution(self):
        """Test that all URLs resolve correctly"""
        print("\n1️⃣ TESTING URL RESOLUTION")
        print("-" * 30)
        
        urls_to_test = [
            ('home', {}, 'Home page'),
            ('health', {}, 'Health page'),
            ('funerals', {}, 'Funerals page'),
            ('direct_survey', {'category_slug': 'health'}, 'Direct health survey'),
            ('direct_survey', {'category_slug': 'funeral'}, 'Direct funeral survey'),
            ('survey', {'category': 'health'}, 'Health survey form'),
            ('survey', {'category': 'funeral'}, 'Funeral survey form'),
            ('results', {'category': 'health'}, 'Health results'),
            ('results', {'category': 'funeral'}, 'Funeral results'),
            ('feature_survey', {'category': 'health'}, 'Feature health survey'),
            ('feature_results', {'category': 'health'}, 'Feature health results'),
        ]
        
        for url_name, kwargs, description in urls_to_test:
            try:
                url = reverse(url_name, kwargs=kwargs)
                self.log_test(f"URL Resolution: {description}", True, f"Resolves to {url}")
            except Exception as e:
                self.log_test(f"URL Resolution: {description}", False, str(e))
    
    def test_page_responses(self):
        """Test that all pages return appropriate HTTP responses"""
        print("\n2️⃣ TESTING PAGE RESPONSES")
        print("-" * 30)
        
        pages_to_test = [
            (reverse('home'), 200, 'Home page'),
            (reverse('health'), 200, 'Health page'),
            (reverse('funerals'), 200, 'Funerals page'),
            (reverse('survey', kwargs={'category': 'health'}), 200, 'Health survey'),
            (reverse('survey', kwargs={'category': 'funeral'}), 200, 'Funeral survey'),
            (reverse('results', kwargs={'category': 'health'}), 200, 'Health results'),
            (reverse('results', kwargs={'category': 'funeral'}), 200, 'Funeral results'),
            (reverse('direct_survey', kwargs={'category_slug': 'health'}), 302, 'Direct health (redirect)'),
            (reverse('direct_survey', kwargs={'category_slug': 'funeral'}), 302, 'Direct funeral (redirect)'),
        ]
        
        for url, expected_status, description in pages_to_test:
            try:
                response = self.client.get(url)
                success = response.status_code == expected_status
                self.log_test(f"Response: {description}", success, 
                            f"Status {response.status_code} (expected {expected_status})")
            except Exception as e:
                self.log_test(f"Response: {description}", False, str(e))
    
    def test_survey_flow(self):
        """Test complete survey submission flow"""
        print("\n3️⃣ TESTING SURVEY FLOW")
        print("-" * 25)
        
        categories = ['health', 'funeral']
        
        for category in categories:
            try:
                # Step 1: Get survey form
                response = self.client.get(reverse('survey', kwargs={'category': category}))
                self.log_test(f"{category.title()} survey form", 
                            response.status_code == 200, f"Form loads successfully")
                
                # Step 2: Submit survey data
                survey_data = {
                    'age': '35',
                    'gender': 'female',
                    'location': 'johannesburg',
                    'coverage_type': 'family' if category == 'health' else 'individual',
                    'budget': '1500' if category == 'health' else '25000'
                }
                
                response = self.client.post(reverse('process', kwargs={'category': category}), 
                                          data=survey_data)
                self.log_test(f"{category.title()} survey submission", 
                            response.status_code == 302, f"Redirects after submission")
                
                # Step 3: Check results page
                response = self.client.get(reverse('results', kwargs={'category': category}))
                self.log_test(f"{category.title()} results page", 
                            response.status_code == 200, f"Results display successfully")
                
            except Exception as e:
                self.log_test(f"{category.title()} survey flow", False, str(e))
    
    def test_ajax_endpoints(self):
        """Test AJAX functionality"""
        print("\n4️⃣ TESTING AJAX ENDPOINTS")
        print("-" * 30)
        
        ajax_tests = [
            ('save_response_ajax', {'category': 'health'}, 'POST', {'question_id': '1', 'answer': 'test'}),
            ('survey_status_ajax', {'category': 'health'}, 'GET', {}),
            ('survey_status_ajax', {'category': 'funeral'}, 'GET', {}),
        ]
        
        for url_name, kwargs, method, data in ajax_tests:
            try:
                url = reverse(url_name, kwargs=kwargs)
                if method == 'POST':
                    response = self.client.post(url, data=data)
                else:
                    response = self.client.get(url)
                
                success = response.status_code == 200
                self.log_test(f"AJAX {method} {url_name}", success, 
                            f"Status {response.status_code}")
                
                # Try to parse JSON response
                if success:
                    try:
                        json_data = json.loads(response.content)
                        self.log_test(f"AJAX JSON {url_name}", True, 
                                    f"Valid JSON response: {list(json_data.keys())}")
                    except json.JSONDecodeError:
                        self.log_test(f"AJAX JSON {url_name}", False, "Invalid JSON response")
                        
            except Exception as e:
                self.log_test(f"AJAX {url_name}", False, str(e))
    
    def test_error_handling(self):
        """Test error handling for invalid requests"""
        print("\n5️⃣ TESTING ERROR HANDLING")
        print("-" * 30)
        
        error_tests = [
            ('/survey/invalid_category/', 'Invalid survey category'),
            ('/direct/invalid_category/', 'Invalid direct survey category'),
            ('/results/invalid_category/', 'Invalid results category'),
        ]
        
        for url, description in error_tests:
            try:
                response = self.client.get(url)
                # Should either return 404 or handle gracefully (200 with error message)
                success = response.status_code in [200, 404]
                self.log_test(f"Error handling: {description}", success, 
                            f"Status {response.status_code}")
            except Exception as e:
                self.log_test(f"Error handling: {description}", False, str(e))
    
    def test_template_content(self):
        """Test that templates contain expected content"""
        print("\n6️⃣ TESTING TEMPLATE CONTENT")
        print("-" * 35)
        
        content_tests = [
            (reverse('home'), ['pholli', 'insurance'], 'Home page content'),
            (reverse('health'), ['health', 'medical'], 'Health page content'),
            (reverse('funerals'), ['funeral', 'cover'], 'Funerals page content'),
            (reverse('survey', kwargs={'category': 'health'}), ['form', 'survey'], 'Health survey content'),
            (reverse('results', kwargs={'category': 'health'}), ['result'], 'Health results content'),
        ]
        
        for url, expected_words, description in content_tests:
            try:
                response = self.client.get(url)
                if response.status_code == 200:
                    content = response.content.decode('utf-8').lower()
                    found_words = [word for word in expected_words if word in content]
                    success = len(found_words) > 0
                    self.log_test(f"Content: {description}", success, 
                                f"Found {len(found_words)}/{len(expected_words)} expected words")
                else:
                    self.log_test(f"Content: {description}", False, 
                                f"Page not accessible (status {response.status_code})")
            except Exception as e:
                self.log_test(f"Content: {description}", False, str(e))
    
    def test_session_handling(self):
        """Test session handling across requests"""
        print("\n7️⃣ TESTING SESSION HANDLING")
        print("-" * 35)
        
        try:
            # Make a series of requests and check session consistency
            response1 = self.client.get(reverse('survey', kwargs={'category': 'health'}))
            session_key1 = self.client.session.session_key
            
            response2 = self.client.post(reverse('process', kwargs={'category': 'health'}), 
                                       data={'age': '30', 'gender': 'male'})
            session_key2 = self.client.session.session_key
            
            response3 = self.client.get(reverse('results', kwargs={'category': 'health'}))
            session_key3 = self.client.session.session_key
            
            # Session should be consistent across requests
            session_consistent = session_key1 == session_key2 == session_key3
            self.log_test("Session consistency", session_consistent, 
                        f"Session maintained across requests")
            
        except Exception as e:
            self.log_test("Session handling", False, str(e))
    
    def test_redirect_chains(self):
        """Test redirect chains work correctly"""
        print("\n8️⃣ TESTING REDIRECT CHAINS")
        print("-" * 35)
        
        redirect_tests = [
            ('health', 'direct_survey', {'category_slug': 'health'}, 'survey', {'category': 'health'}),
            ('funeral', 'direct_survey', {'category_slug': 'funeral'}, 'survey', {'category': 'funeral'}),
        ]
        
        for category, start_url, start_kwargs, end_url, end_kwargs in redirect_tests:
            try:
                # Test the redirect chain
                response = self.client.get(reverse(start_url, kwargs=start_kwargs))
                
                if response.status_code == 302:
                    expected_url = reverse(end_url, kwargs=end_kwargs)
                    success = expected_url in response.url
                    self.log_test(f"Redirect chain: {category}", success, 
                                f"Redirects to correct URL")
                else:
                    self.log_test(f"Redirect chain: {category}", False, 
                                f"Expected redirect, got {response.status_code}")
                    
            except Exception as e:
                self.log_test(f"Redirect chain: {category}", False, str(e))
    
    def run_all_tests(self):
        """Run all tests and provide summary"""
        print("🧪 COMPREHENSIVE TEST SUITE")
        print("=" * 50)
        
        self.test_url_resolution()
        self.test_page_responses()
        self.test_survey_flow()
        self.test_ajax_endpoints()
        self.test_error_handling()
        self.test_template_content()
        self.test_session_handling()
        self.test_redirect_chains()
        
        # Summary
        total_tests = self.test_results['passed'] + self.test_results['failed']
        success_rate = (self.test_results['passed'] / total_tests * 100) if total_tests > 0 else 0
        
        print(f"\n🏆 TEST SUMMARY")
        print("=" * 20)
        print(f"   ✅ Passed: {self.test_results['passed']}")
        print(f"   ❌ Failed: {self.test_results['failed']}")
        print(f"   📊 Success Rate: {success_rate:.1f}%")
        
        if self.test_results['errors']:
            print(f"\n❌ FAILED TESTS:")
            for error in self.test_results['errors']:
                print(f"   • {error}")
        
        return self.test_results['failed'] == 0

if __name__ == '__main__':
    try:
        test_suite = ComprehensiveTestSuite()
        success = test_suite.run_all_tests()
        
        if success:
            print(f"\n🎉 ALL TESTS PASSED! System is ready for production.")
            sys.exit(0)
        else:
            print(f"\n⚠️  Some tests failed. Please review and fix issues.")
            sys.exit(1)
            
    except Exception as e:
        print(f"\n💥 TEST SUITE CRASHED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)