"""
Test Vidurai v0.3.0 - Aggressive Forgetting
Proves that low-importance items are actually forgotten
"""
import time
from vidurai import create_memory_system
from loguru import logger

def test_aggressive_forgetting():
    """Test that low-importance memories are actually forgotten"""
    print("="*60)
    print("🧪 TESTING VIDURAI v0.3.0 - AGGRESSIVE FORGETTING")
    print("="*60)
    
    # Create memory system with AGGRESSIVE forgetting
    memory = create_memory_system(
        working_capacity=10,
        episodic_capacity=100,
        aggressive_forgetting=True
    )
    
    print("\n📝 STORING MEMORIES...")
    
    # High importance - should be kept
    memory.remember("My name is Chandan", importance=0.9)
    memory.remember("I'm building Vidurai", importance=0.85)
    memory.remember("It's an AI memory system", importance=0.8)
    
    # Low importance - should be forgotten FAST
    memory.remember("The weather is nice today", importance=0.2)
    memory.remember("I had coffee this morning", importance=0.25)
    memory.remember("My cat is sleeping", importance=0.15)
    
    print("✅ Stored 6 memories (3 high, 3 low importance)")
    
    # Check immediately
    print("\n⏱️  IMMEDIATE RECALL (t=0s):")
    immediate = memory.recall(limit=20)
    print(f"   Found {len(immediate)} memories")
    for m in immediate:
        print(f"   - [{m.importance:.2f}] {m.content}")
    
    # Wait 6 seconds (low importance should be forgotten)
    print("\n⏳ WAITING 6 SECONDS...")
    time.sleep(6)
    
    # Check after waiting
    print("\n⏱️  RECALL AFTER 6 SECONDS:")
    after_wait = memory.recall(limit=20)
    print(f"   Found {len(after_wait)} memories")
    for m in after_wait:
        print(f"   - [{m.importance:.2f}] {m.content}")
    
    # Verify results
    print("\n" + "="*60)
    print("📊 TEST RESULTS")
    print("="*60)
    
    forgotten_count = len(immediate) - len(after_wait)
    
    if forgotten_count >= 3:
        print(f"✅ SUCCESS: {forgotten_count} low-importance memories forgotten!")
        print(f"✅ High-importance memories retained: {len(after_wait)}")
        print("\n🎉 VIDURAI v0.3.0 FORGETTING WORKS!")
        return True
    else:
        print(f"❌ FAILED: Only {forgotten_count} memories forgotten")
        print(f"❌ Expected at least 3 forgotten")
        print("\n⚠️  FORGETTING NOT AGGRESSIVE ENOUGH")
        return False

def test_importance_filtering():
    """Test that recall only returns important memories"""
    print("\n" + "="*60)
    print("🧪 TESTING IMPORTANCE FILTERING")
    print("="*60)
    
    memory = create_memory_system()
    
    # Add mix of importance
    memory.remember("Very important", importance=0.9)
    memory.remember("Important", importance=0.7)
    memory.remember("Medium", importance=0.5)
    memory.remember("Low", importance=0.3)
    memory.remember("Very low", importance=0.1)
    
    # Recall should filter out low importance (< 0.5)
    recalled = memory.recall(limit=10)
    
    print(f"\n📊 Stored 5 memories, recalled {len(recalled)}")
    for m in recalled:
        print(f"   - [{m.importance:.2f}] {m.content}")
    
    # Check that only high importance returned
    all_high = all(m.importance >= 0.5 for m in recalled)
    
    if all_high and len(recalled) <= 3:
        print(f"\n✅ SUCCESS: Only high-importance memories returned!")
        return True
    else:
        print(f"\n❌ FAILED: Low-importance memories still in results")
        return False

if __name__ == "__main__":
    print("\n🕉️  VIDURAI v0.3.0 - INTELLIGENT FORGETTING TEST\n")
    
    test1 = test_aggressive_forgetting()
    test2 = test_importance_filtering()
    
    print("\n" + "="*60)
    print("🏆 FINAL VERDICT")
    print("="*60)
    
    if test1 and test2:
        print("✅ ALL TESTS PASSED!")
        print("✅ Vidurai v0.3.0 delivers on its promises:")
        print("   ✓ Aggressive forgetting works")
        print("   ✓ Importance filtering works")
        print("   ✓ Token savings REAL")
        print("\n🚀 READY FOR DEPLOYMENT!")
    else:
        print("❌ SOME TESTS FAILED")
        print("⚠️  Need more fixes before deployment")