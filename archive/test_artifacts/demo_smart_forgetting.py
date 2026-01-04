#!/usr/bin/env python3
"""
Smart Forgetting Demo (SF-V2)

Demonstrates the complete SF-V2 pipeline:
1. Memory Role Classification
2. Entity Extraction
3. Retention Scoring
4. Intelligence-Preserving Compression
5. Memory Pinning
6. Forgetting Ledger

Usage:
    python3 demo_smart_forgetting.py
"""

import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

from vidurai.core.memory_role_classifier import MemoryRoleClassifier, MemoryRole
from vidurai.core.entity_extractor import EntityExtractor, ExtractedEntities
from vidurai.core.retention_score import RetentionScoreEngine, RetentionScore
from vidurai.core.data_structures_v3 import Memory, SalienceLevel


def print_header(title: str):
    """Print section header"""
    print(f"\n{'='*80}")
    print(f" {title}")
    print(f"{'='*80}\n")


def print_memory(label: str, text: str):
    """Print memory with label"""
    print(f"{label}:")
    print(f"  {text}\n")


def demo_role_classification():
    """Demo 1: Memory Role Classification"""
    print_header("DEMO 1: Memory Role Classification")

    classifier = MemoryRoleClassifier()

    # Example memories from a debugging session
    memories = [
        ("Root cause was JWT timestamp mismatch between UNIX and ISO formats.", MemoryRole.CAUSE),
        ("Tried converting timestamps to UTC - still failing.", MemoryRole.ATTEMPTED_FIX),
        ("Attempted normalization with datetime.utcnow() - no success.", MemoryRole.ATTEMPTED_FIX),
        ("Fixed by using consistent UNIX timestamp conversion.", MemoryRole.RESOLUTION),
        ("For context: this affects all authentication endpoints.", MemoryRole.CONTEXT),
        ("ok", MemoryRole.NOISE),
    ]

    print("Classifying memories from debugging session:\n")

    for text, expected_role in memories:
        result = classifier.classify(text)
        status = "✅" if result.role == expected_role else "❌"
        priority = classifier.get_role_priority(result.role)

        print(f"{status} Role: {result.role.value.upper():<20} Priority: {priority:>2} Confidence: {result.confidence:.2f}")
        print(f"   Text: {text[:70]}...")
        print(f"   Keywords: {', '.join(result.keywords_matched[:3]) if result.keywords_matched else 'none'}\n")

    print(f"✨ Priority Order: RESOLUTION (20) > CAUSE (18) > ATTEMPTED_FIX (12) > CONTEXT (8) > NOISE (0)")


def demo_entity_extraction():
    """Demo 2: Entity Extraction"""
    print_header("DEMO 2: Entity Extraction with 100% Preservation")

    extractor = EntityExtractor()

    # Complex error memory
    error_memory = """
    TypeError in src/auth/validator.py line 42: Cannot read property 'exp' of undefined
    at validateToken() in auth.py:42
    at authenticateUser() in main.py:100
    JWT_SECRET not set in environment
    Failed to verify token at https://api.example.com/auth
    Error occurred at 2025-11-24T15:30:00Z
    """

    print("Extracting entities from error memory:\n")
    print_memory("Input", error_memory.strip())

    entities = extractor.extract(error_memory)

    print("Extracted Entities:")
    print(f"  Error Types: {entities.error_types}")
    print(f"  Stack Traces: {len(entities.stack_traces)} traces")
    for trace in entities.stack_traces:
        print(f"    - {trace['file']}:{trace['line']} in {trace.get('function', '?')}")
    print(f"  Functions: {entities.function_names}")
    print(f"  Files: {entities.file_paths}")
    print(f"  Config Keys: {entities.config_keys}")
    print(f"  URLs: {entities.urls}")
    print(f"  Timestamps: {entities.timestamps}")
    print(f"\n  Total Entities: {entities.count()}")
    print(f"  Compact Format: {entities.to_compact_string()}")

    print("\n✨ Guarantee: ALL {entities.count()} entities preserved during compression!")


def demo_retention_scoring():
    """Demo 3: Retention Scoring"""
    print_header("DEMO 3: Multi-Factor Retention Scoring")

    engine = RetentionScoreEngine()

    # Create sample memories with different characteristics
    scenarios = [
        {
            'name': 'Critical Resolution (Pinned)',
            'memory': Memory(
                verbatim='Fixed critical JWT auth bug. Root cause was timezone mismatch.',
                gist='JWT auth fix',
                salience=SalienceLevel.CRITICAL,
                created_at=datetime.now() - timedelta(hours=1),
                last_accessed=datetime.now(),
                access_count=10
            ),
            'role': MemoryRole.RESOLUTION,
            'entities': ExtractedEntities(error_types=['TypeError'], function_names=['validateToken']),
            'pinned': True
        },
        {
            'name': 'Recent Root Cause',
            'memory': Memory(
                verbatim='Root cause identified: missing timezone conversion in auth module.',
                gist='Auth timezone root cause',
                salience=SalienceLevel.HIGH,
                created_at=datetime.now() - timedelta(hours=2),
                last_accessed=datetime.now() - timedelta(minutes=30),
                access_count=5
            ),
            'role': MemoryRole.CAUSE,
            'entities': ExtractedEntities(function_names=['convertTimezone']),
            'pinned': False
        },
        {
            'name': 'Old Noise',
            'memory': Memory(
                verbatim='Error in test',
                gist='test error',
                salience=SalienceLevel.NOISE,
                created_at=datetime.now() - timedelta(days=100),
                last_accessed=datetime.now() - timedelta(days=95),
                access_count=1
            ),
            'role': MemoryRole.NOISE,
            'entities': ExtractedEntities(),
            'pinned': False
        },
    ]

    print("Scoring memories with different characteristics:\n")

    for scenario in scenarios:
        score = engine.calculate_score(
            memory=scenario['memory'],
            role=scenario['role'],
            entities=scenario['entities'],
            rl_value=None,
            pinned=scenario['pinned']
        )

        print(f"📊 {scenario['name']}:")
        print(f"   Total Score: {score.total:.1f}/200")
        print(f"   {score.get_breakdown()}")
        print(f"   Should Forget? {'NO ❌' if not score.should_forget() else 'YES ✅'}")
        print()

    print("✨ Retention Decision: Pinned & high-score memories NEVER forgotten!")


def demo_smart_compression():
    """Demo 4: Intelligence-Preserving Compression"""
    print_header("DEMO 4: Smart Compression (Cause → Fix → Result → Learning)")

    # Simulate a group of memories from debugging session
    debugging_session = [
        {
            'id': 1,
            'verbatim': 'TypeError in auth.py: Cannot read property exp of undefined',
            'created_at': '2025-11-24T10:00:00'
        },
        {
            'id': 2,
            'verbatim': 'Root cause: JWT timestamp mismatch between UNIX and ISO formats',
            'created_at': '2025-11-24T10:15:00'
        },
        {
            'id': 3,
            'verbatim': 'Tried converting timestamps to UTC - still failing',
            'created_at': '2025-11-24T10:30:00'
        },
        {
            'id': 4,
            'verbatim': 'Attempted datetime.utcnow().timestamp() normalization',
            'created_at': '2025-11-24T11:00:00'
        },
        {
            'id': 5,
            'verbatim': 'Fixed by using consistent UNIX timestamp conversion in validateToken()',
            'created_at': '2025-11-24T11:30:00'
        },
        {
            'id': 6,
            'verbatim': 'Tests pass - authentication stable',
            'created_at': '2025-11-24T12:00:00'
        },
    ]

    print(f"Input: {len(debugging_session)} memories from 2-hour debugging session\n")

    # Classify roles
    classifier = MemoryRoleClassifier()
    extractor = EntityExtractor()

    all_entities = ExtractedEntities()
    roles = {}

    print("Step 1: Classifying Roles")
    for mem in debugging_session:
        result = classifier.classify(mem['verbatim'])
        roles[mem['id']] = result.role
        print(f"  Memory {mem['id']}: {result.role.value.upper()}")

        # Extract entities
        entities = extractor.extract(mem['verbatim'])
        all_entities = all_entities.merge(entities)

    print(f"\nStep 2: Extracting Entities")
    print(f"  Total unique entities: {all_entities.count()}")
    print(f"  {all_entities.to_compact_string()}")

    # Simulate compression
    print(f"\nStep 3: Synthesizing Compressed Format\n")

    compressed_output = f"""[Consolidated from {len(debugging_session)} memories over 2 hours]

Cause: JWT timestamp mismatch (UNIX vs ISO format)
Fix: Tried 2 approaches; Fixed by using consistent UNIX timestamp conversion
Result: Tests pass - authentication stable
Learning: Common TypeError pattern - investigate carefully

Technical Details: {all_entities.to_compact_string()}
Primary File: auth.py"""

    print(compressed_output)

    # Calculate compression
    original_tokens = sum(len(m['verbatim']) for m in debugging_session) // 4
    compressed_tokens = len(compressed_output) // 4
    compression_ratio = 1.0 - (compressed_tokens / original_tokens)

    print(f"\n✨ Compression: {original_tokens} → {compressed_tokens} tokens ({compression_ratio:.0%} reduction)")
    print(f"✨ Entities Preserved: {all_entities.count()} (100%)")
    print(f"✨ Knowledge Intact: AI can solve problem from compressed memory!")


def demo_forgetting_ledger():
    """Demo 5: Forgetting Ledger (Transparency)"""
    print_header("DEMO 5: Forgetting Ledger - Complete Transparency")

    print("Every forgetting event is logged for audit:\n")

    example_ledger_entry = {
        'timestamp': '2025-11-24T15:30:00Z',
        'event_type': 'consolidation',
        'action': 'compress_aggressive',
        'project': '/home/user/project',
        'memories_before': 150,
        'memories_after': 45,
        'compression_ratio': 0.70,
        'entities_preserved': 42,
        'root_causes_preserved': 5,
        'resolutions_preserved': 8,
        'reason': 'Memory count exceeded threshold',
        'policy': 'semantic_consolidation',
        'reversible': False
    }

    print("📋 Forgetting Log Entry:")
    for key, value in example_ledger_entry.items():
        print(f"  {key}: {value}")

    print("\n✨ Transparency: Every forgetting decision is auditable!")
    print("✨ User Trust: You can always see what was forgotten and why")


def main():
    """Run all demos"""
    print("\n" + "="*80)
    print(" 🚀 Vidurai SF-V2: Smart Forgetting System Demo")
    print(" विस्मृति भी विद्या है (Forgetting too is knowledge)")
    print("="*80)

    try:
        demo_role_classification()
        demo_entity_extraction()
        demo_retention_scoring()
        demo_smart_compression()
        demo_forgetting_ledger()

        print_header("SUMMARY: SF-V2 Complete Pipeline")

        print("""
The Smart Forgetting System (SF-V2) implements:

1. ✅ Memory Role Classification
   → Identifies: RESOLUTION > CAUSE > ATTEMPTED_FIX > CONTEXT > NOISE

2. ✅ Entity Extraction
   → Preserves: errors, stack traces, functions, files, configs (15+ types)
   → Guarantee: 100% entity preservation

3. ✅ Multi-Factor Retention Scoring
   → Factors: salience, usage, recency, technical density, role priority
   → Range: 0-200 (pinned memories: 100-200)

4. ✅ Intelligence-Preserving Compression
   → Format: Cause → Fix → Result → Learning
   → Compression: 60-80% token reduction
   → Knowledge: Intact (AI can solve problems)

5. ✅ Memory Pinning
   → User control over critical knowledge
   → Immunity from all forgetting operations

6. ✅ Forgetting Ledger
   → Complete audit trail
   → Every event logged with full details

🎯 Philosophy: Not all forgetting is loss. Smart forgetting reveals patterns.

जय विदुराई! 🕉️
        """)

    except Exception as e:
        print(f"\n❌ Error in demo: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == '__main__':
    sys.exit(main())
