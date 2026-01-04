#!/usr/bin/env python3
"""
The Victory Lap - Post-Refactor Command Smoke Test

Verifies that all CLI commands execute without import errors after
the lazy loading refactor. Each command is tested for:
1. Exit code 0 (or expected non-zero for certain commands)
2. No ImportError or NameError in output
3. Expected output patterns

Usage:
    python scripts/verify_commands.py

@version 2.2.0
"""

import subprocess
import sys
from pathlib import Path
from typing import Tuple, List


# Commands to test: (name, args, expected_exit_code, must_contain)
COMMANDS = [
    ("--version", ["--version"], 0, "2.2.0"),
    ("info", ["info"], 0, None),
    ("status", ["status"], 0, None),  # May show running or stopped
    ("logs --help", ["logs", "--help"], 0, "Show or follow"),
    ("hygiene --help", ["hygiene", "--help"], 0, None),  # Test help instead of dry-run
    ("audit --help", ["audit", "--help"], 0, None),
    ("recall --help", ["recall", "--help"], 0, "Search"),
    ("context --help", ["context", "--help"], 0, None),
    ("stats --help", ["stats", "--help"], 0, None),
    ("pin --help", ["pin", "--help"], 0, None),
    ("forgetting-stats", ["forgetting-stats"], 0, None),
]

# Error patterns that indicate import failures
ERROR_PATTERNS = [
    "ImportError",
    "ModuleNotFoundError",
    "NameError",
    "AttributeError: module",
    "cannot import name",
]


def run_command(args: List[str]) -> Tuple[int, str, str]:
    """Run a vidurai CLI command and return (exit_code, stdout, stderr)."""
    result = subprocess.run(
        [sys.executable, "-m", "vidurai.cli"] + args,
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent,
        timeout=30
    )
    return result.returncode, result.stdout, result.stderr


def check_for_errors(stdout: str, stderr: str) -> str:
    """Check output for import/name errors. Returns error message or empty string."""
    combined = stdout + stderr
    for pattern in ERROR_PATTERNS:
        if pattern in combined:
            return f"Found '{pattern}' in output"
    return ""


def main():
    """Run the command walkthrough."""
    print("=" * 60)
    print("THE VICTORY LAP - Post-Refactor Command Smoke Test")
    print("=" * 60)
    print(f"Testing {len(COMMANDS)} commands...")
    print("-" * 60)

    results = []
    passed = 0
    failed = 0

    for name, args, expected_exit, must_contain in COMMANDS:
        print(f"\n  Testing: vidurai {name}")

        try:
            exit_code, stdout, stderr = run_command(args)

            # Check for import errors
            error_msg = check_for_errors(stdout, stderr)
            if error_msg:
                status = "FAIL"
                reason = error_msg
                failed += 1
            elif exit_code != expected_exit:
                status = "FAIL"
                reason = f"Exit code {exit_code} (expected {expected_exit})"
                failed += 1
            elif must_contain and must_contain not in stdout:
                status = "FAIL"
                reason = f"Missing '{must_contain}' in output"
                failed += 1
            else:
                status = "PASS"
                reason = f"Exit {exit_code}"
                passed += 1

            results.append((name, status, reason))
            icon = "✅" if status == "PASS" else "❌"
            print(f"    {icon} {status}: {reason}")

            # Show first line of output for context
            first_line = (stdout or stderr).split('\n')[0][:60]
            if first_line:
                print(f"       Output: {first_line}")

        except subprocess.TimeoutExpired:
            status = "FAIL"
            reason = "Timeout (>30s)"
            failed += 1
            results.append((name, status, reason))
            print(f"    ❌ {status}: {reason}")

        except Exception as e:
            status = "FAIL"
            reason = str(e)[:50]
            failed += 1
            results.append((name, status, reason))
            print(f"    ❌ {status}: {reason}")

    # Summary
    print("\n" + "=" * 60)
    print("  SMOKE TEST RESULTS")
    print("=" * 60)

    for name, status, reason in results:
        icon = "✅" if status == "PASS" else "❌"
        print(f"  {icon} {name}: {reason}")

    print("-" * 60)
    print(f"  Passed: {passed}/{len(COMMANDS)}")
    print(f"  Failed: {failed}/{len(COMMANDS)}")
    print("=" * 60)

    if failed == 0:
        print("\n  🎉 ALL COMMANDS OPERATIONAL - LAZY LOADING VERIFIED 🎉\n")
        sys.exit(0)
    else:
        print("\n  ⚠️  Some commands failed. Check lazy loading imports.\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
