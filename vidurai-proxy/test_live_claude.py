#!/usr/bin/env python3
"""
Live Test: vidurai-proxy with Claude API
Tests Vismriti memory management with real Claude conversations
"""

import anthropic
import os
import sys

def test_proxy_with_claude():
    """Test vidurai-proxy with Claude API"""

    # Configuration
    PROXY_URL = "http://localhost:8000/v1"  # Your proxy
    API_KEY = os.getenv("ANTHROPIC_API_KEY")

    if not API_KEY:
        print("❌ Error: ANTHROPIC_API_KEY not set")
        print("   Set it with: export ANTHROPIC_API_KEY='your-key'")
        sys.exit(1)

    print("="*60)
    print("VIDURAI-PROXY + CLAUDE - LIVE TEST")
    print("="*60)

    # Create client pointing to proxy
    client = anthropic.Anthropic(
        api_key=API_KEY,
        base_url=PROXY_URL
    )

    print(f"\n✅ Client configured")
    print(f"   Proxy: {PROXY_URL}")
    print(f"   API Key: {API_KEY[:20]}...")

    # Test conversation
    messages = []

    print("\n" + "="*60)
    print("CONVERSATION 1: Initial context")
    print("="*60)

    # Message 1: Set context
    print("\n📤 User: Remember that my favorite color is blue")
    messages.append({"role": "user", "content": "Remember that my favorite color is blue"})

    response = client.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=1024,
        messages=messages
    )

    assistant_msg = response.content[0].text
    print(f"📥 Claude: {assistant_msg[:200]}...")
    messages.append({"role": "assistant", "content": assistant_msg})

    # Message 2: Add more context
    print("\n📤 User: Also, I'm learning Python programming")
    messages.append({"role": "user", "content": "Also, I'm learning Python programming"})

    response = client.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=1024,
        messages=messages
    )

    assistant_msg = response.content[0].text
    print(f"📥 Claude: {assistant_msg[:200]}...")
    messages.append({"role": "assistant", "content": assistant_msg})

    print("\n" + "="*60)
    print("CONVERSATION 2: Test memory recall")
    print("="*60)

    # Message 3: Test recall (proxy should remember from Vismriti)
    print("\n📤 User: What's my favorite color?")
    messages.append({"role": "user", "content": "What's my favorite color?"})

    response = client.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=1024,
        messages=messages
    )

    assistant_msg = response.content[0].text
    print(f"📥 Claude: {assistant_msg}")

    # Check if Claude remembered
    if "blue" in assistant_msg.lower():
        print("\n✅ SUCCESS: Proxy remembered context from Vismriti!")
    else:
        print("\n⚠️  WARNING: Memory not recalled (might need more messages)")

    print("\n" + "="*60)
    print("TEST COMPLETE")
    print("="*60)
    print("\n💡 Check proxy logs for Vismriti memory operations:")
    print("   - Salience classification")
    print("   - Memory storage")
    print("   - Recall operations")
    print("   - Token savings")

    print("\n📊 Check metrics at: http://localhost:8000/metrics")


if __name__ == "__main__":
    try:
        test_proxy_with_claude()
    except anthropic.APIConnectionError as e:
        print(f"\n❌ Connection Error: {e}")
        print("\n💡 Is vidurai-proxy running?")
        print("   Start it with: python src/main.py")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
