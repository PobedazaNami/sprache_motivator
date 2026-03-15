'use strict';

// ---------------------------------------------------------------------------
// Telegram WebApp init
// ---------------------------------------------------------------------------
const tg = window.Telegram?.WebApp;
if (tg) {
    tg.expand();
    tg.ready();
}

function getTgUserId() {
    return String(tg?.initDataUnsafe?.user?.id ?? 'anonymous');
}

function getTgInitData() {
    return tg?.initData ?? '';
}

// ---------------------------------------------------------------------------
// State
// ---------------------------------------------------------------------------
const state = {
    session: null,          // { videoId, title, cues, selectedLanguage }
    availableVideos: [],
    selectedVideoId: null,
    loadingVideoId: null,
    pendingAutoplay: false,
    activeCueIndex: -1,
    isPlaying: false,
    isLookingUp: false,
    lookingUpWord: null,    // surface form being queried
    popup: null,            // current word card
    player: null,           // YT.Player instance
    intervalId: null,
};

// ---------------------------------------------------------------------------
// Utility: tokenize
// ---------------------------------------------------------------------------
function normalizeToken(token) {
    return token.replace(/^[^\p{L}\p{N}]+|[^\p{L}\p{N}]+$/gu, '').toLowerCase();
}

function tokenize(text) {
    const pieces = text.match(/\p{L}+(?:[''\-]\p{L}+)*|\d+|[^\s]/gu) || [];
    return pieces.map((piece) => {
        const normalized = normalizeToken(piece);
        return { value: piece, normalized, clickable: Boolean(normalized) };
    });
}

function shouldAppendSpace(current, next) {
    if (!next) return false;
    if (/^[([{«„'"-]$/u.test(current.value)) return false;
    if (/^[,.;:!?%)\]}'"»…]$/u.test(next.value)) return false;
    return true;
}

function extractVideoId(input) {
    const m = input.trim().match(
        /(?:youtube\.com\/(?:watch\?.*v=|embed\/|v\/)|youtu\.be\/|shorts\/)?([\w-]{11})/
    );
    const id = m?.[1];
    if (id && /^[\w-]{11}$/.test(id)) return id;
    return null;
}

// ---------------------------------------------------------------------------
const $ = (id) => document.getElementById(id);
const screenLoading  = $('screen-loading');
const screenMain     = $('screen-main');
const statusLine     = $('status-line');
const videosList     = $('videos-list');
const reloadVideosBtn = $('reload-videos-btn');
const playerPlaceholder = $('player-placeholder');
const ytContainer    = $('yt-container');
const pauseOverlay   = $('pause-overlay');
const subtitleOverlay = $('subtitle-overlay');
const subtitleLine   = $('subtitle-line');
const wordPopup      = $('word-popup');
const popupWord      = $('popup-word');
const popupBody      = $('popup-body');
const popupClose     = $('popup-close');

// ---------------------------------------------------------------------------
// Screen management
// ---------------------------------------------------------------------------
function showScreen(id) {
    document.querySelectorAll('.screen').forEach(s => s.classList.remove('active'));
    $(id).classList.add('active');
}

// ---------------------------------------------------------------------------
// API helpers
// ---------------------------------------------------------------------------
const API_BASE = '';

async function apiFetch(path, { method = 'GET', body = null } = {}) {
    const headers = {
        'Content-Type': 'application/json',
        'X-Telegram-Init-Data': getTgInitData(),
        'X-User-Id': getTgUserId(),
    };
    const opts = { method, headers };
    if (body) opts.body = JSON.stringify(body);
    const res = await fetch(API_BASE + path, opts);
    if (!res.ok) {
        const text = await res.text().catch(() => '');
        throw new Error(text || res.statusText);
    }
    return res.json();
}

// ---------------------------------------------------------------------------
// Load video session
// Flow: extract videoId → server fetches subtitles via Invidious API →
// mount YouTube player in user's browser (plays fine from any IP).
// ---------------------------------------------------------------------------
async function loadSession(input, preferredTitle = '') {
    const videoId = extractVideoId(input);
    if (!videoId) {
        setStatus('Невірний ідентифікатор відео', true);
        return;
    }

    setStatus('Відкриваю відео і підтягую субтитри…');
    state.selectedVideoId = videoId;
    state.loadingVideoId = videoId;
    state.session = null;
    state.activeCueIndex = -1;
    renderSubtitles(-1);
    renderVideos(state.availableVideos || []);
    mountPlayer(videoId);

    try {
        const data = await apiFetch('/api/subtitle/session', {
            method: 'POST',
            body: { input: videoId, title: preferredTitle },
        });

        state.session = data;
        state.activeCueIndex = -1;
        state.loadingVideoId = null;
        setStatus(`${data.cues.length} субтитрів • ${data.selectedLanguage}`);
    } catch (err) {
        state.loadingVideoId = null;
        setStatus('Помилка: ' + err.message, true);
    } finally {
        renderVideos(state.availableVideos || []);
    }
}

async function loadVideoCatalog() {
    setStatus('Завантажую список відео…');
    if (reloadVideosBtn) reloadVideosBtn.disabled = true;
    try {
        const data = await apiFetch('/api/subtitle/videos');
        state.availableVideos = data.videos || [];
        renderVideos(state.availableVideos);
        setStatus('Оберіть відео зі списку');
    } catch (err) {
        setStatus('Помилка: ' + err.message, true);
    } finally {
        if (reloadVideosBtn) reloadVideosBtn.disabled = false;
        showScreen('screen-main');
    }
}

function formatPublishedDate(value) {
    if (!value) return '';
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return '';
    return date.toLocaleDateString('uk-UA', { day: '2-digit', month: 'short', year: 'numeric' });
}

function renderVideos(videos) {
    if (!videosList) return;
    if (!videos.length) {
        videosList.innerHTML = '<p class="videos-empty">Список відео порожній.</p>';
        return;
    }

    videosList.innerHTML = videos.map((video) => {
        const selected = video.videoId === state.selectedVideoId ? ' is-selected' : '';
        const loading = video.videoId === state.loadingVideoId ? ' is-loading' : '';
        const dateLabel = formatPublishedDate(video.publishedAt);
        return `
            <button type="button" class="video-card${selected}${loading}" data-video-id="${esc(video.videoId)}">
                <img class="video-thumb" src="${esc(video.thumbnailUrl || '')}" alt="${esc(video.title)}" loading="lazy" />
                <span class="video-card-body">
                    <span class="video-card-title">${esc(video.title)}</span>
                    <span class="video-card-meta">${esc(dateLabel)}</span>
                </span>
            </button>`;
    }).join('');

    videosList.querySelectorAll('[data-video-id]').forEach((el) => {
        el.addEventListener('click', () => {
            const video = videos.find((item) => item.videoId === el.dataset.videoId);
            loadSession(el.dataset.videoId, video?.title || '');
        });
    });
}

// ---------------------------------------------------------------------------
// YouTube IFrame Player
// ---------------------------------------------------------------------------
let ytApiReady = false;
let pendingVideoId = null;

window.onYouTubeIframeAPIReady = function () {
    ytApiReady = true;
    if (pendingVideoId) {
        createPlayer(pendingVideoId);
        pendingVideoId = null;
    }
};

function mountPlayer(videoId) {
    playerPlaceholder.style.display = 'none';
    ytContainer.style.display = 'flex';
    pauseOverlay.style.display = 'none';
    state.pendingAutoplay = true;

    if (state.player) {
        state.player.loadVideoById(videoId);
        startCueInterval();
        return;
    }

    if (ytApiReady) {
        createPlayer(videoId);
    } else {
        pendingVideoId = videoId;
    }
}

function createPlayer(videoId) {
    state.player = new YT.Player('yt-player', {
        videoId,
        width: '100%',
        height: '100%',
        playerVars: {
            autoplay: 1,
            controls: 1,
            enablejsapi: 1,
            modestbranding: 1,
            playsinline: 1,
            rel: 0,
        },
        events: {
            onReady: () => {
                if (state.pendingAutoplay) {
                    state.player?.playVideo?.();
                }
                startCueInterval();
            },
            onStateChange: onPlayerStateChange,
        },
    });
}

function onPlayerStateChange(event) {
    const PLAYING = 1;
    const BUFFERING = 3;
    const PAUSED = 2;
    const ENDED = 0;

    if (event.data === PLAYING || event.data === BUFFERING) {
        state.isPlaying = true;
        state.pendingAutoplay = false;
        pauseOverlay.style.display = 'none';
        closePopup();
    } else if (event.data === PAUSED || event.data === ENDED) {
        state.isPlaying = false;
        pauseOverlay.style.display = 'flex';
    }
}

// ---------------------------------------------------------------------------
// Subtitle sync
// ---------------------------------------------------------------------------
function pickActiveCue(cues, ms) {
    for (let i = cues.length - 1; i >= 0; i--) {
        if (ms >= cues[i].startMs && ms < cues[i].endMs) return i;
    }
    return -1;
}

function startCueInterval() {
    if (state.intervalId) clearInterval(state.intervalId);
    state.intervalId = setInterval(() => {
        if (!state.player || !state.session) return;
        const playerState = state.player.getPlayerState?.();
        if (playerState !== 1) return; // only when playing
        const seconds = state.player.getCurrentTime?.();
        if (typeof seconds !== 'number') return;
        const ms = seconds * 1000;
        const idx = pickActiveCue(state.session.cues, ms);
        if (idx !== state.activeCueIndex) {
            state.activeCueIndex = idx;
            renderSubtitles(idx);
        }
    }, 250);
}

function renderSubtitles(idx) {
    if (idx < 0 || !state.session) {
        subtitleLine.innerHTML = '';
        return;
    }
    const cue = state.session.cues[idx];
    const tokens = tokenize(cue.text);
    const spans = tokens.map((token, i) => {
        const space = shouldAppendSpace(token, tokens[i + 1]) ? ' ' : '';
        if (!token.clickable) {
            return `<span class="st-token">${esc(token.value)}</span>${space}`;
        }
        const isLoading = state.lookingUpWord === token.value;
        const cls = 'st-token st-token--clk' + (isLoading ? ' st-token--loading' : '');
        const spinner = isLoading ? '<span class="st-spinner"></span>' : '';
        return `<span class="${cls}" data-value="${esc(token.value)}" data-norm="${esc(token.normalized)}">${spinner}${esc(token.value)}</span>${space}`;
    });
    subtitleLine.innerHTML = spans.join('');

    // Attach click handlers
    subtitleLine.querySelectorAll('.st-token--clk').forEach(el => {
        el.addEventListener('click', () => handleTokenClick(el));
    });
}

function esc(str) {
    return String(str ?? '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

// ---------------------------------------------------------------------------
// Word click → lookup
// ---------------------------------------------------------------------------
async function handleTokenClick(el) {
    if (state.isLookingUp) return;
    if (!state.session || state.activeCueIndex < 0) return;

    // Pause video
    state.player?.pauseVideo?.();

    const value = el.dataset.value;
    const normalized = el.dataset.norm;
    const cues = state.session.cues;
    const idx = state.activeCueIndex;

    const cueText = cues[idx]?.text ?? '';
    const prev2  = cues[idx - 2]?.text ?? '';
    const prev1  = cues[idx - 1]?.text ?? '';
    const next1  = cues[idx + 1]?.text ?? '';
    const next2  = cues[idx + 2]?.text ?? '';
    const previousCue = [prev2, prev1].filter(Boolean).join(' ');
    const nextCue     = [next1, next2].filter(Boolean).join(' ');

    // Show popup in loading state
    openPopupLoading(value);

    state.isLookingUp = true;
    state.lookingUpWord = value;
    renderSubtitles(state.activeCueIndex); // show spinner on token

    try {
        const card = await apiFetch('/api/subtitle/lookup', {
            method: 'POST',
            body: {
                surfaceForm: value,
                normalizedForm: normalized,
                cueText,
                previousCue,
                nextCue,
                videoId: state.session.videoId,
            },
        });
        renderPopupCard(card);
    } catch (err) {
        renderPopupError(err.message);
    } finally {
        state.isLookingUp = false;
        state.lookingUpWord = null;
        renderSubtitles(state.activeCueIndex);
    }
}

// ---------------------------------------------------------------------------
// Popup
// ---------------------------------------------------------------------------
function openPopupLoading(word) {
    popupWord.textContent = word;
    popupBody.innerHTML = `
        <div class="popup-skeleton">
            <div class="popup-skel-line popup-skel-short"></div>
            <div class="popup-skel-line"></div>
            <div class="popup-skel-line"></div>
            <div class="popup-skel-line popup-skel-mid"></div>
        </div>`;
    wordPopup.style.display = 'flex';
}

function renderPopupCard(card) {
    popupWord.textContent = card.surfaceForm;
    const cueTransHtml = card.cueTranslation
        ? `<p class="popup-cue-translation">${esc(card.cueTranslation)}</p>` : '';
    const explanationHtml = card.explanation
        ? `<p class="popup-explanation">${esc(card.explanation)}</p>` : '';

    popupBody.innerHTML = `
        <div class="popup-tags">
            <span class="pill">${esc(card.translation || '')}</span>
        </div>
        ${explanationHtml}
        <p class="popup-cue">${esc(card.cueText || '')}</p>
        ${cueTransHtml}
        <div class="popup-actions">
            <button class="btn-save" id="btn-save-word">Зберегти</button>
        </div>`;

    $('btn-save-word')?.addEventListener('click', () => saveWord(card));
}

function renderPopupError(msg) {
    popupBody.innerHTML = `<p class="popup-error">Помилка: ${esc(msg)}</p>`;
}

function closePopup() {
    wordPopup.style.display = 'none';
    state.popup = null;
}

async function saveWord(card) {
    const btn = $('btn-save-word');
    if (btn) btn.disabled = true;
    try {
        await apiFetch('/api/subtitle/words', {
            method: 'POST',
            body: {
                userId: getTgUserId(),
                videoId: card.videoId || state.session?.videoId || '',
                surfaceForm: card.surfaceForm,
                normalizedForm: card.normalizedForm,
                translation: card.translation,
                partOfSpeech: card.partOfSpeech ?? '',
                contextExplanation: card.explanation ?? '',
                cueText: card.cueText,
                cueTranslation: card.cueTranslation ?? '',
            },
        });
        if (btn) { btn.textContent = '✓ Збережено'; }
        tg?.HapticFeedback?.notificationOccurred('success');
    } catch (err) {
        if (btn) { btn.disabled = false; btn.textContent = 'Повторити'; }
    }
}

// ---------------------------------------------------------------------------
// Status helper
// ---------------------------------------------------------------------------
function setStatus(msg, isError = false) {
    statusLine.textContent = msg;
    statusLine.className = 'status-line' + (isError ? ' status-error' : '');
}

popupClose.addEventListener('click', closePopup);

reloadVideosBtn?.addEventListener('click', () => {
    loadVideoCatalog();
});

pauseOverlay.addEventListener('click', () => {
    state.player?.playVideo?.();
});

// Close popup when tapping outside it
document.addEventListener('click', (e) => {
    if (wordPopup.style.display !== 'none' &&
        !wordPopup.contains(e.target) &&
        !e.target.classList.contains('st-token--clk')) {
        closePopup();
    }
});

// ---------------------------------------------------------------------------
// Boot
// ---------------------------------------------------------------------------
showScreen('screen-main');
loadVideoCatalog();
