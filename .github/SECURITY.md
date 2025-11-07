# Security Policy

## Secrets Management

### Storing Secrets

**CRITICAL**: Never commit real tokens, API keys, or passwords to the repository.

- **For local development**: Store secrets in a local `.env` file (excluded from git via `.gitignore`)
- **For CI/CD**: Use GitHub Secrets and Variables
  - Navigate to: Repository Settings → Secrets and Variables → Actions
  - Add secrets: `TELEGRAM_BOT_TOKEN`, `OPENAI_API_KEY`, `REDIS_PASSWORD`
  - Add variables: `TRANSLATION_MODEL`, `DEFAULT_INTERFACE_LANG`

### Secrets Rotation

Rotate secrets regularly to maintain security:

1. **Telegram Bot Token**
   - Contact @BotFather on Telegram
   - Use `/token` command to regenerate
   - Update in GitHub Secrets and local `.env`
   - Frequency: Every 90 days or if compromised

2. **OpenAI API Key**
   - Log into OpenAI platform
   - Revoke old key and create new one
   - Update in GitHub Secrets and local `.env`
   - Frequency: Every 90 days or if compromised

3. **Redis Password**
   - Update in docker-compose.yml or Redis configuration
   - Update in GitHub Secrets and local `.env`
   - Restart Redis service
   - Frequency: Every 90 days or if compromised

### Incident Response

If you accidentally commit a secret:

1. **Immediately** revoke/regenerate the compromised secret
2. Update the secret in GitHub Secrets and local `.env`
3. Contact repository administrators
4. Consider using `git-filter-repo` or BFG Repo-Cleaner to remove from history
5. Force push cleaned history (requires coordination with team)

### Reporting Security Issues

If you discover a security vulnerability, please report it to:
- Email: security@example.com (update with actual contact)
- Do NOT create a public GitHub issue

## Gitleaks Scanning

This repository uses Gitleaks to scan for accidentally committed secrets:
- Runs automatically on every push and pull request
- Checks entire git history for secret patterns
- Fails CI if secrets are detected

### False Positives

If Gitleaks flags a false positive:
1. Verify it's truly not a secret
2. Add to `.gitleaksignore` file if necessary
3. Document why it's a false positive
