# Sprache Motivator - Language Learning Telegram Bot

A comprehensive Telegram bot for language practice and motivation with administrative panel.

## Features

### User Features
- **Multi-language Interface**: Ukrainian and Russian interface languages
- **Translation Mode**: 
  - English and German translation support
  - Automatic German article detection
  - Bidirectional translation
  - Translation caching for faster responses
  - Word saving functionality
- **Daily Trainer**:
  - 3 daily practice sessions
  - Multiple difficulty levels (A2, B1, B2, Combined)
  - Grammar explanations for incorrect answers
  - Progress tracking
- **Motivation System**:
  - Activity scoring
  - Progress tracking
  - Performance statistics
- **Settings**: Customizable interface language, learning language, and difficulty level

### Admin Features
- User approval/rejection system
- User statistics dashboard
- Mass broadcast messaging (respecting user preferences)
- User activity ranking
- Real-time user management

## Architecture

### Services
1. **PostgreSQL**: Persistent data storage
   - User profiles and preferences
   - Translation history
   - Training sessions
   - Saved words
   - Broadcast records

2. **Redis**: Caching layer
   - Translation caching (30-day TTL)
   - User state management
   - Token usage tracking

3. **OpenAI API**: Translation and language processing
   - GPT-3.5-turbo for translations
   - Sentence generation for training
   - Answer validation with explanations

### Components

```
bot/
├── handlers/          # Message and callback handlers
│   ├── start.py      # Registration and language selection
│   ├── translator.py # Translation mode
│   ├── trainer.py    # Daily trainer mode
│   ├── settings.py   # User settings
│   └── admin.py      # Admin panel
├── models/
│   └── database.py   # SQLAlchemy models
├── services/
│   ├── redis_service.py       # Redis operations
│   ├── translation_service.py # OpenAI integration
│   └── database_service.py    # Database operations
├── locales/
│   └── texts.py      # Localization strings
├── utils/
│   └── keyboards.py  # Keyboard layouts
├── config.py         # Configuration
└── main.py          # Bot entry point
```

## Installation & Deployment

### Prerequisites
- Docker and Docker Compose
- Telegram Bot Token (from @BotFather)
- OpenAI API Key

**For automated deployment using GitHub Actions, see [DEPLOYMENT.md](DEPLOYMENT.md)**

### Local Setup

1. Clone the repository:
```bash
git clone https://github.com/PobedazaNami/sprache_motivator.git
cd sprache_motivator
```

2. Create `.env` file from example:
```bash
cp .env.example .env
```

3. Edit `.env` and configure:
```env
BOT_TOKEN=your_telegram_bot_token
OPENAI_API_KEY=your_openai_api_key
ADMIN_IDS=123456789,987654321  # Your Telegram user IDs
```

4. Start the services:
```bash
docker-compose up -d
```

5. Check logs:
```bash
docker-compose logs -f bot
```

### Manual Setup (Without Docker)

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Setup PostgreSQL and Redis:
```bash
# Install and start PostgreSQL
# Install and start Redis
```

3. Update `.env` with correct database and Redis URLs

4. Run migrations:
```bash
alembic upgrade head
```

5. Start the bot:
```bash
python -m bot.main
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| BOT_TOKEN | Telegram Bot Token | Required |
| OPENAI_API_KEY | OpenAI API Key | Required |
| POSTGRES_DB | Database name | sprache_bot |
| POSTGRES_USER | Database user | sprache_user |
| POSTGRES_PASSWORD | Database password | sprache_password |
| POSTGRES_HOST | Database host | postgres |
| ADMIN_IDS | Admin user IDs (comma-separated) | Required |
| MAX_CONCURRENT_USERS | Maximum concurrent users | 100 |
| DAILY_TRAINER_TIMES | Training times (HH:MM,HH:MM) | 08:00,14:00,20:00 |
| MAX_TOKENS_PER_USER_DAILY | Daily token limit per user | 10000 |
| CACHE_TTL_SECONDS | Translation cache TTL | 2592000 (30 days) |

### Daily Trainer Schedule

Configure training times in `.env`:
```env
DAILY_TRAINER_TIMES=08:00,14:00,20:00
```

Times are in 24-hour format, separated by commas.

## Usage

### For Users

1. Start the bot: `/start`
2. Select interface language (Ukrainian/Russian)
3. Wait for admin approval
4. Access main menu with features:
   - 📖 Translator
   - 🎯 Daily Trainer
   - 💾 Saved Words
   - ⚙️ Settings
   - 💬 Support

### For Admins

1. Access admin panel: `/admin`
2. Available functions:
   - Approve/reject new users
   - View user statistics
   - Send broadcasts
   - View activity ranking

## Token Optimization

The bot implements several strategies to minimize OpenAI API costs:

1. **Translation Caching**: All translations are cached in Redis for 30 days
2. **Daily Limits**: Users have a daily token limit (configurable)
3. **Efficient Prompts**: Optimized prompts for minimal token usage
4. **Smart Detection**: Language detection to avoid unnecessary API calls

## Database Schema

### Users Table
- User profiles and preferences
- Activity scoring
- Token usage tracking
- Approval status

### Saved Words Table
- User's saved translations
- Source and target languages

### Translations Table
- Translation history
- Usage analytics

### Training Sessions Table
- Daily trainer exercises
- User answers and correctness
- Grammar explanations

### Broadcasts Table
- Broadcast messages
- Delivery statistics

## Localization

The bot supports two interface languages:
- Ukrainian (uk)
- Russian (ru)

All user-facing text is localized in `bot/locales/texts.py`.

## API Rate Limits

The bot is designed to handle ~100 concurrent users with:
- Rate limiting on OpenAI API calls
- Efficient caching strategy
- Asynchronous processing
- Connection pooling

## Monitoring

### Logs
Logs are stored in the `logs/` directory and include:
- Bot startup/shutdown events
- API errors
- User activity
- Broadcast results

### Database Queries
Monitor user activity with built-in statistics:
- Total users
- Approved/pending/rejected counts
- Activity rankings
- Translation counts

## Troubleshooting

### Bot not responding
1. Check if bot is running: `docker-compose ps`
2. View logs: `docker-compose logs bot`
3. Verify BOT_TOKEN in `.env`

### Database connection errors
1. Check PostgreSQL status: `docker-compose ps postgres`
2. Verify database credentials in `.env`
3. Check logs: `docker-compose logs postgres`

### Redis connection errors
1. Check Redis status: `docker-compose ps redis`
2. Verify Redis host/port in `.env`
3. Check logs: `docker-compose logs redis`

### OpenAI API errors
1. Verify OPENAI_API_KEY in `.env`
2. Check API quota and billing
3. Review error logs for specific error messages

## Development

### Running Tests
```bash
# Install dev dependencies
pip install pytest pytest-asyncio

# Run tests
pytest
```

### Database Migrations

Create a new migration:
```bash
alembic revision --autogenerate -m "description"
```

Apply migrations:
```bash
alembic upgrade head
```

Rollback migration:
```bash
alembic downgrade -1
```

## Security Considerations

- Store `.env` securely, never commit to version control
- Use strong database passwords
- Limit admin access with ADMIN_IDS
- Monitor token usage to prevent abuse
- Regularly update dependencies

## Support

For technical support, contact: @reeziat

## License

This project is licensed under the MIT License.

## Roadmap

### Completed
- ✅ User registration and approval system
- ✅ Multi-language interface (Ukrainian/Russian)
- ✅ Translation mode with caching
- ✅ Daily trainer with difficulty levels
- ✅ Admin panel with user management
- ✅ Broadcast system
- ✅ Activity ranking
- ✅ Token optimization

### Future Enhancements
- 🔜 Advanced motivation system (badges, streaks)
- 🔜 Voice message translation
- 🔜 Vocabulary tests
- 🔜 Spaced repetition system
- 🔜 User groups and competitions
- 🔜 Analytics dashboard
- 🔜 Mobile app integration

## Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## Acknowledgments

- aiogram for Telegram bot framework
- OpenAI for translation API
- PostgreSQL and Redis for data storage