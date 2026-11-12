const params = new URLSearchParams(window.location.search);
const classId = params.get('classId') || 'class-1';
const preselectedQuizId = params.get('quizId') || '';
const cameFrom = params.get('from') || '';

const state = {
  classInfo: null,
  quizzes: [],
  localIPs: [],
  port: window.location.port || (window.location.protocol === 'https:' ? '443' : '80'),
  session: null,
  filter: 'all',
  eventSource: null
};

const quizSelect = document.getElementById('quiz-select');
const ipSelect = document.getElementById('ip-select');
const pinInput = document.getElementById('pin-input');
const qrImage = document.getElementById('qr-image');
const joinUrlText = document.getElementById('join-url-text');
const openLobbyBtn = document.getElementById('open-lobby-btn');
const startQuizBtn = document.getElementById('start-quiz-btn');
const endQuizBtn = document.getElementById('end-quiz-btn');
const resetLobbyBtn = document.getElementById('reset-lobby-btn');
const confirmEndBox = document.getElementById('confirm-end-box');
const noticeBanner = document.getElementById('notice-banner');
const noticeText = document.getElementById('notice-text');

function escapeHtml(value) {
  const div = document.createElement('div');
  div.textContent = value == null ? '' : String(value);
  return div.innerHTML;
}

function getInitials(name) {
  const parts = String(name || '').trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return 'ST';
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return `${parts[0][0]}${parts[parts.length - 1][0]}`.toUpperCase();
}

function formatDuration(seconds) {
  const sec = Number(seconds) || 0;
  if (sec <= 0) return 'Untimed';
  const mins = Math.round(sec / 60);
  if (mins >= 60 && mins % 60 === 0) return `${mins / 60} hr`;
  return `${mins} min`;
}

function showNotice(message, type = 'info') {
  noticeText.textContent = message;
  noticeBanner.className = `notice-banner notice-banner--${type}`;
  noticeBanner.hidden = false;
}

function initNavigation() {
  const encClass = encodeURIComponent(classId);
  const backLink = document.getElementById('back-link');
  if (cameFrom === 'predict' && preselectedQuizId) {
    backLink.href = `/predicted_results.html?quizId=${encodeURIComponent(preselectedQuizId)}&classId=${encClass}`;
  } else {
    backLink.href = `/class_dashboard.html?classId=${encClass}`;
  }
  document.getElementById('library-link').href = `/quiz_library.html?classId=${encClass}`;
  updatePredictLink();
}

function updatePredictLink() {
  const quizId = quizSelect.value || preselectedQuizId;
  const encClass = encodeURIComponent(classId);
  const predictLink = document.getElementById('predict-link');
  if (quizId) {
    predictLink.href = `/predicted_results.html?quizId=${encodeURIComponent(quizId)}&classId=${encClass}`;
    predictLink.hidden = false;
  } else {
    predictLink.hidden = true;
  }
}

async function fetchJson(url, options) {
  const res = await fetch(url, options);
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(data.message || `Request failed (${res.status})`);
  }
  return data;
}

const qrLightbox = document.getElementById('qr-lightbox');
const qrLightboxImg = document.getElementById('qr-lightbox-img');
const qrLightboxUrl = document.getElementById('qr-lightbox-url');
const qrLightboxPin = document.getElementById('qr-lightbox-pin');
const qrLightboxJoined = document.getElementById('qr-lightbox-joined');

async function refreshQrCode() {
  const selectedIp = ipSelect.value || window.location.hostname || '127.0.0.1';
  const targetUrl = `http://${selectedIp}:${state.port}/exam`;
  joinUrlText.textContent = targetUrl;
  qrLightboxUrl.textContent = targetUrl;

  try {
    const [smallQr, largeQr] = await Promise.all([
      fetchJson(`/api/qrcode?url=${encodeURIComponent(targetUrl)}&size=240`),
      fetchJson(`/api/qrcode?url=${encodeURIComponent(targetUrl)}&size=560`)
    ]);
    qrImage.src = smallQr.dataUrl;
    qrLightboxImg.src = largeQr.dataUrl;
  } catch (err) {
    console.error('QR generation error:', err);
  }
}

function updateQuizMeta() {
  const selectedId = quizSelect.value;
  const quiz = state.quizzes.find((q) => q.id === selectedId);
  const metaTitle = document.getElementById('meta-quiz-title');
  const metaDiff = document.getElementById('meta-difficulty');
  const metaQuestions = document.getElementById('meta-questions');
  const metaDuration = document.getElementById('meta-duration');
  const metaRandom = document.getElementById('meta-random-chip');

  if (!quiz) {
    metaTitle.textContent = 'No unarchived quizzes available';
    metaDiff.textContent = '--';
    metaQuestions.textContent = '0 Questions';
    metaDuration.textContent = 'Untimed';
    metaRandom.hidden = true;
    return;
  }

  const totalCount = Array.isArray(quiz.questions) ? quiz.questions.length : 0;
  const rand = quiz.randomization || {};
  const effectiveCount =
    rand.useQuestionPool && rand.poolSize > 0 && rand.poolSize < totalCount
      ? `${rand.poolSize} of ${totalCount} (Pool)`
      : `${totalCount} ${totalCount === 1 ? 'Question' : 'Questions'}`;

  metaTitle.textContent = quiz.name;
  metaDiff.textContent = quiz.difficulty || 'Medium';
  metaQuestions.textContent = effectiveCount;
  metaDuration.textContent = formatDuration(quiz.totalTimeLimit);

  const flags = [];
  if (rand.shuffleQuestions) flags.push('Shuffle Qs');
  if (rand.shuffleOptions) flags.push('Shuffle Options');
  if (rand.useQuestionPool) flags.push(`Pool: ${rand.poolSize}`);
  if (flags.length > 0) {
    metaRandom.textContent = flags.join(' • ');
    metaRandom.hidden = false;
  } else {
    metaRandom.hidden = true;
  }

  updatePredictLink();
}

function renderSessionState() {
  const s = state.session || { status: 'idle', participants: [], stats: {} };
  const status = s.status || 'idle';
  const badge = document.getElementById('session-status-badge');
  const badgeText = document.getElementById('session-status-text');

  badge.className = `status-badge status-badge--${status}`;
  if (status === 'lobby') badgeText.textContent = 'Waiting Lobby Open';
  else if (status === 'active') badgeText.textContent = 'Live Session Active';
  else if (status === 'ended') badgeText.textContent = 'Session Ended';
  else badgeText.textContent = 'Ready';

  // Sync quiz dropdown when an active/lobby session dictates the quiz
  if ((status === 'lobby' || status === 'active') && s.quizId && quizSelect.value !== s.quizId) {
    if (state.quizzes.some((q) => q.id === s.quizId)) {
      quizSelect.value = s.quizId;
      updateQuizMeta();
    }
  }

  if (s.pin && !pinInput.matches(':focus')) {
    pinInput.value = s.pin;
  }

  const activePinPill = document.getElementById('active-pin-pill');
  if ((status === 'lobby' || status === 'active') && s.pin) {
    activePinPill.textContent = `Session PIN: ${s.pin}`;
    activePinPill.hidden = false;
    qrLightboxPin.textContent = `Session PIN: ${s.pin}`;
    qrLightboxPin.hidden = false;
  } else {
    activePinPill.hidden = true;
    qrLightboxPin.hidden = true;
  }

  const stats = s.stats || {};
  const totalJoined = stats.totalJoined || 0;
  const submitted = stats.submittedCount || 0;
  const pctDone = totalJoined > 0 ? Math.round((submitted / totalJoined) * 100) : 0;

  qrLightboxJoined.textContent = `${totalJoined} Student${totalJoined === 1 ? '' : 's'} Joined`;
  const subEl = document.getElementById('qr-lightbox-sub');
  if (s.quizName) {
    subEl.textContent = `${s.quizName} • Connect to classroom Wi-Fi/LAN, scan, and enter your assigned Student ID`;
  }

  document.getElementById('kpi-joined').textContent = totalJoined;
  document.getElementById('kpi-waiting-sub').textContent = `${stats.waitingCount || 0} in waiting lobby`;
  document.getElementById('kpi-progress').textContent = stats.inProgressCount || 0;
  document.getElementById('kpi-submitted').textContent = submitted;
  document.getElementById('kpi-completion-sub').textContent = `${pctDone}% completed`;
  document.getElementById('kpi-average').textContent =
    stats.averagePercent != null ? `${stats.averagePercent}%` : '--%';

  // Controls visibility
  const hasQuiz = Boolean(quizSelect.value);
  quizSelect.disabled = status === 'active';
  ipSelect.disabled = status === 'active';
  pinInput.disabled = status === 'active';

  openLobbyBtn.hidden = status === 'active';
  openLobbyBtn.disabled = !hasQuiz;
  openLobbyBtn.querySelector('span').textContent =
    status === 'lobby' ? 'Update Lobby & QR' : 'Open Student Lobby';

  startQuizBtn.hidden = status === 'active';
  startQuizBtn.disabled = !hasQuiz;

  endQuizBtn.hidden = status !== 'active';
  resetLobbyBtn.hidden = status !== 'lobby' && status !== 'ended';

  if (status !== 'active') {
    confirmEndBox.hidden = true;
  }

  const endedBanner = document.getElementById('session-ended-banner');
  endedBanner.hidden = status !== 'ended';
  if (status === 'ended') {
    document.getElementById('ended-summary-text').textContent = `${s.quizName || 'Quiz'} ended with ${submitted} submitted student${submitted === 1 ? '' : 's'}.`;
    const encClass = encodeURIComponent(classId);
    const sid = s.sessionId ? `&sessionId=${encodeURIComponent(s.sessionId)}` : '';
    document.getElementById('view-grades-link').href = `/analyze.html?classId=${encClass}${sid}`;
  }

  renderParticipants();
}

function renderParticipants() {
  const list = state.session?.participants || [];
  document.getElementById('participant-count').textContent = list.length;

  const filtered =
    state.filter === 'all' ? list : list.filter((p) => p.status === state.filter);

  const container = document.getElementById('participants-container');
  if (filtered.length === 0) {
    container.innerHTML = `
      <div class="empty-box">
        ${
          list.length === 0
            ? 'No students connected yet. Open the lobby and share the QR code or URL above.'
            : 'No participants match this filter.'
        }
      </div>
    `;
    return;
  }

  container.innerHTML = `
    <div class="participants-grid">
      ${filtered
        .map((p) => {
          const totalQ = p.totalQuestions || state.session?.quizSummary?.effectiveQuestionCount || 0;
          const answered = p.answeredCount || 0;
          const progressPct =
            p.status === 'submitted'
              ? 100
              : totalQ > 0
                ? Math.min(100, Math.round((answered / totalQ) * 100))
                : 0;
          const statusLabel =
            p.status === 'submitted'
              ? 'Submitted'
              : p.status === 'in-progress'
                ? 'In Progress'
                : 'Waiting';
          const scoreLine =
            p.status === 'submitted'
              ? `Score: ${p.score}/${p.totalGradeable} (${p.percentage}%)`
              : totalQ > 0
                ? `${answered} of ${totalQ} answered`
                : 'Connected';

          return `
            <article class="participant-card">
              <div class="participant-top">
                <div class="participant-id-wrap">
                  <div class="avatar-dot">${escapeHtml(getInitials(p.name))}</div>
                  <div style="min-width: 0;">
                    <div class="p-name">${escapeHtml(p.name)}</div>
                    <div class="p-code">${escapeHtml(p.studentCode || 'Walk-in Student')}</div>
                  </div>
                </div>
                <span class="p-badge p-badge--${escapeHtml(p.status)}">${statusLabel}</span>
              </div>

              <div class="progress-row">
                <div class="progress-track">
                  <div class="progress-fill ${p.status === 'submitted' ? 'progress-fill--done' : ''}" style="width: ${progressPct}%;"></div>
                </div>
                <span class="progress-label">${progressPct}%</span>
              </div>

              <div class="participant-foot">
                <span>${escapeHtml(scoreLine)}</span>
                ${
                  p.status !== 'submitted'
                    ? `<button type="button" class="kick-btn" data-kick-id="${escapeHtml(p.id)}">Remove</button>`
                    : '<span>Recorded</span>'
                }
              </div>
            </article>
          `;
        })
        .join('')}
    </div>
  `;
}

async function loadInitialData() {
  try {
    const [health, classRes, quizzesRes, sessionRes] = await Promise.all([
      fetchJson('/api/health'),
      fetchJson(`/api/classes/${encodeURIComponent(classId)}`).catch(() => null),
      fetchJson(`/api/quizzes?classId=${encodeURIComponent(classId)}`),
      fetchJson('/api/session/current')
    ]);

    state.classInfo = classRes;
    if (classRes) {
      document.getElementById('class-pill').textContent = `${classRes.name} • ${classRes.subject}`;
    }

    state.quizzes = (quizzesRes || []).filter((q) => !q.isArchived);
    quizSelect.innerHTML = '';
    if (state.quizzes.length === 0) {
      const opt = document.createElement('option');
      opt.value = '';
      opt.textContent = 'No quizzes available — create a quiz first';
      quizSelect.appendChild(opt);
    } else {
      state.quizzes.forEach((q) => {
        const opt = document.createElement('option');
        opt.value = q.id;
        opt.textContent = `${q.name} (${Array.isArray(q.questions) ? q.questions.length : 0} Qs)`;
        quizSelect.appendChild(opt);
      });
      if (preselectedQuizId && state.quizzes.some((q) => q.id === preselectedQuizId)) {
        quizSelect.value = preselectedQuizId;
      }
    }

    state.port = String(window.location.port || health.port || 3000);
    const ips = Array.isArray(health.localIPs) ? [...health.localIPs] : [];
    const hasLoopback = ips.some((ip) => ip.address === '127.0.0.1');
    if (!hasLoopback) {
      ips.push({ name: 'Localhost Testing', address: '127.0.0.1' });
    }
    state.localIPs = ips;

    ipSelect.innerHTML = ips
      .map(
        (ip) => `<option value="${escapeHtml(ip.address)}">${escapeHtml(ip.address)} (${escapeHtml(ip.name)})</option>`
      )
      .join('');

    if (sessionRes.selectedIp && ips.some((ip) => ip.address === sessionRes.selectedIp)) {
      ipSelect.value = sessionRes.selectedIp;
    }

    state.session = sessionRes;

    updateQuizMeta();
    renderSessionState();
    await refreshQrCode();
  } catch (err) {
    showNotice(err.message || 'Failed to load session monitor data.', 'error');
  }
}

function connectLiveEvents() {
  if (state.eventSource) {
    state.eventSource.close();
  }
  const source = new EventSource('/api/session/events');
  source.addEventListener('session', (event) => {
    try {
      state.session = JSON.parse(event.data);
      renderSessionState();
    } catch (_) {}
  });
  source.onerror = () => {
    // Reconnects automatically via EventSource; polling interval backs it up
  };
  state.eventSource = source;
}

quizSelect.addEventListener('change', updateQuizMeta);
ipSelect.addEventListener('change', refreshQrCode);

document.getElementById('notice-close').addEventListener('click', () => {
  noticeBanner.hidden = true;
});

openLobbyBtn.addEventListener('click', async () => {
  if (!quizSelect.value) return;
  openLobbyBtn.disabled = true;
  try {
    state.session = await fetchJson('/api/session/open-lobby', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        classId,
        quizId: quizSelect.value,
        selectedIp: ipSelect.value,
        port: Number(state.port),
        pin: pinInput.value.trim()
      })
    });
    renderSessionState();
    await refreshQrCode();
    showNotice('Student lobby is open! Share the QR code or LAN link for students to join.', 'success');
  } catch (err) {
    showNotice(err.message, 'error');
  } finally {
    openLobbyBtn.disabled = false;
  }
});

startQuizBtn.addEventListener('click', async () => {
  if (!quizSelect.value) return;
  startQuizBtn.disabled = true;
  try {
    state.session = await fetchJson('/api/session/start', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        classId,
        quizId: quizSelect.value,
        selectedIp: ipSelect.value,
        port: Number(state.port),
        pin: pinInput.value.trim()
      })
    });
    renderSessionState();
    await refreshQrCode();
    showNotice('Live quiz session started! Connected students now see the exam.', 'success');
  } catch (err) {
    showNotice(err.message, 'error');
  } finally {
    startQuizBtn.disabled = false;
  }
});

endQuizBtn.addEventListener('click', () => {
  confirmEndBox.hidden = false;
});

document.getElementById('confirm-end-cancel').addEventListener('click', () => {
  confirmEndBox.hidden = true;
});

document.getElementById('confirm-end-yes').addEventListener('click', async () => {
  confirmEndBox.hidden = true;
  try {
    state.session = await fetchJson('/api/session/end', { method: 'POST' });
    renderSessionState();
    showNotice('Quiz session ended and finalized cleanly.', 'info');
  } catch (err) {
    showNotice(err.message, 'error');
  }
});

async function handleResetSession() {
  try {
    state.session = await fetchJson('/api/session/reset', { method: 'POST' });
    renderSessionState();
    showNotice('Session lobby reset.', 'info');
  } catch (err) {
    showNotice(err.message, 'error');
  }
}

resetLobbyBtn.addEventListener('click', handleResetSession);
document.getElementById('ended-new-session-btn').addEventListener('click', handleResetSession);

document.getElementById('copy-url-btn').addEventListener('click', async () => {
  const url = joinUrlText.textContent;
  const label = document.getElementById('copy-url-label');
  try {
    await navigator.clipboard.writeText(url);
    label.textContent = 'Copied!';
    setTimeout(() => {
      label.textContent = 'Copy';
    }, 1800);
  } catch (_) {
    showNotice(`Copy manually: ${url}`, 'info');
  }
});

document.querySelectorAll('.filter-pill').forEach((btn) => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.filter-pill').forEach((b) => b.classList.remove('is-active'));
    btn.classList.add('is-active');
    state.filter = btn.dataset.filter || 'all';
    renderParticipants();
  });
});

document.getElementById('participants-container').addEventListener('click', async (event) => {
  const kickBtn = event.target.closest('.kick-btn');
  if (!kickBtn) return;
  const participantId = kickBtn.dataset.kickId;
  try {
    state.session = await fetchJson('/api/session/kick', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ participantId })
    });
    renderSessionState();
  } catch (err) {
    showNotice(err.message, 'error');
  }
});

document.getElementById('qr-expand-btn').addEventListener('click', () => {
  if (!qrLightboxImg.src && qrImage.src) {
    qrLightboxImg.src = qrImage.src;
  }
  qrLightbox.hidden = false;
});

document.getElementById('qr-lightbox-close').addEventListener('click', () => {
  qrLightbox.hidden = true;
});

qrLightbox.addEventListener('click', (event) => {
  if (event.target === qrLightbox) {
    qrLightbox.hidden = true;
  }
});

document.addEventListener('keydown', (event) => {
  if (event.key === 'Escape' && !qrLightbox.hidden) {
    qrLightbox.hidden = true;
  }
});

initNavigation();
loadInitialData();
window.addEventListener('load', () => {
  setTimeout(connectLiveEvents, 120);
});
