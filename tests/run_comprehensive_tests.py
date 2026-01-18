"""
Comprehensive test runner for the Eswatini policy system.
Runs all unit tests, integration tests, and end-to-end tests with detailed reporting.
"""

import os
import sys
import django
from django.test.utils import get_runner
from django.conf import settings
from django.core.management import execute_from_command_line
import time
from io import StringIO
import unittest

# Add the project root to the Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pholli.settings')
django.setup()


class ComprehensiveTestRunner:
    """Custom test runner for comprehensive testing."""
    
    def __init__(self):
        self.test_modules = [
            'tests.test_comprehensive_models',
            'tests.test_feature_matching_integration',
            'tests.test_end_to_end_survey_flow',
            'policies.tests_models',
            'policies.tests_integration',
            'simple_surveys.tests_models',
            'comparison.tests_models',
            'comparison.tests_feature_matching',
            'comparison.tests_feature_comparison',
        ]
        
        self.results = {}
        self.total_tests = 0
        self.total_failures = 0
        self.total_errors = 0
        self.total_skipped = 0
    
    def run_test_module(self, module_name):
        """Run tests for a specific module."""
        print(f"\n{'='*60}")
        print(f"Running tests for: {module_name}")
        print(f"{'='*60}")
        
        # Capture output
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        stdout_capture = StringIO()
        stderr_capture = StringIO()
        
        try:
            sys.stdout = stdout_capture
            sys.stderr = stderr_capture
            
            # Run the tests
            start_time = time.time()
            
            # Use Django's test runner
            TestRunner = get_runner(settings)
            test_runner = TestRunner(verbosity=2, interactive=False, keepdb=True)
            
            # Run specific module
            result = test_runner.run_tests([module_name])
            
            end_time = time.time()
            execution_time = end_time - start_time
            
            # Restore output
            sys.stdout = old_stdout
            sys.stderr = stderr_capture
            
            # Get captured output
            stdout_output = stdout_capture.getvalue()
            stderr_output = stderr_capture.getvalue()
            
            # Parse results from output
            test_count = stdout_output.count('test_')
            failure_count = stdout_output.count('FAIL:')
            error_count = stdout_output.count('ERROR:')
            skip_count = stdout_output.count('SKIP:')
            
            # Store results
            self.results[module_name] = {
                'tests': test_count,
                'failures': failure_count,
                'errors': error_count,
                'skipped': skip_count,
                'time': execution_time,
                'success': result == 0,
                'stdout': stdout_output,
                'stderr': stderr_output
            }
            
            # Update totals
            self.total_tests += test_count
            self.total_failures += failure_count
            self.total_errors += error_count
            self.total_skipped += skip_count
            
            # Print summary for this module
            status = "PASSED" if result == 0 else "FAILED"
            print(f"Module: {module_name}")
            print(f"Status: {status}")
            print(f"Tests: {test_count}, Failures: {failure_count}, Errors: {error_count}, Skipped: {skip_count}")
            print(f"Time: {execution_time:.2f}s")
            
            if result != 0:
                print(f"\nErrors/Failures:")
                if stderr_output:
                    print(stderr_output)
                if failure_count > 0 or error_count > 0:
                    # Print relevant parts of stdout
                    lines = stdout_output.split('\n')
                    for i, line in enumerate(lines):
                        if 'FAIL:' in line or 'ERROR:' in line:
                            # Print the error and a few lines of context
                            start = max(0, i - 2)
                            end = min(len(lines), i + 10)
                            print('\n'.join(lines[start:end]))
                            print('-' * 40)
            
            return result == 0
            
        except Exception as e:
            sys.stdout = old_stdout
            sys.stderr = old_stderr
            print(f"Exception running {module_name}: {str(e)}")
            self.results[module_name] = {
                'tests': 0,
                'failures': 0,
                'errors': 1,
                'skipped': 0,
                'time': 0,
                'success': False,
                'stdout': '',
                'stderr': str(e)
            }
            return False
    
    def run_all_tests(self):
        """Run all test modules."""
        print("Starting Comprehensive Test Suite for Eswatini Policy System")
        print("=" * 80)
        
        start_time = time.time()
        successful_modules = 0
        
        for module in self.test_modules:
            try:
                success = self.run_test_module(module)
                if success:
                    successful_modules += 1
            except Exception as e:
                print(f"Failed to run module {module}: {str(e)}")
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Print comprehensive summary
        self.print_summary(total_time, successful_modules)
        
        return self.total_failures == 0 and self.total_errors == 0
    
    def print_summary(self, total_time, successful_modules):
        """Print comprehensive test summary."""
        print("\n" + "=" * 80)
        print("COMPREHENSIVE TEST SUMMARY")
        print("=" * 80)
        
        print(f"Total Modules: {len(self.test_modules)}")
        print(f"Successful Modules: {successful_modules}")
        print(f"Failed Modules: {len(self.test_modules) - successful_modules}")
        print(f"Total Execution Time: {total_time:.2f}s")
        
        print(f"\nOverall Test Statistics:")
        print(f"  Total Tests: {self.total_tests}")
        print(f"  Passed: {self.total_tests - self.total_failures - self.total_errors}")
        print(f"  Failed: {self.total_failures}")
        print(f"  Errors: {self.total_errors}")
        print(f"  Skipped: {self.total_skipped}")
        
        success_rate = ((self.total_tests - self.total_failures - self.total_errors) / max(self.total_tests, 1)) * 100
        print(f"  Success Rate: {success_rate:.1f}%")
        
        print(f"\nDetailed Module Results:")
        print("-" * 80)
        
        for module, result in self.results.items():
            status = "✓ PASS" if result['success'] else "✗ FAIL"
            print(f"{status} {module}")
            print(f"      Tests: {result['tests']}, Failures: {result['failures']}, "
                  f"Errors: {result['errors']}, Time: {result['time']:.2f}s")
        
        if self.total_failures > 0 or self.total_errors > 0:
            print(f"\n⚠️  SOME TESTS FAILED")
            print("Review the detailed output above for specific failure information.")
        else:
            print(f"\n✅ ALL TESTS PASSED!")
            print("The Eswatini policy system is working correctly.")
        
        print("\n" + "=" * 80)
    
    def run_specific_test_categories(self):
        """Run tests by category for detailed analysis."""
        categories = {
            'Unit Tests - Models': [
                'tests.test_comprehensive_models',
                'policies.tests_models',
                'simple_surveys.tests_models',
                'comparison.tests_models'
            ],
            'Integration Tests': [
                'tests.test_feature_matching_integration',
                'policies.tests_integration',
                'comparison.tests_feature_matching',
                'comparison.tests_feature_comparison'
            ],
            'End-to-End Tests': [
                'tests.test_end_to_end_survey_flow'
            ]
        }
        
        print("Running Tests by Category")
        print("=" * 80)
        
        category_results = {}
        
        for category, modules in categories.items():
            print(f"\n{'-'*60}")
            print(f"Category: {category}")
            print(f"{'-'*60}")
            
            category_start = time.time()
            category_success = True
            category_tests = 0
            category_failures = 0
            category_errors = 0
            
            for module in modules:
                if module in self.test_modules:
                    success = self.run_test_module(module)
                    if not success:
                        category_success = False
                    
                    if module in self.results:
                        category_tests += self.results[module]['tests']
                        category_failures += self.results[module]['failures']
                        category_errors += self.results[module]['errors']
            
            category_end = time.time()
            category_time = category_end - category_start
            
            category_results[category] = {
                'success': category_success,
                'tests': category_tests,
                'failures': category_failures,
                'errors': category_errors,
                'time': category_time
            }
            
            status = "✓ PASSED" if category_success else "✗ FAILED"
            print(f"\nCategory Summary - {category}: {status}")
            print(f"Tests: {category_tests}, Failures: {category_failures}, "
                  f"Errors: {category_errors}, Time: {category_time:.2f}s")
        
        # Print category summary
        print(f"\n{'='*60}")
        print("CATEGORY SUMMARY")
        print(f"{'='*60}")
        
        for category, result in category_results.items():
            status = "✓" if result['success'] else "✗"
            print(f"{status} {category}: {result['tests']} tests, "
                  f"{result['failures']} failures, {result['errors']} errors")


def main():
    """Main function to run comprehensive tests."""
    runner = ComprehensiveTestRunner()
    
    # Check if specific category requested
    if len(sys.argv) > 1:
        if sys.argv[1] == '--by-category':
            runner.run_specific_test_categories()
        elif sys.argv[1] == '--help':
            print("Comprehensive Test Runner for Eswatini Policy System")
            print("Usage:")
            print("  python run_comprehensive_tests.py           # Run all tests")
            print("  python run_comprehensive_tests.py --by-category  # Run tests by category")
            print("  python run_comprehensive_tests.py --help    # Show this help")
            return
        else:
            print(f"Unknown option: {sys.argv[1]}")
            print("Use --help for usage information")
            return
    else:
        # Run all tests
        success = runner.run_all_tests()
        
        # Exit with appropriate code
        sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()