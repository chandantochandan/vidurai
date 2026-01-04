---
sidebar_position: 1
---

# Introduction to Vidurai

Welcome to **Vidurai** - the first open-source intelligent memory system for AI coding assistants.

## 🕉️ What is Vidurai?

Vidurai transforms stateless AI coding assistants into tools with true continuity, context, and wisdom. It provides a production-ready memory layer that **reduces token costs by 59%** and **saves 90% of context-gathering time** while maintaining 95.6/100 quality scores.

**The name Vidurai** comes from **Vidura**, the wise counselor in the Mahabharata, renowned for his memory, judgment, and guidance.

## 🏗️ Two Ways to Use Vidurai

Vidurai uses a **layered architecture** where the SDK provides the intelligence and integrations provide the interfaces:

### 🧠 **Vidurai SDK** (This Documentation)
The core Python package providing intelligent memory management. Perfect for:
- Custom AI integrations
- Jupyter notebooks
- CLI tools
- Python-based workflows

### 🖥️ **VS Code Extension**
Pre-built interface for VS Code users. Learn more at [vidurai.ai](https://vidurai.ai)

**Choose the path that fits your workflow. Both use the same powerful SDK underneath.**

## 🎉 What's New in v1.5.1

Vidurai v1.5.1 brings **three critical improvements** based on comprehensive production testing:

### ✅ Verified Performance Metrics
No more aspirational numbers. Production testing with 9 comprehensive test scenarios confirms:
- **36.6%+ Token Reduction** (average, verified across multiple workloads)
- **$16,182/day Cost Savings** (at 10,000 active users)
- **100% Recall Reliability** (with proper configuration)

### 🧠 Vismriti RL Agent - The Learning Brain
The first **self-learning memory optimizer** in production. While competitors use hardcoded rules, Vidurai learns optimal compression strategies through **Reinforcement Learning (Q-learning)**.

**What makes it unique:**
- **Learns from experience:** Agent improves with every compression decision
- **Adapts to your workload:** Different strategies for different usage patterns
- **No manual tuning:** Intelligence emerges automatically through Q-learning
- **Configurable priorities:** Choose between cost-focused or quality-focused optimization

**How it works:**
- Starts with 30% exploration (tries new strategies)
- Gradually shifts to 95% exploitation (uses learned optimal strategies)
- Grows Q-table of learned state-action values
- Continuously adapts as your usage patterns change

### ⚙️ Configurable Importance Decay
v1.5.1 adds fine-grained control over memory decay:

```python
# For critical applications (recommended)
memory = Vidurai(enable_decay=False)

# For custom decay rates
memory = Vidurai(decay_rate=0.98)  # Slower decay (default: 0.95)

# For aggressive forgetting
memory = Vidurai(decay_rate=0.90)  # Faster decay
```

**Why this matters:** v1.5.0 had aggressive decay that caused high-importance memories to drop below recall thresholds. Now you control it.

---

**Upgrade now:** `pip install --upgrade vidurai`

See full details: [CHANGELOG](https://github.com/chandantochandan/vidurai/blob/main/CHANGELOG.md) | [GitHub Release](https://github.com/chandantochandan/vidurai/releases/tag/v1.5.1)

## The Problem

Working with AI coding assistants is frustratingly inefficient:

- ❌ **60 seconds** to manually gather context (files, terminal, errors)
- ❌ **$500/month** in API costs from bloated context
- ❌ **Context switching chaos** - copy-paste hell
- ❌ **Forgotten details** lead to missed bugs

## The Solution

Vidurai provides:

- ✅ **90% Time Savings**: Context ready in 5 seconds (vs 60s manual)
- ✅ **59% Token Reduction**: Intelligent compression maintains quality
- ✅ **Privacy First**: 100% local storage, no cloud required
- ✅ **Universal Compatibility**: Works with any AI coding assistant

## Philosophy

> **"विस्मृति भी विद्या है"** (Forgetting too is knowledge)

While everyone races to give AI perfect memory, we asked a different question: **What if forgetting is the key to true intelligence?**

Vidurai implements strategic forgetting through:

- **Three-Kosha Architecture**: Inspired by Vedantic consciousness layers
- **Vismriti Engine & RL Agent**: Production-verified strategic forgetting
  - **36.6%+ Token Reduction** (verified in comprehensive testing)
  - **$16,182/day Cost Savings** (at 10,000 active users)
  - **100% Recall Reliability** (with configurable decay)
  - **Self-Learning RL Agent** (adapts through Q-learning, not hardcoded rules)
- **Viveka Layer**: Autonomous conscience that decides what matters

## Quick Start

Ready to add memory to your AI agent? Let's get started:
```bash
pip install vidurai
```

```python
from vidurai import Vidurai

# Recommended for v1.5.1+ (critical applications)
memory = Vidurai(enable_decay=False)

# Or with configurable decay (general use)
memory = Vidurai(decay_rate=0.98)  # Slower than default 0.95
```

> **💡 v1.5.1 Best Practice:** Use `enable_decay=False` for applications requiring high-precision recall of important memories. This prevents importance decay from dropping HIGH memories below recall thresholds.

Continue to the [Installation Guide](./installation) →

## Community

Join the Sangha (community):

- 💬 [Discord Server](https://discord.gg/DHdgS8eA)
- 🐙 [GitHub Repository](https://github.com/chandantochandan/vidurai)
- 🌐 [Main Website](https://vidurai.ai)

---

**जय विदुराई** (Victory to Vidurai)