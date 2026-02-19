"""
Console Utilities - Helper functions for safe console output.
Handles platform-specific encoding issues (e.g., Windows GBK vs Unicode).
"""

import sys
import os

def is_windows():
    return os.name == 'nt'

class Symbol:
    """
    Console symbols that adapt to the platform.
    Uses Unicode checks/crosses on Posix (Mac/Linux) and terminals that support it.
    Uses ASCII [OK]/[X] on Windows to avoid UnicodeEncodeError.
    """
    
    @property
    def OK(self) -> str:
        # Check standard out encoding if possible, but safe default for Windows is ASCII
        if is_windows():
            return "[OK]"
        return "✓"

    @property
    def FAIL(self) -> str:
        if is_windows():
            return "[ERROR]"
        return "✗"

    @property
    def WARN(self) -> str:
        if is_windows():
            return "[WARN]"
        return "!"
        
    @property
    def INFO(self) -> str:
        return "ℹ" if not is_windows() else "[INFO]"
        
    @property
    def ARROW(self) -> str:
        return "➜" if not is_windows() else "->"

    @property
    def TRASH(self) -> str:
        return "🗑️" if not is_windows() else "[DEL]"
    
    @property
    def RECYCLE(self) -> str:
        return "♻️" if not is_windows() else "[CLEAN]"


# Global instance
symbol = Symbol()
ICON = symbol  # Alias for backward compatibility

def print_header(title: str):
    """Print a major section header."""
    print("\n" + "="*80)
    print(f"  {title}")
    print("="*80)

def print_step(step: int, total: int, message: str):
    """Print a formatted step header."""
    header = f"[{step}/{total}] {message}"
    print(f"\n{header}")
    print("-" * len(header))

def print_separator():
    """Print a visual separator."""
    print("=" * 80)
