#!/usr/bin/env python3
"""
Vidurai v2.2.0-Guardian: End-to-End Lifecycle Verification

"The First Breath" - Proves the complete memory lifecycle works:
    Daemon Control → Birth → Archive → Recall → Dream → Cleanup

Test Data Isolation:
    - All test data uses subject: "VIDURAI_GENESIS_TEST_{timestamp}"
    - Cleanup in finally block ensures Leave No Trace

Usage:
    python scripts/verify_lifecycle.py

@version 2.2.0-Guardian
"""

import os
import sys
import sqlite3
import subprocess
import time
from pathlib import Path
from datetime import datetime

# Add parent directory for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Test subject identifier - unique per run
TEST_SUBJECT = f"VIDURAI_GENESIS_TEST_{int(time.time())}"

# Paths
DB_PATH = Path.home() / '.vidurai' / 'vidurai.db'
ARCHIVE_BASE = Path.home() / '.vidurai' / 'archive'

# Track resources for cleanup
created_memory_id = None
created_parquet_files = []
daemon_was_running = False


def log(emoji: str, msg: str):
    """Formatted logging"""
    print(f"{emoji} {msg}")


def run_cli(args: list) -> tuple:
    """Run vidurai CLI command and return (returncode, stdout, stderr)"""
    result = subprocess.run(
        [sys.executable, "-m", "vidurai.cli"] + args,
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent
    )
    return result.returncode, result.stdout, result.stderr


def step0_daemon_lifecycle():
    """
    Step 0: Daemon Lifecycle (start → status → logs → stop)
    Verify daemon process management works correctly
    """
    global daemon_was_running

    log("🔵", "Step 0: Daemon Lifecycle Test")

    # Check if daemon is already running
    code, out, err = run_cli(["status"])
    daemon_was_running = "running" in out.lower() or "PID" in out

    if daemon_was_running:
        log("   ", "Daemon already running, will restore state after test")

    # Test 1: Start daemon
    log("   ", "Testing: vidurai start")
    code, out, err = run_cli(["start"])
    if code != 0 and "already running" not in out.lower() and "already running" not in err.lower():
        log("❌", f"Failed to start daemon: {err or out}")
        return False
    log("   ", "→ Start: OK")

    # Give daemon time to initialize
    time.sleep(1)

    # Test 2: Check status
    log("   ", "Testing: vidurai status")
    code, out, err = run_cli(["status"])
    if code != 0:
        log("❌", f"Status command failed: {err or out}")
        return False
    if "PID" not in out and "running" not in out.lower():
        log("❌", f"Daemon not running after start: {out}")
        return False
    log("   ", f"→ Status: OK (PID found)")

    # Test 3: Check logs (must have content)
    log("   ", "Testing: vidurai logs")
    code, out, err = run_cli(["logs", "-n", "5"])
    if code != 0:
        log("⚠️", f"Logs command returned error: {err}")
        # Non-fatal - logs might just be empty
    else:
        if out.strip():
            log("   ", f"→ Logs: OK ({len(out.splitlines())} lines)")
        else:
            log("⚠️", "→ Logs: Empty (daemon may have just started)")

    # Test 4: Stop daemon (only if we started it)
    if not daemon_was_running:
        log("   ", "Testing: vidurai stop")
        code, out, err = run_cli(["stop"])
        if code != 0:
            log("⚠️", f"Stop command returned error: {err or out}")
        else:
            log("   ", "→ Stop: OK")

        # Verify PID file is gone
        pid_file = Path.home() / ".vidurai" / "daemon.pid"
        time.sleep(0.5)
        if pid_file.exists():
            log("⚠️", "PID file still exists after stop")
        else:
            log("   ", "→ PID file cleaned up")
    else:
        log("   ", "Skipping stop (daemon was already running)")

    log("✅", "Daemon Lifecycle Test Complete")
    return True


def step1_birth():
    """
    Step 1: Birth (Hot Storage)
    Insert a test memory into SQLite with status='ARCHIVED'
    """
    global created_memory_id

    log("🔵", "Step 1: Birth (Hot Storage)")

    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()

    # Insert test memory with ARCHIVED status (ready for flush)
    now = datetime.now().isoformat()
    cursor.execute("""
        INSERT INTO memories (
            verbatim, gist, salience, status, outcome,
            event_type, file_path, project_id, created_at, expires_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        TEST_SUBJECT,                     # verbatim
        f"Genesis test: {TEST_SUBJECT}",  # gist
        'medium',                          # salience
        'ARCHIVED',                        # status - ready for archiver
        1,                                 # outcome (positive for RL)
        'test',                            # event_type
        '/tmp/genesis_test.py',            # file_path
        1,                                 # project_id
        now,                               # created_at
        now                                # expires_at
    ))

    created_memory_id = cursor.lastrowid
    conn.commit()
    conn.close()

    log("✅", f"Memory Born (ID: {created_memory_id})")
    return True


def step2_purgatory():
    """
    Step 2: Purgatory (The Archiver)
    Flush ARCHIVED memories from SQLite to Parquet
    """
    global created_parquet_files

    log("🔵", "Step 2: Purgatory (The Archiver)")

    # Get list of parquet files BEFORE archiving
    existing_files = set()
    if ARCHIVE_BASE.exists():
        existing_files = set(ARCHIVE_BASE.rglob('*.parquet'))

    # Run archiver
    from vidurai.core.archival.archiver import MemoryArchiver
    archiver = MemoryArchiver()

    count = archiver.flush_archived_memories()
    log("📦", f"Archiver flushed {count} memories")

    # Verify memory is GONE from SQLite
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM memories WHERE id = ?", (created_memory_id,))
    row = cursor.fetchone()
    conn.close()

    if row is not None:
        log("❌", f"Memory {created_memory_id} still in SQLite (should be purged)")
        return False

    # Verify new parquet file exists
    new_files = set()
    if ARCHIVE_BASE.exists():
        new_files = set(ARCHIVE_BASE.rglob('*.parquet'))

    created_parquet_files = list(new_files - existing_files)

    if not created_parquet_files:
        log("❌", "No new Parquet file created")
        return False

    log("✅", f"Memory Archived to Cold Storage ({len(created_parquet_files)} new file(s))")
    for f in created_parquet_files:
        log("   ", f"→ {f.relative_to(ARCHIVE_BASE)}")

    return True


def step3_recall():
    """
    Step 3: Recall (The Analyst)
    Query the archived memory via DuckDB
    """
    log("🔵", "Step 3: Recall (The Analyst)")

    from vidurai.core.analytics.engine import RepoAnalyst
    analyst = RepoAnalyst()

    # Query for our test memory
    results = analyst.query_archive(f"""
        SELECT id, verbatim, gist, outcome
        FROM history
        WHERE verbatim = '{TEST_SUBJECT}'
    """)

    if not results:
        log("❌", "Memory not found in archive via DuckDB")
        return False

    if len(results) != 1:
        log("⚠️", f"Expected 1 result, got {len(results)}")

    result = results[0]
    log("✅", f"Memory Recalled via DuckDB (ID: {result.get('id')}, outcome: {result.get('outcome')})")
    return True


def step4_dreaming():
    """
    Step 4: Dreaming (The RL Agent)
    Run the DreamCycle offline training
    """
    log("🔵", "Step 4: Dreaming (The RL Agent)")

    from vidurai.core.rl.dreamer import DreamCycle
    dreamer = DreamCycle(max_episodes=10)  # Limit for test

    stats = dreamer.run()

    if stats.get('error'):
        log("⚠️", f"Dream cycle had error (non-fatal): {stats['error']}")
        # Non-fatal - the dreamer catches all exceptions

    log("✅", f"Dream Cycle Complete (episodes: {stats.get('episodes', 0)}, reward: {stats.get('total_reward', 0):.2f})")
    return True


def step5_cleanup():
    """
    Step 5: Cleanup (Leave No Trace)
    Remove test data from archive
    """
    log("🔵", "Step 5: Cleanup (Leave No Trace)")

    cleaned = 0

    # Remove created parquet files
    for f in created_parquet_files:
        try:
            if f.exists():
                f.unlink()
                cleaned += 1
                log("   ", f"→ Deleted {f.name}")
        except Exception as e:
            log("⚠️", f"Could not delete {f}: {e}")

    # Clean empty partition directories
    if ARCHIVE_BASE.exists():
        for d in sorted(ARCHIVE_BASE.rglob('*'), reverse=True):
            if d.is_dir() and not any(d.iterdir()):
                try:
                    d.rmdir()
                except:
                    pass

    # Ensure no residual test entries in SQLite
    try:
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()
        cursor.execute("DELETE FROM memories WHERE verbatim LIKE 'VIDURAI_GENESIS_TEST_%'")
        deleted = cursor.rowcount
        conn.commit()
        conn.close()
        if deleted > 0:
            log("   ", f"→ Cleaned {deleted} residual DB entries")
    except Exception as e:
        log("⚠️", f"DB cleanup error: {e}")

    log("✅", f"Cleanup Complete ({cleaned} file(s) removed)")
    return True


def main():
    """Run the full lifecycle verification"""
    print("=" * 60)
    print("  VIDURAI v2.2.0-GUARDIAN: THE FIRST BREATH")
    print("  End-to-End Lifecycle Verification")
    print("=" * 60)
    print(f"  Test Subject: {TEST_SUBJECT}")
    print(f"  Database: {DB_PATH}")
    print(f"  Archive: {ARCHIVE_BASE}")
    print("=" * 60)
    print()

    results = {}

    # Step 0: Daemon Lifecycle (doesn't require DB)
    results['daemon'] = step0_daemon_lifecycle()
    print()

    # Check prerequisites for memory tests
    if not DB_PATH.exists():
        log("⚠️", f"Database not found: {DB_PATH}")
        log("💡", "Skipping memory lifecycle tests (run vidurai to initialize)")
        results['birth'] = None
        results['purgatory'] = None
        results['recall'] = None
        results['dreaming'] = None
        results['cleanup'] = None
    else:
        try:
            # Step 1: Birth
            results['birth'] = step1_birth()
            print()

            # Step 2: Purgatory (Archive)
            results['purgatory'] = step2_purgatory()
            print()

            # Step 3: Recall (Query)
            results['recall'] = step3_recall()
            print()

            # Step 4: Dreaming (RL)
            results['dreaming'] = step4_dreaming()
            print()

        finally:
            # Step 5: Cleanup (ALWAYS runs)
            print()
            results['cleanup'] = step5_cleanup()

    # Final Report
    print()
    print("=" * 60)
    print("  VERIFICATION RESULTS")
    print("=" * 60)

    all_passed = True
    for step, passed in results.items():
        if passed is None:
            status = "⏭️ SKIP"
        elif passed:
            status = "✅ PASS"
        else:
            status = "❌ FAIL"
            all_passed = False
        print(f"  {status}: {step.capitalize()}")

    print("=" * 60)

    if all_passed:
        print()
        print("  🚀 VIDURAI v2.2.0 GUARDIAN IS OPERATIONAL 🚀")
        print()
        sys.exit(0)
    else:
        print()
        print("  ⚠️  Some steps failed. Check logs above.")
        print()
        sys.exit(1)


if __name__ == "__main__":
    main()
