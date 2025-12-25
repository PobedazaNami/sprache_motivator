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

### Nginx Example Configuration

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
