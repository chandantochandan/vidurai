"""
Flight Recorder - Crash Forensics via Memory-Mapped Circular Buffer

Glass Box Protocol: Flight Recorder
- Critical daemon crashes MUST write to mmap circular buffer
- Do NOT use standard logging for catastrophic failures (it might die before writing)
- Flight recorder survives process crashes via mmap persistence

Architecture:
- Fixed-size circular buffer (default 1MB)
- Memory-mapped file for crash persistence
- Last 60 seconds of events preserved
- Binary format with struct packing

Usage:
    from vidurai.core.safety import record, dump_on_crash

    # Record events during operation
    record("Starting daemon...")
    record("Processing file: /path/to/file.py")

    # In crash handler
    try:
        risky_operation()
    except Exception as e:
        dump_on_crash(f"CRASH: {e}")
        raise

@version 2.1.0-Guardian
"""

import mmap
import struct
import time
import os
import sys
import atexit
import signal
from pathlib import Path
from typing import Optional, List, Tuple
from threading import Lock
from datetime import datetime

# =============================================================================
# CONSTANTS
# =============================================================================

# Buffer configuration
DEFAULT_BUFFER_SIZE = 1024 * 1024  # 1MB circular buffer
MAX_ENTRY_SIZE = 1024  # Max 1KB per entry
HEADER_SIZE = 16  # 4 bytes magic + 4 bytes write_pos + 4 bytes entry_count + 4 bytes reserved

# Magic number to identify valid flight recorder files
MAGIC_NUMBER = b'VIDR'  # Vidurai Flight Recorder

# Entry format: timestamp (8 bytes double) + length (2 bytes) + data (variable)
ENTRY_HEADER_FORMAT = '<dH'  # little-endian: double timestamp, unsigned short length
ENTRY_HEADER_SIZE = struct.calcsize(ENTRY_HEADER_FORMAT)


# =============================================================================
# FLIGHT RECORDER CLASS
# =============================================================================

class FlightRecorder:
    """
    Memory-mapped circular buffer for crash forensics.

    Glass Box Protocol:
    - Survives process crashes via mmap file persistence
    - Fixed-size buffer with wrap-around
    - Binary format for efficiency
    - Thread-safe via internal lock

    The Flight Recorder maintains the last ~60 seconds of events
    in a crash-persistent memory-mapped file.

    Usage:
        recorder = FlightRecorder()
        recorder.record("Daemon started")
        recorder.record("Processing request from client X")

        # On crash
        recorder.dump_on_crash("Fatal error occurred")

        # Later recovery
        entries = recorder.read_entries()
        for timestamp, message in entries:
            print(f"[{timestamp}] {message}")
    """

    def __init__(
        self,
        buffer_path: Optional[str] = None,
        buffer_size: int = DEFAULT_BUFFER_SIZE
    ):
        """
        Initialize Flight Recorder.

        Args:
            buffer_path: Path to mmap file (default: ~/.vidurai/flight_recorder.bin)
            buffer_size: Size of circular buffer in bytes (default: 1MB)
        """
        self.buffer_size = buffer_size
        self.data_size = buffer_size - HEADER_SIZE

        # Set up buffer path
        if buffer_path is None:
            vidurai_dir = Path.home() / '.vidurai'
            vidurai_dir.mkdir(parents=True, exist_ok=True)
            self.buffer_path = vidurai_dir / 'flight_recorder.bin'
        else:
            self.buffer_path = Path(buffer_path)
            self.buffer_path.parent.mkdir(parents=True, exist_ok=True)

        # Initialize mmap
        self._mmap: Optional[mmap.mmap] = None
        self._file = None
        self._lock = Lock()

        # Initialize buffer
        self._init_buffer()

        # Register crash handlers
        self._register_crash_handlers()

    def _init_buffer(self) -> None:
        """Initialize or open the memory-mapped buffer."""
        try:
            # Check if file exists and has correct size
            if self.buffer_path.exists():
                file_size = self.buffer_path.stat().st_size
                if file_size != self.buffer_size:
                    # Incorrect size - recreate
                    self.buffer_path.unlink()

            # Create file if needed
            if not self.buffer_path.exists():
                with open(self.buffer_path, 'wb') as f:
                    # Write magic number and initial header
                    header = MAGIC_NUMBER + struct.pack('<III', HEADER_SIZE, 0, 0)
                    f.write(header)
                    # Pad to full size
                    f.write(b'\x00' * (self.buffer_size - len(header)))

            # Open file for mmap
            self._file = open(self.buffer_path, 'r+b')
            self._mmap = mmap.mmap(
                self._file.fileno(),
                self.buffer_size,
                access=mmap.ACCESS_WRITE
            )

            # Validate magic number
            if self._mmap[:4] != MAGIC_NUMBER:
                # Invalid file - reset
                self._reset_buffer()

        except Exception as e:
            # Failed to init mmap - use fallback (no-op)
            print(f"FlightRecorder: Failed to init mmap: {e}", file=sys.stderr)
            self._mmap = None

    def _reset_buffer(self) -> None:
        """Reset buffer to initial state."""
        if self._mmap is None:
            return

        with self._lock:
            # Write header
            header = MAGIC_NUMBER + struct.pack('<III', HEADER_SIZE, 0, 0)
            self._mmap[:HEADER_SIZE] = header
            # Clear data area
            self._mmap[HEADER_SIZE:] = b'\x00' * self.data_size
            self._mmap.flush()

    def _get_write_position(self) -> int:
        """Get current write position from header."""
        if self._mmap is None:
            return HEADER_SIZE

        # Read write_pos from header (bytes 4-8)
        write_pos = struct.unpack('<I', self._mmap[4:8])[0]
        return write_pos if write_pos >= HEADER_SIZE else HEADER_SIZE

    def _set_write_position(self, pos: int) -> None:
        """Set write position in header."""
        if self._mmap is None:
            return

        self._mmap[4:8] = struct.pack('<I', pos)

    def _get_entry_count(self) -> int:
        """Get entry count from header."""
        if self._mmap is None:
            return 0

        return struct.unpack('<I', self._mmap[8:12])[0]

    def _increment_entry_count(self) -> None:
        """Increment entry count in header."""
        if self._mmap is None:
            return

        count = self._get_entry_count()
        self._mmap[8:12] = struct.pack('<I', count + 1)

    def record(self, message: str) -> bool:
        """
        Record an event to the flight recorder.

        Thread-safe, crash-persistent.

        Args:
            message: Event message to record (max 1KB)

        Returns:
            True if recorded successfully, False otherwise
        """
        if self._mmap is None:
            return False

        try:
            # Prepare entry
            timestamp = time.time()
            data = message.encode('utf-8')[:MAX_ENTRY_SIZE - ENTRY_HEADER_SIZE]
            entry_size = ENTRY_HEADER_SIZE + len(data)

            # Pack entry
            entry_header = struct.pack(ENTRY_HEADER_FORMAT, timestamp, len(data))
            entry = entry_header + data

            with self._lock:
                write_pos = self._get_write_position()

                # Check if entry fits in remaining space
                if write_pos + entry_size > self.buffer_size:
                    # Wrap around to beginning of data area
                    write_pos = HEADER_SIZE

                # Write entry
                self._mmap[write_pos:write_pos + entry_size] = entry

                # Update write position
                self._set_write_position(write_pos + entry_size)
                self._increment_entry_count()

                # Flush to disk
                self._mmap.flush()

            return True

        except Exception as e:
            # Silent failure - don't crash on logging failure
            print(f"FlightRecorder: record failed: {e}", file=sys.stderr)
            return False

    def dump_on_crash(self, crash_message: Optional[str] = None) -> str:
        """
        Dump flight recorder buffer to crash dump file.

        Called on catastrophic failures. Writes all recorded events
        to a timestamped crash dump file.

        Args:
            crash_message: Optional final message to record before dump

        Returns:
            Path to crash dump file
        """
        # Record final crash message
        if crash_message:
            self.record(f"CRASH: {crash_message}")

        # Generate dump filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        dump_path = self.buffer_path.parent / f'crash_dump_{timestamp}.bin'

        try:
            # Read all entries
            entries = self.read_entries()

            # Write to dump file
            with open(dump_path, 'w') as f:
                f.write(f"=== VIDURAI CRASH DUMP ===\n")
                f.write(f"Timestamp: {datetime.now().isoformat()}\n")
                f.write(f"Entries: {len(entries)}\n")
                f.write(f"{'=' * 40}\n\n")

                for ts, msg in entries:
                    dt = datetime.fromtimestamp(ts)
                    f.write(f"[{dt.strftime('%H:%M:%S.%f')[:-3]}] {msg}\n")

                if crash_message:
                    f.write(f"\n{'=' * 40}\n")
                    f.write(f"FINAL CRASH MESSAGE: {crash_message}\n")

            return str(dump_path)

        except Exception as e:
            # Last resort - print to stderr
            print(f"CRASH DUMP FAILED: {e}", file=sys.stderr)
            return ""

    def read_entries(self) -> List[Tuple[float, str]]:
        """
        Read all entries from the flight recorder.

        Returns:
            List of (timestamp, message) tuples, oldest first
        """
        if self._mmap is None:
            return []

        entries = []

        try:
            with self._lock:
                pos = HEADER_SIZE
                write_pos = self._get_write_position()

                # Read entries until we reach write position
                while pos < write_pos and pos < self.buffer_size - ENTRY_HEADER_SIZE:
                    # Read entry header
                    header_data = self._mmap[pos:pos + ENTRY_HEADER_SIZE]
                    if len(header_data) < ENTRY_HEADER_SIZE:
                        break

                    timestamp, length = struct.unpack(ENTRY_HEADER_FORMAT, header_data)

                    # Sanity check
                    if length == 0 or length > MAX_ENTRY_SIZE or timestamp == 0:
                        break

                    # Read entry data
                    data_start = pos + ENTRY_HEADER_SIZE
                    data_end = data_start + length

                    if data_end > self.buffer_size:
                        break

                    data = self._mmap[data_start:data_end]
                    try:
                        message = data.decode('utf-8')
                        entries.append((timestamp, message))
                    except UnicodeDecodeError:
                        pass

                    pos = data_end

        except Exception as e:
            print(f"FlightRecorder: read_entries failed: {e}", file=sys.stderr)

        return entries

    def _register_crash_handlers(self) -> None:
        """Register signal handlers for crash detection."""
        def signal_handler(signum, frame):
            self.dump_on_crash(f"Signal {signum} received")

        # Register for common crash signals
        try:
            signal.signal(signal.SIGTERM, signal_handler)
            if hasattr(signal, 'SIGINT'):
                signal.signal(signal.SIGINT, signal_handler)
        except Exception:
            pass  # Ignore if signals can't be registered

        # Register atexit handler
        atexit.register(self._cleanup)

    def _cleanup(self) -> None:
        """Cleanup on normal exit."""
        if self._mmap is not None:
            try:
                self._mmap.flush()
                self._mmap.close()
            except Exception:
                pass

        if self._file is not None:
            try:
                self._file.close()
            except Exception:
                pass

    def get_stats(self) -> dict:
        """Get flight recorder statistics."""
        if self._mmap is None:
            return {'status': 'disabled', 'entries': 0, 'size': 0}

        with self._lock:
            return {
                'status': 'active',
                'path': str(self.buffer_path),
                'entries': self._get_entry_count(),
                'write_position': self._get_write_position(),
                'buffer_size': self.buffer_size,
                'utilization_percent': round(
                    (self._get_write_position() - HEADER_SIZE) / self.data_size * 100, 2
                )
            }


# =============================================================================
# SINGLETON & CONVENIENCE FUNCTIONS
# =============================================================================

_default_recorder: Optional[FlightRecorder] = None


def get_recorder(
    buffer_path: Optional[str] = None,
    buffer_size: int = DEFAULT_BUFFER_SIZE
) -> FlightRecorder:
    """
    Get or create the default FlightRecorder instance.

    Args:
        buffer_path: Path to mmap file
        buffer_size: Buffer size in bytes

    Returns:
        FlightRecorder singleton instance
    """
    global _default_recorder
    if _default_recorder is None:
        _default_recorder = FlightRecorder(
            buffer_path=buffer_path,
            buffer_size=buffer_size
        )
    return _default_recorder


def record(message: str) -> bool:
    """
    Convenience function to record an event.

    Usage:
        from vidurai.core.safety import record
        record("Processing started for file X")
    """
    return get_recorder().record(message)


def dump_on_crash(crash_message: Optional[str] = None) -> str:
    """
    Convenience function to dump on crash.

    Usage:
        from vidurai.core.safety import dump_on_crash

        try:
            risky_operation()
        except Exception as e:
            dump_on_crash(str(e))
            raise
    """
    return get_recorder().dump_on_crash(crash_message)


def reset_recorder() -> None:
    """Reset the default recorder instance."""
    global _default_recorder
    if _default_recorder:
        _default_recorder._cleanup()
    _default_recorder = None
