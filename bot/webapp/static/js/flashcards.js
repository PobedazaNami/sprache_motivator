// Telegram Mini App - Premium Flashcards JavaScript with GSAP

// Constants
const SWIPE_THRESHOLD_PX = 50;
const GLOBAL_REVIEW_THRESHOLD_PX = 110;

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
        learnStat: 'Вчити',
        practiceStat: 'Практикувати',
        knownStat: 'Навчився',
        startGlobalStudy: 'ПОЧАТИ',
        dueNow: 'Зараз доступно {count} карток до повторення',
        noDueCards: 'Зараз немає карток для повторення',
        swipeKnow: 'Зрозуміло',
        swipeDontKnow: 'Вчити знову',
        sessionSummary: 'Сесію завершено · Знаю: {correct} · Не знаю: {incorrect} · Всього: {total}',
        deckLabel: 'Набір',
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
        flashcards_rename_set: 'Перейменувати набір',
        deleteCardTitle: 'Видалити картку?',
        deleteCardWarning: 'Ви впевнені, що хочете видалити цю картку?',
        photoObject: 'Сфотографувати об’єкт',
        uploadingImage: 'Завантаження...',
        errorUploadImage: 'Помилка завантаження зображення',
        errorDeleteImage: 'Помилка видалення зображення'
    },
    ru: {
        loading: 'Загрузка...',
        learnStat: 'Учить',
        practiceStat: 'Практиковать',
        knownStat: 'Изучил',
        startGlobalStudy: 'ПОЧАТИ',
        dueNow: 'Сейчас доступно {count} карточек к повторению',
        noDueCards: 'Сейчас нет карточек для повторения',
        swipeKnow: 'Понятно',
        swipeDontKnow: 'Учить снова',
        sessionSummary: 'Сессия завершена · Знаю: {correct} · Не знаю: {incorrect} · Всего: {total}',
        deckLabel: 'Колода',
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
        flashcards_rename_set: 'Переименовать набор',
        deleteCardTitle: 'Удалить карточку?',
        deleteCardWarning: 'Вы уверены, что хотите удалить эту карточку?',
        photoObject: 'Сфотографировать объект',
        uploadingImage: 'Загрузка...',
        errorUploadImage: 'Ошибка загрузки изображения',
        errorDeleteImage: 'Ошибка удаления изображения',
        errorDatabaseUnavailable: 'База данных недоступна. Изображения не могут быть сохранены.',
        errorImageTooLarge: 'Изображение слишком большое (макс 2МБ).',
        errorDatabaseUnavailable: 'База данных недоступна. Изображения не могут быть сохранены.',
        errorImageTooLarge: 'Изображение слишком большое (макс 2МБ).'
    }
};

// App state
let state = {
    userId: null,
    lang: 'ru',
    pendingDelete: null,
    sets: [],
    dashboard: { new: 0, learning: 0, known: 0, due: 0 },
    currentSet: null,
    currentCards: [],
    currentCardIndex: 0,
    studyMode: 'set',
    studyReversed: false,
    isFlipped: false,
    editCardId: null,
    sessionStats: { correct: 0, incorrect: 0 },
    drag: {
        active: false,
        pointerId: null,
        startX: 0,
        startY: 0,
        deltaX: 0,
        deltaY: 0,
        moved: false,
        suppressClickUntil: 0,
    }
};

// Get text by key
function t(key, params = null) {
    let template = TEXTS[state.lang]?.[key] || TEXTS['ru'][key] || key;
    if (!params) return template;
    for (const [name, value] of Object.entries(params)) {
        template = template.replaceAll(`{${name}}`, value);
    }
    return template;
}

// Apply localization
function applyLocalization() {
    document.getElementById('loading-text').textContent = t('loading');
    document.getElementById('sets-title').textContent = t('mySets');
    document.getElementById('create-set-text').textContent = t('createSet');
    document.getElementById('stat-new-label').textContent = t('learnStat');
    document.getElementById('stat-learning-label').textContent = t('practiceStat');
    document.getElementById('stat-known-label').textContent = t('knownStat');
    document.getElementById('start-global-study-text').textContent = t('startGlobalStudy');
    document.getElementById('swipe-badge-know').textContent = t('swipeKnow');
    document.getElementById('swipe-badge-dontknow').textContent = t('swipeDontKnow');
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
    renderDashboard();
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
async function fetchDashboard() { return apiRequest('/dashboard'); }
async function fetchGlobalSession() { return apiRequest('/session'); }
async function reviewGlobalSessionCard(cardId, result) { return apiRequest('/session/review', 'POST', { card_id: cardId, result }); }
async function createSet(name) { return apiRequest('/sets', 'POST', { name }); }
async function updateSetApi(setId, name) { return apiRequest(`/sets/${setId}`, 'PUT', { name }); }
async function deleteSetApi(setId) { return apiRequest(`/sets/${setId}`, 'DELETE'); }
async function fetchCards(setId) { return apiRequest(`/sets/${setId}/cards`); }
async function addCardApi(setId, front, back, example) { return apiRequest(`/sets/${setId}/cards`, 'POST', { front, back, example }); }
async function deleteCardApi(setId, cardId) { return apiRequest(`/sets/${setId}/cards/${cardId}`, 'DELETE'); }
async function updateCardApi(setId, cardId, front, back, example) { return apiRequest(`/sets/${setId}/cards/${cardId}`, 'PUT', { front, back, example }); }

// Image API
async function uploadCardImage(setId, cardId, file) {
    const resized = await resizeImageFile(file, 600);
    const formData = new FormData();
    formData.append('image', resized, 'photo.jpg');
    const response = await fetch(`${API_BASE}/sets/${setId}/cards/${cardId}/image`, {
        method: 'POST',
        headers: { 'X-Telegram-Init-Data': tg.initData },
        body: formData
    });
    if (!response.ok) {
        const statusText = response.status === 503 ? 'Service Unavailable (MongoDB)' : 
                          response.status === 413 ? 'Image Too Large' : 
                          `HTTP ${response.status}`;
        throw new Error(statusText);
    }
    return response.json();
}
function getCardImageUrl(setId, cardId) {
    return `${API_BASE}/sets/${setId}/cards/${cardId}/image`;
}
async function deleteCardImageApi(setId, cardId) { return apiRequest(`/sets/${setId}/cards/${cardId}/image`, 'DELETE'); }

// Resize image before uploading (max dimension, returns Blob)
function resizeImageFile(file, maxDim) {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = (e) => {
            const img = new Image();
            img.onload = () => {
                let w = img.width, h = img.height;
                if (w > maxDim || h > maxDim) {
                    if (w > h) { h = Math.round(h * maxDim / w); w = maxDim; }
                    else { w = Math.round(w * maxDim / h); h = maxDim; }
                }
                const canvas = document.createElement('canvas');
                canvas.width = w;
                canvas.height = h;
                canvas.getContext('2d').drawImage(img, 0, 0, w, h);
                canvas.toBlob((blob) => resolve(blob), 'image/jpeg', 0.82);
            };
            img.onerror = reject;
            img.src = e.target.result;
        };
        reader.onerror = reject;
        reader.readAsDataURL(file);
    });
}
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

function renderDashboard() {
    document.getElementById('stat-new-value').textContent = state.dashboard.new || 0;
    document.getElementById('stat-learning-value').textContent = state.dashboard.learning || 0;
    document.getElementById('stat-known-value').textContent = state.dashboard.known || 0;
    document.getElementById('dashboard-due-text').textContent = t('dueNow', { count: state.dashboard.due || 0 });
}

function hideSessionSummary() {
    const el = document.getElementById('session-summary');
    el.style.display = 'none';
    el.textContent = '';
}

function showSessionSummary(correct, incorrect, total) {
    const el = document.getElementById('session-summary');
    el.textContent = t('sessionSummary', { correct, incorrect, total });
    el.style.display = 'block';
}

function resetSwipeBadges() {
    gsap.set('#swipe-badge-know', { opacity: 0, scale: 0.92 });
    gsap.set('#swipe-badge-dontknow', { opacity: 0, scale: 0.92 });
}

function animateGsap(target, props) {
    return new Promise((resolve) => {
        gsap.to(target, {
            ...props,
            onComplete: () => {
                props.onComplete?.();
                resolve();
            },
        });
    });
}

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
            <span class="set-arrow"><i class="ph ph-caret-right"></i></span>
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
                ${card.has_image ? '<span class="card-preview-image-badge"><i class="ph ph-image"></i></span>' : ''}
                <span class="front">${escapeHtml(card.front)}</span>
                <span class="back"> — ${escapeHtml(card.back)}</span>
            </div>
            <div class="card-preview-actions">
                <button class="edit-card btn-icon" data-card-id="${card._id}" title="${t('flashcards_edit_card')}"><i class="ph ph-pencil-simple"></i></button>
                <button class="delete-card btn-icon" data-card-id="${card._id}" title="${t('delete')}"><i class="ph ph-trash"></i></button>
            </div>
        </div>
    `).join('');
    
    // Reattach listeners
    cardsPreview.querySelectorAll('.edit-card').forEach(btn => {
        btn.addEventListener('click', (e) => { e.stopPropagation(); openEditModal(btn.dataset.cardId); });
    });
    cardsPreview.querySelectorAll('.delete-card').forEach(btn => {
        btn.addEventListener('click', (e) => { e.stopPropagation(); confirmDeleteCard(btn.dataset.cardId); });
    });
}

function renderStudyCard() {
    const card = state.currentCards[state.currentCardIndex];
    if (!card) return;
    const isGlobal = state.studyMode === 'global';
    const frontText = !isGlobal && state.studyReversed ? card.back : card.front;
    const backText = !isGlobal && state.studyReversed ? card.front : card.back;
    document.getElementById('card-front-text').textContent = frontText;
    document.getElementById('card-back-text').textContent = backText;
    
    // Image handling on study card - ONLY on front side
    const frontImgWrapper = document.getElementById('card-front-image-wrapper');
    const backImgWrapper = document.getElementById('card-back-image-wrapper');
    const frontImg = document.getElementById('card-front-image');
    
    const currentSetId = isGlobal ? card.set_id : state.currentSet?._id;
    if (card.has_image && currentSetId) {
        const imgUrl = getCardImageUrl(currentSetId, card._id) + '?h=' + tg.initData.substring(0, 20);
        frontImg.src = imgUrl;
        frontImgWrapper.style.display = '';
        // Add auth header via fetch for the image
        loadAuthImage(frontImg, currentSetId, card._id);
    } else {
        frontImgWrapper.style.display = 'none';
        frontImg.src = '';
    }
    
    // Always hide back image wrapper
    if (backImgWrapper) {
        backImgWrapper.style.display = 'none';
    }
    
    // Example handling - On back side
    const exampleEl = document.getElementById('card-back-example');
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
    updateStudyModeUI();
}

// Load image with auth header (API returns Cloudinary URL)
async function loadAuthImage(imgEl, setId, cardId) {
    try {
        const resp = await fetch(getCardImageUrl(setId, cardId), {
            headers: { 'X-Telegram-Init-Data': tg.initData }
        });
        if (!resp.ok) { 
            imgEl.parentElement.style.display = 'none'; 
            return; 
        }
        const data = await resp.json();
        if (data.url) {
            imgEl.src = data.url;  // Cloudinary URL - no auth needed
        } else {
            imgEl.parentElement.style.display = 'none';
        }
    } catch (e) {
        console.error('Error loading image:', e);
        imgEl.parentElement.style.display = 'none';
    }
}

// ---- Image in Edit Modal ----
let editImagePendingFile = null;
let editImageRemoved = false;

function initEditImageHandlers() {
    const input = document.getElementById('edit-image-input');
    const removeBtn = document.getElementById('edit-image-remove');
    
    input.addEventListener('change', (e) => {
        const file = e.target.files[0];
        if (!file) return;
        editImagePendingFile = file;
        editImageRemoved = false;
        // Show preview
        const reader = new FileReader();
        reader.onload = (ev) => {
            document.getElementById('edit-image-img').src = ev.target.result;
            document.getElementById('edit-image-preview').style.display = '';
            document.getElementById('edit-image-label').style.display = 'none';
        };
        reader.readAsDataURL(file);
    });
    
    removeBtn.addEventListener('click', () => {
        editImagePendingFile = null;
        editImageRemoved = true;
        document.getElementById('edit-image-img').src = '';
        document.getElementById('edit-image-preview').style.display = 'none';
        document.getElementById('edit-image-label').style.display = '';
        document.getElementById('edit-image-input').value = '';
    });
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

async function loadDashboard() {
    try {
        const data = await fetchDashboard();
        state.dashboard = {
            new: data.new || 0,
            learning: data.learning || 0,
            known: data.known || 0,
            due: data.due || 0,
        };
        renderDashboard();
    } catch (error) {
        console.error('Error loading dashboard:', error);
    }
}

async function openSet(setId) {
    try {
        hideSessionSummary();
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

function updateStudyModeUI() {
    const isGlobal = state.studyMode === 'global';
    const prevBtn = document.getElementById('prev-card');
    const nextBtn = document.getElementById('next-card');
    const headerRight = document.querySelector('.header-right');
    const timer = document.getElementById('study-timer');
    const timerSetup = document.getElementById('timer-setup');
    const context = document.getElementById('study-card-context');
    const studyScreen = document.getElementById('study-screen');
    const flashcard = document.getElementById('flashcard');
    const currentCard = state.currentCards[state.currentCardIndex];

    prevBtn.style.display = isGlobal ? 'none' : '';
    nextBtn.style.display = isGlobal ? 'none' : '';
    headerRight.style.display = isGlobal ? 'none' : 'flex';
    timer.style.display = isGlobal ? 'none' : '';
    timerSetup.style.display = 'none';
    studyScreen.classList.toggle('global-study-mode', isGlobal);
    flashcard.classList.toggle('global-swipe-enabled', isGlobal);

    if (isGlobal) {
        context.textContent = currentCard?.set_name ? `${t('deckLabel')}: ${currentCard.set_name}` : '';
        context.style.display = currentCard?.set_name ? 'block' : 'none';
    } else {
        context.style.display = 'none';
    }
}

async function startGlobalStudySession() {
    try {
        hideSessionSummary();
        const data = await fetchGlobalSession();
        const cards = data.cards || [];

        if (cards.length === 0) {
            tg.showAlert(t('noDueCards'));
            return;
        }

        state.currentSet = null;
        state.currentCards = cards;
        state.currentCardIndex = 0;
        state.studyMode = 'global';
        state.studyReversed = false;
        state.isFlipped = false;
        state.sessionStats = { correct: 0, incorrect: 0 };
        resetSwipeBadges();
        renderStudyCard();
        updateStudyModeUI();
        showScreen('study-screen');
        gsap.from('#flashcard', { y: 100, opacity: 0, duration: 0.8, ease: 'back.out(1.7)' });
    } catch (error) {
        console.error('Error starting global session:', error);
        tg.showAlert(t('errorLoadCards'));
    }
}

async function finishGlobalStudySession() {
    const total = state.sessionStats.correct + state.sessionStats.incorrect;
    stopTimer();
    resetSwipeBadges();
    await loadSets();
    await loadDashboard();
    showSessionSummary(state.sessionStats.correct, state.sessionStats.incorrect, total);
    state.studyMode = 'set';
    state.currentCards = [];
    state.currentCardIndex = 0;
    state.isFlipped = false;
    showScreen('sets-screen');
    tg.HapticFeedback.notificationOccurred('success');
}

async function handleGlobalSessionReview(result) {
    const card = state.currentCards[state.currentCardIndex];
    if (!card) return;

    try {
        await reviewGlobalSessionCard(card._id, result);
        if (result === 'know') {
            state.sessionStats.correct += 1;
        } else {
            state.sessionStats.incorrect += 1;
        }

        if (state.currentCardIndex >= state.currentCards.length - 1) {
            await finishGlobalStudySession();
            return;
        }

        state.currentCardIndex += 1;
        state.isFlipped = false;
        resetSwipeBadges();
        renderStudyCard();
        updateStudyModeUI();
        gsap.fromTo('#flashcard', { x: 80, opacity: 0.5 }, { x: 0, opacity: 1, duration: 0.35, ease: 'power2.out' });
        tg.HapticFeedback.notificationOccurred('success');
    } catch (error) {
        console.error('Error reviewing global session card:', error);
        tg.showAlert(t('errorEditCard'));
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
        await loadDashboard();
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
        await loadDashboard();
        showScreen('sets-screen');
        tg.HapticFeedback.notificationOccurred('success');
    } catch (error) { tg.showAlert(t('errorDeleteSet')); }
}

function confirmDeleteSet() {
    state.pendingDelete = { type: 'set' };
    document.getElementById('delete-title').textContent = t('deleteTitle');
    document.getElementById('delete-warning').textContent = t('deleteWarning');
    showModal('delete-modal');
}

function confirmDeleteCard(cardId) {
    state.pendingDelete = { type: 'card', id: cardId };
    document.getElementById('delete-title').textContent = t('deleteCardTitle');
    document.getElementById('delete-warning').textContent = t('deleteCardWarning');
    showModal('delete-modal');
}

async function executeDelete() {
    if (!state.pendingDelete) return;
    
    if (state.pendingDelete.type === 'set') {
        await handleDeleteSet();
    } else if (state.pendingDelete.type === 'card') {
        const cardId = state.pendingDelete.id;
        try {
            await deleteCardApi(state.currentSet._id, cardId);
            hideModal('delete-modal');
            const data = await fetchCards(state.currentSet._id);
            state.currentCards = data.cards || [];
            renderCards();
            await loadDashboard();
            tg.HapticFeedback.notificationOccurred('success');
        } catch (error) { tg.showAlert(t('errorDeleteCard')); }
    }
    state.pendingDelete = null;
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
        await loadDashboard();
        tg.HapticFeedback.notificationOccurred('success');
    } catch (error) { tg.showAlert(t('errorAddCard')); }
}

async function deleteCard(cardId) {
    try {
        await deleteCardApi(state.currentSet._id, cardId);
        const data = await fetchCards(state.currentSet._id);
        state.currentCards = data.cards || [];
        renderCards();
        await loadDashboard();
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
    
    // Reset image state
    editImagePendingFile = null;
    editImageRemoved = false;
    document.getElementById('edit-image-input').value = '';
    document.getElementById('edit-image-text').textContent = t('photoObject');
    
    if (card.has_image && state.currentSet) {
        // Load existing image preview
        const img = document.getElementById('edit-image-img');
        loadAuthImage(img, state.currentSet._id, cardId);
        document.getElementById('edit-image-preview').style.display = '';
        document.getElementById('edit-image-label').style.display = 'none';
    } else {
        document.getElementById('edit-image-preview').style.display = 'none';
        document.getElementById('edit-image-label').style.display = '';
        document.getElementById('edit-image-img').src = '';
    }
    
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
        
        // Handle image changes
        if (editImageRemoved) {
            try { await deleteCardImageApi(state.currentSet._id, state.editCardId); } catch(e) { console.warn('Image delete failed:', e); }
        }
        if (editImagePendingFile) {
            const label = document.getElementById('edit-image-label');
            const origText = document.getElementById('edit-image-text').textContent;
            document.getElementById('edit-image-text').textContent = t('uploadingImage');
            label.classList.add('uploading');
            try {
                await uploadCardImage(state.currentSet._id, state.editCardId, editImagePendingFile);
            } catch(e) {
                console.error('Image upload failed:', e);
                // Check if it's a 503 (service unavailable - MongoDB)
                if (e.message && e.message.includes('503')) {
                    tg.showAlert(t('errorDatabaseUnavailable'));
                } else if (e.message && e.message.includes('413')) {
                    tg.showAlert(t('errorImageTooLarge'));
                } else {
                    tg.showAlert(t('errorUploadImage') + ' ' + (e.message || ''));
                }
            }
            label.classList.remove('uploading');
            document.getElementById('edit-image-text').textContent = origText;
        }
        editImagePendingFile = null;
        editImageRemoved = false;
        
        hideModal('edit-card-modal');
        state.editCardId = null;
        const data = await fetchCards(state.currentSet._id);
        state.currentCards = data.cards || [];
        renderCards();
        tg.HapticFeedback.notificationOccurred('success');
    } catch (error) { tg.showAlert(t('errorEditCard')); }
}

// ------------------------------------
// STUDY TIMER LOGIC
// ------------------------------------

let timerInterval = null;
let timerSeconds = 0;
let timerRunning = false;

function initTimer() {
    const display = document.getElementById('timer-display');
    const setup = document.getElementById('timer-setup');
    const rangeValue = document.getElementById('timer-range-value');
    const minusBtn = document.getElementById('timer-minus');
    const plusBtn = document.getElementById('timer-plus');
    const startBtn = document.getElementById('timer-start-btn');
    const closeBtn = document.getElementById('timer-close-btn');
    let selectedMinutes = 5;

    // Toggle setup panel on click
    display.addEventListener('click', (e) => {
        e.stopPropagation();
        if (timerRunning) {
            // If timer is running, click stops it and resets
            stopTimer();
            return;
        }
        setup.style.display = setup.style.display === 'none' ? 'block' : 'none';
    });

    const clampMinutes = (value) => Math.min(60, Math.max(1, value));
    const updateMinutesUI = () => {
        rangeValue.textContent = selectedMinutes;
    };

    // Step -5 minutes
    minusBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        selectedMinutes = clampMinutes(selectedMinutes - 5);
        updateMinutesUI();
        tg.HapticFeedback.impactOccurred('light');
    });

    // Step +5 minutes
    plusBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        selectedMinutes = clampMinutes(selectedMinutes + 5);
        updateMinutesUI();
        tg.HapticFeedback.impactOccurred('light');
    });

    // Start timer
    startBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        startTimer(selectedMinutes);
        setup.style.display = 'none';
    });

    // Close setup without starting
    closeBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        setup.style.display = 'none';
    });

    // Close setup when clicking outside
    document.addEventListener('click', (e) => {
        if (!setup.contains(e.target) && !display.contains(e.target)) {
            setup.style.display = 'none';
        }
    });

    updateMinutesUI();
}

function startTimer(minutes) {
    stopTimer(); // clear any existing
    timerSeconds = minutes * 60;
    timerRunning = true;
    updateTimerDisplay();
    updateTimerStyle();

    timerInterval = setInterval(() => {
        timerSeconds--;
        updateTimerDisplay();
        updateTimerStyle();

        if (timerSeconds <= 0) {
            timerSeconds = 0;
            clearInterval(timerInterval);
            timerInterval = null;
            timerRunning = false;
            onTimerDone();
        }
    }, 1000);

    tg.HapticFeedback.impactOccurred('light');
}

function stopTimer() {
    if (timerInterval) {
        clearInterval(timerInterval);
        timerInterval = null;
    }
    timerRunning = false;
    timerSeconds = 0;
    updateTimerDisplay();
    resetTimerStyle();
}

function updateTimerDisplay() {
    const m = Math.floor(timerSeconds / 60);
    const s = timerSeconds % 60;
    const text = document.getElementById('timer-text');
    text.textContent = `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
}

function updateTimerStyle() {
    const display = document.getElementById('timer-display');
    display.classList.remove('timer-active', 'timer-warning', 'timer-danger', 'timer-done');
    if (!timerRunning) return;
    if (timerSeconds <= 10) {
        display.classList.add('timer-danger');
    } else if (timerSeconds <= 30) {
        display.classList.add('timer-warning');
    } else {
        display.classList.add('timer-active');
    }
}

function resetTimerStyle() {
    const display = document.getElementById('timer-display');
    display.classList.remove('timer-active', 'timer-warning', 'timer-danger', 'timer-done');
}

function onTimerDone() {
    const display = document.getElementById('timer-display');
    display.classList.add('timer-done');
    document.getElementById('timer-text').textContent = '00:00';
    tg.HapticFeedback.notificationOccurred('warning');
    // Auto-remove done state after 5 seconds
    setTimeout(() => {
        display.classList.remove('timer-done');
    }, 5000);
}

// ------------------------------------
// CHANGED ANIMATION LOGIC (GSAP)
// ------------------------------------

function startStudy() {
    if (state.currentCards.length === 0) return;
    state.studyMode = 'set';
    state.currentCardIndex = 0;
    state.studyReversed = false;
    state.isFlipped = false;
    updateReverseButton();
    renderStudyCard();
    updateStudyModeUI();
    showScreen('study-screen');
    
    // Entrance animation for the card
    gsap.from('#flashcard', { y: 100, opacity: 0, duration: 0.8, ease: "back.out(1.7)" });
}

function nextCard() {
    if (state.studyMode !== 'set') return;
    if (state.currentCardIndex < state.currentCards.length - 1) {
        // Animate Out
        gsap.to('#flashcard', { 
            x: -window.innerWidth, 
            rotation: -20, 
            duration: 0.35, 
            ease: "power2.in",
            onComplete: () => {
                // Update State and DOM
                state.currentCardIndex++;
                state.isFlipped = false;
                renderStudyCard();
                
                gsap.set('#flashcard', { x: window.innerWidth, rotation: 20 });
                
                // Animate In
                gsap.to('#flashcard', { 
                    x: 0, 
                    rotation: 0, 
                    duration: 0.5, 
                    ease: "power3.out" 
                });
            }
        });
        tg.HapticFeedback.impactOccurred('light');
    }
}

function prevCard() {
    if (state.studyMode !== 'set') return;
    if (state.currentCardIndex > 0) {
        // Animate Out
        gsap.to('#flashcard', { 
            x: window.innerWidth, 
            rotation: 20, 
            duration: 0.35, 
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
                    duration: 0.5, 
                    ease: "power3.out" 
                });
            }
        });
        tg.HapticFeedback.impactOccurred('light');
    }
}

function flipCard() {
    if (Date.now() < state.drag.suppressClickUntil) return;
    // Toggle state
    state.isFlipped = !state.isFlipped;
    
    const targetRotation = state.isFlipped ? 180 : 0;
    
    gsap.to('#flashcard .card-inner', { 
        rotationY: targetRotation, 
        duration: 0.5, 
        ease: "back.out(1.5)" 
    });

    updateStudyModeUI();
    
    tg.HapticFeedback.impactOccurred('light');
}

function exitStudyMode() {
    // Stop and reset the timer
    stopTimer();
    document.getElementById('timer-setup').style.display = 'none';

    // Animate removal then switch screen
    gsap.to('#flashcard', {
        scale: 0.8,
        opacity: 0,
        duration: 0.3,
        onComplete: async () => {
            resetSwipeBadges();
            if (state.studyMode === 'global') {
                state.studyMode = 'set';
                await Promise.all([loadSets(), loadDashboard()]);
                showScreen('sets-screen');
            } else {
                showScreen('set-screen');
            }
            // Reset for next time
            gsap.set('#flashcard', { scale: 1, opacity: 1, x: 0, rotation: 0 });
        }
    });
}

function toggleReverse() {
    if (state.studyMode !== 'set') return;
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
    btn.classList.toggle('active', state.studyMode === 'set' && state.studyReversed);
}

function shuffleArrayInPlace(arr) {
    for (let i = arr.length - 1; i > 0; i--) {
        const j = Math.floor(Math.random() * (i + 1));
        [arr[i], arr[j]] = [arr[j], arr[i]];
    }
}

function shuffleStudyCards() {
    if (state.studyMode !== 'set') return;
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
document.getElementById('start-global-study-btn').addEventListener('click', startGlobalStudySession);
document.getElementById('cancel-create-set').addEventListener('click', () => hideModal('create-set-modal'));
document.getElementById('confirm-create-set').addEventListener('click', handleCreateSet);
document.getElementById('back-to-sets').addEventListener('click', () => { state.currentSet = null; showScreen('sets-screen'); });
document.getElementById('study-btn').addEventListener('click', startStudy);
document.getElementById('add-card-btn').addEventListener('click', () => showModal('add-card-modal'));
document.getElementById('cancel-add-card').addEventListener('click', () => hideModal('add-card-modal'));
document.getElementById('confirm-add-card').addEventListener('click', handleAddCard);
document.getElementById('cancel-edit-card').addEventListener('click', () => { state.editCardId = null; hideModal('edit-card-modal'); });
document.getElementById('confirm-edit-card').addEventListener('click', handleEditCard);

// Delete handlers (Sets & Cards)
document.getElementById('delete-set-btn').addEventListener('click', confirmDeleteSet);
document.getElementById('cancel-delete').addEventListener('click', () => hideModal('delete-modal'));
document.getElementById('confirm-delete').addEventListener('click', executeDelete);

// Rename Set
document.getElementById('set-name-trigger').addEventListener('click', openRenameSetModal);
document.getElementById('cancel-rename-set').addEventListener('click', () => hideModal('rename-set-modal'));
document.getElementById('confirm-rename-set').addEventListener('click', handleRenameSet);

// New Exit Button
document.getElementById('exit-study-mode').addEventListener('click', exitStudyMode);
// Keep old back button working just in case (hidden via CSS usually)
document.getElementById('back-to-set').addEventListener('click', exitStudyMode);

document.getElementById('flashcard').addEventListener('click', flipCard);
document.getElementById('flashcard').addEventListener('pointerdown', onGlobalPointerDown);
document.getElementById('flashcard').addEventListener('pointermove', onGlobalPointerMove);
document.getElementById('flashcard').addEventListener('pointerup', onGlobalPointerUp);
document.getElementById('flashcard').addEventListener('pointercancel', onGlobalPointerUp);
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
        if (e.key === 'ArrowLeft' && state.studyMode === 'set') prevCard();
        else if (e.key === 'ArrowRight' && state.studyMode === 'set') nextCard();
        else if (e.key === ' ') flipCard();
        else if (e.key === 'Escape') exitStudyMode();
    }
});

// Swipe support
let touchStartX = 0;
let touchEndX = 0;
document.getElementById('flashcard').addEventListener('touchstart', (e) => {
    if (state.studyMode === 'global') {
        const touch = e.changedTouches[0];
        beginGlobalDrag(touch.identifier, touch.screenX, touch.screenY);
        return;
    }
    touchStartX = e.changedTouches[0].screenX;
}, { passive: true });
document.getElementById('flashcard').addEventListener('touchmove', (e) => {
    if (state.studyMode !== 'global' || !state.drag.active) {
        return;
    }

    const touch = Array.from(e.changedTouches).find((item) => item.identifier === state.drag.pointerId)
        || Array.from(e.touches).find((item) => item.identifier === state.drag.pointerId);

    if (!touch) {
        return;
    }

    e.preventDefault();
    updateGlobalDrag(touch.screenX, touch.screenY);
}, { passive: false });
document.getElementById('flashcard').addEventListener('touchend', (e) => {
    if (state.studyMode === 'global') {
        const touch = Array.from(e.changedTouches).find((item) => item.identifier === state.drag.pointerId);
        if (touch) {
            e.preventDefault();
            finishGlobalDrag();
        }
        return;
    }
    touchEndX = e.changedTouches[0].screenX;
    const diff = touchStartX - touchEndX;
    if (Math.abs(diff) > SWIPE_THRESHOLD_PX) {
        if (diff > 0) nextCard();
        else prevCard();
    }
}, { passive: true });

function updateGlobalSwipeVisuals(deltaX, deltaY) {
    const rotation = deltaX * 0.05;
    gsap.set('#flashcard', { x: deltaX, y: deltaY * 0.12, rotation });

    const positiveOpacity = Math.min(Math.abs(Math.max(deltaX, 0)) / GLOBAL_REVIEW_THRESHOLD_PX, 1);
    const negativeOpacity = Math.min(Math.abs(Math.min(deltaX, 0)) / GLOBAL_REVIEW_THRESHOLD_PX, 1);
    gsap.set('#swipe-badge-know', { opacity: positiveOpacity, scale: 0.92 + positiveOpacity * 0.08 });
    gsap.set('#swipe-badge-dontknow', { opacity: negativeOpacity, scale: 0.92 + negativeOpacity * 0.08 });
}

function resetGlobalSwipePosition(animated = true) {
    resetSwipeBadges();
    if (animated) {
        gsap.to('#flashcard', { x: 0, y: 0, rotation: 0, duration: 0.22, ease: 'power2.out' });
    } else {
        gsap.set('#flashcard', { x: 0, y: 0, rotation: 0 });
    }
}

async function resolveGlobalSwipe(result, direction) {
    state.drag.active = false;
    state.drag.moved = false;
    state.drag.suppressClickUntil = Date.now() + 250;
    resetSwipeBadges();
    const exitX = direction === 'right' ? window.innerWidth * 1.2 : -window.innerWidth * 1.2;
    await animateGsap('#flashcard', { x: exitX, rotation: direction === 'right' ? 18 : -18, duration: 0.22, ease: 'power2.in' });
    gsap.set('#flashcard', { x: 0, y: 0, rotation: 0 });
    await handleGlobalSessionReview(result);
}

function beginGlobalDrag(pointerId, startX, startY) {
    if (state.studyMode !== 'global') return;
    state.drag.active = true;
    state.drag.pointerId = pointerId;
    state.drag.startX = startX;
    state.drag.startY = startY;
    state.drag.deltaX = 0;
    state.drag.deltaY = 0;
    state.drag.moved = false;
}

function updateGlobalDrag(currentX, currentY) {
    state.drag.deltaX = currentX - state.drag.startX;
    state.drag.deltaY = currentY - state.drag.startY;

    if (Math.abs(state.drag.deltaX) < 6 && Math.abs(state.drag.deltaY) < 6) {
        return;
    }

    state.drag.moved = true;
    updateGlobalSwipeVisuals(state.drag.deltaX, state.drag.deltaY);
}

async function finishGlobalDrag() {
    if (!state.drag.active) return;

    const deltaX = state.drag.deltaX;
    state.drag.active = false;
    state.drag.pointerId = null;

    if (!state.drag.moved) {
        resetGlobalSwipePosition(false);
        return;
    }

    if (deltaX >= GLOBAL_REVIEW_THRESHOLD_PX) {
        await resolveGlobalSwipe('know', 'right');
        return;
    }

    if (deltaX <= -GLOBAL_REVIEW_THRESHOLD_PX) {
        await resolveGlobalSwipe('dontknow', 'left');
        return;
    }

    state.drag.suppressClickUntil = Date.now() + 180;
    resetGlobalSwipePosition();
}

function onGlobalPointerDown(e) {
    if (state.studyMode !== 'global') return;
    beginGlobalDrag(e.pointerId, e.screenX, e.screenY);
    document.getElementById('flashcard').setPointerCapture?.(e.pointerId);
}

function onGlobalPointerMove(e) {
    if (state.studyMode !== 'global' || !state.drag.active || state.drag.pointerId !== e.pointerId) return;
    updateGlobalDrag(e.screenX, e.screenY);
}

async function onGlobalPointerUp(e) {
    if (state.studyMode !== 'global' || state.drag.pointerId !== e.pointerId) return;
    document.getElementById('flashcard').releasePointerCapture?.(e.pointerId);
    await finishGlobalDrag();
}

// GSAP Button Animations
function initButtonAnimations() {
    const btns = document.querySelectorAll('.btn-nav-floating, .btn-full-width, .icon-btn');
    btns.forEach(btn => {
        // Hover
        btn.addEventListener('mouseenter', () => {
            if (!btn.disabled) {
                gsap.to(btn, { scale: 1.05, duration: 0.3, ease: 'back.out(1.7)' });
                // Add glow if it's a floating button
                if (btn.classList.contains('btn-nav-floating')) {
                    gsap.to(btn, { boxShadow: "0 0 20px var(--accent-color)", borderColor: "var(--accent-color)", color: "#fff", duration: 0.3 });
                }
            }
        });
        
        // Hover out
        btn.addEventListener('mouseleave', () => {
            gsap.to(btn, { scale: 1, duration: 0.3, ease: 'power2.out' });
             if (btn.classList.contains('btn-nav-floating')) {
                gsap.to(btn, { boxShadow: "0 4px 20px rgba(0,0,0,0.4)", borderColor: "rgba(255,255,255,0.1)", color: "var(--accent-color)", duration: 0.3 });
            }
        });
        
        // Click press
        btn.addEventListener('mousedown', () => {
            if (!btn.disabled) gsap.to(btn, { scale: 0.95, duration: 0.1 });
        });
        
        // Click release
        btn.addEventListener('mouseup', () => {
            if (!btn.disabled) gsap.to(btn, { scale: 1.05, duration: 0.4, ease: 'elastic.out(1, 0.3)' });
        });
    });
}

// Initialize app
async function init() {
    try {
        state.lang = await fetchUserLang();
        applyLocalization();
        await Promise.all([loadSets(), loadDashboard()]);
        initButtonAnimations(); // Initialize animations
        initTimer(); // Initialize study timer
        initEditImageHandlers(); // Initialize image upload handlers
        showScreen('sets-screen');
        const loadingEl = document.getElementById('loading');
        if (loadingEl) loadingEl.remove();
    } catch (error) {
        console.error(error);
        applyLocalization();
        showScreen('sets-screen');
        const loadingEl = document.getElementById('loading');
        if (loadingEl) loadingEl.remove();
    }
}

init();
