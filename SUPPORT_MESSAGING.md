# Support Messaging System

## Overview

The bot now includes a bidirectional support messaging system that allows users to communicate with administrators directly through the bot interface.

## How It Works

### For Users

1. **Initiating Contact**:
   - Click the "💬 Техподдержка" (Support) button in the main menu
   - The bot will prompt you to type your message
   - Type your question or problem description
   - Your message will be sent to all configured administrators

2. **Receiving Replies**:
   - When an admin responds, you'll receive their reply directly in your chat with the bot
   - Replies are clearly marked as "Ответ от администратора" (Reply from administrator)

3. **Canceling**:
   - If you change your mind, click "❌ Отменить" (Cancel) to return to the main menu

### For Administrators

1. **Receiving User Messages**:
   - When a user sends a support message, you'll receive:
     - User's full name
     - Username (if available)
     - Telegram ID
     - The actual message content

2. **Replying to Users**:
   - Simply use Telegram's native "Reply" feature on the user's message
   - Your reply will be automatically forwarded to the user
   - You'll receive a confirmation when the reply is sent

## Technical Implementation

### Key Components

1. **FSM State Machine** (`SupportStates`):
   - `waiting_for_message`: Active when user is composing a support message

2. **Handlers**:
   - `support_message`: Initiates support conversation
   - `receive_support_message`: Processes and forwards user messages to admins
   - `handle_admin_reply`: Detects admin replies and forwards them to users

3. **Message Flow**:
   ```
   User clicks Support button
   → Bot prompts for message
   → User types message
   → Message forwarded to all admins with context
   → Admin replies using Telegram's reply feature
   → Reply forwarded to user
   → Both parties receive confirmations
   ```

### Localization

The feature supports both Ukrainian and Russian languages with the following new strings:

- `support_prompt`: Initial message asking user to type their request
- `support_message_sent`: Confirmation that message was sent to admins
- `support_admin_reply`: Header for admin replies
- `btn_cancel`: Cancel button text

### Security

- Only configured admins (listed in `ADMIN_IDS` environment variable) can use the reply functionality
- User IDs are extracted from message context to prevent spoofing
- All errors are logged but don't expose sensitive information to users

## Testing

The implementation includes comprehensive tests:

- Unit tests for individual handler functions
- Integration tests for complete conversation flows
- Tests for edge cases (multiple admins, non-admin replies, etc.)

Run tests with:
```bash
python3 -m pytest test_support_messaging.py -v
python3 -m pytest test_support_integration.py -v
```

## Configuration

No additional configuration is required. The system uses the existing `ADMIN_IDS` setting from the environment variables.

## Benefits

1. **User Experience**:
   - No need to leave the bot to contact support
   - Receive replies in the same interface
   - Clear feedback at each step

2. **Admin Experience**:
   - All support requests in one place
   - Full user context provided
   - Use familiar Telegram interface for replies

3. **System Design**:
   - Minimal changes to existing codebase
   - Uses Telegram's native reply feature
   - Follows existing patterns (FSM, localization, etc.)
