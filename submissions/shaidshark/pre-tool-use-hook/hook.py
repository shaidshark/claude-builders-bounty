#!/usr/bin/env python3
"""
Pre-tool-use hook for Claude Code that blocks destructive bash commands.
Blocks: rm -rf, DROP TABLE, git push --force, TRUNCATE, DELETE FROM without WHERE.
Override: ALLOW_DESTRUCTIVE=1
"""

import os
import re
import sys
from datetime import datetime, timezone

BLOCKED_PATTERNS = [
    (r"\brm\s+.*-.*[rR].*f\b|\brm\s+.*-.*f.*[rR]\b", "CRITICAL", "rm -rf detected"),
    (r"\bgit\s+push\s+.*--force\b|\bgit\s+push\s+.*-f\b", "HIGH", "git push --force detected"),
    (r"\bDROP\s+TABLE\b", "CRITICAL", "DROP TABLE detected"),
    (r"\bTRUNCATE\s+\w+", "HIGH", "TRUNCATE detected"),
    (r"\bDELETE\s+FROM\b(?!.+\bWHERE\b)", "CRITICAL", "DELETE FROM without WHERE detected"),
]

LOG_FILE = os.path.expanduser("~/.claude/hooks/blocked.log")


def log_blocked(command: str, risk: str, reason: str) -> None:
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{ts}] BLOCKED (risk={risk}): {reason} | command: {command}\n")


def main() -> int:
    if os.environ.get("ALLOW_DESTRUCTIVE") == "1":
        return 0

    # Read command from stdin (Claude Code hooks receive tool input via stdin)
    command = ""
    try:
        command = sys.stdin.read().strip()
    except Exception:
        pass

    # Also check TOOL_INPUT env var (alternative hook interface)
    if not command:
        command = os.environ.get("TOOL_INPUT", "")

    if not command:
        return 0

    for pattern, risk, reason in BLOCKED_PATTERNS:
        if re.search(pattern, command, re.IGNORECASE | re.DOTALL):
            log_blocked(command, risk, reason)
            print(f"🚫 BLOCKED: {reason}", file=sys.stderr)
            print(f"   Risk level: {risk}", file=sys.stderr)
            print(f"   Set ALLOW_DESTRUCTIVE=1 to override.", file=sys.stderr)
            return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
