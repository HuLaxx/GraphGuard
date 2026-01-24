"""
GraphGuard API - Test Client
============================
Test the deployed fraud detection API
"""

import os
import requests
import json
from datetime import datetime

API_URL = "http://localhost:8000"
API_KEY = os.getenv("API_KEY", "change-me")

def test_health():
    """Test health endpoint"""
    print("\n" + "="*60)
    print("1. Testing /health endpoint...")
    print("="*60)
    
    response = requests.get(f"{API_URL}/health")
    
    if response.status_code == 200:
        data = response.json()
        print("✅ Health Check Passed")
        print(f"   Status: {data['status']}")
        print(f"   Model Loaded: {data['model_loaded']}")
        print(f"   Redis Available: {data['redis_available']}")
        print(f"   Version: {data['version']}")
        print(f"   Uptime: {data['uptime_seconds']}s")
        return True
    else:
        print(f"❌ Health check failed: {response.status_code}")
        return False

def test_scoring():
    """Test fraud scoring endpoint"""
    print("\n" + "="*60)
    print("2. Testing /score endpoint...")
    print("="*60)
    
    # Test cases
    test_cases = [
        {
            "name": "Small legitimate transaction",
            "data": {
                "transaction_id": "test_001",
                "user_id": "user_00123",
                "merchant_id": "merchant_0087",
                "amount": 45.99,
                "currency": "USD",
                "device_id": "device_abc123",
                "ip_address": "192.168.1.100"
            }
        },
        {
            "name": "Large suspicious transaction",
            "data": {
                "transaction_id": "test_002",
                "user_id": "user_99999",
                "merchant_id": "merchant_0500",
                "amount": 2500.00,
                "currency": "USD",
                "device_id": "device_xyz789",
                "ip_address": "203.45.67.89"
            }
        },
        {
            "name": "Medium transaction",
            "data": {
                "transaction_id": "test_003",
                "user_id": "user_05432",
                "merchant_id": "merchant_0250",
                "amount": 389.50,
                "currency": "USD",
                "device_id": "device_mid456",
                "ip_address": "10.0.0.45"
            }
        }
    ]
    
    headers = {"X-API-Key": API_KEY}
    
    for i, test in enumerate(test_cases, 1):
        print(f"\n   Test Case {i}: {test['name']}")
        print(f"   Amount: ${test['data']['amount']}")
        
        response = requests.post(
            f"{API_URL}/score",
            json=test['data'],
            headers=headers
        )
        
        if response.status_code == 200:
            result = response.json()
            score = result['fraud_score']
            decision = result['decision']
            latency = result['latency_ms']
            
            # Color code based on decision
            if decision == "AUTO_APPROVE":
                status = "✅"
            elif decision == "REVIEW":
                status = "⚠️ "
            else:
                status = "❌"
            
            print(f"   {status} Fraud Score: {score:.3f}")
            print(f"      Decision: {decision}")
            print(f"      Latency: {latency}ms")
            print(f"      Reasoning: {result['explanation']['reasoning']}")
        else:
            print(f"   ❌ Request failed: {response.status_code}")
            print(f"      {response.text}")

def test_metrics():
    """Test metrics endpoint"""
    print("\n" + "="*60)
    print("3. Testing /metrics endpoint...")
    print("="*60)
    
    response = requests.get(f"{API_URL}/metrics")
    
    if response.status_code == 200:
        print("✅ Metrics endpoint working")
        print("\nSample metrics:")
        lines = response.text.strip().split('\n')
        for line in lines[:5]:
            if not line.startswith('#'):
                print(f"   {line}")
    else:
        print(f"❌ Metrics failed: {response.status_code}")

def main():
    print("\n" + "="*60)
    print("GraphGuard API Test Suite")
    print("="*60)
    print(f"API URL: {API_URL}")
    if API_KEY == "change-me":
        print("⚠️  API_KEY not set. Update your environment or .env file.")
    else:
        print(f"Using API Key: {API_KEY[:20]}...")
    
    try:
        # Test 1: Health
        if not test_health():
            print("\n❌ Health check failed, aborting tests")
            return
        
        # Test 2: Scoring
        test_scoring()
        
        # Test 3: Metrics
        test_metrics()
        
        print("\n" + "="*60)
        print("✅ All API tests completed!")
        print("="*60)
        print(f"\n📖 API Documentation: {API_URL}/docs")
        print(f"🔍 Interactive Testing: {API_URL}/docs")
        
    except requests.exceptions.ConnectionError:
        print("\n❌ Cannot connect to API. Is it running?")
        print(f"   Start with: python api_production.py")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")

if __name__ == "__main__":
    main()
