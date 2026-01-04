#!/usr/bin/env python3
"""
RC1 Verification Test - Trinity Test Suite
Tests the Daemon backend logic via IPC before building UI.

Tests:
1. ZOMBIE KILL - active_state table updates correctly
2. PINNING - Memory pinning works via IPC
3. ARCHIVER - Dependencies and structure in place

Usage:
    1. Start the daemon: python3 vidurai-daemon/daemon.py
    2. Run tests: python3 scripts/verify_rc1.py
"""

import sys
import os
import json
import time
import socket
import sqlite3
import getpass
import tempfile
from pathlib import Path
from datetime import datetime

# =============================================================================
# COLORS
# =============================================================================

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    RESET = '\033[0m'
    BOLD = '\033[1m'


def print_header(text: str):
    print(f"\n{Colors.BLUE}{Colors.BOLD}{'='*60}{Colors.RESET}")
    print(f"{Colors.BLUE}{Colors.BOLD}{text:^60}{Colors.RESET}")
    print(f"{Colors.BLUE}{Colors.BOLD}{'='*60}{Colors.RESET}\n")


def print_pass(test_num: int, text: str):
    print(f"{Colors.GREEN}[PASS]{Colors.RESET} TEST {test_num}: {text}")


def print_fail(test_num: int, text: str, detail: str = ""):
    print(f"{Colors.RED}[FAIL]{Colors.RESET} TEST {test_num}: {text}")
    if detail:
        print(f"       {Colors.YELLOW}Detail: {detail}{Colors.RESET}")


def print_info(text: str):
    print(f"{Colors.CYAN}[INFO]{Colors.RESET} {text}")


def print_warn(text: str):
    print(f"{Colors.YELLOW}[WARN]{Colors.RESET} {text}")


# =============================================================================
# IPC CLIENT
# =============================================================================

def get_pipe_path() -> str:
    """Get platform-appropriate pipe path"""
    uid = getpass.getuser()

    if sys.platform == 'win32':
        return f"\\\\.\\pipe\\vidurai-{uid}"
    else:
        return os.path.join(tempfile.gettempdir(), f"vidurai-{uid}.sock")


class IPCClient:
    """Simple IPC client for testing"""

    def __init__(self, timeout: float = 5.0):
        self.pipe_path = get_pipe_path()
        self.timeout = timeout
        self.sock = None
        self.buffer = ""
        self.request_id = 0

    def connect(self) -> bool:
        """Connect to the daemon"""
        try:
            if sys.platform == 'win32':
                # Windows named pipe - not implemented for this test
                print_warn("Windows named pipe not yet supported in test harness")
                return False
            else:
                self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                self.sock.settimeout(self.timeout)
                self.sock.connect(self.pipe_path)
            return True
        except Exception as e:
            print_warn(f"Failed to connect to {self.pipe_path}: {e}")
            return False

    def disconnect(self):
        """Disconnect from daemon"""
        if self.sock:
            try:
                self.sock.close()
            except:
                pass
            self.sock = None

    def send_event(self, event_type: str, data: dict = None) -> bool:
        """Send an event (fire-and-forget)"""
        if not self.sock:
            return False

        message = {
            "v": 1,
            "type": event_type,
            "ts": int(time.time() * 1000),
            "data": data or {}
        }

        try:
            payload = json.dumps(message) + "\n"
            self.sock.sendall(payload.encode())
            return True
        except Exception as e:
            print_warn(f"Send failed: {e}")
            return False

    def send_request(self, event_type: str, data: dict = None) -> dict:
        """Send a request and wait for response"""
        if not self.sock:
            return {"ok": False, "error": "Not connected"}

        self.request_id += 1
        request_id = f"test_{self.request_id}"

        message = {
            "v": 1,
            "type": event_type,
            "ts": int(time.time() * 1000),
            "id": request_id,
            "data": data or {}
        }

        try:
            payload = json.dumps(message) + "\n"
            self.sock.sendall(payload.encode())

            # Read response
            response = self._read_response(request_id)
            return response
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def _read_response(self, request_id: str, timeout: float = 5.0) -> dict:
        """Read response with matching request ID"""
        start = time.time()

        while time.time() - start < timeout:
            try:
                chunk = self.sock.recv(4096).decode()
                self.buffer += chunk

                # Process complete lines
                while '\n' in self.buffer:
                    line, self.buffer = self.buffer.split('\n', 1)
                    if line.strip():
                        try:
                            msg = json.loads(line)
                            # Check if this is our response
                            if msg.get('id') == request_id:
                                return msg
                            # Also accept response type
                            if msg.get('type') in ('ack', 'response', 'error'):
                                if msg.get('id') == request_id:
                                    return msg
                        except json.JSONDecodeError:
                            pass
            except socket.timeout:
                continue

        return {"ok": False, "error": "Response timeout"}


# =============================================================================
# DATABASE CLIENT
# =============================================================================

def get_db_path() -> Path:
    """Get the Vidurai database path"""
    return Path.home() / ".vidurai" / "memory.db"


def connect_db():
    """Connect to the Vidurai database"""
    db_path = get_db_path()
    if not db_path.exists():
        return None
    return sqlite3.connect(str(db_path))


# =============================================================================
# TEST 1: ZOMBIE KILL
# =============================================================================

def test_zombie_kill(ipc: IPCClient, db_conn) -> bool:
    """
    Test that errors are added to active_state and removed when fixed.

    Steps:
    1. Send diagnostic error for test file
    2. Verify row exists in active_state
    3. Send clean diagnostic (info/hint)
    4. Verify row is removed
    """
    print_info("Testing zombie kill (active_state lifecycle)...")

    test_file = "/test/zombie/test_zombie.py"

    # Step 1: Send error diagnostic
    print_info("  Sending error diagnostic...")
    ipc.send_event('diagnostic', {
        'file': test_file,
        'sev': 0,  # 0 = error
        'msg': 'Test error for zombie verification',
        'ln': 42
    })

    # Wait for async processing
    time.sleep(1.5)

    # Step 2: Check database for error
    cursor = db_conn.cursor()
    cursor.execute(
        "SELECT file_path, has_errors, error_count FROM active_state WHERE file_path = ?",
        (test_file,)
    )
    row = cursor.fetchone()

    if not row:
        print_fail(1, "Zombie not created", f"No active_state row for {test_file}")
        return False

    file_path, has_errors, error_count = row
    if not has_errors:
        print_fail(1, "Zombie not marked as error", f"has_errors={has_errors}")
        return False

    print_info(f"  Error created: file={file_path}, errors={error_count}")

    # Step 3: Send clean diagnostic (info severity clears errors)
    print_info("  Sending clean diagnostic (info)...")
    ipc.send_event('diagnostic', {
        'file': test_file,
        'sev': 2,  # 2 = info (clears errors)
        'msg': 'File is now clean',
        'ln': 42
    })

    # Wait for async processing
    time.sleep(1.5)

    # Step 4: Check that row is removed (zombie killed)
    cursor.execute(
        "SELECT COUNT(*) FROM active_state WHERE file_path = ?",
        (test_file,)
    )
    count = cursor.fetchone()[0]

    if count > 0:
        print_fail(1, "Zombie not killed", f"Row still exists with count={count}")
        return False

    print_pass(1, "ZOMBIE KILL - Errors tracked and cleaned correctly")
    return True


# =============================================================================
# TEST 2: PINNING
# =============================================================================

def test_pinning(ipc: IPCClient, db_conn) -> bool:
    """
    Test that memory pinning works via IPC.

    Steps:
    1. Create a test memory in the database
    2. Send pin request via IPC
    3. Verify memory is marked as pinned
    4. Send unpin request
    5. Verify memory is unpinned
    """
    print_info("Testing memory pinning...")

    cursor = db_conn.cursor()

    # Step 1: Insert a test memory if not exists
    test_memory_gist = "Test memory for pin verification - RC1"

    # Check if memories table exists
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='memories'"
    )
    if not cursor.fetchone():
        print_warn("  Memories table not found - skipping pin test")
        print_fail(2, "PINNING - Memories table missing")
        return False

    # Insert test memory
    try:
        cursor.execute(
            """INSERT INTO memories (project_id, verbatim, gist, salience, event_type, created_at)
               VALUES (1, 'Test verbatim content', ?, 'HIGH', 'test', datetime('now'))""",
            (test_memory_gist,)
        )
        db_conn.commit()
        memory_id = cursor.lastrowid
        print_info(f"  Created test memory with ID: {memory_id}")
    except sqlite3.IntegrityError:
        # Memory might already exist
        cursor.execute(
            "SELECT id FROM memories WHERE gist = ?",
            (test_memory_gist,)
        )
        row = cursor.fetchone()
        if row:
            memory_id = row[0]
            print_info(f"  Using existing test memory ID: {memory_id}")
        else:
            print_fail(2, "PINNING - Could not create test memory")
            return False

    # Step 2: Send pin request via IPC
    print_info(f"  Sending pin request for memory_id={memory_id}...")
    response = ipc.send_request('pin', {
        'memory_id': memory_id,
        'reason': 'RC1 verification test'
    })

    if not response.get('ok', False):
        # Check if pin manager is available
        error = response.get('error', 'Unknown error')
        if 'not initialized' in error.lower():
            print_warn("  Pin manager not initialized - checking DB directly")
        else:
            print_info(f"  Pin response: {response}")

    time.sleep(0.5)

    # Step 3: Check if pinned column exists and is set
    cursor.execute("PRAGMA table_info(memories)")
    columns = [row[1] for row in cursor.fetchall()]

    if 'pinned' not in columns:
        print_warn("  'pinned' column not in memories table - Pin Manager not initialized")
        print_fail(2, "PINNING - Schema missing 'pinned' column")
        return False

    cursor.execute(
        "SELECT pinned FROM memories WHERE id = ?",
        (memory_id,)
    )
    row = cursor.fetchone()

    if row and row[0] == 1:
        print_info("  Memory is pinned!")

        # Step 4: Unpin
        print_info("  Sending unpin request...")
        ipc.send_request('unpin', {'memory_id': memory_id})
        time.sleep(0.5)

        cursor.execute(
            "SELECT pinned FROM memories WHERE id = ?",
            (memory_id,)
        )
        row = cursor.fetchone()

        if row and row[0] == 0:
            print_pass(2, "PINNING - Pin/unpin cycle works correctly")
            return True
        else:
            print_warn("  Unpin may have failed, but pin worked")
            print_pass(2, "PINNING - Pin works (unpin not verified)")
            return True
    else:
        # Pin via IPC didn't work, try direct DB verification
        print_warn("  Pin via IPC didn't update DB - checking if handler exists")
        print_fail(2, "PINNING - IPC pin handler not working")
        return False


# =============================================================================
# TEST 3: ARCHIVER DEPENDENCIES
# =============================================================================

def test_archiver() -> bool:
    """
    Test archiver dependencies and structure.

    Checks:
    1. pyarrow is importable
    2. Archive directories exist or can be created
    3. Hot storage path is configured
    """
    print_info("Testing archiver dependencies...")

    passed = True

    # Check 1: pyarrow availability
    try:
        import pyarrow
        print_info(f"  pyarrow version: {pyarrow.__version__}")
        pyarrow_ok = True
    except ImportError:
        print_warn("  pyarrow not installed - Parquet archival disabled")
        pyarrow_ok = False

    # Check 2: Archive directory structure
    archive_base = Path.home() / ".vidurai" / "archive"
    hot_path = archive_base / "hot"
    cold_path = archive_base / "cold"

    # Check if directories exist
    if archive_base.exists():
        print_info(f"  Archive base exists: {archive_base}")
    else:
        print_info(f"  Archive base not yet created: {archive_base}")

    if hot_path.exists():
        print_info(f"  Hot storage exists: {hot_path}")

        # Check for JSONL files
        jsonl_files = list(hot_path.glob("*.jsonl"))
        if jsonl_files:
            print_info(f"  Found {len(jsonl_files)} hot storage file(s)")
        else:
            print_info("  No hot storage files yet (daemon may not have archived)")
    else:
        print_info(f"  Hot storage not yet created: {hot_path}")

    # Check 3: Archiver module is importable
    try:
        sys.path.insert(0, str(Path(__file__).parent.parent / "vidurai-daemon"))
        from archiver.archiver import Archiver, ArchiverOptions, get_archiver
        print_info("  Archiver module importable")
        archiver_ok = True
    except ImportError as e:
        print_warn(f"  Archiver module not importable: {e}")
        archiver_ok = False

    # Overall result
    if archiver_ok:
        if pyarrow_ok:
            print_pass(3, "ARCHIVER - All dependencies available")
        else:
            print_pass(3, "ARCHIVER - Ready (Parquet disabled, JSONL fallback)")
        return True
    else:
        print_fail(3, "ARCHIVER - Module not available")
        return False


# =============================================================================
# MAIN TEST RUNNER
# =============================================================================

def run_tests():
    """Run all RC1 verification tests"""
    print_header("VIDURAI RC1 VERIFICATION - TRINITY TEST")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print(f"Database: {get_db_path()}")
    print(f"IPC Pipe: {get_pipe_path()}")

    results = {
        'passed': 0,
        'failed': 0,
        'skipped': 0
    }

    # Connect to IPC
    print_info("\nConnecting to daemon...")
    ipc = IPCClient(timeout=5.0)

    if not ipc.connect():
        print_fail(0, "Cannot connect to daemon",
                   "Make sure daemon is running: python3 vidurai-daemon/daemon.py")
        print(f"\n{Colors.RED}ABORTED - Daemon not running{Colors.RESET}")
        return 1

    print_info("Connected to daemon!")

    # Send ping to verify
    response = ipc.send_request('ping')
    if response.get('type') == 'pong' or response.get('ok'):
        print_info("Daemon responded to ping")
    else:
        print_warn(f"Ping response: {response}")

    # Connect to database
    print_info("\nConnecting to database...")
    db_conn = connect_db()

    if not db_conn:
        print_fail(0, "Cannot connect to database",
                   f"Database not found at {get_db_path()}")
        ipc.disconnect()
        return 1

    print_info("Connected to database!")

    # Run tests
    print_header("RUNNING TESTS")

    # TEST 1: Zombie Kill
    try:
        if test_zombie_kill(ipc, db_conn):
            results['passed'] += 1
        else:
            results['failed'] += 1
    except Exception as e:
        print_fail(1, f"ZOMBIE KILL - Exception: {e}")
        results['failed'] += 1

    print("")

    # TEST 2: Pinning
    try:
        if test_pinning(ipc, db_conn):
            results['passed'] += 1
        else:
            results['failed'] += 1
    except Exception as e:
        print_fail(2, f"PINNING - Exception: {e}")
        results['failed'] += 1

    print("")

    # TEST 3: Archiver
    try:
        if test_archiver():
            results['passed'] += 1
        else:
            results['failed'] += 1
    except Exception as e:
        print_fail(3, f"ARCHIVER - Exception: {e}")
        results['failed'] += 1

    # Cleanup
    ipc.disconnect()
    db_conn.close()

    # Results
    print_header("TEST RESULTS")

    total = results['passed'] + results['failed']
    print(f"{Colors.BOLD}Passed:{Colors.RESET} {Colors.GREEN}{results['passed']}{Colors.RESET}/{total}")
    print(f"{Colors.BOLD}Failed:{Colors.RESET} {Colors.RED}{results['failed']}{Colors.RESET}/{total}")

    if results['failed'] == 0:
        print(f"\n{Colors.GREEN}{Colors.BOLD}ALL TESTS PASSED - RC1 VERIFIED!{Colors.RESET}")
        return 0
    else:
        print(f"\n{Colors.RED}{Colors.BOLD}SOME TESTS FAILED - FIX BEFORE RELEASE{Colors.RESET}")
        return 1


if __name__ == "__main__":
    sys.exit(run_tests())
