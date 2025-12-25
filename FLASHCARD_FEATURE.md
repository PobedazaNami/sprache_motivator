# Flashcard Mini App Feature

## Overview

The Flashcard Mini App is a learning tool integrated into the Sprache Motivator bot that allows users to create and study flashcards for vocabulary learning.

## Features

### 1. Flashcard Sets Management
- **Create Sets**: Users can create multiple flashcard sets to organize their learning materials
- **View Sets**: Browse all created flashcard sets with card counts
- **Delete Sets**: Remove sets and all associated flashcards

### 2. Flashcard Management
- **Add Cards**: Create flashcards with front (word/text) and back (translation) sides
- **View Cards**: Study flashcards in a sequential manner
- **Flip Cards**: Toggle between front and back sides of flashcards
- **Navigate Cards**: Swipe through cards using previous/next navigation
- **Delete Cards**: Remove individual flashcards from sets

### 3. User Interface
- **Slider Navigation**: Cards can be navigated using previous/next buttons (swipe-like experience)
- **Flip Animation**: Click to flip cards and reveal translations
- **Inline Keyboards**: All interactions are done via inline buttons for smooth UX

## Database Schema

### Collections

#### `flashcard_sets`
- `_id`: ObjectId - Unique set identifier
- `user_id`: int - Telegram user ID who owns the set
- `name`: string - Name of the flashcard set
- `created_at`: datetime - When the set was created
- `updated_at`: datetime - Last modification time

**Indexes:**
- `(user_id, created_at)` - For efficient querying of user's sets

#### `flashcards`
- `_id`: ObjectId - Unique card identifier
- `user_id`: int - Telegram user ID who owns the card
- `set_id`: string - Reference to the flashcard set
- `front`: string - Front side of the card (word/text)
- `back`: string - Back side of the card (translation)
- `created_at`: datetime - When the card was created

**Indexes:**
- `(set_id, created_at)` - For efficient retrieval of cards in a set
- `(user_id)` - For user-specific queries

## User Workflow

### Creating a Flashcard Set
1. User clicks "🎴 Картки" / "🎴 Карточки" from main menu
2. Selects "➕ Створити набір" / "➕ Создать набор"
3. Enters a name for the set
4. Set is created and ready for cards

### Adding Flashcards
1. User selects a flashcard set
2. Clicks "➕ Додати картку" / "➕ Добавить карточку"
3. Enters the front side text (word or phrase)
4. Enters the back side text (translation)
5. Card is added to the set

### Studying Flashcards
1. User selects a flashcard set
2. Clicks "👁 Переглянути картки" / "👁 Просмотр карточек"
3. Views cards one by one
4. Clicks "🔄 Перевернути" / "🔄 Перевернуть" to flip the card
5. Uses "➡️ Наступна" / "➡️ Следующая" to move to next card
6. Uses "⬅️ Попередня" / "⬅️ Предыдущая" to go back to previous card

### Deleting Content
- **Delete Card**: Click "🗑 Видалити картку" / "🗑 Удалить карточку" while viewing a card
- **Delete Set**: Click "🗑 Видалити набір" / "🗑 Удалить набор" from set view, confirm deletion

## Technical Implementation

### Handler: `bot/handlers/flashcards.py`
Main router handling all flashcard-related interactions:
- Message handlers for menu access
- Callback query handlers for all button interactions
- FSM states for multi-step operations (creating sets, adding cards)

### Keyboards: `bot/utils/keyboards.py`
Inline keyboard generators for:
- Main flashcard menu
- Set list display
- Set management options
- Card viewing interface with navigation
- Deletion confirmations

### Localization: `bot/locales/texts.py`
All user-facing text in Ukrainian and Russian:
- Menu texts
- Instructions
- Button labels
- Confirmation messages

### States
```python
class FlashcardStates(StatesGroup):
    creating_set = State()        # Waiting for set name
    adding_card_front = State()   # Waiting for card front text
    adding_card_back = State()    # Waiting for card back text
```

## Integration

The flashcard feature is:
- Integrated into the main menu via the "🎴 Картки" / "🎴 Карточки" button
- Available to all approved users (no subscription required)
- Router registered in `bot/main.py` before the trainer router

## Accessibility

- **Free for all users**: Unlike the translator feature, flashcards are available to all approved users
- **No limits**: Users can create unlimited sets and cards
- **Multilingual**: Full support for Ukrainian and Russian interfaces

## Future Enhancements (Not Implemented)

Potential improvements for future versions:
- Spaced repetition algorithm
- Progress tracking per set
- Card difficulty ratings
- Import/export functionality
- Shared flashcard sets
- Audio pronunciation support
- Image support for flashcards
- Quiz mode with scoring
