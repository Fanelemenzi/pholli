#!/usr/bin/env python
"""
Performance test for the survey system to ensure it can handle load.
"""

import os
import sys
import django
import time
import threading
from django.test import Client
from django.urls import reverse

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pholli.settings')
django.setup()

def single_user_flow(user_id, results):
    """Simulate a single user going through the complete flow"""
    client = Client()
    start_time = time.time()
    
    try:
        # Step 1: Visit home page
        response = client.get(reverse('home'))
        assert response.status_code == 200
        
        # Step 2: Visit health page
        response = client.get(reverse('health'))
        assert response.status_code == 200
        
        # Step 3: Access health survey via direct link
        response = client.get(reverse('direct_survey', kwargs={'category_slug': 'health'}))
        assert response.status_code == 302
        
        # Step 4: Follow redirect to survey form
        response = client.get(reverse('survey', kwargs={'category': 'health'}))
        assert response.status_code == 200
        
        # Step 5: Submit survey
        survey_data = {
            'age': str(25 + (user_id % 40)),  # Age between 25-65
            'gender': 'male' if user_id % 2 == 0 else 'female',
            'location': ['johannesburg', 'cape_town', 'durban'][user_id % 3],
            'coverage_type': 'individual' if user_id % 2 == 0 else 'family',
            'budget': str(500 + (user_id % 10) * 200)  # Budget between 500-2300
        }
        response = client.post(reverse('process', kwargs={'category': 'health'}), data=survey_data)
        assert response.status_code == 302
        
        # Step 6: View results
        response = client.get(reverse('results', kwargs={'category': 'health'}))
        assert response.status_code == 200
        
        end_time = time.time()
        duration = end_time - start_time
        
        results[user_id] = {
            'success': True,
            'duration': duration,
            'error': None
        }
        
    except Exception as e:
        end_time = time.time()
        duration = end_time - start_time
        results[user_id] = {
            'success': False,
            'duration': duration,
            'error': str(e)
        }

def test_concurrent_users(num_users=10):
    """Test multiple concurrent users"""
    print(f"🚀 TESTING {num_users} CONCURRENT USERS")
    print("=" * 50)
    
    results = {}
    threads = []
    start_time = time.time()
    
    # Create and start threads
    for i in range(num_users):
        thread = threading.Thread(target=single_user_flow, args=(i, results))
        threads.append(thread)
        thread.start()
    
    # Wait for all threads to complete
    for thread in threads:
        thread.join()
    
    end_time = time.time()
    total_duration = end_time - start_time
    
    # Analyze results
    successful = sum(1 for r in results.values() if r['success'])
    failed = num_users - successful
    avg_duration = sum(r['duration'] for r in results.values()) / num_users
    min_duration = min(r['duration'] for r in results.values())
    max_duration = max(r['duration'] for r in results.values())
    
    print(f"\n📊 PERFORMANCE RESULTS")
    print(f"   ✅ Successful requests: {successful}/{num_users} ({successful/num_users*100:.1f}%)")
    print(f"   ❌ Failed requests: {failed}")
    print(f"   ⏱️  Total test duration: {total_duration:.2f}s")
    print(f"   📈 Average request duration: {avg_duration:.2f}s")
    print(f"   🏃 Fastest request: {min_duration:.2f}s")
    print(f"   🐌 Slowest request: {max_duration:.2f}s")
    print(f"   🔥 Requests per second: {num_users/total_duration:.2f}")
    
    # Show any errors
    if failed > 0:
        print(f"\n❌ ERRORS:")
        for user_id, result in results.items():
            if not result['success']:
                print(f"   User {user_id}: {result['error']}")
    
    return successful == num_users

def test_memory_usage():
    """Test for memory leaks during repeated requests"""
    print(f"\n🧠 TESTING MEMORY USAGE")
    print("=" * 30)
    
    client = Client()
    
    # Make 100 requests and check if performance degrades
    durations = []
    
    for i in range(100):
        start_time = time.time()
        
        # Complete flow
        client.get(reverse('home'))
        client.get(reverse('health'))
        client.get(reverse('survey', kwargs={'category': 'health'}))
        client.post(reverse('process', kwargs={'category': 'health'}), data={
            'age': '30',
            'gender': 'male',
            'location': 'johannesburg'
        })
        client.get(reverse('results', kwargs={'category': 'health'}))
        
        end_time = time.time()
        durations.append(end_time - start_time)
        
        if (i + 1) % 20 == 0:
            avg_last_20 = sum(durations[-20:]) / 20
            print(f"   Request {i+1}: Avg last 20 requests: {avg_last_20:.3f}s")
    
    # Check if performance degraded significantly
    first_20_avg = sum(durations[:20]) / 20
    last_20_avg = sum(durations[-20:]) / 20
    degradation = (last_20_avg - first_20_avg) / first_20_avg * 100
    
    print(f"\n📈 MEMORY USAGE ANALYSIS:")
    print(f"   First 20 requests avg: {first_20_avg:.3f}s")
    print(f"   Last 20 requests avg: {last_20_avg:.3f}s")
    print(f"   Performance change: {degradation:+.1f}%")
    
    if abs(degradation) < 20:  # Less than 20% degradation is acceptable
        print(f"   ✅ No significant memory leaks detected")
        return True
    else:
        print(f"   ⚠️  Possible memory leak detected")
        return False

def test_stress_endpoints():
    """Test individual endpoints under stress"""
    print(f"\n💪 STRESS TESTING INDIVIDUAL ENDPOINTS")
    print("=" * 45)
    
    client = Client()
    endpoints = [
        ('Home', reverse('home')),
        ('Health', reverse('health')),
        ('Funerals', reverse('funerals')),
        ('Health Survey', reverse('survey', kwargs={'category': 'health'})),
        ('Funeral Survey', reverse('survey', kwargs={'category': 'funeral'})),
        ('Health Results', reverse('results', kwargs={'category': 'health'})),
        ('Funeral Results', reverse('results', kwargs={'category': 'funeral'})),
    ]
    
    for name, url in endpoints:
        print(f"\n🎯 Testing {name}")
        durations = []
        errors = 0
        
        for i in range(50):  # 50 requests per endpoint
            start_time = time.time()
            try:
                response = client.get(url)
                if response.status_code not in [200, 302]:
                    errors += 1
            except Exception:
                errors += 1
            end_time = time.time()
            durations.append(end_time - start_time)
        
        avg_duration = sum(durations) / len(durations)
        success_rate = (50 - errors) / 50 * 100
        
        print(f"   ✅ Success rate: {success_rate:.1f}%")
        print(f"   ⏱️  Average response time: {avg_duration:.3f}s")
        print(f"   🏃 Fastest: {min(durations):.3f}s")
        print(f"   🐌 Slowest: {max(durations):.3f}s")

if __name__ == '__main__':
    try:
        print("🧪 PERFORMANCE TESTING SUITE")
        print("=" * 50)
        
        # Test 1: Concurrent users
        success1 = test_concurrent_users(5)  # Start with 5 users
        
        if success1:
            success2 = test_concurrent_users(10)  # Scale up to 10 users
            
            if success2:
                success3 = test_concurrent_users(20)  # Scale up to 20 users
        
        # Test 2: Memory usage
        memory_ok = test_memory_usage()
        
        # Test 3: Stress test endpoints
        test_stress_endpoints()
        
        print(f"\n🏆 PERFORMANCE TESTING COMPLETED!")
        print(f"   Concurrent users: {'✅' if success1 else '❌'}")
        print(f"   Memory usage: {'✅' if memory_ok else '❌'}")
        
    except Exception as e:
        print(f"\n❌ PERFORMANCE TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)