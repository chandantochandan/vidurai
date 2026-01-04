"""
Code Auditor - Static Safety Analysis

Glass Box Protocol: Safe Parsing (CRITICAL)
- ast.parse() crashes on syntax errors
- ALL ast.parse() calls MUST be wrapped in try/except
- On SyntaxError: return warning, do NOT crash daemon

The Auditor checks code for security risks before execution.
Part of The Shadow v2 pipeline: Auditor (Static) -> Build Runner (Dynamic)

@version 2.1.0-Guardian
"""

import ast
from typing import List, Set, Optional, Tuple
from dataclasses import dataclass
from loguru import logger


# =============================================================================
# DENYLIST CONFIGURATION
# =============================================================================

# Dangerous module imports
BANNED_IMPORTS: Set[str] = {
    'os',
    'subprocess',
    'shutil',
    'sys',
    'commands',      # Deprecated but dangerous
    'pty',           # Pseudo-terminal
    'socket',        # Network access
    'ctypes',        # C interface
    'pickle',        # Arbitrary code execution
    'marshal',       # Code object serialization
}

# Dangerous function calls (module.function format)
BANNED_CALLS: Set[str] = {
    'os.system',
    'os.popen',
    'os.spawn',
    'os.spawnl',
    'os.spawnle',
    'os.spawnlp',
    'os.spawnlpe',
    'os.spawnv',
    'os.spawnve',
    'os.spawnvp',
    'os.spawnvpe',
    'os.exec',
    'os.execl',
    'os.execle',
    'os.execlp',
    'os.execlpe',
    'os.execv',
    'os.execve',
    'os.execvp',
    'os.execvpe',
    'os.remove',
    'os.unlink',
    'os.rmdir',
    'subprocess.run',
    'subprocess.call',
    'subprocess.Popen',
    'subprocess.check_call',
    'subprocess.check_output',
    'shutil.rmtree',
    'shutil.move',
    'shutil.copy',
    'shutil.copy2',
}

# Dangerous builtins (called without module prefix)
BANNED_BUILTINS: Set[str] = {
    'eval',
    'exec',
    'compile',
    '__import__',
    'open',         # File operations (when combined with write)
    'input',        # Can be used for injection
}


# =============================================================================
# AST VISITOR
# =============================================================================

@dataclass
class SecurityWarning:
    """A security warning found during audit."""
    category: str      # 'import', 'call', 'builtin'
    risk_item: str     # The dangerous item found
    line_number: int   # Line in source code
    message: str       # Human-readable warning


class SafetyVisitor(ast.NodeVisitor):
    """
    AST visitor that checks for security risks.

    Collects warnings about:
    - Banned imports (os, subprocess, etc.)
    - Banned function calls (os.system, eval, etc.)
    - Dangerous patterns
    """

    def __init__(self):
        self.warnings: List[SecurityWarning] = []
        self.imported_modules: Set[str] = set()
        self.import_aliases: dict = {}  # alias -> real module name

    def visit_Import(self, node: ast.Import) -> None:
        """Check import statements: import os, import subprocess"""
        for alias in node.names:
            module_name = alias.name.split('.')[0]  # Get top-level module

            if module_name in BANNED_IMPORTS:
                self.warnings.append(SecurityWarning(
                    category='import',
                    risk_item=module_name,
                    line_number=node.lineno,
                    message=f"Security Risk: import of banned module '{module_name}'"
                ))

            # Track for later call checking
            self.imported_modules.add(module_name)
            if alias.asname:
                self.import_aliases[alias.asname] = module_name

        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        """Check from X import Y statements"""
        if node.module:
            module_name = node.module.split('.')[0]

            if module_name in BANNED_IMPORTS:
                self.warnings.append(SecurityWarning(
                    category='import',
                    risk_item=module_name,
                    line_number=node.lineno,
                    message=f"Security Risk: import from banned module '{module_name}'"
                ))

            self.imported_modules.add(module_name)

        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        """Check function calls for dangerous patterns"""
        call_name = self._get_call_name(node)

        if call_name:
            # Check banned calls (module.function)
            if call_name in BANNED_CALLS:
                self.warnings.append(SecurityWarning(
                    category='call',
                    risk_item=call_name,
                    line_number=node.lineno,
                    message=f"Security Risk: usage of banned call '{call_name}'"
                ))

            # Check banned builtins (eval, exec, etc.)
            if call_name in BANNED_BUILTINS:
                self.warnings.append(SecurityWarning(
                    category='builtin',
                    risk_item=call_name,
                    line_number=node.lineno,
                    message=f"Security Risk: usage of dangerous builtin '{call_name}'"
                ))

        self.generic_visit(node)

    def _get_call_name(self, node: ast.Call) -> Optional[str]:
        """Extract the full call name from a Call node."""
        try:
            if isinstance(node.func, ast.Name):
                # Simple call: eval(), exec()
                return node.func.id

            elif isinstance(node.func, ast.Attribute):
                # Attribute call: os.system(), subprocess.run()
                parts = []
                current = node.func

                while isinstance(current, ast.Attribute):
                    parts.append(current.attr)
                    current = current.value

                if isinstance(current, ast.Name):
                    parts.append(current.id)

                # Reverse to get module.function order
                parts.reverse()

                # Resolve aliases
                if parts[0] in self.import_aliases:
                    parts[0] = self.import_aliases[parts[0]]

                return '.'.join(parts)

        except Exception:
            pass

        return None


# =============================================================================
# CODE AUDITOR
# =============================================================================

class CodeAuditor:
    """
    Static code analyzer for security risks.

    Glass Box Protocol: Safe Parsing
    - All ast.parse() wrapped in try/except
    - SyntaxError returns warning, never crashes
    - Only Python supported (other languages skip)

    Usage:
        auditor = CodeAuditor()
        warnings = auditor.scan_safety(code_string)

        for warning in warnings:
            print(warning)  # "Security Risk: usage of os.system detected"
    """

    def __init__(self):
        """Initialize CodeAuditor."""
        logger.debug("CodeAuditor initialized")

    def scan_safety(
        self,
        code: str,
        language: str = "python"
    ) -> List[str]:
        """
        Scan code for security risks.

        Args:
            code: Source code to analyze
            language: Programming language ("python" supported, others skip)

        Returns:
            List of warning strings. Empty list = safe (or skipped).

        Glass Box Protocol:
        - Non-Python: Returns [] (skip, no warnings)
        - SyntaxError: Returns ["Syntax Error: ..."] (no crash)
        - Clean code: Returns [] (safe)
        """
        # Only Python supported for now
        if language.lower() != "python":
            logger.debug(f"Skipping audit for language: {language}")
            return []

        if not code or not code.strip():
            return []

        # CRITICAL: Safe Parse - wrap in try/except
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            # Glass Box: Return warning, do NOT crash
            error_msg = f"Syntax Error: {e.msg} (line {e.lineno})"
            logger.warning(f"CodeAuditor parse failed: {error_msg}")
            return [error_msg]
        except Exception as e:
            # Catch any other parsing errors
            error_msg = f"Parse Error: {str(e)}"
            logger.warning(f"CodeAuditor parse failed: {error_msg}")
            return [error_msg]

        # Run safety visitor
        visitor = SafetyVisitor()
        visitor.visit(tree)

        # Convert warnings to strings
        warning_strings = [w.message for w in visitor.warnings]

        if warning_strings:
            logger.info(f"CodeAuditor found {len(warning_strings)} security warnings")

        return warning_strings

    def scan_file(self, file_path: str) -> Tuple[List[str], str]:
        """
        Scan a file for security risks.

        Args:
            file_path: Path to file to scan

        Returns:
            Tuple of (warnings, language)
        """
        from pathlib import Path

        path = Path(file_path)

        if not path.exists():
            return [f"File not found: {file_path}"], "unknown"

        # Determine language from extension
        ext_to_lang = {
            '.py': 'python',
            '.pyw': 'python',
            '.js': 'javascript',
            '.ts': 'typescript',
            '.rb': 'ruby',
            '.go': 'go',
            '.rs': 'rust',
            '.java': 'java',
        }

        language = ext_to_lang.get(path.suffix.lower(), 'unknown')

        # Read file
        try:
            code = path.read_text(encoding='utf-8')
        except Exception as e:
            return [f"Read error: {e}"], language

        warnings = self.scan_safety(code, language)
        return warnings, language

    def get_denylist(self) -> dict:
        """
        Get the current denylist configuration.

        Useful for documentation and transparency.
        """
        return {
            'banned_imports': sorted(BANNED_IMPORTS),
            'banned_calls': sorted(BANNED_CALLS),
            'banned_builtins': sorted(BANNED_BUILTINS),
        }


# =============================================================================
# MODULE-LEVEL CONVENIENCE
# =============================================================================

_default_auditor: Optional[CodeAuditor] = None


def get_auditor() -> CodeAuditor:
    """Get or create the default CodeAuditor instance."""
    global _default_auditor
    if _default_auditor is None:
        _default_auditor = CodeAuditor()
    return _default_auditor


def scan_code(code: str, language: str = "python") -> List[str]:
    """
    Convenience function to scan code.

    Usage:
        from vidurai.core.verification import scan_code
        warnings = scan_code("import os; os.system('rm -rf /')")
    """
    return get_auditor().scan_safety(code, language)


# =============================================================================
# CLI TEST INTERFACE
# =============================================================================

def _test_cli():
    """
    Test function for manual verification.

    Usage:
        python -m vidurai.core.verification.auditor --test
    """
    import argparse

    parser = argparse.ArgumentParser(description="Code Auditor Test")
    parser.add_argument("--test", action="store_true", help="Run test cases")
    parser.add_argument("--file", type=str, help="Scan a specific file")
    parser.add_argument("--denylist", action="store_true", help="Show denylist")

    args = parser.parse_args()

    auditor = CodeAuditor()

    if args.denylist:
        denylist = auditor.get_denylist()
        print("\n=== Code Auditor Denylist ===\n")
        print("Banned Imports:")
        for item in denylist['banned_imports']:
            print(f"  - {item}")
        print("\nBanned Calls:")
        for item in denylist['banned_calls']:
            print(f"  - {item}")
        print("\nBanned Builtins:")
        for item in denylist['banned_builtins']:
            print(f"  - {item}")
        return

    if args.file:
        warnings, lang = auditor.scan_file(args.file)
        print(f"\nScanning: {args.file} (detected: {lang})")
        if warnings:
            print(f"Found {len(warnings)} warnings:")
            for w in warnings:
                print(f"  - {w}")
        else:
            print("No security issues found")
        return

    if args.test:
        print("\n=== Code Auditor Test Cases ===\n")

        test_cases = [
            ("Safe code", "def hello(): return 'world'"),
            ("Banned import", "import os"),
            ("Banned call", "import subprocess; subprocess.run(['ls'])"),
            ("Dangerous builtin", "eval('1+1')"),
            ("Syntax error", "def broken( return"),
            ("Complex safe", "import json\ndata = json.loads('{}')\nprint(data)"),
        ]

        for name, code in test_cases:
            warnings = auditor.scan_safety(code)
            status = "WARN" if warnings else "SAFE"
            print(f"[{status}] {name}")
            if warnings:
                for w in warnings:
                    print(f"       {w}")
            print()


if __name__ == "__main__":
    _test_cli()
