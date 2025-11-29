"""
Test Vidurai integration with simulated Claude Code conversation
"""

from claude_code_vidurai_wrapper import ClaudeCodeViduriWrapper
import time

def simulate_claude_code_session():
    """Simulate a typical Claude Code coding session"""

    print("🚀 Starting Vidurai + Claude Code Integration Test\n")

    # Initialize wrapper
    wrapper = ClaudeCodeViduriWrapper(session_id="test-logo-implementation")

    # Simulate conversation about logo implementation (this actual conversation!)
    messages = [
        ("user", "I need to update the Vidurai docs website logo"),
        ("assistant", "I can help with that. Where are the logo files located?"),
        ("user", "The logo is in /mnt/user-data/uploads/WhatsApp_Image_2025-11-05_at_8_13_53_PM.jpeg"),
        ("assistant", "I'll help you update the favicon and navbar logo. First, let me check the current files..."),
        ("user", "The favicon isn't showing up on the live site"),
        ("assistant", "This is likely a caching issue. Let me check the HTML references..."),
        ("user", "Can you replace the three-kosha circles with the VI logo?"),
        ("assistant", "Sure! I'll create SVG files with the overlapping circles and your VI logo in the center..."),
        ("user", "No, keep the original colorful circles, just add VI logo"),
        ("assistant", "Understood. I'll overlay the VI logo on the existing purple/blue/green circles..."),
        ("user", "The colors look too dark, can you make them more vibrant?"),
        ("assistant", "I'll adjust the color values to make the circles more vibrant: #A78BFA for purple, #60A5FA for blue, #34D399 for green..."),
        ("user", "Actually, revert everything and start fresh with the correct approach"),
        ("assistant", "Reverting changes. I'll restore the original circles and properly overlay just the VI graphic..."),
        ("user", "How can I be sure Vidurai is actually working in Claude Code?"),
        ("assistant", "Good question! We need to verify with logs and metrics. Let me check for Vidurai-specific indicators..."),
        ("user", "Let's implement Vidurai in Claude Code right away to see real impact"),
        ("assistant", "Excellent idea! I'll create a proof-of-concept integration to measure actual token savings..."),
    ]

    # Add all messages
    print("📥 Adding messages to Vidurai memory...\n")
    for i, (role, content) in enumerate(messages, 1):
        wrapper.add_message(role, content, metadata={"step": i})
        time.sleep(0.1)  # Simulate time between messages

    print("\n" + "="*60 + "\n")

    # Now simulate getting context for next query
    print("🔍 Testing context retrieval with different queries...\n")

    # Query 1: Specific technical question
    print("Query 1: Technical implementation question")
    query1 = "How do I update the logo in the docs site?"
    context1 = wrapper.get_context_for_claude(query1, max_messages=5)
    print(f"   Query: '{query1}'")
    print(f"   Retrieved: {len(context1)} messages\n")

    # Query 2: Debugging question
    print("Query 2: Debugging question")
    query2 = "Why isn't the favicon showing?"
    context2 = wrapper.get_context_for_claude(query2, max_messages=5)
    print(f"   Query: '{query2}'")
    print(f"   Retrieved: {len(context2)} messages\n")

    # Query 3: Design question
    print("Query 3: Design question")
    query3 = "What colors should I use for the circles?"
    context3 = wrapper.get_context_for_claude(query3, max_messages=5)
    print(f"   Query: '{query3}'")
    print(f"   Retrieved: {len(context3)} messages\n")

    # Show sample retrieved context
    print("="*60)
    print(f"\n📋 Sample context for: '{query1}'\n")
    for msg in context1[:3]:
        print(f"   [{msg['role']}] {msg['content'][:70]}...")
        print(f"   Importance: {msg['importance']:.2f}\n")

    # Get savings report
    print("="*60)
    print(wrapper.get_savings_report())

    # Additional metrics
    print("\n📈 ADDITIONAL METRICS:")
    print(f"   Average tokens per message (before): {wrapper.total_tokens_before / wrapper.message_count:.1f}")
    print(f"   Average tokens retrieved per query: {wrapper.total_tokens_after / 3:.1f}")
    print(f"   Compression ratio: {wrapper.total_tokens_after / wrapper.total_tokens_before:.2f}x")
    print("\n" + "="*60)

if __name__ == "__main__":
    simulate_claude_code_session()
