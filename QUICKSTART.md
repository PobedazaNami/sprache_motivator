# Quick Start Guide

This guide will help you get the Sprache Motivator bot up and running quickly.

## Prerequisites

Before you begin, ensure you have:

1. **Docker** and **Docker Compose** installed
2. A **Telegram Bot Token** (get it from [@BotFather](https://t.me/BotFather))
3. An **OpenAI API Key** (get it from [OpenAI Platform](https://platform.openai.com/api-keys))
4. Your **Telegram User ID** (get it from [@userinfobot](https://t.me/userinfobot))

## Step-by-Step Setup

### 1. Clone the Repository

```bash
git clone https://github.com/PobedazaNami/sprache_motivator.git
cd sprache_motivator
```

### 2. Configure Environment

Create a `.env` file:

```bash
cp .env.example .env
```

Edit the `.env` file and add your credentials:

```env
BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz  # Your bot token
OPENAI_API_KEY=sk-...                             # Your OpenAI API key
ADMIN_IDS=123456789                               # Your Telegram user ID
```

### 3. Start the Bot

```bash
docker-compose up -d
```

This will:
- Start PostgreSQL database
- Start Redis cache
- Build and start the bot
- Run database migrations automatically

### 4. Check Status

```bash
# View logs
docker-compose logs -f bot

# Check services
docker-compose ps
```

You should see:
```
NAME                  IMAGE               STATUS
postgres              postgres:15-alpine  Up (healthy)
redis                 redis:7-alpine      Up (healthy)
bot                   bot:latest          Up
```

### 5. Test the Bot

1. Open Telegram and find your bot (search for the username you set in @BotFather)
2. Send `/start` command
3. Select your interface language
4. You'll be automatically approved since you're the admin
5. Try the features!

## Common Commands

### View Logs
```bash
docker-compose logs -f bot
```

### Restart Bot
```bash
docker-compose restart bot
```

### Stop Services
```bash
docker-compose down
```

### Stop and Remove Data
```bash
docker-compose down -v  # WARNING: This deletes all data!
```

### Update Bot Code
```bash
git pull
docker-compose build
docker-compose up -d
```

## Testing Bot Features

### As a User

1. **Translator Mode**:
   - Click "📖 Translator"
   - Send any English/German word or phrase
   - Get translation in your interface language
   - Click "💾 Save word" to save it

2. **Daily Trainer**:
   - Click "🎯 Daily Trainer"
   - Click "▶️ Start Trainer"
   - You'll receive tasks 3 times daily (configured in .env)
   - Translate the sentence and send your answer
   - Get feedback and explanations

3. **Saved Words**:
   - Click "💾 Saved Words"
   - View your translation history

4. **Settings**:
   - Click "⚙️ Settings"
   - Change interface language
   - Change learning language (English/German)
   - Change difficulty level (A2, B1, B2, A2-B2)

### As an Admin

1. **Access Admin Panel**:
   - Send `/admin` command
   - See admin menu

2. **Approve Users**:
   - Click "👥 Users on Review"
   - Approve or reject new users

3. **View Statistics**:
   - Click "📊 User Statistics"
   - See total users and breakdown

4. **Send Broadcast**:
   - Click "📢 Broadcast"
   - Enter your message
   - Confirm to send to all users

5. **View Ranking**:
   - Click "🏆 Activity Ranking"
   - See top 10 most active users

## Customization

### Change Training Times

Edit `.env`:
```env
DAILY_TRAINER_TIMES=09:00,15:00,21:00
```

Restart the bot:
```bash
docker-compose restart bot
```

### Adjust Token Limits

Edit `.env`:
```env
MAX_TOKENS_PER_USER_DAILY=5000  # Reduce for cost control
```

### Change Cache Duration

Edit `.env`:
```env
CACHE_TTL_SECONDS=604800  # 7 days instead of 30
```

## Troubleshooting

### Bot Not Responding

**Check if services are running:**
```bash
docker-compose ps
```

**View bot logs:**
```bash
docker-compose logs bot
```

**Common issues:**
- Invalid BOT_TOKEN: Check your token in .env
- Database not ready: Wait for PostgreSQL healthcheck
- Redis not connected: Check Redis logs

### Database Issues

**Reset database (WARNING: Deletes all data!):**
```bash
docker-compose down -v
docker-compose up -d
```

### OpenAI API Errors

**Common issues:**
- Invalid API key: Check OPENAI_API_KEY in .env
- Quota exceeded: Check your OpenAI billing
- Rate limit: Wait a moment and try again

### Docker Issues

**Rebuild from scratch:**
```bash
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

## Getting Help

1. Check the logs: `docker-compose logs -f bot`
2. Review the [README.md](README.md) for detailed documentation
3. Check [ARCHITECTURE.md](ARCHITECTURE.md) for system design
4. Contact support: @reeziat

## Next Steps

1. ✅ Bot is running
2. ✅ Users can register and use features
3. ✅ Admin can manage users and send broadcasts

Now you can:
- Invite users to try your bot
- Monitor activity in admin panel
- Adjust settings based on usage
- Review logs for any issues

## Production Deployment

For production deployment:

1. **Use a VPS/Cloud Server**:
   - DigitalOcean, AWS, Google Cloud, etc.
   - Minimum: 1 CPU, 1GB RAM, 10GB storage

2. **Secure your .env**:
   - Never commit .env to git
   - Use strong database passwords
   - Restrict admin access

3. **Setup Monitoring**:
   - Monitor logs regularly
   - Set up alerts for errors
   - Track API usage and costs

4. **Backup Database**:
   ```bash
   docker-compose exec postgres pg_dump -U sprache_user sprache_bot > backup.sql
   ```

5. **Keep Updated**:
   ```bash
   git pull
   docker-compose build
   docker-compose up -d
   ```

Happy language learning! 🎓📚
