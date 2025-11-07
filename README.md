# Sprache Motivator - Language Learning Telegram Bot

A Telegram bot for language practice (DE/EN ⇄ UK/RU) built with Node.js and TypeScript.

## Description

Sprache Motivator is a Telegram bot designed to help users practice German and English languages with Ukrainian and Russian interface support. The bot provides translation services, caching for efficient API usage, and is built with a scalable architecture ready for future enhancements like training modes and admin panels.

## Tech Stack

- **Node.js** (v18+) with **TypeScript**
- **telegraf** - Telegram Bot API framework
- **openai** - OpenAI API integration for translations
- **ioredis** - Redis client for caching
- **Docker & Docker Compose** - Containerization
- **ESLint** - Code linting
- **Gitleaks** - Secret scanning

## Project Structure

```
src/
├── index.ts              # Entry point
├── bot/
│   └── telegram.ts       # Telegraf bot initialization
├── config/
│   └── env.ts            # Environment variables loading and validation
├── services/
│   ├── logger.ts         # Logging service
│   └── redisClient.ts    # Redis connection
└── i18n/
    ├── ru.json           # Russian localization
    └── uk.json           # Ukrainian localization
```

## Quick Start

### Prerequisites

- Node.js 18+ and npm
- Docker and Docker Compose
- Telegram Bot Token (from @BotFather)
- OpenAI API Key

### Installation

1. Clone the repository:
```bash
git clone https://github.com/PobedazaNami/sprache_motivator.git
cd sprache_motivator
```

2. Install dependencies:
```bash
npm ci
```

3. Create `.env` file from example:
```bash
cp .env.example .env
```

4. Edit `.env` and configure your environment variables (see below)

### Running Locally

Development mode with hot reload:
```bash
npm run dev
```

Production build and run:
```bash
npm run build
npm start
```

### Running with Docker

Build and start services:
```bash
docker-compose build
docker-compose up -d
```

View logs:
```bash
docker-compose logs -f bot
```

## Environment Variables

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `TELEGRAM_BOT_TOKEN` | Telegram Bot API token | Yes | - |
| `OPENAI_API_KEY` | OpenAI API key | Yes | - |
| `REDIS_URL` | Redis connection URL | Yes | redis://redis:6379 |
| `REDIS_PASSWORD` | Redis password (if required) | No | - |
| `TRANSLATION_MODEL` | OpenAI model for translations | No | gpt-3.5-turbo |
| `DEFAULT_INTERFACE_LANG` | Default interface language (uk/ru) | No | uk |

**IMPORTANT**: Never commit real tokens to the repository! Store them only in:
- Local `.env` file (gitignored)
- GitHub Secrets for CI/CD

## CI/CD and Secrets

### GitHub Actions Workflow

The CI workflow (`.github/workflows/ci.yml`) runs on every push and pull request to `main`:

1. Checkout code
2. Set up Node.js
3. Install dependencies (`npm ci`)
4. Generate `.env` from GitHub Secrets and Variables
5. Build TypeScript (`npm run build`)
6. Run linter (`npm run lint`)
7. Run tests (`npm test`)
8. Scan for secrets with Gitleaks

### Configuring Secrets

Navigate to: **Repository Settings → Secrets and Variables → Actions**

**Secrets** (encrypted):
- `TELEGRAM_BOT_TOKEN` - Your Telegram bot token
- `OPENAI_API_KEY` - Your OpenAI API key
- `REDIS_PASSWORD` - Redis password (if using authentication)

**Variables** (plain text):
- `TRANSLATION_MODEL` - OpenAI model name (e.g., `gpt-3.5-turbo`)
- `DEFAULT_INTERFACE_LANG` - Default interface language (`uk` or `ru`)

### Secret Rotation

For security best practices, rotate secrets every 90 days or immediately if compromised. See [SECURITY.md](.github/SECURITY.md) for detailed instructions.

## Development

### Build

Compile TypeScript:
```bash
npm run build
```

### Lint

Run ESLint:
```bash
npm run lint
```

### Test

Run tests:
```bash
npm test
```

## Available Commands

Currently implemented:
- `/ping` - Health check command (responds with "pong")

Future commands (planned):
- `/start` - Start the bot and select interface language
- `/translate` - Enter translation mode
- `/train` - Enter training mode
- `/settings` - Configure bot settings

## Docker

### Multi-stage Build

The Dockerfile uses a multi-stage build for optimal image size:
1. **installer** - Install production dependencies
2. **builder** - Build TypeScript
3. **runtime** - Final image with only necessary files

### Services

- **redis** - Redis 7 Alpine for caching
- **bot** - Node.js application

## Security

- ✅ Environment variables validated on startup
- ✅ Secrets stored in GitHub Secrets, never in code
- ✅ Gitleaks scanning in CI to prevent secret leaks
- ✅ `.env.example` contains only placeholder values
- ✅ Regular secret rotation policy documented

See [SECURITY.md](.github/SECURITY.md) for complete security guidelines.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Future Development

Out of scope for initial release, planned for future:
- Translation caching and optimization
- Daily training exercises
- Admin panel for user management
- Motivation and progress tracking system
- Multi-language support expansion

## Contributing

Contributions are welcome! Please ensure:
- Code follows ESLint rules
- All tests pass
- No secrets are committed
- Changes are documented in pull requests
