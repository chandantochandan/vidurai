"""
Test script for vidurai-proxy deployed on Render
Tests memory persistence and token compression
"""
import requests
import json
import sys

# Configuration
PROXY_URL = "https://vidurai-proxy.onrender.com"
ANTHROPIC_API_KEY = input("Enter your Anthropic API key: ").strip()

def test_health():
    """Test 1: Health endpoint"""
    print("\n=== Test 1: Health Check ===")
    response = requests.get(f"{PROXY_URL}/health")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    return response.status_code == 200

def test_initial_request():
    """Test 2: Send initial context through proxy"""
    print("\n=== Test 2: Initial Request with Context ===")

    headers = {
        "Content-Type": "application/json",
        "x-api-key": ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01"
    }

    payload = {
        "model": "claude-sonnet-4-20250514",
        "max_tokens": 100,
        "messages": [
            {
                "role": "user",
                "content": "My name is Chandan and I'm testing Vidurai proxy. Remember this: my favorite color is blue and I work on AI memory systems."
            }
        ]
    }

    response = requests.post(
        f"{PROXY_URL}/v1/messages",
        headers=headers,
        json=payload
    )

    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Claude's response: {data['content'][0]['text']}")
        return True
    else:
        print(f"Error: {response.text}")
        return False

def test_memory_recall():
    """Test 3: Test if proxy remembers context"""
    print("\n=== Test 3: Memory Recall Test ===")

    headers = {
        "Content-Type": "application/json",
        "x-api-key": ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01"
    }

    payload = {
        "model": "claude-sonnet-4-20250514",
        "max_tokens": 100,
        "messages": [
            {
                "role": "user",
                "content": "What's my favorite color and what do I work on?"
            }
        ]
    }

    response = requests.post(
        f"{PROXY_URL}/v1/messages",
        headers=headers,
        json=payload
    )

    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        response_text = data['content'][0]['text']
        print(f"Claude's response: {response_text}")

        # Check if Claude remembers
        if "blue" in response_text.lower() and "memory" in response_text.lower():
            print("✅ Memory recall SUCCESSFUL!")
            return True
        else:
            print("⚠️ Memory recall might not be working")
            return False
    else:
        print(f"Error: {response.text}")
        return False

def test_metrics():
    """Test 4: Check metrics endpoint"""
    print("\n=== Test 4: Metrics Check ===")
    response = requests.get(f"{PROXY_URL}/metrics")
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        print(f"Metrics: {json.dumps(response.json(), indent=2)}")
        return True
    return False

def main():
    print("🚀 Testing Vidurai Proxy on Render")
    print(f"Proxy URL: {PROXY_URL}")

    results = []

    # Run tests
    results.append(("Health Check", test_health()))
    results.append(("Initial Request", test_initial_request()))
    results.append(("Memory Recall", test_memory_recall()))
    results.append(("Metrics", test_metrics()))

    # Summary
    print("\n" + "="*50)
    print("TEST SUMMARY")
    print("="*50)
    for test_name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{test_name}: {status}")

    total_passed = sum(1 for _, passed in results if passed)
    print(f"\nTotal: {total_passed}/{len(results)} tests passed")

    if total_passed == len(results):
        print("\n🎉 All tests passed! Vidurai proxy is working perfectly!")
    else:
        print("\n⚠️ Some tests failed. Check the logs above.")

if __name__ == "__main__":
    main()
