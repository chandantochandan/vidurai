"""
Verify Bug #3 Fix: Reward Profile Behavior
Test that COST_FOCUSED compresses MORE than QUALITY_FOCUSED
"""

from vidurai.core.rl_agent_v2 import Outcome, RewardProfile


def test_reward_profiles():
    """
    Test that reward profiles produce correct behavior:
    - COST_FOCUSED should reward aggressive compression more
    - QUALITY_FOCUSED should penalize aggressive compression more
    """
    print("=" * 70)
    print("BUG #3 VERIFICATION: Reward Profile Behavior")
    print("=" * 70)

    # Simulate AGGRESSIVE compression outcome
    aggressive_outcome = Outcome(
        action=None,
        tokens_saved=200,         # High token savings
        retrieval_accuracy=1.0,   # Perfect accuracy
        information_loss=0.15,    # Higher information loss (aggressive)
        user_satisfaction=0.8
    )

    # Simulate CONSERVATIVE compression outcome
    conservative_outcome = Outcome(
        action=None,
        tokens_saved=100,         # Lower token savings
        retrieval_accuracy=1.0,   # Perfect accuracy
        information_loss=0.02,    # Lower information loss (conservative)
        user_satisfaction=0.8
    )

    print("\n📊 Scenario 1: AGGRESSIVE Compression")
    print(f"  Tokens saved: {aggressive_outcome.tokens_saved}")
    print(f"  Information loss: {aggressive_outcome.information_loss}")

    print("\n📊 Scenario 2: CONSERVATIVE Compression")
    print(f"  Tokens saved: {conservative_outcome.tokens_saved}")
    print(f"  Information loss: {conservative_outcome.information_loss}")

    # Calculate rewards for each profile
    print("\n" + "=" * 70)
    print("REWARD CALCULATIONS")
    print("=" * 70)

    profiles = [
        RewardProfile.BALANCED,
        RewardProfile.COST_FOCUSED,
        RewardProfile.QUALITY_FOCUSED
    ]

    results = {}

    for profile in profiles:
        aggressive_reward = aggressive_outcome.calculate_reward(profile)
        conservative_reward = conservative_outcome.calculate_reward(profile)

        print(f"\n{profile.value.upper()}:")
        print(f"  Aggressive compression reward: {aggressive_reward:.2f}")
        print(f"  Conservative compression reward: {conservative_reward:.2f}")
        print(f"  Preference: {'AGGRESSIVE' if aggressive_reward > conservative_reward else 'CONSERVATIVE'}")
        print(f"  Gap: {abs(aggressive_reward - conservative_reward):.2f}")

        results[profile] = {
            'aggressive': aggressive_reward,
            'conservative': conservative_reward,
            'prefers_aggressive': aggressive_reward > conservative_reward
        }

    # Verify expected behavior
    print("\n" + "=" * 70)
    print("VERIFICATION")
    print("=" * 70)

    success = True

    # Test 1: COST_FOCUSED should prefer AGGRESSIVE compression
    if results[RewardProfile.COST_FOCUSED]['prefers_aggressive']:
        print("\n✅ COST_FOCUSED correctly prefers AGGRESSIVE compression")
        print("   (Higher token savings outweigh information loss penalty)")
    else:
        print("\n❌ COST_FOCUSED incorrectly prefers CONSERVATIVE compression")
        print("   (Should prioritize token savings over quality)")
        success = False

    # Test 2: QUALITY_FOCUSED should prefer CONSERVATIVE compression
    if not results[RewardProfile.QUALITY_FOCUSED]['prefers_aggressive']:
        print("\n✅ QUALITY_FOCUSED correctly prefers CONSERVATIVE compression")
        print("   (Information loss penalty outweighs token savings)")
    else:
        print("\n❌ QUALITY_FOCUSED incorrectly prefers AGGRESSIVE compression")
        print("   (Should prioritize quality over token savings)")
        success = False

    # Test 3: Gap should be larger for focused profiles than balanced
    cost_gap = abs(results[RewardProfile.COST_FOCUSED]['aggressive'] -
                   results[RewardProfile.COST_FOCUSED]['conservative'])
    quality_gap = abs(results[RewardProfile.QUALITY_FOCUSED]['aggressive'] -
                      results[RewardProfile.QUALITY_FOCUSED]['conservative'])
    balanced_gap = abs(results[RewardProfile.BALANCED]['aggressive'] -
                       results[RewardProfile.BALANCED]['conservative'])

    if cost_gap > balanced_gap and quality_gap > balanced_gap:
        print("\n✅ Focused profiles have stronger preferences than BALANCED")
        print(f"   COST_FOCUSED gap: {cost_gap:.2f}")
        print(f"   QUALITY_FOCUSED gap: {quality_gap:.2f}")
        print(f"   BALANCED gap: {balanced_gap:.2f}")
    else:
        print("\n⚠️  Focused profiles may not have strong enough preferences")
        success = False

    return success


if __name__ == "__main__":
    result = test_reward_profiles()

    print("\n" + "=" * 70)
    if result:
        print("✅ BUG #3 VERIFICATION PASSED")
        print("   Reward profiles now behave correctly!")
    else:
        print("❌ BUG #3 VERIFICATION FAILED")
        print("   Reward profiles still have issues")
    print("=" * 70)
