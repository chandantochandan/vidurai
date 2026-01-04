"""
Vidurai RL Module - Reinforcement Learning

DreamCycle: Offline batch training from archived memories.

Glass Box Protocol: Dream Cycle Safety
- Runs in background thread
- Must capture ALL exceptions (never kill main Daemon)

@version 2.1.0-Guardian
"""

from vidurai.core.rl.dreamer import DreamCycle

__all__ = ['DreamCycle']
