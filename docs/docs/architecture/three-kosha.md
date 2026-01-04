---
sidebar_position: 1
---

# Three-Kosha Architecture

Inspired by Vedantic consciousness layers, Vidurai implements a three-layer memory system.

## Annamaya Kosha (Physical Sheath)
- **Purpose:** Working memory for immediate context
- **Capacity:** Last 10 messages
- **Retention:** TTL-based eviction
- **Use case:** High-speed, volatile storage

## Manomaya Kosha (Mental Sheath)
- **Purpose:** Episodic memory with intelligent decay
- **Capacity:** 50-1000 memories (configurable)
- **Retention:** Importance-based with decay
- **Use case:** Active conversation history

## Vijnanamaya Kosha (Wisdom Sheath)
- **Purpose:** Archival memory for permanent wisdom
- **Capacity:** Unlimited
- **Retention:** Never forgotten
- **Use case:** Core preferences, foundational knowledge

See [Configuration](../configuration.md) for setup details.
