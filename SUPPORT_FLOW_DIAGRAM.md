# Support Messaging Flow Diagram

## Complete Flow Visualization

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         SUPPORT MESSAGING FLOW                           │
└─────────────────────────────────────────────────────────────────────────┘

USER SIDE                           BOT                         ADMIN SIDE
═══════════                        ═════                        ═══════════

   │                                 │                               │
   │  1. Click "💬 Техподдержка"     │                               │
   ├────────────────────────────────>│                               │
   │                                 │                               │
   │  2. Prompt: "Напишите свое      │                               │
   │     сообщение..."               │                               │
   │<────────────────────────────────┤                               │
   │     [Cancel button shown]       │                               │
   │                                 │                               │
   │  3. User types message:         │                               │
   │     "У меня проблема с ботом"   │                               │
   ├────────────────────────────────>│                               │
   │                                 │                               │
   │  4. Confirmation:               │  5. Forward to admins:        │
   │     "✅ Ваше сообщение          │     "📩 Сообщение от          │
   │      отправлено!"               │      пользователя:            │
   │<────────────────────────────────┤      👤 Ivan Petrov           │
   │     [Main menu shown]           │      @ivanpetrov              │
   │                                 │      ID: 12345                │
   │                                 │                               │
   │                                 │      💬 Сообщение:            │
   │                                 │      У меня проблема с ботом" │
   │                                 ├──────────────────────────────>│
   │                                 │                               │
   │                                 │  6. [Message copied]          │
   │                                 ├──────────────────────────────>│
   │                                 │                               │
   │                                 │  7. Admin uses Telegram's     │
   │                                 │     native "Reply" feature    │
   │                                 │     "Мы разберемся с этим"    │
   │                                 │<──────────────────────────────┤
   │                                 │                               │
   │  8. Admin's reply delivered:    │  9. Confirmation to admin:    │
   │     "📬 Ответ от администратора:│     "✅ Ответ отправлен       │
   │      Мы разберемся с этим"      │      пользователю"            │
   │<────────────────────────────────┤──────────────────────────────>│
   │                                 │                               │
   │                                 │                               │
   ▼                                 ▼                               ▼


════════════════════════════════════════════════════════════════════════════

EDGE CASES:

1. User Cancels:
   ─────────────
   User clicks "❌ Отменить" (Cancel)
   → State cleared
   → Main menu shown
   → No message sent to admins

2. Multiple Admins:
   ────────────────
   Message forwarded to ALL configured admins
   Any admin can reply
   Reply goes to original user

3. Non-Admin Reply:
   ─────────────────
   Regular user tries to reply
   → Handler returns early
   → No action taken
   → System ignores the message

4. Error Handling:
   ───────────────
   Admin notification fails → Error logged, user still gets confirmation
   User notification fails → Error logged, admin gets error message
   Invalid user ID → Error logged, admin informed


════════════════════════════════════════════════════════════════════════════

STATE MACHINE:

┌──────────────┐
│   Initial    │
│    State     │
└───────┬──────┘
        │
        │ User clicks Support button
        │
        ▼
┌──────────────────────┐
│  SupportStates.      │
│  waiting_for_message │
└───────┬──────────────┘
        │
        ├─── User types message ─────> Message sent, state cleared
        │
        └─── User cancels ──────────> State cleared, back to menu


════════════════════════════════════════════════════════════════════════════

MESSAGE IDENTIFICATION:

Admin reply detection relies on:
1. Sender must be in ADMIN_IDS
2. Message must be a reply (reply_to_message exists)
3. Replied message must contain "ID: {user_id}" pattern
4. User ID extracted and validated

Security:
✓ Only admins can trigger reply handler
✓ User ID extracted from context, not user input
✓ All errors logged but not exposed
✓ No direct message forwarding (prevents spoofing)
```

## Key Components

### Files Modified

1. **bot/handlers/settings.py** (112 lines added):
   - `SupportStates` class
   - `support_message()` - Initiates conversation
   - `receive_support_message()` - Processes user message
   - `handle_admin_reply()` - Processes admin reply

2. **bot/locales/texts.py** (8 lines added):
   - Ukrainian and Russian translations for:
     - `support_prompt`
     - `support_message_sent`
     - `support_admin_reply`
     - `btn_cancel`

3. **bot/utils/keyboards.py** (8 lines added):
   - `get_cancel_keyboard()` function

### Files Created

1. **test_support_messaging.py** (183 lines):
   - Unit tests for all handlers
   - Localization tests

2. **test_support_integration.py** (234 lines):
   - Complete flow integration test
   - Edge case tests
   - Multiple admins test

3. **SUPPORT_MESSAGING.md** (109 lines):
   - Feature documentation
   - User guide
   - Admin guide
   - Technical details

4. **SUPPORT_FLOW_DIAGRAM.md** (this file):
   - Visual flow diagram
   - Edge cases explanation
   - State machine diagram

## Benefits

✅ **User Experience**: Direct communication without leaving the bot
✅ **Admin Experience**: All requests in one place, familiar interface
✅ **Security**: Proper permission checks, ID extraction from context
✅ **Reliability**: Error handling, logging, confirmations
✅ **Maintainability**: Follows existing patterns, well-tested
✅ **Localization**: Full support for Ukrainian and Russian
