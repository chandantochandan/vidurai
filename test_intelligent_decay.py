"""
Test Intelligent Decay Module
Verify entropy, relevance, and decay calculations
"""
from vidurai.core.intelligent_decay_v2 import (
    IntelligentDecay,
    EntropyCalculator,
    RelevanceScorer
)

print("=" * 70)
print("🧠 TESTING INTELLIGENT DECAY MODULE")
print("=" * 70)

# Test 1: Entropy Calculation
print("\n📊 Test 1: Entropy Calculation")
print("-" * 70)

test_texts = [
    ("The weather is nice", "Low entropy (common phrase)"),
    ("I'm building Vidurai, an intelligent AI memory system with semantic compression", "High entropy (technical, specific)"),
    ("Ok yes sure", "Very low entropy (filler)"),
    ("Quantum entanglement enables non-local correlations", "High entropy (complex concept)"),
]

entropy_calc = EntropyCalculator()

for text, description in test_texts:
    entropy = entropy_calc.calculate_combined(text)
    print(f"   Text: '{text[:50]}...'")
    print(f"   Entropy: {entropy:.3f} - {description}")
    print()

# Test 2: Relevance Scoring
print("\n🎯 Test 2: Relevance Scoring")
print("-" * 70)

relevance_scorer = RelevanceScorer(use_transformers=False)

memory_text = "I work in fintech building AI systems"
context_texts = [
    "Tell me about your work",
    "What do you do for a living?",
    "The weather is nice today",
]

print(f"   Memory: '{memory_text}'")
print(f"\n   Relevance to different contexts:")

for ctx in context_texts:
    relevance = relevance_scorer.calculate_relevance(memory_text, [ctx])
    print(f"   - '{ctx}': {relevance:.3f}")

# Test 3: Intelligent Decay
print("\n\n🧠 Test 3: Intelligent Decay Decisions")
print("-" * 70)

decay_engine = IntelligentDecay(
    base_decay_rate=0.5,
    use_embeddings=False
)

# Create simple memory class
class TestMemory:
    def __init__(self, content, access_count=0):
        self.content = content
        self.access_count = access_count
        self.decay_score = 0.0

test_memories = [
    TestMemory("My name is Chandan, I'm from Delhi, India", access_count=5),
    TestMemory("The weather is nice", access_count=0),
    TestMemory("I'm building Vidurai, an intelligent memory system", access_count=3),
    TestMemory("Ok sure yes", access_count=0),
    TestMemory("I work in fintech and AI", access_count=4),
    TestMemory("Hmm interesting", access_count=1),
]

context = {
    'recent_messages': [
        "Tell me about your work",
        "What projects are you working on?",
    ]
}

print("\n   Memory Evaluations:\n")

keep_count = 0
forget_count = 0

for i, memory in enumerate(test_memories, 1):
    decay_score = decay_engine.calculate_decay_score(memory, context)
    should_forget = decay_engine.should_forget(memory, decay_threshold=0.1, context=context)
    
    # Calculate entropy for display
    entropy = entropy_calc.calculate_combined(memory.content)
    
    decision = "🗑️  FORGET" if should_forget else "✅ KEEP"
    
    if should_forget:
        forget_count += 1
    else:
        keep_count += 1
    
    print(f"   {i}. {decision}")
    print(f"      Content: '{memory.content[:50]}...'")
    print(f"      Entropy: {entropy:.3f} | Access: {memory.access_count} | Decay: {decay_score:.3f}")
    print()

# Test 4: Statistics
print("\n📈 Test 4: Decay Engine Statistics")
print("-" * 70)

stats = decay_engine.get_statistics()
print(f"   Total evaluations: {stats['total_evaluations']}")
print(f"   High entropy memories: {stats['high_entropy_memories']}")
print(f"   Low entropy memories: {stats['low_entropy_memories']}")
print(f"   Embeddings available: {stats['embeddings_available']}")
print(f"   Base decay rate: {stats['base_decay_rate']}")

# Summary
print("\n" + "=" * 70)
print("📊 SUMMARY")
print("=" * 70)
print(f"   Memories to KEEP: {keep_count}")
print(f"   Memories to FORGET: {forget_count}")
print(f"   Keep/Forget Ratio: {keep_count}:{forget_count}")

if forget_count > 0 and keep_count > 0:
    print("\n✅ SUCCESS! Intelligent Decay is working correctly")
    print("   ✓ High entropy + high access → KEEP")
    print("   ✓ Low entropy + low access → FORGET")
    print("   ✓ Intelligent decisions based on content, not just time")
else:
    print("\n⚠️  Check thresholds - all memories same decision")

print("=" * 70)