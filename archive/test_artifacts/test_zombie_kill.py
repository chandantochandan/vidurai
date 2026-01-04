#!/usr/bin/env python3
"""
Zombie Killer Verification Test

Tests the State Projector's ability to:
1. Track errors when they occur
2. Clear errors when they're fixed (ZOMBIE KILL!)

Usage:
    python scripts/test_zombie_kill.py

Expected Output:
    [PASS] Error injected - row exists in active_state
    [PASS] Error cleared - row removed (ZOMBIE KILLED!)
"""

import sys
import asyncio
import importlib
from pathlib import Path
from datetime import datetime

# IMPORTANT: Force local paths BEFORE any vidurai imports
# This overrides the pip-installed version
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))  # For vidurai package
sys.path.insert(0, str(project_root / "vidurai-daemon"))  # For daemon modules

# Remove any cached vidurai modules
modules_to_remove = [k for k in sys.modules.keys() if 'vidurai' in k or 'storage' in k]
for mod in modules_to_remove:
    del sys.modules[mod]

# Now import with fresh paths
from vidurai.storage.database import MemoryDatabase
from intelligence.state_projector import StateProjector

# Verify we have the new methods
assert hasattr(MemoryDatabase, 'upsert_file_state'), \
    "ERROR: Using old vidurai version! Run: pip uninstall vidurai && pip install -e ."


class Colors:
    """ANSI color codes for terminal output"""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'


def print_header(text: str):
    print(f"\n{Colors.BLUE}{Colors.BOLD}{'='*60}{Colors.RESET}")
    print(f"{Colors.BLUE}{Colors.BOLD}{text:^60}{Colors.RESET}")
    print(f"{Colors.BLUE}{Colors.BOLD}{'='*60}{Colors.RESET}\n")


def print_pass(text: str):
    print(f"{Colors.GREEN}[PASS]{Colors.RESET} {text}")


def print_fail(text: str):
    print(f"{Colors.RED}[FAIL]{Colors.RESET} {text}")


def print_info(text: str):
    print(f"{Colors.YELLOW}[INFO]{Colors.RESET} {text}")


async def test_zombie_kill():
    """Main test function"""
    print_header("ZOMBIE KILLER VERIFICATION TEST")

    # Use test database
    test_db_path = Path("/tmp/vidurai_zombie_test.db")
    if test_db_path.exists():
        test_db_path.unlink()

    print_info(f"Using test database: {test_db_path}")

    # Initialize database and projector
    db = MemoryDatabase(test_db_path)
    projector = StateProjector(database=db, project_path="/test/project")
    await projector.start()

    test_file = "/test/project/src/broken.ts"
    passed = 0
    failed = 0

    # -------------------------------------------------------------------------
    # TEST 1: Inject Error Event
    # -------------------------------------------------------------------------
    print_info("Test 1: Injecting error event...")

    error_event = {
        'type': 'diagnostic',
        'file': test_file,
        'data': {
            'sev': 0,  # ERROR severity
            'msg': 'Type Error: Cannot read property "x" of undefined',
            'ln': 42,
            'src': 'typescript'
        }
    }

    await projector.update_state(error_event)

    # Give async worker time to process
    await asyncio.sleep(0.1)

    # Check database
    state = db.get_file_state(test_file)

    if state:
        print_pass(f"Error injected - row exists in active_state")
        print_info(f"  file_path: {state['file_path']}")
        print_info(f"  has_errors: {state['has_errors']}")
        print_info(f"  error_count: {state['error_count']}")
        print_info(f"  error_summary: {state['error_summary'][:50]}...")
        passed += 1
    else:
        print_fail("Error injection failed - no row in active_state")
        failed += 1

    # -------------------------------------------------------------------------
    # TEST 2: Inject Clean Event (Kill Zombie!)
    # -------------------------------------------------------------------------
    print("\n")
    print_info("Test 2: Injecting clean event (fixing the error)...")

    clean_event = {
        'type': 'diagnostic',
        'file': test_file,
        'data': {
            'sev': 2,  # INFO severity = clean
            'msg': '',  # No error message
            'ln': 0,
            'src': 'typescript'
        }
    }

    await projector.update_state(clean_event)

    # Give async worker time to process
    await asyncio.sleep(0.1)

    # Check database
    state = db.get_file_state(test_file)

    if state is None:
        print_pass(f"Error cleared - row removed (ZOMBIE KILLED!)")
        passed += 1
    else:
        print_fail(f"Zombie still alive - row exists: {state}")
        failed += 1

    # -------------------------------------------------------------------------
    # TEST 3: Summary Statistics
    # -------------------------------------------------------------------------
    print("\n")
    print_info("Test 3: Checking summary statistics...")

    summary = db.get_active_state_summary("/test/project")
    print_info(f"  total_files: {summary['total_files']}")
    print_info(f"  files_with_errors: {summary['files_with_errors']}")
    print_info(f"  total_errors: {summary['total_errors']}")
    print_info(f"  total_warnings: {summary['total_warnings']}")

    if summary['files_with_errors'] == 0:
        print_pass("No zombie files remaining in summary")
        passed += 1
    else:
        print_fail(f"Summary shows {summary['files_with_errors']} files with errors")
        failed += 1

    # -------------------------------------------------------------------------
    # TEST 4: Projector Stats
    # -------------------------------------------------------------------------
    print("\n")
    print_info("Test 4: Checking projector statistics...")

    stats = projector.get_stats()
    print_info(f"  events_processed: {stats.events_processed}")
    print_info(f"  errors_upserted: {stats.errors_upserted}")
    print_info(f"  errors_cleared: {stats.errors_cleared}")
    print_info(f"  async_errors: {stats.async_errors}")

    if stats.errors_upserted > 0 and stats.errors_cleared > 0:
        print_pass("Both upsert and clear operations recorded")
        passed += 1
    else:
        print_fail("Stats don't reflect both operations")
        failed += 1

    # -------------------------------------------------------------------------
    # Cleanup
    # -------------------------------------------------------------------------
    await projector.stop()
    db.close()

    # Clean up test database
    if test_db_path.exists():
        test_db_path.unlink()

    # -------------------------------------------------------------------------
    # Results
    # -------------------------------------------------------------------------
    print_header("TEST RESULTS")

    total = passed + failed
    print(f"{Colors.BOLD}Passed:{Colors.RESET} {Colors.GREEN}{passed}{Colors.RESET}/{total}")
    print(f"{Colors.BOLD}Failed:{Colors.RESET} {Colors.RED}{failed}{Colors.RESET}/{total}")

    if failed == 0:
        print(f"\n{Colors.GREEN}{Colors.BOLD}ALL TESTS PASSED - ZOMBIE KILLER IS OPERATIONAL!{Colors.RESET}")
        return 0
    else:
        print(f"\n{Colors.RED}{Colors.BOLD}SOME TESTS FAILED{Colors.RESET}")
        return 1


async def test_multiple_files():
    """Test with multiple files"""
    print_header("MULTI-FILE ZOMBIE TEST")

    test_db_path = Path("/tmp/vidurai_zombie_multi.db")
    if test_db_path.exists():
        test_db_path.unlink()

    db = MemoryDatabase(test_db_path)
    projector = StateProjector(database=db, project_path="/test/project")
    await projector.start()

    # Create errors in multiple files
    files = [
        "/test/project/src/auth.ts",
        "/test/project/src/api.ts",
        "/test/project/src/utils.ts",
    ]

    print_info("Creating errors in 3 files...")
    for f in files:
        await projector.update_state({
            'type': 'diagnostic',
            'file': f,
            'data': {'sev': 0, 'msg': f'Error in {Path(f).name}'}
        })

    await asyncio.sleep(0.1)

    errors = db.get_files_with_errors("/test/project")
    print_info(f"Files with errors: {len(errors)}")

    # Fix one file
    print_info("Fixing auth.ts...")
    await projector.update_state({
        'type': 'diagnostic',
        'file': files[0],
        'data': {'sev': 2, 'msg': ''}  # Clean
    })

    await asyncio.sleep(0.1)

    errors = db.get_files_with_errors("/test/project")
    print_info(f"Files with errors after fix: {len(errors)}")

    if len(errors) == 2:
        print_pass("Correct number of files after partial fix")
    else:
        print_fail(f"Expected 2 files, got {len(errors)}")

    # Fix remaining files
    print_info("Fixing remaining files...")
    for f in files[1:]:
        await projector.update_state({
            'type': 'diagnostic',
            'file': f,
            'data': {'sev': 2, 'msg': ''}
        })

    await asyncio.sleep(0.1)

    errors = db.get_files_with_errors("/test/project")
    print_info(f"Files with errors after all fixes: {len(errors)}")

    if len(errors) == 0:
        print_pass("All zombies killed!")
    else:
        print_fail(f"Still have {len(errors)} zombie files")

    # Cleanup
    await projector.stop()
    db.close()
    if test_db_path.exists():
        test_db_path.unlink()


if __name__ == "__main__":
    print(f"\n{Colors.BOLD}Vidurai State Projector - Zombie Killer Test{Colors.RESET}")
    print(f"Timestamp: {datetime.now().isoformat()}\n")

    # Run main test
    result = asyncio.run(test_zombie_kill())

    # Run multi-file test
    print("\n")
    asyncio.run(test_multiple_files())

    sys.exit(result)
