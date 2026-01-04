"""
Vidurai Safety Module - Crash Forensics & Recovery

Glass Box Protocol: Flight Recorder
- Critical daemon crashes MUST write to mmap circular buffer
- Standard logging might die before writing
- Flight recorder survives process crashes

@version 2.1.0-Guardian
"""

from vidurai.core.safety.flight_recorder import (
    FlightRecorder,
    get_recorder,
    record,
    dump_on_crash,
)

__all__ = [
    'FlightRecorder',
    'get_recorder',
    'record',
    'dump_on_crash',
]
