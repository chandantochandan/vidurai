# Changelog

All notable changes to Vidurai will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.5.0] - 2025-11-01 - "The Learning Release"

### Added

- **Vismriti RL Agent**: Self-learning memory management brain
  - Q-learning policy with decaying epsilon (30% → 5% exploration)
  - Learns optimal compression timing from experience
  - Configurable reward profiles (balanced/cost-focused/quality-focused)
  - Persistent learning via file-based experience buffer (~/.vidurai/)
  - No hardcoded thresholds; optimal policies emerge from experience
  - Achieves 36%+ token reduction in testing

- **Semantic Compression Module**:
  - LLM-based intelligent compression of conversation history
  - Preserves key facts while reducing verbosity
  - Automatic compression window detection
  - Supports OpenAI and Anthropic models
  - Mock LLM client for testing without API costs
  - Extracts structured facts from compressed summaries

- **Core Data Structures**:
  - MemoryState, Action, Outcome for RL decision loop
  - CompressedMemory with compression metadata tracking
  - Experience buffer for persistent learning
  - Reward calculation with configurable profiles

### In Progress (Experimental)

- **Intelligent Decay Module**: The foundational code for our advanced decay system has been implemented and tested. This includes:
  - Entropy-based memory importance calculation
  - Semantic relevance scoring using embeddings
  - Access pattern tracking for reinforcement
  - Combined decay score formula
  
  **Note:** This module is not yet fully integrated with the Vismriti RL Agent and will be activated in a future release (v1.6.0). The code is present and tested, but the RL Agent does not yet use it for decay decisions.

### Changed

- Enhanced ViduraiMemory (koshas.py) with RL decision loop
- Agent now orchestrates memory management: observe → decide → act → learn
- Compression triggered intelligently by learned policy, not by fixed thresholds
- Working memory now managed by intelligent agent decisions

### Technical Details

- **Modules**: 4 new files, ~1,700 lines of production code
- **Tests**: Full test coverage for all modules (RL agent, compression, decay)
- **Storage**: File-based (JSONL) for experiences and Q-table persistence
- **Backward Compatible**: Fully compatible with the v0.3.0 API. Your existing code using ViduraiMemory will continue to work without changes, but will now benefit from the new intelligent background processing.
- **Dependencies**: Optional sentence-transformers for enhanced relevance scoring

### Performance

- **Token reduction**: 36.6% average in testing
- **Q-table learning**: 9 states learned after 15 messages
- **Experience persistence**: 20 experiences stored and reused across sessions
- **Epsilon decay**: Agent matures from 0.300 to 0.051 exploration over 1000 episodes
- **File storage**: Lightweight JSONL format (~/.vidurai/ directory)

### Philosophy

*"Intelligence emerges from experience, not from rules"*

- No hardcoded thresholds or static rules
- Policies adapt to each user's conversation patterns
- Continuous learning from outcomes and feedback
- Balances cost reduction vs. quality preservation
- Honors Vedantic principles: observe, discriminate, act with wisdom

### Migration Guide

No migration needed! If you're upgrading from v0.3.0:
```python
# Your existing code works unchanged
from vidurai.core import ViduraiMemory

memory = ViduraiMemory()  # Now with RL agent enabled by default
memory.remember("Your content")
memories = memory.recall()

# Optional: Configure RL agent behavior
from vidurai.core.rl_agent_v2 import RewardProfile

memory = ViduraiMemory(
    enable_rl_agent=True,  # Default
    reward_profile=RewardProfile.COST_FOCUSED  # Or BALANCED, QUALITY_FOCUSED
)
```

### Known Limitations

- RL agent requires ~100 episodes to develop stable policies
- Initial epsilon (0.3) means 30% exploration in early usage
- File-based storage not suitable for >100K experiences (consider SQLite for scale)
- Intelligent Decay module implemented but not yet integrated with RL agent

### Coming in v1.6.0

- Full integration of Intelligent Decay with RL Agent
- Consolidation module (memory merging during "sleep")
- Enhanced semantic similarity using embeddings
- Multi-user support with separate Q-tables
- Optional SQLite backend for large-scale deployments


---

*Vidurai: Intelligent memory for AI systems, inspired by ancient wisdom*