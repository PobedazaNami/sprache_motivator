# Hint Activation Feature

## Overview
The hint activation feature allows users to request a translation/hint when they receive a training task and don't know how to translate it. This feature ensures that users can still learn from tasks they find too difficult, while maintaining accurate daily statistics.

## User Experience

### When User Receives a Training Task
1. User receives a training task with a sentence to translate
2. Below the task, a button is displayed: "💡 Отримати переклад" (Ukrainian) or "💡 Получить перевод" (Russian)
3. User has two options:
   - **Option A**: Type their translation answer (normal flow, counts in daily stats)
   - **Option B**: Click the hint button to see the correct translation

### When User Clicks Hint Button
1. The task message is updated to show:
   - The correct translation
   - A notice that this task won't count in daily statistics
   - Information that it's tracked as "hint activation"
2. The hint button is removed
3. The training state is cleared

## Statistics Tracking

### Separate Tracking
- **Daily Stats**: When user answers normally, it counts towards:
  - `completed_tasks`
  - `quality_sum`
  - `correct_answers` or `incorrect_answers`
  
- **Hint Activations**: When user requests a hint, it counts towards:
  - `hint_activations` (separate counter)
  - Does NOT count in `completed_tasks`
  - Does NOT affect quality metrics

### Database Structure
The daily_stats collection in MongoDB includes:
```javascript
{
  user_id: int,
  date: datetime,
  total_tasks: int,           // All tasks sent
  completed_tasks: int,        // Only answered tasks (no hints)
  hint_activations: int,       // Separate counter for hints
  quality_sum: int,
  expected_tasks: int,
  correct_answers: int,
  incorrect_answers: int
}
```

## Implementation Details

### Files Modified

1. **bot/locales/texts.py**
   - Added `btn_get_hint`: Button text for both languages
   - Added `hint_activated`: Message shown when hint is requested

2. **bot/utils/keyboards.py**
   - Added `get_trainer_task_keyboard()`: Creates inline keyboard with hint button
   - Button callback data format: `hint_{training_id}`

3. **bot/handlers/trainer.py**
   - Modified `send_training_task()`: Now includes hint button in task messages
   - Added `show_hint()`: Callback handler for hint button clicks
   - Handler retrieves training session, shows translation, tracks activation, clears state

4. **bot/services/mongo_service.py**
   - Added `track_hint_activation()`: Records hint usage in daily_stats
   - Uses `$inc` to increment `hint_activations` counter
   - Uses `$setOnInsert` to initialize document if it doesn't exist

### API Flow

```
User clicks hint button
    ↓
Callback: hint_{training_id}
    ↓
show_hint() handler
    ├─→ Extract training_id from callback data
    ├─→ Fetch training session from MongoDB
    ├─→ Get expected_translation
    ├─→ Show translation to user
    ├─→ Call track_hint_activation(user_id)
    └─→ Clear training state in Redis
```

### MongoDB Operations

**track_hint_activation** performs:
```python
update_one(
    {"user_id": user_id, "date": today},
    {
        "$inc": {"hint_activations": 1},
        "$set": {"updated_at": now},
        "$setOnInsert": {
            "user_id": user_id,
            "date": today,
            "created_at": now,
            "total_tasks": 0,
            "completed_tasks": 0,
            "quality_sum": 0,
            "expected_tasks": 0,
            "correct_answers": 0,
            "incorrect_answers": 0,
        }
    },
    upsert=True
)
```

## Benefits

1. **Learning Support**: Users can still learn from difficult tasks without being penalized
2. **Accurate Statistics**: Daily statistics reflect actual user performance, not hint usage
3. **Transparency**: Users are informed that hints don't count in daily stats
4. **Tracking**: Administrators can see hint usage patterns to understand content difficulty
5. **No Pressure**: Users feel less pressured when they know they can request help

## Future Enhancements

Potential improvements for this feature:
- Add hint counter display in user statistics
- Implement daily hint limits
- Show hint usage in daily/weekly reports
- Add "partial hint" option (show only grammatical structure, not full translation)
- Track which topics/difficulty levels get the most hints

## Testing

The feature includes comprehensive tests:
- Localization texts verification
- Keyboard creation and button data
- Handler registration and execution
- MongoDB tracking functionality
- Integration test for complete flow

Tests validate:
- ✅ Hint button appears with correct text in both languages
- ✅ Button callback data includes training ID
- ✅ Handler processes callback correctly
- ✅ Translation is shown to user
- ✅ Hint activation is tracked separately
- ✅ Training state is cleared after hint
- ✅ No impact on daily completion statistics
