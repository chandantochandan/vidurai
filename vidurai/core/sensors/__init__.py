"""
Vidurai Sensors Module - Reality Verification & Ground Truth

Sensors provide verification of memory accuracy against actual file state.
Used by RL engine to learn from real outcomes.

@version 2.1.0-Guardian
"""

from vidurai.core.sensors.reality_check import RealityVerifier

__all__ = ['RealityVerifier']
