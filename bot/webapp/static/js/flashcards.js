// Telegram Mini App - Premium Flashcards JavaScript with GSAP

// Constants
const SWIPE_THRESHOLD_PX = 50;

// Initialize Telegram WebApp
const tg = window.Telegram.WebApp;
tg.ready();
tg.expand();
// Force dark mode for this premium design
tg.setHeaderColor('#0e100f');
tg.setBackgroundColor('#0e100f');

// Localization (Keeping existing structure)
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
    
    // Updated simple text for buttons that might be hidden but kept for logic
    const prevText = document.getElementById('prev-text');
    if (prevText) prevText.textContent = t('prev');
    const nextText = document.getElementById('next-text');
    if (nextText) nextText.textContent = t('next');
    
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

// API functions (Same as before)
const API_BASE = '/api/flashcards';

async function apiRequest(endpoint, method = 'GET', body = null) {
    const options = {
        method,
        headers: {
            'Content-Type': 'application/json',
            'X-Telegram-Init-Data': tg.initData
        }
    };
    if (body) options.body = JSON.stringify(body);
    const response = await fetch(`${API_BASE}${endpoint}`, options);
    if (!response.ok) throw new Error(`API error: ${response.status}`);
    return response.json();
}

async function fetchSets() { return apiRequest('/sets'); }
async function createSet(name) { return apiRequest('/sets', 'POST', { name }); }
async function updateSetApi(setId, name) { return apiRequest(`/sets/${setId}`, 'PUT', { name }); }
async function deleteSetApi(setId) { return apiRequest(`/sets/${setId}`, 'DELETE'); }
async function fetchCards(setId) { return apiRequest(`/sets/${setId}/cards`); }
async function addCardApi(setId, front, back, example) { return apiRequest(`/sets/${setId}/cards`, 'POST', { front, back, example }); }
async function deleteCardApi(setId, cardId) { return apiRequest(`/sets/${setId}/cards/${cardId}`, 'DELETE'); }
async function updateCardApi(setId, cardId, front, back, example) { return apiRequest(`/sets/${setId}/cards/${cardId}`, 'PUT', { front, back, example }); }
async function fetchUserLang() {
    try {
        const data = await apiRequest('/user/lang');
        return data.lang || 'ru';
    } catch { return 'ru'; }
}

// Screen management
function showScreen(screenId) {
    document.querySelectorAll('.screen').forEach(s => s.classList.remove('active'));
    document.getElementById(screenId).classList.add('active');
}

function showModal(modalId) { document.getElementById(modalId).classList.add('active'); }
function hideModal(modalId) { document.getElementById(modalId).classList.remove('active'); }

// Render Logic
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
    
    setsList.querySelectorAll('.set-item').forEach(item => {
        item.addEventListener('click', () => {
            openSet(item.dataset.setId);
        });
    });
}

function renderCards() {
    const cardsPreview = document.getElementById('cards-preview');
    if (state.currentCards.length === 0) {
        cardsPreview.innerHTML = `<p style="text-align: center; color: rgba(255,255,255,0.5);">${t('noCards')}</p>`;
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
                <button class="edit-card btn-icon" data-card-id="${card._id}" title="${t('flashcards_edit_card')}">✏️</button>
                <button class="delete-card btn-icon" data-card-id="${card._id}" title="${t('delete')}">🗑</button>
            </div>
        </div>
    `).join('');
    
    // Reattach listeners
    cardsPreview.querySelectorAll('.edit-card').forEach(btn => {
        btn.addEventListener('click', (e) => { e.stopPropagation(); openEditModal(btn.dataset.cardId); });
    });
    cardsPreview.querySelectorAll('.delete-card').forEach(btn => {
        btn.addEventListener('click', async (e) => { e.stopPropagation(); await deleteCard(btn.dataset.cardId); });
    });
}

function renderStudyCard() {
    const card = state.currentCards[state.currentCardIndex];
    if (!card) return;
    const frontText = state.studyReversed ? card.back : card.front;
    const backText = state.studyReversed ? card.front : card.back;
    document.getElementById('card-front-text').textContent = frontText;
    document.getElementById('card-back-text').textContent = backText;
    
    // Example handling
    const exampleEl = document.getElementById('card-example-below');
    if (exampleEl) {
        if (card.example) {
            exampleEl.textContent = card.example;
            exampleEl.style.display = 'block';
        } else {
            exampleEl.style.display = 'none';
        }
    }
    document.getElementById('card-counter').textContent = `${state.currentCardIndex + 1}/${state.currentCards.length}`;
    
    // Reset visual rotation for new card
    // Note: state.isFlipped reset is handled in navigation logic
    gsap.set('#flashcard .card-inner', { rotationY: 0 });

    document.getElementById('prev-card').disabled = state.currentCardIndex === 0;
    document.getElementById('next-card').disabled = state.currentCardIndex === state.currentCards.length - 1;
}

// Data Actions
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

// Handlers for Sets and Cards (keeping logic identical)
async function handleCreateSet() {
    const input = document.getElementById('set-name-input');
    const name = input.value.trim();
    if (!name) { tg.showAlert(t('validationEnterName')); return; }
    try {
        await createSet(name);
        input.value = '';
        hideModal('create-set-modal');
        await loadSets();
        tg.HapticFeedback.notificationOccurred('success');
    } catch (error) { tg.showAlert(t('errorCreateSet')); }
}

async function handleDeleteSet() {
    if (!state.currentSet) return;
    try {
        await deleteSetApi(state.currentSet._id);
        hideModal('delete-modal');
        state.currentSet = null;
        await loadSets();
        showScreen('sets-screen');
        tg.HapticFeedback.notificationOccurred('success');
    } catch (error) { tg.showAlert(t('errorDeleteSet')); }
}

function openRenameSetModal() {
    if (!state.currentSet) return;
    const input = document.getElementById('rename-set-input');
    input.value = state.currentSet.name || '';
    showModal('rename-set-modal');
    input.focus();
}

async function handleRenameSet() {
    if (!state.currentSet) return;
    const input = document.getElementById('rename-set-input');
    const name = input.value.trim();
    if (!name) { tg.showAlert(t('validationEnterName')); return; }
    try {
        await updateSetApi(state.currentSet._id, name);
        hideModal('rename-set-modal');
        state.currentSet.name = name;
        document.getElementById('set-name').textContent = name;
        const idx = state.sets.findIndex(s => s._id === state.currentSet._id);
        if (idx !== -1) state.sets[idx].name = name;
        renderSets();
        tg.HapticFeedback.notificationOccurred('success');
    } catch (error) { tg.showAlert(t('errorCreateSet')); }
}

async function handleAddCard() {
    const front = document.getElementById('card-front-input').value.trim();
    const back = document.getElementById('card-back-input').value.trim();
    const example = document.getElementById('card-example-input').value.trim();
    if (!front || !back) { tg.showAlert(t('validationFillBothFields')); return; }
    try {
        await addCardApi(state.currentSet._id, front, back, example);
        document.getElementById('card-front-input').value = '';
        document.getElementById('card-back-input').value = '';
        document.getElementById('card-example-input').value = '';
        hideModal('add-card-modal');
        const data = await fetchCards(state.currentSet._id);
        state.currentCards = data.cards || [];
        renderCards();
        tg.HapticFeedback.notificationOccurred('success');
    } catch (error) { tg.showAlert(t('errorAddCard')); }
}

async function deleteCard(cardId) {
    try {
        await deleteCardApi(state.currentSet._id, cardId);
        const data = await fetchCards(state.currentSet._id);
        state.currentCards = data.cards || [];
        renderCards();
        tg.HapticFeedback.notificationOccurred('success');
    } catch (error) { tg.showAlert(t('errorDeleteCard')); }
}

function openEditModal(cardId) {
    const card = state.currentCards.find(c => c._id === cardId);
    if (!card) return;
    state.editCardId = cardId;
    document.getElementById('card-front-edit').value = card.front || '';
    document.getElementById('card-back-edit').value = card.back || '';
    document.getElementById('card-example-edit').value = card.example || '';
    showModal('edit-card-modal');
}

async function handleEditCard() {
    if (!state.editCardId) return;
    const front = document.getElementById('card-front-edit').value.trim();
    const back = document.getElementById('card-back-edit').value.trim();
    const example = document.getElementById('card-example-edit').value.trim();
    if (!front || !back) { tg.showAlert(t('validationFillBothFields')); return; }
    try {
        await updateCardApi(state.currentSet._id, state.editCardId, front, back, example);
        hideModal('edit-card-modal');
        state.editCardId = null;
        const data = await fetchCards(state.currentSet._id);
        state.currentCards = data.cards || [];
        renderCards();
        tg.HapticFeedback.notificationOccurred('success');
    } catch (error) { tg.showAlert(t('errorEditCard')); }
}

// ------------------------------------
// CHANGED ANIMATION LOGIC (GSAP)
// ------------------------------------

function startStudy() {
    if (state.currentCards.length === 0) return;
    state.currentCardIndex = 0;
    state.studyReversed = false;
    state.isFlipped = false;
    updateReverseButton();
    renderStudyCard();
    showScreen('study-screen');
    
    // Entrance animation for the card
    gsap.from('#flashcard', { y: 100, opacity: 0, duration: 0.8, ease: "back.out(1.7)" });
}

function nextCard() {
    if (state.currentCardIndex < state.currentCards.length - 1) {
        // Animate Out
        gsap.to('#flashcard', { 
            x: -window.innerWidth, 
            rotation: -20, 
            duration: 0.5, 
            ease: "power2.in",
            onComplete: () => {
                // Update State and DOM
                state.currentCardIndex++;
                state.isFlipped = false;
                renderStudyCard();
                
                // Immediately reset position for entrance but keep it hidden/offscreen if needed?
                // Actually start from opposite side for swipe effect
                gsap.set('#flashcard', { x: window.innerWidth, rotation: 20 });
                
                // Animate In
                gsap.to('#flashcard', { 
                    x: 0, 
                    rotation: 0, 
                    duration: 0.8, 
                    ease: "power3.out" 
                });
            }
        });
        tg.HapticFeedback.impactOccurred('light');
    }
}

function prevCard() {
    if (state.currentCardIndex > 0) {
        // Animate Out
        gsap.to('#flashcard', { 
            x: window.innerWidth, 
            rotation: 20, 
            duration: 0.5, 
            ease: "power2.in",
            onComplete: () => {
                state.currentCardIndex--;
                state.isFlipped = false;
                renderStudyCard();
                
                gsap.set('#flashcard', { x: -window.innerWidth, rotation: -20 });
                
                // Animate In
                gsap.to('#flashcard', { 
                    x: 0, 
                    rotation: 0, 
                    duration: 0.8, 
                    ease: "power3.out" 
                });
            }
        });
        tg.HapticFeedback.impactOccurred('light');
    }
}

function flipCard() {
    // Toggle state
    state.isFlipped = !state.isFlipped;
    
    // GSAP Flip
    // Front is 0deg, Back is 180deg (implied by design). 
    // We add 180 or set to specific depending on state.
    // If we want simple toggle:
    const targetRotation = state.isFlipped ? 180 : 0;
    
    gsap.to('#flashcard .card-inner', { 
        rotationY: targetRotation, 
        duration: 1.2, 
        ease: "elastic.out(1, 0.75)" 
    });
    
    tg.HapticFeedback.impactOccurred('light');
}

function exitStudyMode() {
    // Animate removal then switch screen
    gsap.to('#flashcard', {
        scale: 0.8,
        opacity: 0,
        duration: 0.3,
        onComplete: () => {
            showScreen('set-screen');
            // Reset for next time
            gsap.set('#flashcard', { scale: 1, opacity: 1, x: 0, rotation: 0 });
        }
    });
}

function toggleReverse() {
    state.studyReversed = !state.studyReversed;
    state.isFlipped = false;
    updateReverseButton();
    // Re-render essentially resets the content and flips it back to front (0deg)
    // We can do a little shake or fade to indicate change
    renderStudyCard();
    gsap.fromTo('#flashcard', { scale: 0.95 }, { scale: 1, duration: 0.4, ease: "elastic.out(1, 0.5)" });
    tg.HapticFeedback.impactOccurred('light');
}

function updateReverseButton() {
    const btn = document.getElementById('toggle-reverse');
    if (!btn) return;
    btn.classList.toggle('active', state.studyReversed);
}

function shuffleArrayInPlace(arr) {
    for (let i = arr.length - 1; i > 0; i--) {
        const j = Math.floor(Math.random() * (i + 1));
        [arr[i], arr[j]] = [arr[j], arr[i]];
    }
}

function shuffleStudyCards() {
    if (!state.currentCards || state.currentCards.length < 2) return;
    
    // Animation specific to shuffle
    gsap.to('#flashcard', { 
        rotation: 360, 
        scale: 0.5, 
        opacity: 0, 
        duration: 0.5, 
        onComplete: () => {
             shuffleArrayInPlace(state.currentCards);
             state.currentCardIndex = 0;
             state.isFlipped = false;
             renderStudyCard();
             
             // Spin back in
             gsap.set('#flashcard', { rotation: -180 });
             gsap.to('#flashcard', { rotation: 0, scale: 1, opacity: 1, duration: 0.6, ease: "back.out(1.5)" });
        }
    });
    
    tg.HapticFeedback.impactOccurred('light');
}

// Utility functions
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Event listeners
document.getElementById('create-set-btn').addEventListener('click', () => showModal('create-set-modal'));
document.getElementById('cancel-create-set').addEventListener('click', () => hideModal('create-set-modal'));
document.getElementById('confirm-create-set').addEventListener('click', handleCreateSet);
document.getElementById('back-to-sets').addEventListener('click', () => { state.currentSet = null; showScreen('sets-screen'); });
document.getElementById('study-btn').addEventListener('click', startStudy);
document.getElementById('add-card-btn').addEventListener('click', () => showModal('add-card-modal'));
document.getElementById('cancel-add-card').addEventListener('click', () => hideModal('add-card-modal'));
document.getElementById('confirm-add-card').addEventListener('click', handleAddCard);
document.getElementById('cancel-edit-card').addEventListener('click', () => { state.editCardId = null; hideModal('edit-card-modal'); });
document.getElementById('confirm-edit-card').addEventListener('click', handleEditCard);
document.getElementById('delete-set-btn').addEventListener('click', () => showModal('delete-modal'));
document.getElementById('cancel-delete').addEventListener('click', () => hideModal('delete-modal'));
document.getElementById('confirm-delete').addEventListener('click', handleDeleteSet);
document.getElementById('edit-set-btn').addEventListener('click', openRenameSetModal);
document.getElementById('cancel-rename-set').addEventListener('click', () => hideModal('rename-set-modal'));
document.getElementById('confirm-rename-set').addEventListener('click', handleRenameSet);

// New Exit Button
document.getElementById('exit-study-mode').addEventListener('click', exitStudyMode);
// Keep old back button working just in case (hidden via CSS usually)
document.getElementById('back-to-set').addEventListener('click', exitStudyMode);

document.getElementById('flashcard').addEventListener('click', flipCard);
document.getElementById('prev-card').addEventListener('click', prevCard);
document.getElementById('next-card').addEventListener('click', nextCard);
document.getElementById('shuffle-cards').addEventListener('click', shuffleStudyCards);
document.getElementById('toggle-reverse').addEventListener('click', toggleReverse);

// Input Enter handling
document.getElementById('set-name-input').addEventListener('keypress', (e) => { if (e.key === 'Enter') handleCreateSet(); });
document.getElementById('rename-set-input').addEventListener('keypress', (e) => { if (e.key === 'Enter') handleRenameSet(); });

// Keyboard navigation
document.addEventListener('keydown', (e) => {
    if (document.getElementById('study-screen').classList.contains('active')) {
        if (e.key === 'ArrowLeft') prevCard();
        else if (e.key === 'ArrowRight') nextCard();
        else if (e.key === ' ') flipCard();
        else if (e.key === 'Escape') exitStudyMode();
    }
});

// Swipe support
let touchStartX = 0;
let touchEndX = 0;
document.getElementById('flashcard').addEventListener('touchstart', (e) => { touchStartX = e.changedTouches[0].screenX; }, { passive: true });
document.getElementById('flashcard').addEventListener('touchend', (e) => {
    touchEndX = e.changedTouches[0].screenX;
    const diff = touchStartX - touchEndX;
    if (Math.abs(diff) > SWIPE_THRESHOLD_PX) {
        if (diff > 0) nextCard();
        else prevCard();
    }
}, { passive: true });

// Initialize app
async function init() {
    try {
        state.lang = await fetchUserLang();
        applyLocalization();
        await loadSets();
        showScreen('sets-screen');
        const loadingEl = document.getElementById('loading');
        if (loadingEl) loadingEl.remove();
    } catch (error) {
        applyLocalization();
        showScreen('sets-screen');
        const loadingEl = document.getElementById('loading');
        if (loadingEl) loadingEl.remove();
    }
}

init();
