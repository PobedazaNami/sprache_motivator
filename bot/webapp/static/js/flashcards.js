// Telegram Mini App - Flashcards JavaScript

// Constants
const SWIPE_THRESHOLD_PX = 50;

// Initialize Telegram WebApp
const tg = window.Telegram.WebApp;
tg.ready();
tg.expand();

// Apply Telegram theme
function applyTheme() {
    const root = document.documentElement;
    if (tg.themeParams) {
        root.style.setProperty('--tg-theme-bg-color', tg.themeParams.bg_color || '#ffffff');
        root.style.setProperty('--tg-theme-text-color', tg.themeParams.text_color || '#000000');
        root.style.setProperty('--tg-theme-hint-color', tg.themeParams.hint_color || '#999999');
        root.style.setProperty('--tg-theme-link-color', tg.themeParams.link_color || '#2481cc');
        root.style.setProperty('--tg-theme-button-color', tg.themeParams.button_color || '#2481cc');
        root.style.setProperty('--tg-theme-button-text-color', tg.themeParams.button_text_color || '#ffffff');
        root.style.setProperty('--tg-theme-secondary-bg-color', tg.themeParams.secondary_bg_color || '#f0f0f0');
    }
}

// Localization
const TEXTS = {
    uk: {
        loading: 'Завантаження...',
        reverseOn: '↔ Реверс: увімкнено',
        reverseOff: '↔ Реверс: вимкнено',
        shuffle: '🔀 Перемішати',
        mySets: '📚 Мої набори',
        createSet: 'Створити набір',
        noSetsText: 'У вас поки немає наборів карток',
        noSetsHint: 'Створіть перший набір для вивчення слів!',
        study: 'Вивчати',
        addCard: 'Додати картку',
        deleteSet: '🗑 Видалити набір',
        createSetTitle: 'Створити набір',
        setNamePlaceholder: 'Назва набору',
        cancel: 'Скасувати',
        create: 'Створити',
        addCardTitle: 'Додати картку',
        frontPlaceholder: 'Лицьова сторона (слово)',
        backPlaceholder: 'Зворотна сторона (переклад)',
        examplePlaceholder: 'Приклад речення',
        add: 'Додати',
        flashcards_edit_card: 'Редагувати картку',
        flashcards_save: 'Зберегти',
        deleteTitle: 'Видалити набір?',
        deleteWarning: 'Всі картки в цьому наборі будуть видалені.',
        delete: 'Видалити',
        prev: 'Назад',
        next: 'Далі',
        tapHint: 'Натисніть на картку, щоб перевернути',
        cards: 'карт',
        noCards: 'Немає карток',
        // Error and validation messages
        errorLoadSets: 'Помилка завантаження наборів',
        errorLoadCards: 'Помилка завантаження карток',
        errorCreateSet: 'Помилка створення набору',
        errorDeleteSet: 'Помилка видалення набору',
        errorAddCard: 'Помилка додавання картки',
        errorDeleteCard: 'Помилка видалення картки',
        errorEditCard: 'Помилка редагування картки',
        validationEnterName: 'Будь ласка, введіть назву',
        validationFillBothFields: 'Будь ласка, заповніть обидва поля',
        flashcards_rename_set: 'Перейменувати набір'
    },
    ru: {
        loading: 'Загрузка...',
        reverseOn: '↔ Реверс: включён',
        reverseOff: '↔ Реверс: выключен',
        shuffle: '🔀 Перемешать',
        mySets: '📚 Мои наборы',
        createSet: 'Создать набор',
        noSetsText: 'У вас пока нет наборов карточек',
        noSetsHint: 'Создайте первый набор для изучения слов!',
        study: 'Изучать',
        addCard: 'Добавить карточку',
        deleteSet: '🗑 Удалить набор',
        createSetTitle: 'Создать набор',
        setNamePlaceholder: 'Название набора',
        cancel: 'Отмена',
        create: 'Создать',
        addCardTitle: 'Добавить карточку',
        frontPlaceholder: 'Лицевая сторона (слово)',
        backPlaceholder: 'Обратная сторона (перевод)',
        examplePlaceholder: 'Пример предложения',
        add: 'Добавить',
        flashcards_edit_card: 'Редактировать карточку',
        flashcards_save: 'Сохранить',
        deleteTitle: 'Удалить набор?',
        deleteWarning: 'Все карточки в этом наборе будут удалены.',
        delete: 'Удалить',
        prev: 'Назад',
        next: 'Далее',
        tapHint: 'Нажмите на карточку, чтобы перевернуть',
        cards: 'карт',
        noCards: 'Нет карточек',
        // Error and validation messages
        errorLoadSets: 'Ошибка загрузки наборов',
        errorLoadCards: 'Ошибка загрузки карточек',
        errorCreateSet: 'Ошибка создания набора',
        errorDeleteSet: 'Ошибка удаления набора',
        errorAddCard: 'Ошибка добавления карточки',
        errorDeleteCard: 'Ошибка удаления карточки',
        errorEditCard: 'Ошибка редактирования карточки',
        validationEnterName: 'Пожалуйста, введите название',
        validationFillBothFields: 'Пожалуйста, заполните оба поля',
        flashcards_rename_set: 'Переименовать набор'
    }
};

// App state
let state = {
    userId: null,
    lang: 'ru',
    sets: [],
    currentSet: null,
    currentCards: [],
    currentCardIndex: 0,
    studyReversed: false,
    isFlipped: false,
    editCardId: null
};

// Get text by key
function t(key) {
    return TEXTS[state.lang]?.[key] || TEXTS['ru'][key] || key;
}

// Apply localization
function applyLocalization() {
    document.getElementById('loading-text').textContent = t('loading');
    document.getElementById('sets-title').textContent = t('mySets');
    document.getElementById('create-set-text').textContent = t('createSet');
    document.getElementById('no-sets-text').textContent = t('noSetsText');
    document.getElementById('no-sets-hint').textContent = t('noSetsHint');
    document.getElementById('study-text').textContent = t('study');
    document.getElementById('add-card-text').textContent = t('addCard');
    document.getElementById('delete-set-text').textContent = t('deleteSet');
    document.getElementById('modal-create-set-title').textContent = t('createSetTitle');
    document.getElementById('set-name-input').placeholder = t('setNamePlaceholder');
    document.getElementById('cancel-text').textContent = t('cancel');
    document.getElementById('create-text').textContent = t('create');
    document.getElementById('modal-add-card-title').textContent = t('addCardTitle');
    document.getElementById('card-front-input').placeholder = t('frontPlaceholder');
    document.getElementById('card-back-input').placeholder = t('backPlaceholder');
    document.getElementById('card-example-input').placeholder = t('examplePlaceholder');
    document.getElementById('modal-edit-card-title').textContent = t('flashcards_edit_card');
    document.getElementById('card-front-edit').placeholder = t('frontPlaceholder');
    document.getElementById('card-back-edit').placeholder = t('backPlaceholder');
    document.getElementById('card-example-edit').placeholder = t('examplePlaceholder');
    document.getElementById('confirm-edit-card').textContent = t('flashcards_save');
    document.getElementById('cancel-edit-card').textContent = t('cancel');
    document.getElementById('cancel-add-text').textContent = t('cancel');
    document.getElementById('add-text').textContent = t('add');
    document.getElementById('delete-title').textContent = t('deleteTitle');
    document.getElementById('delete-warning').textContent = t('deleteWarning');
    document.getElementById('cancel-delete-text').textContent = t('cancel');
    document.getElementById('confirm-delete-text').textContent = t('delete');
    document.getElementById('prev-text').textContent = t('prev');
    document.getElementById('next-text').textContent = t('next');
    const tapHint = document.getElementById('tap-hint');
    if (tapHint) tapHint.textContent = t('tapHint');
    const shuffleBtn = document.getElementById('shuffle-cards');
    if (shuffleBtn) shuffleBtn.textContent = t('shuffle');
    const renameTitle = document.getElementById('modal-rename-set-title');
    if (renameTitle) renameTitle.textContent = t('flashcards_rename_set');
    const renameInput = document.getElementById('rename-set-input');
    if (renameInput) renameInput.placeholder = t('setNamePlaceholder');
    const cancelRename = document.getElementById('cancel-rename-set');
    if (cancelRename) cancelRename.textContent = t('cancel');
    const confirmRename = document.getElementById('confirm-rename-set');
    if (confirmRename) confirmRename.textContent = t('flashcards_save');
    updateReverseButton();
}

// API functions
const API_BASE = '/api/flashcards';

async function apiRequest(endpoint, method = 'GET', body = null) {
    const options = {
        method,
        headers: {
            'Content-Type': 'application/json',
            'X-Telegram-Init-Data': tg.initData
        }
    };
    
    if (body) {
        options.body = JSON.stringify(body);
    }
    
    const response = await fetch(`${API_BASE}${endpoint}`, options);
    
    if (!response.ok) {
        throw new Error(`API error: ${response.status}`);
    }
    
    return response.json();
}

async function fetchSets() {
    return apiRequest('/sets');
}

async function createSet(name) {
    return apiRequest('/sets', 'POST', { name });
}

async function updateSetApi(setId, name) {
    return apiRequest(`/sets/${setId}`, 'PUT', { name });
}

async function deleteSetApi(setId) {
    return apiRequest(`/sets/${setId}`, 'DELETE');
}

async function fetchCards(setId) {
    return apiRequest(`/sets/${setId}/cards`);
}

async function addCardApi(setId, front, back, example) {
    return apiRequest(`/sets/${setId}/cards`, 'POST', { front, back, example });
}

async function deleteCardApi(setId, cardId) {
    return apiRequest(`/sets/${setId}/cards/${cardId}`, 'DELETE');
}

async function updateCardApi(setId, cardId, front, back, example) {
    return apiRequest(`/sets/${setId}/cards/${cardId}`, 'PUT', { front, back, example });
}

async function fetchUserLang() {
    try {
        const data = await apiRequest('/user/lang');
        return data.lang || 'ru';
    } catch {
        return 'ru';
    }
}

// Screen management
function showScreen(screenId) {
    document.querySelectorAll('.screen').forEach(s => s.classList.remove('active'));
    document.getElementById(screenId).classList.add('active');
}

function showModal(modalId) {
    document.getElementById(modalId).classList.add('active');
}

function hideModal(modalId) {
    document.getElementById(modalId).classList.remove('active');
}

// Render functions
function renderSets() {
    const setsList = document.getElementById('sets-list');
    const noSets = document.getElementById('no-sets');
    
    if (state.sets.length === 0) {
        setsList.innerHTML = '';
        noSets.style.display = 'block';
        return;
    }
    
    noSets.style.display = 'none';
    setsList.innerHTML = state.sets.map(set => `
        <div class="set-item" data-set-id="${set._id}">
            <div class="set-info">
                <h3>${escapeHtml(set.name)}</h3>
                <p>${set.card_count || 0} ${t('cards')}</p>
            </div>
            <span class="set-arrow">›</span>
        </div>
    `).join('');
    
    // Add click handlers
    setsList.querySelectorAll('.set-item').forEach(item => {
        item.addEventListener('click', () => {
            const setId = item.dataset.setId;
            openSet(setId);
        });
    });
}

function renderCards() {
    const cardsPreview = document.getElementById('cards-preview');
    
    if (state.currentCards.length === 0) {
        cardsPreview.innerHTML = `<p style="text-align: center; color: var(--tg-theme-hint-color);">${t('noCards')}</p>`;
        document.getElementById('study-btn').disabled = true;
        return;
    }
    
    document.getElementById('study-btn').disabled = false;
    
    cardsPreview.innerHTML = state.currentCards.map(card => `
        <div class="card-preview-item" data-card-id="${card._id}">
            <div>
                <span class="front">${escapeHtml(card.front)}</span>
                <span class="back"> — ${escapeHtml(card.back)}</span>
            </div>
            <div class="card-preview-actions">
                <button class="edit-card" data-card-id="${card._id}" title="${t('flashcards_edit_card')}">✏️</button>
                <button class="delete-card" data-card-id="${card._id}" title="${t('delete')}">🗑</button>
            </div>
        </div>
    `).join('');
    
    // Add edit handlers
    cardsPreview.querySelectorAll('.edit-card').forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.stopPropagation();
            const cardId = btn.dataset.cardId;
            openEditModal(cardId);
        });
    });

    // Add delete handlers
    cardsPreview.querySelectorAll('.delete-card').forEach(btn => {
        btn.addEventListener('click', async (e) => {
            e.stopPropagation();
            const cardId = btn.dataset.cardId;
            await deleteCard(cardId);
        });
    });
}

function renderStudyCard() {
    const card = state.currentCards[state.currentCardIndex];
    if (!card) return;
    const frontText = state.studyReversed ? card.back : card.front;
    const backText = state.studyReversed ? card.front : card.back;
    document.getElementById('card-front-text').textContent = frontText;
    document.getElementById('card-back-text').textContent = backText;
    const exampleEl = document.getElementById('card-example-below');
    if (exampleEl) {
        if (card.example) {
            exampleEl.textContent = card.example;
            exampleEl.style.display = 'block';
        } else {
            exampleEl.textContent = '';
            exampleEl.style.display = 'none';
        }
    }
    document.getElementById('card-counter').textContent = `${state.currentCardIndex + 1}/${state.currentCards.length}`;
    
    // Reset flip state
    document.getElementById('flashcard').classList.remove('flipped');
    
    // Update navigation buttons
    document.getElementById('prev-card').disabled = state.currentCardIndex === 0;
    document.getElementById('next-card').disabled = state.currentCardIndex === state.currentCards.length - 1;
}

// Actions
async function loadSets() {
    try {
        const data = await fetchSets();
        state.sets = data.sets || [];
        renderSets();
    } catch (error) {
        console.error('Error loading sets:', error);
        tg.showAlert(t('errorLoadSets'));
    }
}

async function openSet(setId) {
    try {
        state.currentSet = state.sets.find(s => s._id === setId);
        document.getElementById('set-name').textContent = state.currentSet?.name || '';
        
        const data = await fetchCards(setId);
        state.currentCards = data.cards || [];
        
        renderCards();
        showScreen('set-screen');
    } catch (error) {
        console.error('Error opening set:', error);
        tg.showAlert(t('errorLoadCards'));
    }
}

async function handleCreateSet() {
    const input = document.getElementById('set-name-input');
    const name = input.value.trim();
    
    if (!name) {
        tg.showAlert(t('validationEnterName'));
        return;
    }
    
    try {
        await createSet(name);
        input.value = '';
        hideModal('create-set-modal');
        await loadSets();
        tg.HapticFeedback.notificationOccurred('success');
    } catch (error) {
        console.error('Error creating set:', error);
        tg.showAlert(t('errorCreateSet'));
    }
}

async function handleDeleteSet() {
    if (!state.currentSet) return;
    
    try {
        await deleteSetApi(state.currentSet._id);
        hideModal('delete-modal');
        state.currentSet = null;
        state.currentCards = [];
        await loadSets();
        showScreen('sets-screen');
        tg.HapticFeedback.notificationOccurred('success');
    } catch (error) {
        console.error('Error deleting set:', error);
        tg.showAlert(t('errorDeleteSet'));
    }
}

function openRenameSetModal() {
    if (!state.currentSet) return;
    const input = document.getElementById('rename-set-input');
    if (!input) return;
    input.value = state.currentSet.name || '';
    showModal('rename-set-modal');
    input.focus();
}

async function handleRenameSet() {
    if (!state.currentSet) return;
    const input = document.getElementById('rename-set-input');
    if (!input) return;
    const name = input.value.trim();

    if (!name) {
        tg.showAlert(t('validationEnterName'));
        return;
    }

    try {
        await updateSetApi(state.currentSet._id, name);
        hideModal('rename-set-modal');

        // Update local state and UI
        state.currentSet.name = name;
        document.getElementById('set-name').textContent = name;

        const idx = state.sets.findIndex(s => s._id === state.currentSet._id);
        if (idx !== -1) {
            state.sets[idx].name = name;
        }
        renderSets();

        tg.HapticFeedback.notificationOccurred('success');
    } catch (error) {
        console.error('Error renaming set:', error);
        tg.showAlert(t('errorCreateSet'));
    }
}

async function handleAddCard() {
    const frontInput = document.getElementById('card-front-input');
    const backInput = document.getElementById('card-back-input');
    const exampleInput = document.getElementById('card-example-input');
    const front = frontInput.value.trim();
    const back = backInput.value.trim();
    const example = exampleInput.value.trim();
    
    if (!front || !back) {
        tg.showAlert(t('validationFillBothFields'));
        return;
    }
    
    try {
        await addCardApi(state.currentSet._id, front, back, example);
        frontInput.value = '';
        backInput.value = '';
        exampleInput.value = '';
        adjustTextareaHeight(frontInput);
        adjustTextareaHeight(backInput);
        adjustTextareaHeight(exampleInput);
        hideModal('add-card-modal');
        
        // Reload cards
        const data = await fetchCards(state.currentSet._id);
        state.currentCards = data.cards || [];
        
        // Update card count in sets
        const setIndex = state.sets.findIndex(s => s._id === state.currentSet._id);
        if (setIndex !== -1) {
            state.sets[setIndex].card_count = state.currentCards.length;
        }
        
        renderCards();
        tg.HapticFeedback.notificationOccurred('success');
    } catch (error) {
        console.error('Error adding card:', error);
        tg.showAlert(t('errorAddCard'));
    }
}

async function deleteCard(cardId) {
    try {
        await deleteCardApi(state.currentSet._id, cardId);
        
        // Reload cards
        const data = await fetchCards(state.currentSet._id);
        state.currentCards = data.cards || [];
        
        // Update card count
        const setIndex = state.sets.findIndex(s => s._id === state.currentSet._id);
        if (setIndex !== -1) {
            state.sets[setIndex].card_count = state.currentCards.length;
        }
        
        renderCards();
        tg.HapticFeedback.notificationOccurred('success');
    } catch (error) {
        console.error('Error deleting card:', error);
        tg.showAlert(t('errorDeleteCard'));
    }
}

function openEditModal(cardId) {
    const card = state.currentCards.find(c => c._id === cardId);
    if (!card) return;
    state.editCardId = cardId;
    const frontInput = document.getElementById('card-front-edit');
    const backInput = document.getElementById('card-back-edit');
    const exampleInput = document.getElementById('card-example-edit');
    frontInput.value = card.front || '';
    backInput.value = card.back || '';
    exampleInput.value = card.example || '';
    adjustTextareaHeight(frontInput);
    adjustTextareaHeight(backInput);
    adjustTextareaHeight(exampleInput);
    showModal('edit-card-modal');
}

async function handleEditCard() {
    if (!state.editCardId || !state.currentSet) return;
    const frontInput = document.getElementById('card-front-edit');
    const backInput = document.getElementById('card-back-edit');
    const exampleInput = document.getElementById('card-example-edit');
    const front = frontInput.value.trim();
    const back = backInput.value.trim();
    const example = exampleInput.value.trim();

    if (!front || !back) {
        tg.showAlert(t('validationFillBothFields'));
        return;
    }

    try {
        await updateCardApi(state.currentSet._id, state.editCardId, front, back, example);
        hideModal('edit-card-modal');
        state.editCardId = null;

        const data = await fetchCards(state.currentSet._id);
        state.currentCards = data.cards || [];

        const setIndex = state.sets.findIndex(s => s._id === state.currentSet._id);
        if (setIndex !== -1) {
            state.sets[setIndex].card_count = state.currentCards.length;
        }

        renderCards();
        tg.HapticFeedback.notificationOccurred('success');
    } catch (error) {
        console.error('Error editing card:', error);
        tg.showAlert(t('errorEditCard'));
    }
}

function startStudy() {
    if (state.currentCards.length === 0) return;
    
    state.currentCardIndex = 0;
    state.studyReversed = false;
    updateReverseButton();
    renderStudyCard();
    showScreen('study-screen');
}

function nextCard() {
    if (state.currentCardIndex < state.currentCards.length - 1) {
        animateSwipeOut('left');
        state.currentCardIndex++;
        setTimeout(() => {
            renderStudyCard();
            animateSwipeIn('right');
        }, 160);
        tg.HapticFeedback.impactOccurred('light');
    }
}

function prevCard() {
    if (state.currentCardIndex > 0) {
        animateSwipeOut('right');
        state.currentCardIndex--;
        setTimeout(() => {
            renderStudyCard();
            animateSwipeIn('left');
        }, 160);
        tg.HapticFeedback.impactOccurred('light');
    }
}

function animateSwipeOut(direction) {
    const flashcard = document.getElementById('flashcard');
    if (!flashcard) return;
    flashcard.classList.remove('swipe-left', 'swipe-right', 'swipe-in-left', 'swipe-in-right');
    void flashcard.offsetWidth;
    flashcard.classList.add(direction === 'left' ? 'swipe-left' : 'swipe-right');
    setTimeout(() => {
        flashcard.classList.remove('swipe-left', 'swipe-right');
    }, 260);
}

function animateSwipeIn(fromDirection) {
    const flashcard = document.getElementById('flashcard');
    if (!flashcard) return;
    flashcard.classList.remove('swipe-left', 'swipe-right', 'swipe-in-left', 'swipe-in-right');
    void flashcard.offsetWidth;
    flashcard.classList.add(fromDirection === 'left' ? 'swipe-in-left' : 'swipe-in-right');
    setTimeout(() => {
        flashcard.classList.remove('swipe-in-left', 'swipe-in-right');
    }, 260);
}

function flipCard() {
    const card = document.getElementById('flashcard');
    card.classList.toggle('flipped');
    tg.HapticFeedback.impactOccurred('light');
}

function toggleReverse() {
    state.studyReversed = !state.studyReversed;
    document.getElementById('flashcard').classList.remove('flipped');
    updateReverseButton();
    renderStudyCard();
    tg.HapticFeedback.impactOccurred('light');
}

function updateReverseButton() {
    const btn = document.getElementById('toggle-reverse');
    if (!btn) return;
    btn.textContent = state.studyReversed ? t('reverseOn') : t('reverseOff');
}

function shuffleArrayInPlace(arr) {
    for (let i = arr.length - 1; i > 0; i--) {
        const j = Math.floor(Math.random() * (i + 1));
        [arr[i], arr[j]] = [arr[j], arr[i]];
    }
}

function shuffleStudyCards() {
    if (!state.currentCards || state.currentCards.length < 2) return;
    shuffleArrayInPlace(state.currentCards);
    state.currentCardIndex = 0;
    document.getElementById('flashcard').classList.remove('flipped');
    renderStudyCard();
    tg.HapticFeedback.impactOccurred('light');
}

// Utility functions
function adjustTextareaHeight(el) {
    if (!el) return;
    el.style.height = 'auto';
    el.style.height = `${el.scrollHeight}px`;
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Event listeners
document.getElementById('create-set-btn').addEventListener('click', () => showModal('create-set-modal'));
document.getElementById('cancel-create-set').addEventListener('click', () => hideModal('create-set-modal'));
document.getElementById('confirm-create-set').addEventListener('click', handleCreateSet);

document.getElementById('back-to-sets').addEventListener('click', () => {
    state.currentSet = null;
    state.currentCards = [];
    showScreen('sets-screen');
});

document.getElementById('study-btn').addEventListener('click', startStudy);
document.getElementById('add-card-btn').addEventListener('click', () => showModal('add-card-modal'));
document.getElementById('cancel-add-card').addEventListener('click', () => hideModal('add-card-modal'));
document.getElementById('confirm-add-card').addEventListener('click', handleAddCard);
document.getElementById('cancel-edit-card').addEventListener('click', () => {
    state.editCardId = null;
    hideModal('edit-card-modal');
});
document.getElementById('confirm-edit-card').addEventListener('click', handleEditCard);

document.getElementById('delete-set-btn').addEventListener('click', () => showModal('delete-modal'));
document.getElementById('cancel-delete').addEventListener('click', () => hideModal('delete-modal'));
document.getElementById('confirm-delete').addEventListener('click', handleDeleteSet);

document.getElementById('edit-set-btn').addEventListener('click', openRenameSetModal);
document.getElementById('cancel-rename-set').addEventListener('click', () => hideModal('rename-set-modal'));
document.getElementById('confirm-rename-set').addEventListener('click', handleRenameSet);

document.getElementById('back-to-set').addEventListener('click', () => {
    showScreen('set-screen');
});

document.getElementById('flashcard').addEventListener('click', flipCard);
document.getElementById('prev-card').addEventListener('click', prevCard);
document.getElementById('next-card').addEventListener('click', nextCard);
document.getElementById('shuffle-cards').addEventListener('click', shuffleStudyCards);
document.getElementById('toggle-reverse').addEventListener('click', toggleReverse);

// Handle Enter key in inputs
document.getElementById('set-name-input').addEventListener('keypress', (e) => {
    if (e.key === 'Enter') handleCreateSet();
});

document.getElementById('rename-set-input').addEventListener('keypress', (e) => {
    if (e.key === 'Enter') handleRenameSet();
});

['card-front-input', 'card-back-input', 'card-example-input', 'card-front-edit', 'card-back-edit', 'card-example-edit'].forEach(id => {
    const el = document.getElementById(id);
    if (!el) return;
    el.addEventListener('input', () => adjustTextareaHeight(el));
});

// Keyboard navigation for study mode
document.addEventListener('keydown', (e) => {
    if (document.getElementById('study-screen').classList.contains('active')) {
        if (e.key === 'ArrowLeft') prevCard();
        else if (e.key === 'ArrowRight') nextCard();
        else if (e.key === ' ') flipCard();
    }
});

// Swipe support for cards
let touchStartX = 0;
let touchEndX = 0;

document.getElementById('flashcard').addEventListener('touchstart', (e) => {
    touchStartX = e.changedTouches[0].screenX;
}, { passive: true });

document.getElementById('flashcard').addEventListener('touchend', (e) => {
    touchEndX = e.changedTouches[0].screenX;
    handleSwipe();
}, { passive: true });

function handleSwipe() {
    const diff = touchStartX - touchEndX;
    if (Math.abs(diff) > SWIPE_THRESHOLD_PX) {
        if (diff > 0) {
            nextCard();
        } else {
            prevCard();
        }
    }
}

// Initialize app
async function init() {
    console.log('Init started');
    applyTheme();
    
    try {
        // Get user language
        console.log('Fetching user lang...');
        state.lang = await fetchUserLang();
        console.log('User lang:', state.lang);
        applyLocalization();
        
        // Load sets
        console.log('Loading sets...');
        await loadSets();
        console.log('Sets loaded:', state.sets.length);

        // Set initial textarea heights
        ['card-front-input', 'card-back-input', 'card-example-input', 'card-front-edit', 'card-back-edit', 'card-example-edit'].forEach(id => {
            const el = document.getElementById(id);
            if (el) adjustTextareaHeight(el);
        });
        
        showScreen('sets-screen');
        const loadingEl = document.getElementById('loading');
        if (loadingEl) loadingEl.remove();
        console.log('Init completed');
    } catch (error) {
        console.error('Initialization error:', error);
        // Still show screen with default language
        applyLocalization();
        showScreen('sets-screen');
        const loadingEl = document.getElementById('loading');
        if (loadingEl) loadingEl.remove();
    }
}

// Start app
init();
