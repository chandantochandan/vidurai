#!/usr/bin/env python3
"""
Context Oracle Verification Test

Tests the Oracle API end-to-end:
1. Inject errors into active_state
2. Query Oracle for context
3. Verify formatted output for different audiences
4. Clear errors and verify "clean" response

Usage:
    python scripts/test_oracle.py
"""

import sys
from pathlib import Path
from datetime import datetime

# Force local paths
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "vidurai-daemon"))

# Clean cached modules
modules_to_remove = [k for k in sys.modules.keys() if 'vidurai' in k or 'storage' in k]
for mod in modules_to_remove:
    del sys.modules[mod]

from vidurai.storage.database import MemoryDatabase
from vidurai.core.oracle import Oracle


class Colors:
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


def test_oracle():
    """Test the Oracle API"""
    print_header("CONTEXT ORACLE VERIFICATION TEST")

    # Use test database
    test_db_path = Path("/tmp/vidurai_oracle_test.db")
    if test_db_path.exists():
        test_db_path.unlink()

    print_info(f"Using test database: {test_db_path}")

    db = MemoryDatabase(test_db_path)
    oracle = Oracle(database=db, project_path="/test/project")

    passed = 0
    failed = 0

    # -------------------------------------------------------------------------
    # TEST 1: Empty state returns clean response
    # -------------------------------------------------------------------------
    print_info("Test 1: Empty state (clean project)")

    ctx = oracle.get_context('developer')
    print_info(f"  Response: {ctx.formatted[:60]}...")

    if "All clear" in ctx.formatted and ctx.files_with_errors == 0:
        print_pass("Empty state returns 'All clear' message")
        passed += 1
    else:
        print_fail(f"Expected 'All clear', got: {ctx.formatted}")
        failed += 1

    # -------------------------------------------------------------------------
    # TEST 2: Inject errors and verify developer format
    # -------------------------------------------------------------------------
    print("\n")
    print_info("Test 2: Inject errors and check developer format")

    # Add some file states with errors
    db.upsert_file_state(
        file_path="/test/project/src/auth.ts",
        project_path="/test/project",
        has_errors=True,
        error_count=2,
        warning_count=1,
        error_summary="Type 'string' is not assignable to type 'number'"
    )

    db.upsert_file_state(
        file_path="/test/project/src/api.ts",
        project_path="/test/project",
        has_errors=True,
        error_count=1,
        warning_count=0,
        error_summary="Cannot find module '@/utils'"
    )

    db.upsert_file_state(
        file_path="/test/project/src/utils.ts",
        project_path="/test/project",
        has_errors=False,
        error_count=0,
        warning_count=2,
        error_summary="'foo' is declared but never used"
    )

    ctx = oracle.get_context('developer')

    print_info("Developer format:")
    print("  " + ctx.formatted.replace("\n", "\n  "))

    if ctx.files_with_errors >= 2 and "auth.ts" in ctx.formatted:
        print_pass("Developer format shows files with errors")
        passed += 1
    else:
        print_fail(f"Expected files in output, got {ctx.files_with_errors} files")
        failed += 1

    # -------------------------------------------------------------------------
    # TEST 3: AI format (XML)
    # -------------------------------------------------------------------------
    print("\n")
    print_info("Test 3: AI format (XML structure)")

    ctx = oracle.get_context('ai')

    print_info("AI format (first 400 chars):")
    print("  " + ctx.formatted[:400].replace("\n", "\n  ") + "...")

    if "<context" in ctx.formatted and "<errors>" in ctx.formatted:
        print_pass("AI format returns valid XML structure")
        passed += 1
    else:
        print_fail("Missing XML tags in AI format")
        failed += 1

    # -------------------------------------------------------------------------
    # TEST 4: Manager format
    # -------------------------------------------------------------------------
    print("\n")
    print_info("Test 4: Manager format (high-level summary)")

    ctx = oracle.get_context('manager')

    print_info("Manager format:")
    print("  " + ctx.formatted.replace("\n", "\n  "))

    if "Code Health Report" in ctx.formatted:
        print_pass("Manager format shows health report")
        passed += 1
    else:
        print_fail("Missing health report header")
        failed += 1

    # -------------------------------------------------------------------------
    # TEST 5: Clear errors and verify clean state
    # -------------------------------------------------------------------------
    print("\n")
    print_info("Test 5: Clear all errors and verify clean state")

    db.clear_file_state("/test/project/src/auth.ts")
    db.clear_file_state("/test/project/src/api.ts")
    db.clear_file_state("/test/project/src/utils.ts")

    ctx = oracle.get_context('developer')

    if "All clear" in ctx.formatted:
        print_pass("After clearing, state shows 'All clear'")
        passed += 1
    else:
        print_fail(f"Expected 'All clear', got: {ctx.formatted}")
        failed += 1

    # -------------------------------------------------------------------------
    # TEST 6: get_summary API
    # -------------------------------------------------------------------------
    print("\n")
    print_info("Test 6: Quick summary API")

    # Add one error back
    db.upsert_file_state(
        file_path="/test/project/src/index.ts",
        project_path="/test/project",
        has_errors=True,
        error_count=3,
        warning_count=1,
        error_summary="Module not found"
    )

    summary = oracle.get_summary("/test/project")

    print_info(f"  Summary: {summary}")

    if summary['files_with_errors'] == 1 and summary['total_errors'] == 3:
        print_pass("Summary API returns correct counts")
        passed += 1
    else:
        print_fail(f"Summary counts incorrect: {summary}")
        failed += 1

    # -------------------------------------------------------------------------
    # Cleanup
    # -------------------------------------------------------------------------
    db.close()
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
        print(f"\n{Colors.GREEN}{Colors.BOLD}ALL TESTS PASSED - ORACLE IS OPERATIONAL!{Colors.RESET}")
        return 0
    else:
        print(f"\n{Colors.RED}{Colors.BOLD}SOME TESTS FAILED{Colors.RESET}")
        return 1


def test_simulated_ipc():
    """Simulate the IPC request/response flow"""
    print_header("SIMULATED IPC FLOW TEST")

    test_db_path = Path("/tmp/vidurai_oracle_ipc.db")
    if test_db_path.exists():
        test_db_path.unlink()

    db = MemoryDatabase(test_db_path)

    # Simulate: VS Code sends request
    print_info("Simulating VS Code request: get_context (audience=ai)")

    # Add some state
    db.upsert_file_state(
        file_path="/project/src/app.tsx",
        project_path="/project",
        has_errors=True,
        error_count=1,
        error_summary="JSX element type does not have call signatures"
    )

    # Simulate daemon handler
    from vidurai.core.oracle import get_oracle
    oracle = get_oracle(database=db)

    # This is what the daemon would do
    ctx = oracle.get_context(
        audience='ai',
        project_path='/project',
        include_raw=False
    )

    # Build response (like daemon.py does)
    response = {
        'context': ctx.formatted,
        'files_with_errors': ctx.files_with_errors,
        'total_errors': ctx.total_errors,
        'total_warnings': ctx.total_warnings,
        'audience': ctx.audience,
        'timestamp': ctx.timestamp,
    }

    print_info("Response data:")
    print(f"  files_with_errors: {response['files_with_errors']}")
    print(f"  total_errors: {response['total_errors']}")
    print(f"  audience: {response['audience']}")
    print(f"  context preview: {response['context'][:200]}...")

    if response['files_with_errors'] == 1 and '<context' in response['context']:
        print_pass("IPC simulation successful - response matches expected format")
    else:
        print_fail("IPC simulation failed")

    # Cleanup
    db.close()
    if test_db_path.exists():
        test_db_path.unlink()


if __name__ == "__main__":
    print(f"\n{Colors.BOLD}Vidurai Context Oracle Test{Colors.RESET}")
    print(f"Timestamp: {datetime.now().isoformat()}\n")

    result = test_oracle()

    print("\n")
    test_simulated_ipc()

    sys.exit(result)
