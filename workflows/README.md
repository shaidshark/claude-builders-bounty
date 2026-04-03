# n8n + Claude API — Weekly Dev Summary

> Automated workflow that collects weekly git activity and generates a dev summary using Claude API.

## Install (2 commands)

```bash
# 1. Import the workflow into n8n
n8n import:workflow --input=workflows/weekly-dev-summary.json

# 2. Set environment variables
export GITHUB_REPO="owner/repo"
export ANTHROPIC_API_KEY="sk-ant-..."
```

## Architecture

```
Cron (Mon 9am) → Fetch Commits + PRs → Merge → Process → Claude API → Email + Gist
```

## What It Does

1. **Triggers** every Monday at 9am
2. **Fetches** all commits and merged PRs from the past 7 days via GitHub API
3. **Aggregates** data: commits by author, PR titles, top contributors
4. **Sends to Claude API** for a structured Markdown summary
5. **Delivers** via email and saves as a private GitHub Gist

## Output Format

```markdown
# Weekly Dev Summary - 2026-04-03

## 📊 Stats
- Total commits: 47
- Merged PRs: 12
- Active contributors: 5

## 🏆 Top Contributors
1. Alice — 18 commits
2. Bob — 14 commits

## 🔀 Merged Pull Requests
- #142: Add user authentication
- #139: Fix payment gateway timeout

## 📝 Key Changes
- Authentication: New JWT-based auth system
- Performance: Redis caching for API endpoints

## 🎯 Focus Areas for Next Week
- Complete migration to TypeScript
- Load testing for new auth system
```

## Requirements

- **n8n** (self-hosted or cloud)
- **GitHub API** credentials (for commit/PR data)
- **Anthropic API key** (for Claude)
- **SMTP** credentials (optional, for email delivery)

## Configuration

| Variable | Required | Description |
|----------|----------|-------------|
| `GITHUB_REPO` | ✅ | GitHub repo in `owner/repo` format |
| `ANTHROPIC_API_KEY` | ✅ | Claude API key |
| `EMAIL_TO` | ❌ | Recipient email for summary |
| `SMTP_HOST` | ❌ | SMTP server for email |

## License

MIT
