# PR Reviewer Agent

> Claude Code sub-agent that reviews pull requests and posts structured Markdown comments.

## Install

```bash
# 1. Copy the agent
cp agents/pr_reviewer.py ~/.claude/agents/pr-reviewer.py

# 2. Run
python agents/pr_reviewer.py --repo owner/repo --pr 123 --post
```

## Features

- **Security scanning** — hardcoded secrets, eval(), SQL injection, shell injection
- **Error handling** — bare except, swallowed exceptions
- **Code quality** — print statements, TODO/FIXME, type safety
- **Structured output** — Markdown with severity levels (🔴 Critical, 🟡 Warning, 🔵 Info)
- **Scoring** — 0-100 score with verdict (Approve/Comment/Request Changes)
- **GitHub integration** — Posts comment directly via `gh` CLI

## Usage

```bash
# Review and print to stdout
python agents/pr_reviewer.py --repo owner/repo --pr 42

# Review and post comment to PR
python agents/pr_reviewer.py --repo owner/repo --pr 42 --post

# Dry run (no output)
python agents/pr_reviewer.py --repo owner/repo --pr 42 --dry-run
```

## Example Output

```markdown
## 🤖 Automated PR Review: Add login feature

**Author:** @dev | **Score:** 75/100 | **Verdict:** Request Changes

**Summary:** Reviewed 3 files (+45/-12). Found 1 critical, 2 warnings.

### 🔴 Critical (1)
- **[Security]** `auth.py`:L23: Hardcoded secret/credential
  - 💡 Use env vars or secrets manager

### 🟡 Warning (2)
- **[Security]** `api.py`:L15: subprocess with shell=True
  - 💡 Pass args as list
- **[Error Handling]** `utils.py`:L8: Bare except
  - 💡 Catch specific exceptions
```

## License

MIT
