"""
Test Script - Vismriti Phase 1-2 Components
Validates data structures, gist extraction, and salience classification

Run: python test_vismriti_phase1_2.py
"""

print("="*70)
print("VISMRITI v1.6.0 - PHASE 1-2 VALIDATION")
print("="*70)
print()

# Test 1: Import data structures
print("Test 1: Importing data_structures_v3...")
try:
    from vidurai.core.data_structures_v3 import Memory, SalienceLevel, MemoryStatus
    print("✅ Successfully imported: Memory, SalienceLevel, MemoryStatus")
except Exception as e:
    print(f"❌ Import failed: {e}")
    exit(1)

# Test 2: Create Memory instances
print("\nTest 2: Creating dual-trace Memory instances...")
try:
    # Test verbatim + gist
    mem1 = Memory(
        verbatim="User said: 'Remember to update the API key in production'",
        gist="Update production API key"
    )
    print(f"✅ Created memory with both traces: {mem1.engram_id}")

    # Test gist-only
    mem2 = Memory(
        verbatim="",
        gist="User fixed authentication bug"
    )
    print(f"✅ Created gist-only memory: {mem2.engram_id}")

    # Test validation (should fail without either trace)
    try:
        mem_invalid = Memory(verbatim="", gist="")
        print("❌ Validation failed: Should have raised ValueError")
    except ValueError:
        print("✅ Validation works: Rejects empty memory")

except Exception as e:
    print(f"❌ Memory creation failed: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

# Test 3: Test SalienceLevel enum
print("\nTest 3: Testing SalienceLevel enum...")
try:
    levels = [
        SalienceLevel.CRITICAL,
        SalienceLevel.HIGH,
        SalienceLevel.MEDIUM,
        SalienceLevel.LOW,
        SalienceLevel.NOISE
    ]

    for level in levels:
        print(f"  - {level.name} ({level.value}): {level.description}")

    print("✅ All salience levels accessible with descriptions")
except Exception as e:
    print(f"❌ SalienceLevel test failed: {e}")
    exit(1)

# Test 4: Test MemoryStatus enum
print("\nTest 4: Testing MemoryStatus enum...")
try:
    statuses = [
        MemoryStatus.ACTIVE,
        MemoryStatus.CONSOLIDATED,
        MemoryStatus.PRUNED,
        MemoryStatus.UNLEARNED,
        MemoryStatus.SILENCED
    ]

    for status in statuses:
        print(f"  - {status.name} ({status.value})")

    print("✅ All memory statuses accessible")
except Exception as e:
    print(f"❌ MemoryStatus test failed: {e}")
    exit(1)

# Test 5: Test Memory methods
print("\nTest 5: Testing Memory methods...")
try:
    mem = Memory(verbatim="Test", gist="Test memory", salience=SalienceLevel.HIGH)

    # Test access tracking
    initial_count = mem.access_count
    mem.access()
    assert mem.access_count == initial_count + 1, "Access count not incremented"
    print("✅ access() method works")

    # Test age calculation
    age = mem.age_days()
    assert age == 0, "New memory should have age 0"
    print("✅ age_days() method works")

    # Test trace checks
    assert not mem.is_verbatim_only(), "Memory has both traces"
    assert not mem.is_gist_only(), "Memory has both traces"
    print("✅ is_verbatim_only() and is_gist_only() work")

    # Test with verbatim-only
    mem_verb = Memory(verbatim="Only verbatim", gist="")
    assert mem_verb.is_verbatim_only(), "Should be verbatim-only"
    print("✅ Verbatim-only detection works")

    # Test with gist-only
    mem_gist = Memory(verbatim="", gist="Only gist")
    assert mem_gist.is_gist_only(), "Should be gist-only"
    print("✅ Gist-only detection works")

except Exception as e:
    print(f"❌ Memory methods test failed: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

# Test 6: Import salience classifier
print("\nTest 6: Importing salience_classifier...")
try:
    from vidurai.core.salience_classifier import SalienceClassifier
    print("✅ Successfully imported SalienceClassifier")
except Exception as e:
    print(f"❌ Import failed: {e}")
    exit(1)

# Test 7: Test salience classification
print("\nTest 7: Testing salience classification...")
try:
    classifier = SalienceClassifier()

    # Test CRITICAL classification
    mem_critical = Memory(
        verbatim="Remember this: API key is abc123",
        gist="Store API key"
    )
    salience = classifier.classify(mem_critical)
    assert salience == SalienceLevel.CRITICAL, f"Expected CRITICAL, got {salience}"
    print(f"✅ CRITICAL: '{mem_critical.gist}' → {salience.name}")

    # Test HIGH classification
    mem_high = Memory(
        verbatim="Finally fixed the authentication bug!",
        gist="Fixed auth bug"
    )
    salience = classifier.classify(mem_high)
    assert salience == SalienceLevel.HIGH, f"Expected HIGH, got {salience}"
    print(f"✅ HIGH: '{mem_high.gist}' → {salience.name}")

    # Test MEDIUM classification
    mem_medium = Memory(
        verbatim="Working on the dashboard component",
        gist="Building dashboard"
    )
    salience = classifier.classify(mem_medium)
    assert salience == SalienceLevel.MEDIUM, f"Expected MEDIUM, got {salience}"
    print(f"✅ MEDIUM: '{mem_medium.gist}' → {salience.name}")

    # Test LOW classification
    mem_low = Memory(
        verbatim="Hi",
        gist="Greeting"
    )
    salience = classifier.classify(mem_low)
    assert salience == SalienceLevel.LOW, f"Expected LOW, got {salience}"
    print(f"✅ LOW: '{mem_low.gist}' → {salience.name}")

    # Test NOISE classification
    mem_noise = Memory(
        verbatim="log: [2024-11-07 10:00:00] System startup",
        gist="System log entry"
    )
    salience = classifier.classify(mem_noise)
    assert salience == SalienceLevel.NOISE, f"Expected NOISE, got {salience}"
    print(f"✅ NOISE: '{mem_noise.gist}' → {salience.name}")

    print("✅ All salience classifications work correctly")

except Exception as e:
    print(f"❌ Salience classification test failed: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

# Test 8: Test classification explanation
print("\nTest 8: Testing classification explanations...")
try:
    classifier = SalienceClassifier()

    mem = Memory(
        verbatim="Solved the critical bug in production",
        gist="Fixed production bug",
        salience=SalienceLevel.HIGH
    )

    explanation = classifier.explain_classification(mem)
    print(f"  Memory: '{mem.gist}'")
    print(f"  Explanation: {explanation}")
    print("✅ Explanation generation works")

except Exception as e:
    print(f"❌ Explanation test failed: {e}")
    exit(1)

# Test 9: Test batch classification
print("\nTest 9: Testing batch classification...")
try:
    classifier = SalienceClassifier()

    memories = [
        Memory(verbatim="Remember this API key", gist="Store key"),
        Memory(verbatim="Fixed bug", gist="Bug fix"),
        Memory(verbatim="Working on code", gist="Coding"),
        Memory(verbatim="Hi there", gist="Greeting"),
        Memory(verbatim="log: system event", gist="System log")
    ]

    stats = classifier.classify_batch(memories)

    print("  Classification statistics:")
    for level_name, count in stats.items():
        if count > 0:
            print(f"    {level_name}: {count}")

    # Verify all memories were classified
    total_classified = sum(stats.values())
    assert total_classified == len(memories), "Not all memories classified"

    print("✅ Batch classification works")

except Exception as e:
    print(f"❌ Batch classification test failed: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

# Test 10: Import gist extractor (may fail if no OpenAI key, which is OK)
print("\nTest 10: Importing gist_extractor...")
try:
    from vidurai.core.gist_extractor import GistExtractor
    print("✅ Successfully imported GistExtractor")

    # Try to initialize (will fail without API key, which is expected)
    import os
    if os.getenv("OPENAI_API_KEY"):
        extractor = GistExtractor()
        print("✅ GistExtractor initialized (OpenAI API key found)")
    else:
        print("⚠️  OpenAI API key not set (expected for gist extraction)")
        try:
            extractor = GistExtractor()
            print("❌ Should have raised ValueError without API key")
        except ValueError as e:
            print(f"✅ Correctly requires API key: {e}")

except Exception as e:
    print(f"❌ Import failed: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

# Summary
print("\n" + "="*70)
print("PHASE 1-2 VALIDATION COMPLETE")
print("="*70)
print("✅ All imports successful")
print("✅ Data structures functional")
print("✅ Salience classification working")
print("✅ Memory lifecycle tracking operational")
print()
print("Ready for Phase 3-4 (Passive Decay & Active Unlearning)")
print("="*70)
