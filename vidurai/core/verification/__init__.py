"""
Vidurai Verification Module - Code Safety & Static Analysis

Glass Box Protocol: Safe Parsing
- All AST operations wrapped in try/except
- Syntax errors return warnings, never crash
- Only Python supported (other languages return empty/skip)

@version 2.1.0-Guardian
"""

from vidurai.core.verification.auditor import CodeAuditor

__all__ = ['CodeAuditor']
