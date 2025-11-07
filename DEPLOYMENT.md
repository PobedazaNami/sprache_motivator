# Deployment Guide

This guide explains how to set up automated deployment using GitHub Actions.

## GitHub Actions Configuration

### Required Secrets

Navigate to your repository Settings → Secrets and variables → Actions → Secrets and add the following secrets:

| Secret Name | Description | Example |
|-------------|-------------|---------|
| `BOT_TOKEN` | Telegram Bot Token from @BotFather | `1234567890:ABCD-fake_example_token_here` |
| `OPENAI_API_KEY` | OpenAI API Key | `sk-proj-example123...` |
| `POSTGRES_PASSWORD` | PostgreSQL database password | `your_secure_password` |
| `SSH_PRIVATE_KEY` | SSH private key for server access | `-----BEGIN OPENSSH PRIVATE KEY-----...` |
| `SSH_HOST` | Server hostname or IP address | `example.com` or `192.168.1.100` |
| `SSH_USER` | SSH username for server access | `ubuntu` or `root` |
| `SSH_PORT` | SSH port (optional, defaults to 22) | `22` or `2222` |

### Required Variables

Navigate to your repository Settings → Secrets and variables → Actions → Variables and add the following variables:

| Variable Name | Description | Default | Example |
|---------------|-------------|---------|---------|
| `ADMIN_IDS` | Comma-separated Telegram user IDs for admins | Required | `123456789,987654321` |
| `DEPLOY_PATH` | Path on server where bot will be deployed | `/opt/sprache_motivator` | `/home/user/bot` |
| `POSTGRES_DB` | PostgreSQL database name | `sprache_bot` | `sprache_bot` |
| `POSTGRES_USER` | PostgreSQL username | `sprache_user` | `sprache_user` |
| `POSTGRES_HOST` | PostgreSQL host | `postgres` | `postgres` |
| `POSTGRES_PORT` | PostgreSQL port | `5432` | `5432` |
| `REDIS_HOST` | Redis host | `redis` | `redis` |
| `REDIS_PORT` | Redis port | `6379` | `6379` |
| `MAX_CONCURRENT_USERS` | Maximum concurrent users | `100` | `100` |
| `DAILY_TRAINER_TIMES` | Training times (HH:MM format) | `08:00,14:00,20:00` | `09:00,15:00,21:00` |
| `MAX_TOKENS_PER_USER_DAILY` | Daily token limit per user | `10000` | `10000` |
| `CACHE_TTL_SECONDS` | Cache TTL in seconds | `2592000` | `2592000` |

## Server Setup

### 1. Prepare Your Server

Ensure your server has:
- Docker and Docker Compose installed
- SSH access configured
- Sufficient disk space for Docker volumes

### 2. Generate SSH Key for Deployment

On your local machine:

```bash
# Generate a new SSH key pair for deployment
ssh-keygen -t ed25519 -C "github-actions-deploy" -f github-deploy-key

# Copy the public key to your server
ssh-copy-id -i github-deploy-key.pub user@your-server.com

# Display the private key to copy to GitHub secrets
cat github-deploy-key
```

Copy the entire private key (including `-----BEGIN OPENSSH PRIVATE KEY-----` and `-----END OPENSSH PRIVATE KEY-----`) and add it as the `SSH_PRIVATE_KEY` secret in GitHub.

### 3. Configure GitHub Actions Secrets and Variables

1. Go to your GitHub repository
2. Navigate to Settings → Secrets and variables → Actions
3. Add all required secrets (tab: Secrets)
4. Add all required variables (tab: Variables)

## Deployment

### Automatic Deployment

The bot will automatically deploy when you push to the `main` branch:

```bash
git push origin main
```

### Manual Deployment

You can also trigger deployment manually:

1. Go to your repository on GitHub
2. Click on "Actions" tab
3. Select "Deploy to Server" workflow
4. Click "Run workflow" button
5. Select the branch and click "Run workflow"

## Monitoring Deployment

1. Go to the "Actions" tab in your GitHub repository
2. Click on the latest "Deploy to Server" workflow run
3. Expand the "Deploy to server" step to see deployment logs
4. Check the server logs at the end of deployment

## Troubleshooting

### SSH Connection Issues

If deployment fails with SSH errors:

1. Verify `SSH_HOST`, `SSH_USER`, and `SSH_PORT` are correct
2. Ensure the `SSH_PRIVATE_KEY` is the complete private key
3. Check that the public key is in `~/.ssh/authorized_keys` on the server
4. Verify firewall rules allow SSH connections from GitHub Actions IPs
5. **Security Note**: The workflow uses `ssh-keyscan` for convenience, but for enhanced security, consider manually adding your server's SSH host key to the workflow or using GitHub's secrets to store the host key fingerprint

### Environment Variable Issues

If the bot doesn't start or has configuration errors:

1. Check that all required secrets are set in GitHub Actions
2. Verify variable names match exactly (case-sensitive)
3. Review deployment logs for any .env file creation errors
4. SSH into the server and check the `.env` file:
   ```bash
   cat /opt/sprache_motivator/.env
   ```

### Docker Issues

If Docker containers don't start:

1. SSH into the server
2. Navigate to deployment directory:
   ```bash
   cd /opt/sprache_motivator
   ```
3. Check container status:
   ```bash
   docker-compose ps
   ```
4. View logs:
   ```bash
   docker-compose logs bot
   docker-compose logs postgres
   docker-compose logs redis
   ```

### Permission Issues

If you get permission errors during deployment:

1. Ensure the SSH user has appropriate permissions
2. You may need to add the user to the docker group:
   ```bash
   sudo usermod -aG docker $USER
   ```
3. Or use `sudo` in the deployment commands

## Security Best Practices

1. **Never commit secrets to the repository** - Always use GitHub Secrets
2. **Use strong passwords** - Especially for database passwords
3. **Limit SSH access** - Consider using firewall rules to restrict access
4. **Rotate keys regularly** - Update SSH keys and API tokens periodically
5. **Monitor access logs** - Check server logs for unauthorized access attempts
6. **Use environment-specific configurations** - Consider separate staging/production environments

## Alternative Deployment Methods

If you prefer not to use GitHub Actions, you can still deploy manually:

### Manual Deployment

1. SSH into your server
2. Clone the repository:
   ```bash
   git clone https://github.com/PobedazaNami/sprache_motivator.git
   cd sprache_motivator
   ```
3. Create `.env` file with your configuration
4. Start the services:
   ```bash
   docker-compose up -d
   ```

### Using Docker Hub

You can also build and push images to Docker Hub, then pull them on your server:

1. Build and push:
   ```bash
   docker build -t yourusername/sprache-motivator:latest .
   docker push yourusername/sprache-motivator:latest
   ```
2. Update `docker-compose.yml` to use your image
3. Pull and run on server:
   ```bash
   docker-compose pull
   docker-compose up -d
   ```
