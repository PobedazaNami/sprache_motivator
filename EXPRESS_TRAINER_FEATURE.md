# Express Trainer Feature

## Overview
The Express Trainer is a new on-demand training mode that allows users to practice translation tasks one after another at their own pace, without being tied to a schedule.

## Key Differences from Daily Trainer

| Feature | Daily Trainer | Express Trainer |
|---------|---------------|-----------------|
| **Scheduling** | Time-based (scheduled throughout the day) | On-demand (user-initiated) |
| **Task Limit** | Limited to X tasks per day | Unlimited tasks |
| **Progress Tracking** | Daily progress with countdown timers | No daily limits or tracking |
| **Settings** | Time period, messages per day, topic | Topic only |
| **Use Case** | Consistent daily practice | Quick practice sessions when free |

## User Flow

```
Main Menu
    ↓
[⚡️ Експрес тренажер / ⚡️ Экспресс тренажёр]
    ↓
Express Trainer Menu
    ├─ [▶️ Start Express Trainer] → Generate Task
    └─ [⚙️ Settings]
           └─ Topic Selection (A2/B1/B2/Random)
    
Generate Task
    ↓
Display Sentence + Topic + Level
    ↓
User Submits Answer
    ↓
Bot Provides Feedback
    ├─ ✅ Correct (with quality %)
    └─ ❌ Incorrect (with explanation + correct answer)
    ↓
[➡️ Next Sentence] → Generate Task (loops back)
```

## Implementation Details

### New Files
- `bot/handlers/express_trainer.py` - Main handler for express trainer functionality

### Modified Files
- `bot/locales/texts.py` - Added Ukrainian and Russian localization
- `bot/utils/keyboards.py` - Added express trainer keyboard functions
- `bot/services/database_service.py` - Added `express_trainer_topic` field to UserModel
- `bot/main.py` - Registered express_trainer router

### Key Features

1. **On-Demand Task Generation**
   - User clicks "Start" or "Next Sentence" to get a task
   - No scheduling or time-based triggers
   - No daily limits

2. **Topic Selection**
   - Same topic selection as Daily Trainer
   - Independent settings (doesn't affect Daily Trainer)
   - Supports A2, B1, B2 levels and random topics

3. **Quality Assessment**
   - Same translation validation as Daily Trainer
   - Quality percentage feedback
   - Grammar explanations for incorrect answers

4. **State Management**
   - Uses Redis for session state (`awaiting_express_answer`)
   - Separate state from Daily Trainer
   - Properly handles translator state restoration

5. **User Data**
   - Updates user statistics (total_answers, correct_answers)
   - Updates activity score
   - Stores training sessions in MongoDB (same as Daily Trainer)

## Localization

### Ukrainian (uk)
- Main button: `⚡️ Експрес тренажер`
- Start button: `▶️ Почати експрес тренажер`
- Next sentence: `➡️ Наступне речення`
- Menu description: "Отримуйте завдання для перекладу одне за одним, коли у вас є вільний час!"

### Russian (ru)
- Main button: `⚡️ Экспресс тренажёр`
- Start button: `▶️ Начать экспресс тренажёр`
- Next sentence: `➡️ Следующее предложение`
- Menu description: "Получайте задания для перевода одно за одним, когда у вас есть свободное время!"

## Security
- ✅ Passed CodeQL security scan (0 issues)
- ✅ Proper callback data parsing
- ✅ Redis keys have TTL (30 days) to prevent memory leaks
- ✅ Type-safe enum handling for topics

## Testing
- ✅ All module imports verified
- ✅ Localization completeness validated
- ✅ Handler functions existence confirmed
- ✅ Router registration verified
- ✅ Database model integration tested
