#!/usr/bin/env python3
"""
Pre-tool-use hook for Claude Code that blocks destructive bash commands.

Install: cp pre-tool-use-block-destructive.py ~/.claude/hooks/pre-tool-use.py
Config: Add to ~/.claude/hooks.json in the "PreToolUse" array.

Logs blocked attempts to ~/.claude/hooks/blocked.log
"""

import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

LOG_FILE = Path.home() / ".claude" / "hooks" / "blocked.log"

DESTRUCTIVE_PATTERNS = [
    (r"\brm\s+(-[a-zA-Z]*f[a-zA-Z]*\s+|-[a-zA-Z]*r[a-zA-Z]*\s+).*/", "rm -rf with path"),
    (r"\brm\s+--recursive\s+--force\s+", "rm --recursive --force"),
    (r"\bDROP\s+(TABLE|DATABASE|SCHEMA)\b", "DROP TABLE/DATABASE/SCHEMA"),
    (r"\bTRUNCATE\s+(TABLE\s+)?[a-zA-Z_]", "TRUNCATE table"),
    (r"\bDELETE\s+FROM\b", "DELETE FROM"),
    (r"\bmkfs\b", "mkfs (format filesystem)"),
    (r"\bdd\s+if=.*of=/dev/", "dd writing to device"),
    (r"\b(shutdown|reboot|halt|poweroff|init\s+[06])\b", "system shutdown/reboot"),
    (r"\bchmod\s+-R\s+(777|666)\s+/", "chmod -R 777/666 on root"),
    (r"\bchown\s+-R\s+\w+\s+/", "chown -R on root"),
    (r"\bgit\s+push\s+.*(--force|-f\b)", "git push --force"),
    (r"\bgit\s+clean\s+(-[a-zA-Z]*f|-fdx)", "git clean -f"),
    (r"\bdocker\s+(system\s+)?prune\b", "docker prune"),
    (r"\bdocker\s+rm\s+(-f|--force)", "docker rm --force"),
    (r"\bkubectl\s+delete\s+namespace", "kubectl delete namespace"),
    (r"\b(npm|pip)\s+uninstall\s+(-g|--global)", "global package uninstall"),
    (r":\(\)\{.*:\|:&\}", "fork bomb pattern"),
    (r">\s*/dev/sd[a-z]", "overwrite block device"),
]

WHITELIST = [
    "rm -rf node_modules",
    "rm -rf __pycache__",
    "rm -rf .cache",
    "rm -rf dist",
    "rm -rf build",
    "rm -rf .next",
    "rm -rf .turbo",
    "rm -rf coverage",
    "rm -rf .pytest_cache",
]


def log_blocked(command: str, reason: str) -> None:
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    project = os.environ.get("CLAUDE_PROJECT_DIR", os.getcwd())
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "command": command,
        "reason": reason,
        "project_path": project,
    }
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


def is_whitelisted(command: str) -> bool:
    cmd_stripped = command.strip()
    return any(cmd_stripped.startswith(w) for w in WHITELIST)


def check_command(command: str) -> tuple[bool, str]:
    if is_whitelisted(command):
        return False, ""
    for pattern, description in DESTRUCTIVE_PATTERNS:
        if re.search(pattern, command, re.IGNORECASE):
            return True, description
    return False, ""


def main():
    try:
        input_data = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        sys.exit(0)

    tool_name = input_data.get("tool_name", "")
    if tool_name not in ("Bash", "bash"):
        sys.exit(0)

    tool_input = input_data.get("tool_input", {})
    command = tool_input.get("command", "")
    if not command:
        sys.exit(0)

    is_destructive, reason = check_command(command)
    if is_destructive:
        log_blocked(command, reason)
        message = (
            f"⛔ Command blocked by safety hook: {reason}\n"
            f"Command: {command}\n"
            f"This command was identified as potentially destructive. "
            f"If you believe this is a false positive, ask the user to run it manually."
        )
        print(json.dumps({"decision": "block", "reason": message}))
        sys.exit(0)
    sys.exit(0)


if __name__ == "__main__":
    main()
