# Telegram Mini App (Web App) - Flashcards

## Overview

The Flashcard Mini App is a Telegram Web App that provides a beautiful, interactive interface for learning vocabulary with flashcards. It works like the Telegram Wallet app - as an HTML application embedded directly inside Telegram.

## Features

### Interactive Learning
- **Flip Animation**: Cards flip with smooth 3D CSS animations
- **Swipe Navigation**: Swipe left/right to navigate between cards
- **Touch Support**: Optimized for mobile devices
- **Keyboard Navigation**: Arrow keys and spacebar for desktop users

### Card Management
- **Create Sets**: Organize flashcards into themed sets
- **Add Cards**: Create cards with front (word) and back (translation) sides
- **Delete Cards**: Remove individual cards or entire sets
- **View All Cards**: Preview all cards in a set before studying

### Visual Design
- **Telegram Theme Integration**: Automatically adapts to Telegram's light/dark theme
- **Gradient Cards**: Beautiful gradient backgrounds for cards
- **Haptic Feedback**: Vibration feedback on interactions (on supported devices)
- **Responsive Layout**: Works on any screen size

### Localization
- Ukrainian (uk) interface
- Russian (ru) interface
- Automatic language detection based on user's Telegram settings

## Architecture

### Frontend
```
bot/webapp/
├── templates/
│   └── flashcards.html     # Main HTML template
├── static/
│   ├── css/
│   │   └── flashcards.css  # Styles with theme variables
│   └── js/
│       └── flashcards.js   # App logic and API calls
└── server.py               # aiohttp web server
```

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/flashcards` | GET | Serve the Mini App HTML |
| `/api/flashcards/user/lang` | GET | Get user's language |
| `/api/flashcards/sets` | GET | List all sets |
| `/api/flashcards/sets` | POST | Create a new set |
| `/api/flashcards/sets/{id}` | DELETE | Delete a set |
| `/api/flashcards/sets/{id}/cards` | GET | Get cards in a set |
| `/api/flashcards/sets/{id}/cards` | POST | Add a card |
| `/api/flashcards/sets/{id}/cards/{card_id}` | DELETE | Delete a card |

### Authentication

All API requests are authenticated using Telegram's `initData` validation:
1. Client sends `X-Telegram-Init-Data` header with WebApp init data
2. Server validates the hash using bot token
3. User ID is extracted from validated data

## Configuration

### Environment Variables

```env
# URL where the web app is hosted (required for Mini App)
WEBAPP_URL=https://yourdomain.com

# Port for the web app server (default: 8080)
WEBAPP_PORT=8080
```

### Hosting Requirements

1. **HTTPS Required**: Telegram requires all Web Apps to use HTTPS
2. **Public URL**: The web app must be accessible from the internet
3. **SSL Certificate**: Valid SSL certificate (Let's Encrypt works fine)

---

## 🚀 Пошаговая инструкция по развёртыванию

### Предварительные требования
- Сервер с Ubuntu/Debian (или другой Linux)
- Домен, направленный на IP сервера (A-запись в DNS)
- Docker и Docker Compose установлены на сервере

### Шаг 1: Установка Nginx и Certbot (для HTTPS)

```bash
# Обновляем пакеты
sudo apt update && sudo apt upgrade -y

# Устанавливаем Nginx
sudo apt install nginx -y

# Устанавливаем Certbot для Let's Encrypt SSL
sudo apt install certbot python3-certbot-nginx -y
```

### Шаг 2: Настройка Nginx

Создайте конфигурацию для вашего домена:

```bash
sudo nano /etc/nginx/sites-available/yourdomain.com
```

Вставьте (замените `yourdomain.com` на ваш домен):

```nginx
server {
    listen 80;
    server_name yourdomain.com;

    location / {
        proxy_pass http://localhost:8080;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
    }
}
```

Активируйте конфигурацию:

```bash
# Создаём символическую ссылку
sudo ln -s /etc/nginx/sites-available/yourdomain.com /etc/nginx/sites-enabled/

# Проверяем конфигурацию
sudo nginx -t

# Перезапускаем Nginx
sudo systemctl restart nginx
```

### Шаг 3: Получение SSL сертификата (HTTPS)

```bash
# Получаем сертификат Let's Encrypt (замените yourdomain.com и email)
sudo certbot --nginx -d yourdomain.com --email your@email.com --agree-tos --non-interactive
```

Certbot автоматически обновит конфигурацию Nginx для HTTPS.

### Шаг 4: Настройка бота

1. Склонируйте репозиторий на сервер:
```bash
git clone https://github.com/PobedazaNami/sprache_motivator.git
cd sprache_motivator
```

2. Создайте файл `.env` из примера:
```bash
cp .env.example .env
nano .env
```

3. Настройте переменные в `.env`:
```env
# Telegram Bot Token (от @BotFather)
BOT_TOKEN=your_telegram_bot_token

# OpenAI API Key
OPENAI_API_KEY=your_openai_key

# MongoDB (используйте MongoDB Atlas или локальный)
MONGODB_URI=mongodb://localhost:27017/sprache_motivator

# Redis
REDIS_HOST=redis
REDIS_PORT=6379

# Admin IDs
ADMIN_IDS=your_telegram_id

# ⭐ ВАЖНО: Настройка Web App
WEBAPP_URL=https://yourdomain.com
WEBAPP_PORT=8080
```

### Шаг 5: Обновление docker-compose.yml

Добавьте порт 8080 для Web App в docker-compose.yml:

```bash
nano docker-compose.yml
```

В секции `bot` добавьте `ports`:

```yaml
  bot:
    build:
      context: .
      dockerfile: Dockerfile
    depends_on:
      redis:
        condition: service_healthy
      languagetool:
        condition: service_healthy
    env_file:
      - .env
    environment:
      - LANGUAGETOOL_URL=http://languagetool:8010
    ports:
      - "8080:8080"  # ⭐ Добавьте эту строку для Web App
    volumes:
      - ./logs:/app/logs
    restart: unless-stopped
```

### Шаг 6: Запуск бота

```bash
# Собираем и запускаем
docker-compose up -d --build

# Проверяем логи
docker-compose logs -f bot
```

### Шаг 7: Проверка работы

1. Откройте в браузере: `https://yourdomain.com/flashcards`
   - Вы должны увидеть страницу приложения (будет показывать ошибку аутентификации - это нормально, так как нет Telegram данных)

2. Откройте вашего Telegram бота
3. Нажмите "🎴 Карточки" / "🎴 Картки"
4. Нажмите кнопку "📱 Открыть приложение" / "📱 Відкрити додаток"
5. Приложение должно открыться внутри Telegram!

### Проверка статуса

```bash
# Проверить статус всех сервисов
docker-compose ps

# Проверить логи бота
docker-compose logs bot

# Проверить доступность Web App
curl -I https://yourdomain.com/flashcards
```

### Автоматическое обновление SSL сертификата

Certbot автоматически настраивает cron для обновления. Проверить можно так:

```bash
sudo certbot renew --dry-run
```

---

### Nginx Example Configuration (Manual SSL)

Если вы настраиваете SSL вручную (не через Certbot):

```nginx
server {
    listen 443 ssl;
    server_name yourdomain.com;

    ssl_certificate /path/to/certificate.crt;
    ssl_certificate_key /path/to/private.key;

    location / {
        proxy_pass http://localhost:8080;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_cache_bypass $http_upgrade;
    }
}
```

## User Flow

1. User clicks "🎴 Карточки" in the bot menu
2. User sees options: "📱 Открыть приложение" (Open App) and traditional menu
3. Clicking "Open App" launches the Mini App inside Telegram
4. Mini App shows user's flashcard sets
5. User can create sets, add cards, and study with flip animations

## Development

### Running Locally

1. Set up environment variables:
   ```bash
   export WEBAPP_URL=https://your-ngrok-url.ngrok.io
   export WEBAPP_PORT=8080
   ```

2. Run the bot:
   ```bash
   python -m bot.main
   ```

3. Use ngrok for HTTPS tunneling during development:
   ```bash
   ngrok http 8080
   ```

### Testing the Mini App

1. Open your Telegram bot
2. Navigate to Flashcards menu
3. Click "Open App" button
4. The Mini App should load inside Telegram

## Security Considerations

- All API requests validate Telegram init data
- User IDs are extracted from validated Telegram data, not from user input
- MongoDB queries use user_id to ensure data isolation
- Input is sanitized and length-limited

## Troubleshooting

### "Invalid authentication" error
- Ensure the init data header is being sent correctly
- Check that the bot token is correct in environment variables

### Mini App not loading
- Verify WEBAPP_URL is correct and accessible
- Check that HTTPS is properly configured
- Ensure the port is not blocked by firewall

### Theme not applying
- Check browser console for JavaScript errors
- Verify Telegram WebApp SDK is loaded correctly
