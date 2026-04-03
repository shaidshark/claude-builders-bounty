#!/usr/bin/env python3
"""
PR Reviewer Agent for Claude Code.

A sub-agent that reviews pull requests and posts structured Markdown comments.

Usage:
  python pr_reviewer.py --repo owner/repo --pr 123 --post

Requires: gh CLI authenticated, Python 3.10+
"""

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class Severity(Enum):
    CRITICAL = "🔴 Critical"
    WARNING = "🟡 Warning"
    INFO = "🔵 Info"


@dataclass
class ReviewFinding:
    file: str
    line: Optional[int]
    severity: Severity
    category: str
    message: str
    suggestion: str = ""


@dataclass
class ReviewResult:
    summary: str
    findings: list[ReviewFinding] = field(default_factory=list)
    overall_score: int = 0
    verdict: str = ""


def run_gh(args: list[str]) -> str:
    result = subprocess.run(["gh"] + args, capture_output=True, text=True, timeout=60)
    if result.returncode != 0:
        print(f"gh error: {result.stderr}", file=sys.stderr)
        sys.exit(1)
    return result.stdout


def get_pr_diff(repo: str, pr_number: int) -> str:
    return run_gh(["pr", "diff", str(pr_number), "--repo", repo])


def get_pr_info(repo: str, pr_number: int) -> dict:
    output = run_gh(["pr", "view", str(pr_number), "--repo", repo, "--json",
                      "title,body,author,additions,deletions,changedFiles,labels"])
    return json.loads(output)


def analyze_diff(diff: str, pr_info: dict) -> ReviewResult:
    findings = []
    current_file = ""
    current_line = 0

    for line in diff.split("\n"):
        if line.startswith("+++ b/"):
            current_file = line[6:]
        elif line.startswith("@@"):
            match = re.search(r"@@ -\d+(?:,\d+)? \+(\d+)", line)
            if match:
                current_line = int(match.group(1))
        elif line.startswith("+") and not line.startswith("+++"):
            content = line[1:].strip()

            # Security
            if re.search(r"(password|secret|api_key|token)\s*=\s*['\"]", content, re.I):
                findings.append(ReviewFinding(current_file, current_line, Severity.CRITICAL,
                    "Security", "Hardcoded secret/credential", "Use env vars or secrets manager"))

            if re.search(r"eval\s*\(", content):
                findings.append(ReviewFinding(current_file, current_line, Severity.CRITICAL,
                    "Security", "Use of eval()", "Use ast.literal_eval() or json.loads()"))

            if re.search(r"subprocess.*shell\s*=\s*True", content):
                findings.append(ReviewFinding(current_file, current_line, Severity.WARNING,
                    "Security", "subprocess with shell=True", "Pass args as list"))

            # Error handling
            if re.search(r"except\s*:", content):
                findings.append(ReviewFinding(current_file, current_line, Severity.WARNING,
                    "Error Handling", "Bare except", "Catch specific exceptions"))

            # Code quality
            if re.search(r"print\s*\(", content) and "def " not in content:
                findings.append(ReviewFinding(current_file, current_line, Severity.INFO,
                    "Code Quality", "Print statement", "Use logging module"))

            if re.search(r"# TODO|# FIXME|# HACK", content, re.I):
                findings.append(ReviewFinding(current_file, current_line, Severity.INFO,
                    "Code Quality", "TODO/FIXME left", "Resolve or create issue"))

            # SQL injection
            if re.search(r"(execute|cursor).*%[sd]", content) or \
               re.search(r"f['\"].*(SELECT|INSERT|UPDATE|DELETE)", content, re.I):
                findings.append(ReviewFinding(current_file, current_line, Severity.CRITICAL,
                    "Security", "Potential SQL injection", "Use parameterized queries"))

            current_line += 1
        elif not line.startswith("-") and not line.startswith("\\"):
            current_line += 1

    critical = sum(1 for f in findings if f.severity == Severity.CRITICAL)
    warnings = sum(1 for f in findings if f.severity == Severity.WARNING)
    score = max(0, min(100, 100 - critical * 20 - warnings * 5))

    if critical > 0:
        verdict = "Request Changes"
    elif warnings > 3:
        verdict = "Request Changes"
    elif warnings > 0:
        verdict = "Comment"
    else:
        verdict = "Approve"

    additions = pr_info.get("additions", 0)
    deletions = pr_info.get("deletions", 0)
    files = pr_info.get("changedFiles", 0)
    summary = f"Reviewed {files} files (+{additions}/-{deletions}). Found {critical} critical, {warnings} warnings."

    return ReviewResult(summary, findings, score, verdict)


def format_review(result: ReviewResult, pr_info: dict) -> str:
    title = pr_info.get("title", "PR")
    author = pr_info.get("author", {}).get("login", "unknown")

    lines = [
        f"## 🤖 Automated PR Review: {title}", "",
        f"**Author:** @{author} | **Score:** {result.overall_score}/100 | **Verdict:** {result.verdict}", "",
        f"**Summary:** {result.summary}", "",
    ]

    if not result.findings:
        lines.append("✅ No issues found. Clean PR!")
    else:
        for severity in [Severity.CRITICAL, Severity.WARNING, Severity.INFO]:
            grouped = [f for f in result.findings if f.severity == severity]
            if not grouped:
                continue
            lines.append(f"### {severity.value} ({len(grouped)})")
            lines.append("")
            for f in grouped:
                loc = f"`{f.file}`" + (f":L{f.line}" if f.line else "")
                lines.append(f"- **[{f.category}]** {loc}: {f.message}")
                if f.suggestion:
                    lines.append(f"  - 💡 _{f.suggestion}_")
            lines.append("")

    lines.extend(["---", "_Generated by PR Reviewer Agent_ 🤖"])
    return "\n".join(lines)


def post_comment(repo: str, pr_number: int, comment: str) -> None:
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False, encoding="utf-8") as f:
        f.write(comment)
        tmp = f.name
    run_gh(["pr", "comment", str(pr_number), "--repo", repo, "--body-file", tmp])
    os.unlink(tmp)
    print(f"✅ Review posted on {repo}#{pr_number}")


def main():
    parser = argparse.ArgumentParser(description="PR Reviewer Agent")
    parser.add_argument("--repo", required=True)
    parser.add_argument("--pr", type=int, required=True)
    parser.add_argument("--post", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    print(f"📋 Reviewing {args.repo}#{args.pr}...")
    pr_info = get_pr_info(args.repo, args.pr)
    diff = get_pr_diff(args.repo, args.pr)
    result = analyze_diff(diff, pr_info)
    comment = format_review(result, pr_info)

    if args.dry_run:
        print(comment)
    elif args.post:
        post_comment(args.repo, args.pr, comment)
    else:
        print(comment)


if __name__ == "__main__":
    main()
