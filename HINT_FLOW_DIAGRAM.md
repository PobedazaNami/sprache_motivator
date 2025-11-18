# Hint Feature Flow Diagram

## User Flow Visualization

```
┌─────────────────────────────────────────────────────────────┐
│                    Training Task Sent                        │
│                                                               │
│  🎯 Task 1/3 for today                                       │
│  📚 Level: A2 | Topic: Family and friends                   │
│                                                               │
│  Translate this sentence:                                    │
│  I like to play football with my friends.                   │
│                                                               │
│  ┌─────────────────────────────────────┐                    │
│  │   💡 Отримати переклад / Get Hint  │  ← Hint Button     │
│  └─────────────────────────────────────┘                    │
└─────────────────────────────────────────────────────────────┘
                        │
                        │
         ┌──────────────┴──────────────┐
         │                             │
         ▼                             ▼
┌─────────────────┐          ┌──────────────────┐
│  User Types     │          │  User Clicks     │
│  Answer         │          │  Hint Button     │
└────────┬────────┘          └────────┬─────────┘
         │                            │
         │                            │
         ▼                            ▼
┌─────────────────┐          ┌──────────────────────────────┐
│  Check Answer   │          │  Show Translation Hint       │
│                 │          │                              │
│  ✅ or ❌       │          │  💡 Підказка активована!    │
│  Quality: X%    │          │                              │
│                 │          │  ✏️ Correct translation:    │
│  Update Stats:  │          │  Ich spiele gerne...         │
│  ✓ completed    │          │                              │
│  ✓ quality      │          │  ⚠️ This task doesn't count │
│  ✓ correct/     │          │  in daily statistics but is  │
│    incorrect    │          │  tracked as 'hint activation'│
└────────┬────────┘          └────────┬─────────────────────┘
         │                            │
         │                            │
         ▼                            ▼
┌─────────────────┐          ┌──────────────────────────────┐
│  Daily Stats    │          │  Hint Tracking               │
│  MongoDB        │          │  MongoDB                     │
│                 │          │                              │
│  completed: +1  │          │  hint_activations: +1        │
│  quality: +X    │          │                              │
│  correct/       │          │  completed_tasks: unchanged  │
│  incorrect: +1  │          │  quality_sum: unchanged      │
└─────────────────┘          └──────────────────────────────┘
```

## Database Structure Comparison

### Regular Answer (Counts in Stats)
```javascript
daily_stats: {
  user_id: 12345,
  date: "2025-11-18",
  
  // These are updated when user answers
  completed_tasks: 1,        // ← Incremented
  quality_sum: 85,           // ← Added
  correct_answers: 1,        // ← Incremented (if correct)
  
  // Hint counter unchanged
  hint_activations: 0        // ← Not touched
}
```

### Hint Activated (Separate Counter)
```javascript
daily_stats: {
  user_id: 12345,
  date: "2025-11-18",
  
  // These remain unchanged
  completed_tasks: 0,        // ← Not incremented
  quality_sum: 0,            // ← Not updated
  correct_answers: 0,        // ← Not touched
  
  // Only hint counter updated
  hint_activations: 1        // ← Incremented
}
```

## Code Flow

```
1. send_training_task() in trainer.py
   ├─→ Generate sentence
   ├─→ Get expected translation
   ├─→ Create training session in MongoDB
   ├─→ Send message with hint button
   │   └─→ get_trainer_task_keyboard(lang, training_id)
   └─→ Store state in Redis: "awaiting_training_answer"

2a. User types answer → check_training_answer()
    ├─→ Get training session from MongoDB
    ├─→ Check translation quality
    ├─→ Update training session
    ├─→ update_daily_stats() with quality
    └─→ Clear Redis state

2b. User clicks hint → show_hint()
    ├─→ Extract training_id from callback
    ├─→ Get training session from MongoDB
    ├─→ Show expected_translation
    ├─→ track_hint_activation(user_id)
    │   └─→ MongoDB: $inc hint_activations
    └─→ Clear Redis state
```

## Statistics Separation Logic

### Daily Report Calculation
```python
# Completed tasks only include answered tasks
completed = doc.get("completed_tasks", 0)  # Excludes hints

# Average quality from answered tasks only
avg_quality = quality_sum / max(1, completed)  # Based on answers

# Hints are tracked separately
hints = doc.get("hint_activations", 0)  # Separate metric
```

### Admin Dashboard (Future)
```
User Daily Activity:
━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 Tasks Sent: 3
✅ Completed: 2 (66%)
💡 Hints Used: 1
📈 Avg Quality: 85%
```

## Key Benefits

```
┌──────────────────────────────────────────────────┐
│  ✅ Accurate Statistics                          │
│  User's performance metrics reflect actual       │
│  translation ability, not hint usage             │
└──────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────┐
│  📚 Learning Support                             │
│  Users can learn from difficult tasks without    │
│  being penalized in daily statistics             │
└──────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────┐
│  📊 Hint Analytics                               │
│  Admins can track which tasks/topics need hints  │
│  to adjust difficulty levels                     │
└──────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────┐
│  🎯 No Pressure                                  │
│  Users feel comfortable knowing they can get     │
│  help when needed                                │
└──────────────────────────────────────────────────┘
```
