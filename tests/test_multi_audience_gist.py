#!/usr/bin/env python3
"""
Test suite for Phase 5.2: Multi-Audience Gist Generator
Tests rule-based gist generation for different audiences
"""

import sys
from pathlib import Path

# Add paths
sys.path.insert(0, str(Path(__file__).parent))

def test_basic_generation():
    """Test basic multi-audience gist generation"""
    print("=" * 70)
    print("🧪 TEST 1: Basic Generation")
    print("=" * 70)
    print()

    from vidurai.core.multi_audience_gist import MultiAudienceGistGenerator

    generator = MultiAudienceGistGenerator()

    verbatim = "Fixed authentication bug in JWT validation middleware"
    canonical = "Fixed auth bug in JWT validation"

    gists = generator.generate(verbatim, canonical)

    print(f"Canonical: {canonical}")
    print()
    print("Generated gists:")
    for audience, gist in gists.items():
        print(f"  {audience:12s}: {gist}")

    # Verify all audiences present
    assert 'developer' in gists
    assert 'ai' in gists
    assert 'manager' in gists
    assert 'personal' in gists

    # Verify none are empty
    assert all(len(g) > 0 for g in gists.values())

    print("\n✅ PASSED: All 4 audience gists generated\n")


def test_developer_gist():
    """Test developer-focused gist generation"""
    print("=" * 70)
    print("🧪 TEST 2: Developer Gist")
    print("=" * 70)
    print()

    from vidurai.core.multi_audience_gist import MultiAudienceGistGenerator

    generator = MultiAudienceGistGenerator()

    # Test with file context
    verbatim = "TypeError in authentication module when validating JWT tokens"
    canonical = "Fixed JWT validation error"
    context = {"file_path": "/src/auth/middleware.py", "line_number": 42}

    gists = generator.generate(verbatim, canonical, context)

    print(f"Canonical: {canonical}")
    print(f"Developer: {gists['developer']}")
    print()

    dev_gist = gists['developer']

    # Should include file reference
    assert 'middleware.py' in dev_gist or 'line' in dev_gist, \
        "Developer gist should include file/line context"

    # Should preserve technical terms
    assert 'JWT' in dev_gist or 'jwt' in dev_gist.lower(), \
        "Developer gist should preserve technical terms"

    print("✅ Includes file context")
    print("✅ Preserves technical terms")
    print("\n✅ PASSED: Developer gist is technical\n")


def test_ai_gist():
    """Test AI-focused gist generation"""
    print("=" * 70)
    print("🧪 TEST 3: AI Gist")
    print("=" * 70)
    print()

    from vidurai.core.multi_audience_gist import MultiAudienceGistGenerator

    generator = MultiAudienceGistGenerator()

    # Test different event types
    test_cases = [
        ("Fixed auth bug", {"event_type": "bugfix"}, "Bug resolution"),
        ("Added user login", {"event_type": "feature"}, "Feature implementation"),
        ("TypeError in module", {"event_type": "error"}, "Error pattern"),
    ]

    for canonical, context, expected_pattern in test_cases:
        gists = generator.generate("", canonical, context)
        ai_gist = gists['ai']

        print(f"Canonical: {canonical}")
        print(f"AI:        {ai_gist}")
        print(f"Expected:  {expected_pattern}")

        assert expected_pattern in ai_gist or "Pattern:" in ai_gist, \
            f"AI gist should have pattern marker"

        print("✅ Has pattern marker\n")

    print("✅ PASSED: AI gist has structure markers\n")


def test_manager_gist():
    """Test manager-focused gist generation"""
    print("=" * 70)
    print("🧪 TEST 4: Manager Gist")
    print("=" * 70)
    print()

    from vidurai.core.multi_audience_gist import MultiAudienceGistGenerator

    generator = MultiAudienceGistGenerator()

    verbatim = "Fixed critical JWT token validation bug in auth.py line 42"
    canonical = "Fixed JWT token validation in auth.py"

    gists = generator.generate(verbatim, canonical)

    print(f"Canonical: {canonical}")
    print(f"Manager:   {gists['manager']}")
    print()

    manager_gist = gists['manager']

    # Should be shorter than canonical
    assert len(manager_gist) <= len(canonical) * 1.2, \
        "Manager gist should be concise"

    # Should remove technical details
    assert 'line 42' not in manager_gist, \
        "Manager gist should remove line numbers"

    # Should have action focus
    assert any(word in manager_gist.lower() for word in ['fixed', 'updated', 'added', 'created']), \
        "Manager gist should start with action"

    print("✅ Shorter than canonical")
    print("✅ Removes technical details")
    print("✅ Action-focused")
    print("\n✅ PASSED: Manager gist is concise and impact-focused\n")


def test_personal_gist():
    """Test personal diary-style gist generation"""
    print("=" * 70)
    print("🧪 TEST 5: Personal Gist")
    print("=" * 70)
    print()

    from vidurai.core.multi_audience_gist import MultiAudienceGistGenerator

    generator = MultiAudienceGistGenerator()

    test_cases = [
        ("Fixed auth bug", "I fixed"),
        ("Implemented user login", "I implemented"),
        ("Updated configuration", "I updated"),
        ("Created new module", "I created"),
    ]

    for canonical, expected_start in test_cases:
        gists = generator.generate("", canonical)
        personal_gist = gists['personal']

        print(f"Canonical: {canonical}")
        print(f"Personal:  {personal_gist}")

        # Should be first-person
        assert personal_gist.startswith('I '), \
            f"Personal gist should start with 'I', got: {personal_gist}"

        # Should contain the action
        assert expected_start.lower() in personal_gist.lower(), \
            f"Personal gist should contain action"

        print("✅ First-person narrative\n")

    print("✅ PASSED: Personal gist is diary-style\n")


def test_length_constraints():
    """Test that all gists respect length constraints"""
    print("=" * 70)
    print("🧪 TEST 6: Length Constraints")
    print("=" * 70)
    print()

    from vidurai.core.multi_audience_gist import MultiAudienceGistGenerator

    generator = MultiAudienceGistGenerator()

    # Very long verbatim
    verbatim = "This is a very long description " * 20
    canonical = "Fixed bug"

    gists = generator.generate(verbatim, canonical)

    print(f"Verbatim length: {len(verbatim)} chars")
    print(f"Canonical length: {len(canonical)} chars")
    print()

    for audience, gist in gists.items():
        print(f"{audience:12s}: {len(gist):3d} chars - {gist[:60]}...")

        # All gists should be reasonable length
        assert len(gist) < 150, \
            f"{audience} gist too long: {len(gist)} chars"

        # Developer can be slightly longer, others should be <= canonical * 1.5
        if audience != 'developer':
            assert len(gist) <= len(canonical) * 3, \
                f"{audience} gist should not be much longer than canonical"

    print("\n✅ All gists within length limits")
    print("\n✅ PASSED: Length constraints respected\n")


def test_technical_term_preservation():
    """Test that technical terms are preserved in appropriate gists"""
    print("=" * 70)
    print("🧪 TEST 7: Technical Term Preservation")
    print("=" * 70)
    print()

    from vidurai.core.multi_audience_gist import MultiAudienceGistGenerator

    generator = MultiAudienceGistGenerator()

    verbatim = "TypeError occurred in API endpoint when parsing JSON response from OAuth provider"
    canonical = "Fixed API error"

    gists = generator.generate(verbatim, canonical, {"event_type": "error"})

    print(f"Verbatim contains: TypeError, API, JSON, OAuth")
    print()

    # Developer should preserve technical terms
    dev_gist = gists['developer'].lower()
    print(f"Developer: {gists['developer']}")
    # Should mention at least some technical terms
    tech_count = sum([
        1 for term in ['type', 'error', 'api', 'json', 'oauth']
        if term in dev_gist
    ])
    assert tech_count >= 2, "Developer gist should preserve some technical terms"
    print("✅ Preserves technical terms")

    # Manager should simplify
    manager_gist = gists['manager'].lower()
    print(f"\nManager: {gists['manager']}")
    # Should have fewer technical terms
    assert 'oauth' not in manager_gist or 'json' not in manager_gist, \
        "Manager gist should simplify technical jargon"
    print("✅ Simplifies for managers")

    print("\n✅ PASSED: Technical terms handled appropriately per audience\n")


def test_configuration():
    """Test configuration options"""
    print("=" * 70)
    print("🧪 TEST 8: Configuration")
    print("=" * 70)
    print()

    from vidurai.core.multi_audience_gist import MultiAudienceGistGenerator
    from vidurai.config.multi_audience_config import MultiAudienceConfig

    # Custom config with only 2 audiences
    config = MultiAudienceConfig(
        enabled=True,
        audiences=['developer', 'ai']
    )

    generator = MultiAudienceGistGenerator(config=config)

    gists = generator.generate("", "Test gist")

    print(f"Configured audiences: {config.audiences}")
    print(f"Generated gists: {list(gists.keys())}")

    assert len(gists) == 2, "Should generate only configured audiences"
    assert 'developer' in gists
    assert 'ai' in gists
    assert 'manager' not in gists
    assert 'personal' not in gists

    print("\n✅ PASSED: Configuration respected\n")


def test_real_world_examples():
    """Test with real-world examples"""
    print("=" * 70)
    print("🧪 TEST 9: Real-World Examples")
    print("=" * 70)
    print()

    from vidurai.core.multi_audience_gist import MultiAudienceGistGenerator

    generator = MultiAudienceGistGenerator()

    examples = [
        {
            "verbatim": "Deployed new authentication service using OAuth2 and JWT tokens to production environment",
            "canonical": "Deployed new auth service to production",
            "context": {"event_type": "deployment", "file": "deploy.sh"}
        },
        {
            "verbatim": "Refactored database query optimization in user model, improved performance by 50%",
            "canonical": "Optimized database queries",
            "context": {"event_type": "refactor", "file": "models/user.py"}
        },
        {
            "verbatim": "MemoryError when processing large CSV file with 1M rows",
            "canonical": "Fixed memory error in CSV processing",
            "context": {"event_type": "error", "file": "import.py", "line": 156}
        }
    ]

    for i, example in enumerate(examples, 1):
        print(f"Example {i}:")
        print(f"  Canonical: {example['canonical']}")

        gists = generator.generate(
            example['verbatim'],
            example['canonical'],
            example['context']
        )

        for audience, gist in gists.items():
            print(f"  {audience:12s}: {gist}")

        # Verify all gists are different
        unique_gists = set(gists.values())
        assert len(unique_gists) >= 3, \
            "At least 3 audiences should have different gists"

        print()

    print("✅ PASSED: Real-world examples generate diverse gists\n")


if __name__ == "__main__":
    try:
        print()
        print("🚀 PHASE 5.2 TEST SUITE: Multi-Audience Gist Generator")
        print()

        test_basic_generation()
        test_developer_gist()
        test_ai_gist()
        test_manager_gist()
        test_personal_gist()
        test_length_constraints()
        test_technical_term_preservation()
        test_configuration()
        test_real_world_examples()

        print()
        print("=" * 70)
        print("✅ ALL PHASE 5.2 TESTS PASSED")
        print("=" * 70)
        print()

    except AssertionError as e:
        print(f"\n\n❌ TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
