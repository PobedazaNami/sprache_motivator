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
const screenLoading   = $('screen-loading');
const screenCatalog   = $('screen-catalog');
const screenPlayer    = $('screen-player');
const statusLine      = $('status-line');
const videosList      = $('videos-list');
const reloadVideosBtn = $('reload-videos-btn');
const backBtn         = $('back-btn');
const playerTitle     = $('player-title');
const ytContainer     = $('yt-container');
const pauseOverlay    = $('pause-overlay');
const subtitleOverlay = $('subtitle-overlay');
const subtitleLine    = $('subtitle-line');
const wordPopup       = $('word-popup');
const popupWord       = $('popup-word');
const popupBody       = $('popup-body');
const popupClose      = $('popup-close');

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

    state.selectedVideoId = videoId;
    state.loadingVideoId = videoId;
    state.session = null;
    state.activeCueIndex = -1;
    renderSubtitles(-1);

    // Switch to player screen
    playerTitle.textContent = preferredTitle || videoId;
    showScreen('screen-player');
    mountPlayer(videoId);

    try {
        const data = await apiFetch('/api/subtitle/session', {
            method: 'POST',
            body: { input: videoId, title: preferredTitle },
        });

        state.session = data;
        state.activeCueIndex = -1;
        state.loadingVideoId = null;
        playerTitle.textContent = data.title || preferredTitle || videoId;
    } catch (err) {
        state.loadingVideoId = null;
        state.selectedVideoId = null;
        setStatus(err.message, true);
        showScreen('screen-catalog');
    }
}

async function loadVideoCatalog() {
    setStatus('Завантажую список відео…');
    if (reloadVideosBtn) reloadVideosBtn.disabled = true;
    try {
        const data = await apiFetch('/api/subtitle/videos');
        state.availableVideos = data.videos || [];
        renderVideos(state.availableVideos);
        setStatus('');
    } catch (err) {
        setStatus('Помилка: ' + err.message, true);
    } finally {
        if (reloadVideosBtn) reloadVideosBtn.disabled = false;
        showScreen('screen-catalog');
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
        const notCached = !video.cached ? ' not-cached' : '';
        const dateLabel = formatPublishedDate(video.publishedAt);
        return `
            <button type="button" class="video-card${selected}${loading}${notCached}" data-video-id="${esc(video.videoId)}">
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

function buildSubtitleTokenWindow(cues, startIdx, maxCues = 8) {
    const items = [];
    const endIdx = Math.min(cues.length, startIdx + maxCues);

    for (let cueIdx = startIdx; cueIdx < endIdx; cueIdx++) {
        const cue = cues[cueIdx];
        const tokens = tokenize(cue.text);
        tokens.forEach((token, tokenIdx) => {
            items.push({
                token,
                cueIdx,
                trailingSpace: shouldAppendSpace(token, tokens[tokenIdx + 1]),
            });
        });
    }

    return items;
}

function renderTokenHtml(item) {
    const { token, cueIdx, trailingSpace } = item;
    const space = trailingSpace ? ' ' : '';

    if (!token.clickable) {
        return `<span class="st-token">${esc(token.value)}</span>${space}`;
    }

    const isLoading = state.lookingUpWord === token.value;
    const cls = 'st-token st-token--clk' + (isLoading ? ' st-token--loading' : '');
    const spinner = isLoading ? '<span class="st-spinner"></span>' : '';
    return `<span class="${cls}" data-value="${esc(token.value)}" data-norm="${esc(token.normalized)}" data-cue="${cueIdx}">${spinner}${esc(token.value)}</span>${space}`;
}

let subtitleMeasureEl = null;

function ensureSubtitleMeasureEl() {
    if (!subtitleMeasureEl) {
        subtitleMeasureEl = document.createElement('div');
        subtitleMeasureEl.setAttribute('aria-hidden', 'true');
        subtitleMeasureEl.style.position = 'absolute';
        subtitleMeasureEl.style.left = '-99999px';
        subtitleMeasureEl.style.top = '0';
        subtitleMeasureEl.style.visibility = 'hidden';
        subtitleMeasureEl.style.pointerEvents = 'none';
        subtitleMeasureEl.style.whiteSpace = 'nowrap';
        document.body.appendChild(subtitleMeasureEl);
    }

    const styles = window.getComputedStyle(subtitleLine);
    subtitleMeasureEl.style.fontSize = styles.fontSize;
    subtitleMeasureEl.style.fontWeight = styles.fontWeight;
    subtitleMeasureEl.style.lineHeight = styles.lineHeight;
    subtitleMeasureEl.style.fontFamily = styles.fontFamily;
    subtitleMeasureEl.style.letterSpacing = styles.letterSpacing;
    subtitleMeasureEl.style.textTransform = styles.textTransform;
    return subtitleMeasureEl;
}

function measureTokenLine(items) {
    if (!items.length) return 0;
    const measureEl = ensureSubtitleMeasureEl();
    measureEl.innerHTML = `<div class="st-cue-line st-cue-line--measure">${items.map(renderTokenHtml).join('')}</div>`;
    return measureEl.firstElementChild?.getBoundingClientRect().width ?? 0;
}

function rebalancePackedLines(lines, maxWidth) {
    for (let i = 0; i < lines.length - 1; i++) {
        let changed = true;
        while (changed && lines[i].length > 1 && lines[i + 1].length > 0) {
            changed = false;
            const currentWidth = measureTokenLine(lines[i]);
            const nextWidth = measureTokenLine(lines[i + 1]);
            const moved = lines[i][lines[i].length - 1];
            const candidateCurrent = lines[i].slice(0, -1);
            const candidateNext = [moved, ...lines[i + 1]];
            const candidateCurrentWidth = measureTokenLine(candidateCurrent);
            const candidateNextWidth = measureTokenLine(candidateNext);
            const currentGap = Math.abs(currentWidth - nextWidth);
            const candidateGap = Math.abs(candidateCurrentWidth - candidateNextWidth);

            if (candidateCurrentWidth <= maxWidth && candidateNextWidth <= maxWidth && candidateGap < currentGap) {
                lines[i] = candidateCurrent;
                lines[i + 1] = candidateNext;
                changed = true;
            }
        }
    }

    return lines;
}

function packTokensIntoLines(items, lineCount, maxWidth) {
    if (!items.length) {
        return Array.from({ length: lineCount }, () => []);
    }

    const lines = [];
    let cursor = 0;

    for (let lineIdx = 0; lineIdx < lineCount && cursor < items.length; lineIdx++) {
        const remainingLines = lineCount - lineIdx;
        const maxEnd = items.length - (remainingLines - 1);
        let bestEnd = Math.min(cursor + 1, items.length);

        for (let end = cursor + 1; end <= maxEnd; end++) {
            const width = measureTokenLine(items.slice(cursor, end));
            if (width <= maxWidth || end === cursor + 1) {
                bestEnd = end;
                continue;
            }
            break;
        }

        lines.push(items.slice(cursor, bestEnd));
        cursor = bestEnd;
    }

    if (cursor < items.length && lines.length) {
        lines[lines.length - 1] = lines[lines.length - 1].concat(items.slice(cursor));
    }

    while (lines.length < lineCount) {
        lines.push([]);
    }

    return rebalancePackedLines(lines, maxWidth);
}

function renderSubtitles(idx) {
    if (idx < 0 || !state.session) {
        subtitleLine.innerHTML = '';
        return;
    }

    const cues = state.session.cues;
    const tokenWindow = buildSubtitleTokenWindow(cues, idx, 8);
    const availableWidth = Math.max(subtitleLine.clientWidth || 0, 240);
    const packedLines = packTokensIntoLines(tokenWindow, 4, availableWidth);

    const parts = packedLines.map((lineItems, lineIdx) => {
        const cls = lineIdx < 2 ? 'st-cue-line st-cue-line--active' : 'st-cue-line st-cue-line--future';
        const html = lineItems.length ? lineItems.map(renderTokenHtml).join('') : '&nbsp;';
        return `<div class="${cls}">${html}</div>`;
    });

    subtitleLine.innerHTML = parts.join('');

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
    const idx = el.dataset.cue != null ? parseInt(el.dataset.cue, 10) : state.activeCueIndex;

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

backBtn?.addEventListener('click', () => {
    // Pause video when going back to catalog
    state.player?.pauseVideo?.();
    closePopup();
    showScreen('screen-catalog');
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
showScreen('screen-catalog');
loadVideoCatalog();
