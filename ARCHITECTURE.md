# Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                        SPRACHE MOTIVATOR                         │
│                   Language Learning Telegram Bot                 │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                         USER FLOWS                               │
└─────────────────────────────────────────────────────────────────┘

┌──────────────┐      ┌──────────────┐      ┌──────────────┐
│ New User     │      │ Approved     │      │ Admin User   │
│ Registration │      │ User Flow    │      │ Flow         │
└──────┬───────┘      └──────┬───────┘      └──────┬───────┘
       │                     │                     │
       ▼                     ▼                     ▼
  /start cmd            Main Menu            /admin cmd
       │                     │                     │
       ▼                     ├──────┐              ▼
Select Language         Translator │         Admin Panel
       │                     │      │              │
       ▼                     │      ├────Daily     ├────Approve/Reject
Pending Approval        Translate  │    Trainer   │    Users
       │                     │      │              │
       ▼                     │      ├────Saved     ├────View Stats
Admin Notified          Save Word  │    Words     │
       │                     │      │              │
       ▼                     │      ├────Settings  ├────Broadcast
Approved/Rejected        Continue  │              │    Messages
       │                     │      │              │
       └─────────────────────┘      └────Support   └────User Rating


┌─────────────────────────────────────────────────────────────────┐
│                    SYSTEM ARCHITECTURE                           │
└─────────────────────────────────────────────────────────────────┘

┌───────────────────────────────────────────────────────────────┐
│                     Telegram Users                             │
└──────────────────────────┬────────────────────────────────────┘
                           │
                           ▼
┌───────────────────────────────────────────────────────────────┐
│                    Telegram Bot API                            │
└──────────────────────────┬────────────────────────────────────┘
                           │
                           ▼
┌───────────────────────────────────────────────────────────────┐
│                      BOT SERVICE                               │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │                    bot/main.py                          │  │
│  │  - aiogram Bot & Dispatcher                            │  │
│  │  - APScheduler for daily tasks                         │  │
│  │  - Handler registration                                │  │
│  └──────────────────┬──────────────────────────────────────┘  │
│                     │                                          │
│  ┌──────────────────┴──────────────────────────────────────┐  │
│  │              HANDLERS                                    │  │
│  │  ┌──────────┬──────────┬──────────┬──────────┐         │  │
│  │  │ Start    │Translator│ Trainer  │ Settings │ Admin   │  │
│  │  │ /start   │ Mode     │ Mode     │          │ /admin  │  │
│  │  └──────────┴──────────┴──────────┴──────────┴─────────┘  │
│  └─────────────────────────────────────────────────────────┘  │
│                     │                                          │
│  ┌──────────────────┴──────────────────────────────────────┐  │
│  │              SERVICES                                    │  │
│  │  ┌────────────────┬────────────────┬─────────────────┐  │  │
│  │  │ Translation    │ Database       │ Redis           │  │  │
│  │  │ Service        │ Service        │ Service         │  │  │
│  │  │ - OpenAI API   │ - User CRUD    │ - Caching       │  │  │
│  │  │ - Translation  │ - Word CRUD    │ - User State    │  │  │
│  │  │ - Validation   │ - Training     │ - Token Track   │  │  │
│  │  └────────────────┴────────────────┴─────────────────┘  │  │
│  └─────────────────────────────────────────────────────────┘  │
└───────────────┬───────────────────┬───────────────────────────┘
                │                   │
                ▼                   ▼
┌───────────────────────┐  ┌──────────────────────┐
│   PostgreSQL DB       │  │     Redis Cache      │
│  - Users              │  │  - Translations      │
│  - SavedWords         │  │  - User States       │
│  - Translations       │  │  - Token Counters    │
│  - TrainingSessions   │  │                      │
│  - Broadcasts         │  │  TTL: 30 days        │
└───────────────────────┘  └──────────────────────┘
                │
                ▼
┌──────────────────────────────────────┐
│         OpenAI API                   │
│  - GPT-3.5-turbo                     │
│  - Translation                       │
│  - Sentence Generation               │
│  - Answer Validation                 │
└──────────────────────────────────────┘


┌─────────────────────────────────────────────────────────────────┐
│                      DATA FLOW                                   │
└─────────────────────────────────────────────────────────────────┘

Translation Request:
User → Handler → Check Cache → Cache Hit? → Return Translation
                      │              │
                      └──────No──────┘
                      │
                      ▼
              Check Token Limit
                      │
                      ▼
                OpenAI API
                      │
                      ▼
              Cache Translation
                      │
                      ▼
              Save to DB History
                      │
                      ▼
              Update User Stats
                      │
                      ▼
              Return Translation

Daily Trainer Flow:
Scheduler → Generate Sentence → Get Translation → Create Session
                                                        │
                                                        ▼
                                                  Send to User
                                                        │
                                                        ▼
                                               Store State in Redis
                                                        │
User Answers ────────────────────────────────────────┐│
                                                      ││
                                                      ▼▼
                                        Check Translation with OpenAI
                                                      │
                                                      ▼
                                              Update Session
                                                      │
                                                      ▼
                                            Update User Stats
                                                      │
                                                      ▼
                                            Send Feedback


┌─────────────────────────────────────────────────────────────────┐
│                   OPTIMIZATION STRATEGIES                        │
└─────────────────────────────────────────────────────────────────┘

1. CACHING
   - All translations cached in Redis (30 days)
   - Cache key: "translation:{source_lang}:{target_lang}:{text}"
   - Reduces OpenAI API calls by ~70-80%

2. TOKEN LIMITS
   - Daily limit per user: 10,000 tokens
   - Tracked in Redis with 24h TTL
   - Prevents abuse and controls costs

3. ASYNCHRONOUS PROCESSING
   - All I/O operations async
   - Concurrent request handling
   - Non-blocking database queries

4. CONNECTION POOLING
   - PostgreSQL connection pool
   - Redis connection reuse
   - Efficient resource utilization

5. SMART LANGUAGE DETECTION
   - Heuristic-based detection (Cyrillic check)
   - Avoids unnecessary API calls
   - Determines translation direction


┌─────────────────────────────────────────────────────────────────┐
│                    DOCKER SERVICES                               │
└─────────────────────────────────────────────────────────────────┘

docker-compose.yml:

┌────────────────────┐
│   postgres:15      │  Port: 5432
│   - PERSISTENT     │  Volume: postgres_data
│   - USER/PASS/DB   │  Health: pg_isready
└────────────────────┘

┌────────────────────┐
│   redis:7          │  Port: 6379
│   - IN-MEMORY      │  Volume: redis_data
│   - CACHE          │  Health: redis-cli ping
└────────────────────┘

┌────────────────────┐
│   bot (custom)     │  Depends: postgres, redis
│   - PYTHON 3.11    │  Restart: unless-stopped
│   - MIGRATIONS     │  Volume: ./logs
│   - BOT LOGIC      │  CMD: alembic + python
└────────────────────┘


┌─────────────────────────────────────────────────────────────────┐
│                      DEPLOYMENT                                  │
└─────────────────────────────────────────────────────────────────┘

1. Clone Repository
2. Create .env from .env.example
3. Configure BOT_TOKEN, OPENAI_API_KEY, ADMIN_IDS
4. Run: docker-compose up -d
5. Check logs: docker-compose logs -f bot
6. Bot starts automatically, runs migrations
7. Ready to receive messages!


┌─────────────────────────────────────────────────────────────────┐
│                   MONITORING & LOGS                              │
└─────────────────────────────────────────────────────────────────┘

Logs Directory: ./logs/
- Bot startup/shutdown
- API errors
- User activity
- Broadcast results
- Training task delivery

Database Statistics:
- Total users (approved/pending/rejected)
- Activity rankings
- Translation counts
- Training session stats
- Broadcast delivery stats
```
