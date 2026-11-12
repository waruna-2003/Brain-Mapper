const STORAGE_KEY = 'bmStudentSession';

const state = {
  sessionId: null,
  participantId: null,
  studentName: '',
  studentCode: null,
  status: 'idle',
  pinRequired: false,
  quiz: null,
  activeQuestionIndex: 0,
  flaggedQuestions: new Set(),
  questionTimers: {}, // { qIdx: { remaining, expired, active } }
  overallRemaining: 0,
  elapsedSeconds: 0,
  overallInterval: null,
  questionInterval: null,
  draftTimer: null,
  ttsEnabled: false,
  submitting: false,
  eventSource: null
};

const toastBanner = document.getElementById('toast-banner');
const viewJoin = document.getElementById('view-join');
const viewLobby = document.getElementById('view-lobby');
const viewExam = document.getElementById('view-exam');
const viewResult = document.getElementById('view-result');
const questionListEl = document.getElementById('question-list');
const navDrawer = document.getElementById('nav-drawer');
const navToggleBtn = document.getElementById('nav-toggle-btn');
const settingsPopover = document.getElementById('settings-popover');

function escapeHtml(value) {
  const div = document.createElement('div');
  div.textContent = value == null ? '' : String(value);
  return div.innerHTML;
}

function safeImageSource(value) {
  return typeof value === 'string' && /^data:image\/(png|jpeg|gif|webp);base64,/i.test(value)
    ? value
    : '';
}

function showToast(message, type = 'info') {
  toastBanner.textContent = message;
  toastBanner.className = `toast toast--${type}`;
  toastBanner.hidden = false;
  clearTimeout(showToast.timer);
  showToast.timer = setTimeout(() => {
    toastBanner.hidden = true;
  }, 4500);
}

function showView(name) {
  viewJoin.hidden = name !== 'join';
  viewLobby.hidden = name !== 'lobby';
  viewExam.hidden = name !== 'exam';
  viewResult.hidden = name !== 'result';

  const inExam = name === 'exam';
  navToggleBtn.hidden = !inExam;
  document.getElementById('manual-save-draft-btn').hidden = !inExam;
  if (!inExam) navDrawer.hidden = true;
}

function formatClock(seconds) {
  const sec = Math.max(0, Math.floor(Number(seconds) || 0));
  const hrs = Math.floor(sec / 3600);
  const mins = Math.floor((sec % 3600) / 60);
  const rem = sec % 60;
  if (hrs > 0) {
    return `${String(hrs).padStart(2, '0')}:${String(mins).padStart(2, '0')}:${String(rem).padStart(2, '0')}`;
  }
  return `${String(mins).padStart(2, '0')}:${String(rem).padStart(2, '0')}`;
}

function getDraftStorageKey() {
  if (!state.sessionId || !state.participantId) return null;
  return `bmExamDraft_${state.sessionId}_${state.participantId}`;
}

function saveStoredStudentSession() {
  if (!state.sessionId || !state.participantId) return;
  localStorage.setItem(
    STORAGE_KEY,
    JSON.stringify({
      sessionId: state.sessionId,
      participantId: state.participantId,
      studentName: state.studentName,
      studentCode: state.studentCode
    })
  );
}

function clearStoredStudentSession() {
  const draftKey = getDraftStorageKey();
  if (draftKey) localStorage.removeItem(draftKey);
  localStorage.removeItem(STORAGE_KEY);
  state.participantId = null;
  state.studentName = '';
  state.studentCode = null;
  state.quiz = null;
  state.flaggedQuestions.clear();
  stopAllTimers();
  document.getElementById('student-identity-sub').textContent = 'Offline Classroom Exam Portal';
}

function stopAllTimers() {
  if (state.overallInterval) clearInterval(state.overallInterval);
  if (state.questionInterval) clearInterval(state.questionInterval);
  if (state.draftTimer) clearTimeout(state.draftTimer);
  state.overallInterval = null;
  state.questionInterval = null;
  state.draftTimer = null;
}

function updateIdentityHeader() {
  const sub = document.getElementById('student-identity-sub');
  if (state.studentName) {
    sub.textContent = state.studentCode
      ? `${state.studentName} (${state.studentCode})`
      : state.studentName;
  } else {
    sub.textContent = 'Offline Classroom Exam Portal';
  }
}

async function fetchJson(url, options) {
  const res = await fetch(url, options);
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const err = new Error(data.message || `Error ${res.status}`);
    err.status = res.status;
    err.data = data;
    throw err;
  }
  return data;
}

// ---- Accessibility Preferences ----

function loadAccessibilityPrefs() {
  const dark = localStorage.getItem('bmDarkMode') === 'true';
  document.body.classList.toggle('dark-mode', dark);
  document.getElementById('dark-mode-toggle').checked = dark;

  const font = localStorage.getItem('bmFontSize') || 'medium';
  applyFontSize(font);
}

function applyFontSize(size) {
  document.body.classList.remove('font-small', 'font-medium', 'font-large', 'font-xlarge');
  document.body.classList.add(`font-${size}`);
  document.querySelectorAll('.font-pill').forEach((btn) => {
    btn.classList.toggle('is-active', btn.dataset.font === size);
  });
  localStorage.setItem('bmFontSize', size);
}

document.getElementById('settings-toggle-btn').addEventListener('click', () => {
  settingsPopover.hidden = !settingsPopover.hidden;
});

document.addEventListener('click', (e) => {
  if (
    !settingsPopover.contains(e.target) &&
    !e.target.closest('#settings-toggle-btn')
  ) {
    settingsPopover.hidden = true;
  }
});

document.getElementById('dark-mode-toggle').addEventListener('change', (e) => {
  document.body.classList.toggle('dark-mode', e.target.checked);
  localStorage.setItem('bmDarkMode', String(e.target.checked));
});

document.querySelectorAll('.font-pill').forEach((btn) => {
  btn.addEventListener('click', () => applyFontSize(btn.dataset.font));
});

document.getElementById('tts-toggle-btn').addEventListener('click', () => {
  state.ttsEnabled = !state.ttsEnabled;
  const btn = document.getElementById('tts-toggle-btn');
  btn.textContent = state.ttsEnabled ? 'Disable Read Aloud' : 'Enable Read Aloud';
  if (!state.ttsEnabled && window.speechSynthesis) {
    window.speechSynthesis.cancel();
  } else if (state.ttsEnabled && state.quiz) {
    speakQuestion(state.activeQuestionIndex);
  }
});

function speakQuestion(idx) {
  if (!state.ttsEnabled || !window.speechSynthesis || !state.quiz) return;
  const q = state.quiz.questions[idx];
  if (!q) return;
  window.speechSynthesis.cancel();
  const utt = new SpeechSynthesisUtterance(`Question ${idx + 1}. ${q.question}`);
  window.speechSynthesis.speak(utt);
}

navToggleBtn.addEventListener('click', () => {
  navDrawer.hidden = !navDrawer.hidden;
});

// ---- Session Sync & Lifecycle ----

function renderJoinBanner(statusData) {
  const headline = document.getElementById('join-session-headline');
  const detail = document.getElementById('join-session-detail');
  const card = document.getElementById('join-session-card');
  const pinWrap = document.getElementById('pin-field-wrap');
  const joinBtn = document.getElementById('join-submit-btn');

  pinWrap.hidden = !statusData.pinRequired;

  if (statusData.status === 'lobby' || statusData.status === 'active') {
    card.className = 'status-card status-card--open';
    headline.textContent = statusData.quizName || 'Classroom Quiz Open';
    const meta = statusData.quizMeta;
    const parts = [statusData.className, meta ? `${meta.questionCount} questions` : null, statusData.status === 'active' ? 'In progress' : 'Lobby open'].filter(Boolean);
    detail.textContent = parts.join(' • ');
    joinBtn.disabled = false;
  } else if (statusData.status === 'ended') {
    card.className = 'status-card';
    headline.textContent = 'Previous Session Ended';
    detail.textContent = 'Waiting for your teacher to open the next classroom session.';
    joinBtn.disabled = true;
  } else {
    card.className = 'status-card';
    headline.textContent = 'Waiting for Teacher to Open Session';
    detail.textContent = 'This page refreshes automatically once your teacher opens the lobby.';
    joinBtn.disabled = true;
  }
}

async function syncSessionState() {
  const saved = (() => {
    try {
      return JSON.parse(localStorage.getItem(STORAGE_KEY) || 'null');
    } catch (_) {
      return null;
    }
  })();

  const queryPid = saved?.participantId || state.participantId || '';
  const url = queryPid
    ? `/api/session/status?participantId=${encodeURIComponent(queryPid)}`
    : '/api/session/status';

  const data = await fetchJson(url);
  state.status = data.status;
  state.pinRequired = Boolean(data.pinRequired);

  // If teacher started a different session, clear stale client identity
  if (saved?.sessionId && data.sessionId !== saved.sessionId) {
    clearStoredStudentSession();
  } else if (saved?.participantId && data.participant && !data.participant.registered) {
    clearStoredStudentSession();
  } else if (saved?.participantId && data.participant?.registered) {
    state.sessionId = data.sessionId;
    state.participantId = saved.participantId;
    state.studentName = data.participant.name || saved.studentName;
    state.studentCode = data.participant.studentCode || saved.studentCode;
    updateIdentityHeader();
  }

  state.sessionId = data.sessionId;

  if (state.participantId && data.participant?.registered) {
    const p = data.participant;
    if (p.status === 'submitted') {
      stopAllTimers();
      renderSubmittedResult({
        score: p.score,
        totalGradeable: p.totalGradeable,
        percentage: p.percentage,
        pendingManualGrading: p.pendingManualGrading
      });
      showView('result');
      return;
    }

    if (data.status === 'active') {
      if (!state.quiz || state.quiz.sessionId !== data.sessionId) {
        await loadAndRenderExam();
      }
      return;
    }

    if (data.status === 'lobby') {
      document.getElementById('lobby-welcome').textContent = `Welcome, ${state.studentName}!`;
      document.getElementById('lobby-subtitle').textContent = `Connected to "${data.quizName || 'Classroom Quiz'}". Waiting for teacher to start.`;
      showView('lobby');
      return;
    }

    if (data.status === 'ended') {
      stopAllTimers();
      renderSubmittedResult({
        endedByTeacher: true
      });
      showView('result');
      return;
    }
  }

  renderJoinBanner(data);
  showView('join');
}

document.getElementById('join-form').addEventListener('submit', async (e) => {
  e.preventDefault();
  const studentCode = document.getElementById('join-code').value.trim();
  const pin = document.getElementById('join-pin').value.trim();

  if (!studentCode) {
    showToast('Please enter your assigned Student ID.', 'error');
    document.getElementById('join-code').focus();
    return;
  }

  const joinBtn = document.getElementById('join-submit-btn');
  joinBtn.disabled = true;
  joinBtn.textContent = 'Verifying ID...';

  try {
    const joined = await fetchJson('/api/join', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ studentCode, pin })
    });

    state.sessionId = joined.sessionId;
    state.participantId = joined.participantId;
    state.studentName = joined.name;
    state.studentCode = joined.studentCode;
    saveStoredStudentSession();
    updateIdentityHeader();

    if (joined.sessionStatus === 'active') {
      await loadAndRenderExam();
    } else {
      document.getElementById('lobby-welcome').textContent = `Welcome, ${state.studentName}!`;
      showView('lobby');
      showToast('Connected to waiting lobby.', 'success');
    }
  } catch (err) {
    showToast(err.message, 'error');
  } finally {
    joinBtn.disabled = false;
    joinBtn.textContent = 'Join Classroom Session';
  }
});

document.getElementById('leave-lobby-btn').addEventListener('click', async () => {
  if (!state.participantId) return;
  try {
    await fetchJson('/api/leave', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ participantId: state.participantId })
    });
  } catch (_) {}
  clearStoredStudentSession();
  await syncSessionState();
});

document.getElementById('result-check-new-btn').addEventListener('click', async () => {
  clearStoredStudentSession();
  await syncSessionState();
});

// ---- Active Exam Rendering & Draft Recovery ----

async function loadAndRenderExam() {
  try {
    const quiz = await fetchJson(
      `/api/currentQuiz?studentId=${encodeURIComponent(state.participantId)}`
    );
    state.quiz = quiz;
    state.overallRemaining = Math.max(0, Number(quiz.remainingSeconds) || 0);
    state.elapsedSeconds = Math.max(0, Number(quiz.elapsedSeconds) || 0);

    document.getElementById('exam-quiz-title').textContent = quiz.name;

    const draft = mergeDraft(quiz);
    initQuestionTimers(quiz, draft);
    renderQuestions(quiz);
    if (draft) {
      applyDraftToDom(draft);
    }
    setActiveQuestion(draft?.activeQuestionIndex || 0, false);
    updateProgress();
    startTimers(quiz);
    showView('exam');
  } catch (err) {
    if (err.status === 409 && err.data?.submitted) {
      renderSubmittedResult(err.data.resultSummary || {});
      showView('result');
    } else {
      showToast(err.message, 'error');
    }
  }
}

function mergeDraft(quiz) {
  let localDraft = null;
  const draftKey = getDraftStorageKey();
  if (draftKey) {
    try {
      localDraft = JSON.parse(localStorage.getItem(draftKey) || 'null');
    } catch (_) {}
  }
  const serverDraft = quiz.draft || null;
  if (!localDraft) return serverDraft;
  if (!serverDraft) return localDraft;

  const localTs = new Date(localDraft.updatedAt || 0).getTime();
  const serverTs = new Date(serverDraft.updatedAt || 0).getTime();
  return localTs >= serverTs ? localDraft : serverDraft;
}

function initQuestionTimers(quiz, draft) {
  state.questionTimers = {};
  const savedTimers = draft?.questionTimersRemaining || {};

  (quiz.questions || []).forEach((q, idx) => {
    const limit = Math.max(0, Number(q.timeLimit) || 0);
    if (limit <= 0) return;

    const savedVal = savedTimers[idx];
    const remaining =
      savedVal !== undefined && Number.isFinite(Number(savedVal))
        ? Math.max(0, Math.min(limit, Number(savedVal)))
        : limit;

    state.questionTimers[idx] = {
      limit,
      remaining,
      expired: remaining <= 0
    };
  });
}

function renderQuestions(quiz) {
  questionListEl.innerHTML = '';

  (quiz.questions || []).forEach((q, idx) => {
    const qCard = document.createElement('article');
    qCard.className = 'q-card';
    qCard.dataset.qIdx = String(idx);
    qCard.dataset.qType = q.type || 'multiple-choice';

    const timerInfo = state.questionTimers[idx];
    const timerBadgeHtml = timerInfo
      ? `<span class="q-timer-badge" id="q-timer-${idx}">${
          timerInfo.expired ? 'Expired' : `${timerInfo.remaining}s (Paused)`
        }</span>`
      : '';

    const imgSrc = safeImageSource(q.image);
    const imageHtml = imgSrc
      ? `<img src="${imgSrc}" alt="Question illustration" class="q-image">`
      : '';

    const options = q.options && typeof q.options === 'object' ? q.options : {};
    const answerHtml = `
      <div class="options-stack">
        ${Object.entries(options)
          .map(
            ([key, label]) => `
              <label class="option-choice">
                <input type="radio" name="q_${idx}" value="${escapeHtml(key)}">
                <span>${escapeHtml(key)}) ${escapeHtml(label)}</span>
              </label>
            `
          )
          .join('')}
      </div>
    `;

    qCard.innerHTML = `
      <div class="q-head">
        <div class="q-badges">
          <span class="q-index-badge">Question ${idx + 1}</span>
          ${timerBadgeHtml}
        </div>
        <button type="button" class="flag-btn" data-flag-idx="${idx}">
          <img src="/assets/icons/flag.svg" alt="" width="12" height="12">
          <span>Flag</span>
        </button>
      </div>
      <p class="q-prompt">${escapeHtml(q.question)}</p>
      ${imageHtml}
      ${answerHtml}
    `;

    questionListEl.appendChild(qCard);

    if (timerInfo?.expired) {
      lockQuestionInputs(qCard);
    }
  });
}

function lockQuestionInputs(qCard) {
  qCard.classList.add('is-expired');
  qCard.querySelectorAll('input, select, textarea').forEach((el) => {
    el.disabled = true;
  });
}

function applyDraftToDom(draft) {
  if (!draft) return;
  if (Array.isArray(draft.flaggedQuestions)) {
    state.flaggedQuestions = new Set(draft.flaggedQuestions);
  }

  const answers = Array.isArray(draft.answers) ? draft.answers : [];
  const cards = questionListEl.querySelectorAll('.q-card');

  cards.forEach((card, idx) => {
    const val = answers[idx];
    const flagBtn = card.querySelector('.flag-btn');
    if (flagBtn) {
      const flagged = state.flaggedQuestions.has(idx);
      flagBtn.classList.toggle('is-flagged', flagged);
      flagBtn.querySelector('span').textContent = flagged ? 'Flagged' : 'Flag';
    }
    if (val === null || val === undefined) return;

    card.querySelectorAll('input[type="radio"]').forEach((r) => {
      r.checked = r.value === String(val);
    });
  });
}

function collectAnswersFromDom() {
  const cards = questionListEl.querySelectorAll('.q-card');
  return Array.from(cards).map((card) => {
    const checked = card.querySelector('input[type="radio"]:checked');
    return checked ? checked.value : null;
  });
}

function isQuestionAnswered(answers, idx) {
  const val = answers[idx];
  return typeof val === 'string' && val.trim() !== '';
}

function updateProgress() {
  if (!state.quiz) return;
  const answers = collectAnswersFromDom();
  const questions = state.quiz.questions || [];
  const total = questions.length;
  let answered = 0;

  questions.forEach((q, idx) => {
    if (isQuestionAnswered(answers, idx, q)) answered += 1;
  });

  const pct = total > 0 ? Math.round((answered / total) * 100) : 0;
  document.getElementById('progress-label').textContent = `${answered} of ${total} answered`;
  document.getElementById('progress-fill').style.width = `${pct}%`;

  const navChips = document.getElementById('nav-chips');
  navChips.innerHTML = questions
    .map((q, idx) => {
      const classes = ['nav-chip'];
      if (isQuestionAnswered(answers, idx, q)) classes.push('is-answered');
      if (state.flaggedQuestions.has(idx)) classes.push('is-flagged');
      if (idx === state.activeQuestionIndex) classes.push('is-current');
      return `<button type="button" class="${classes.join(' ')}" data-nav-idx="${idx}">${idx + 1}</button>`;
    })
    .join('');

  scheduleDraftSync(answers);
}

function scheduleDraftSync(answers) {
  const timersSnapshot = {};
  Object.entries(state.questionTimers).forEach(([k, v]) => {
    timersSnapshot[k] = v.remaining;
  });

  const payload = {
    participantId: state.participantId,
    sessionId: state.sessionId,
    answers,
    flaggedQuestions: Array.from(state.flaggedQuestions),
    activeQuestionIndex: state.activeQuestionIndex,
    questionTimersRemaining: timersSnapshot,
    updatedAt: new Date().toISOString()
  };

  const draftKey = getDraftStorageKey();
  if (draftKey) {
    localStorage.setItem(draftKey, JSON.stringify(payload));
  }

  clearTimeout(state.draftTimer);
  state.draftTimer = setTimeout(() => {
    flushDraftToServer(payload);
  }, 600);
}

async function flushDraftToServer(payload) {
  if (!state.participantId || state.status !== 'active') return;
  try {
    await fetch('/api/student/draft', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
  } catch (_) {}
}

function setActiveQuestion(idx, shouldScroll = true) {
  const cards = questionListEl.querySelectorAll('.q-card');
  if (cards.length === 0) return;
  const clamped = Math.max(0, Math.min(cards.length - 1, idx));
  state.activeQuestionIndex = clamped;

  cards.forEach((c, i) => {
    c.classList.toggle('is-active-question', i === clamped);
    const badge = document.getElementById(`q-timer-${i}`);
    const tInfo = state.questionTimers[i];
    if (badge && tInfo) {
      if (tInfo.expired) {
        badge.textContent = 'Time Expired';
        badge.className = 'q-timer-badge q-timer-badge--critical';
      } else if (i === clamped) {
        badge.textContent = `${tInfo.remaining}s remaining`;
        badge.className =
          tInfo.remaining <= 5
            ? 'q-timer-badge q-timer-badge--critical'
            : 'q-timer-badge q-timer-badge--running';
      } else {
        badge.textContent = `${tInfo.remaining}s (Paused)`;
        badge.className = 'q-timer-badge';
      }
    }
  });

  document.getElementById('focus-label').textContent = `Active Question ${clamped + 1} of ${cards.length}`;
  document.getElementById('prev-q-btn').disabled = clamped === 0;
  document.getElementById('next-q-btn').disabled = clamped === cards.length - 1;

  if (shouldScroll) {
    cards[clamped].scrollIntoView({ behavior: 'smooth', block: 'center' });
    speakQuestion(clamped);
  }
}

function startTimers(quiz) {
  stopAllTimers();

  const overallPill = document.getElementById('overall-timer-pill');
  const overallText = document.getElementById('overall-timer-text');

  if (quiz.totalTimeLimit && quiz.totalTimeLimit > 0) {
    overallPill.hidden = false;
    overallText.textContent = formatClock(state.overallRemaining);
    if (state.overallRemaining <= 0) {
      submitExam(true, 'Quiz time limit reached');
      return;
    }

    state.overallInterval = setInterval(() => {
      state.elapsedSeconds += 1;
      state.overallRemaining = Math.max(0, state.overallRemaining - 1);
      overallText.textContent = formatClock(state.overallRemaining);

      if (state.overallRemaining <= 30) {
        overallPill.className = 'timer-pill timer-pill--critical';
      } else if (state.overallRemaining <= 180) {
        overallPill.className = 'timer-pill timer-pill--warning';
      } else {
        overallPill.className = 'timer-pill';
      }

      if (state.overallRemaining === 300) showToast('5 minutes remaining.', 'warning');
      if (state.overallRemaining === 60) showToast('1 minute remaining!', 'warning');
      if (state.overallRemaining === 30) showToast('30 seconds left!', 'error');

      if (state.overallRemaining <= 0) {
        clearInterval(state.overallInterval);
        submitExam(true, 'Overall time limit expired');
      }
    }, 1000);
  } else {
    overallPill.hidden = true;
    state.overallInterval = setInterval(() => {
      state.elapsedSeconds += 1;
    }, 1000);
  }

  // Sequential/active per-question timer: ticks ONLY state.activeQuestionIndex!
  if (Object.keys(state.questionTimers).length > 0) {
    state.questionInterval = setInterval(() => {
      const idx = state.activeQuestionIndex;
      const tInfo = state.questionTimers[idx];
      if (!tInfo || tInfo.expired) return;

      tInfo.remaining = Math.max(0, tInfo.remaining - 1);
      const badge = document.getElementById(`q-timer-${idx}`);
      if (badge) {
        badge.textContent = `${tInfo.remaining}s remaining`;
        badge.className =
          tInfo.remaining <= 5
            ? 'q-timer-badge q-timer-badge--critical'
            : 'q-timer-badge q-timer-badge--running';
      }

      if (tInfo.remaining <= 0) {
        tInfo.expired = true;
        const card = questionListEl.querySelector(`.q-card[data-q-idx="${idx}"]`);
        if (card) lockQuestionInputs(card);
        if (badge) {
          badge.textContent = 'Time Expired';
          badge.className = 'q-timer-badge q-timer-badge--critical';
        }
        showToast(`Question ${idx + 1} timer finished.`, 'warning');

        const nextUnexpired = (state.quiz?.questions || []).findIndex(
          (_, qIdx) => qIdx > idx && !state.questionTimers[qIdx]?.expired
        );
        if (nextUnexpired !== -1) {
          setActiveQuestion(nextUnexpired, true);
        }
        updateProgress();
      }
    }, 1000);
  }
}

// ---- Interactions inside Questions ----

questionListEl.addEventListener('change', (e) => {
  const card = e.target.closest('.q-card');
  if (card) {
    const idx = Number(card.dataset.qIdx);
    if (idx !== state.activeQuestionIndex) setActiveQuestion(idx, false);
  }
  updateProgress();
});

questionListEl.addEventListener('input', (e) => {
  const card = e.target.closest('.q-card');
  if (card) {
    const idx = Number(card.dataset.qIdx);
    if (idx !== state.activeQuestionIndex) setActiveQuestion(idx, false);
  }
  updateProgress();
});

questionListEl.addEventListener('click', (e) => {
  const flagBtn = e.target.closest('.flag-btn');
  if (flagBtn) {
    const idx = Number(flagBtn.dataset.flagIdx);
    if (state.flaggedQuestions.has(idx)) {
      state.flaggedQuestions.delete(idx);
      flagBtn.classList.remove('is-flagged');
      flagBtn.querySelector('span').textContent = 'Flag';
    } else {
      state.flaggedQuestions.add(idx);
      flagBtn.classList.add('is-flagged');
      flagBtn.querySelector('span').textContent = 'Flagged';
    }
    updateProgress();
    return;
  }

  const card = e.target.closest('.q-card');
  if (card) {
    const idx = Number(card.dataset.qIdx);
    if (idx !== state.activeQuestionIndex) {
      setActiveQuestion(idx, false);
      updateProgress();
    }
  }
});

document.getElementById('nav-chips').addEventListener('click', (e) => {
  const chip = e.target.closest('.nav-chip');
  if (!chip) return;
  const idx = Number(chip.dataset.navIdx);
  setActiveQuestion(idx, true);
  updateProgress();
});

document.getElementById('prev-q-btn').addEventListener('click', () => {
  setActiveQuestion(state.activeQuestionIndex - 1, true);
  updateProgress();
});

document.getElementById('next-q-btn').addEventListener('click', () => {
  setActiveQuestion(state.activeQuestionIndex + 1, true);
  updateProgress();
});

document.getElementById('manual-save-draft-btn').addEventListener('click', async () => {
  if (!state.quiz) return;
  const answers = collectAnswersFromDom();
  scheduleDraftSync(answers);
  await flushDraftToServer({
    participantId: state.participantId,
    sessionId: state.sessionId,
    answers,
    flaggedQuestions: Array.from(state.flaggedQuestions),
    activeQuestionIndex: state.activeQuestionIndex,
    questionTimersRemaining: Object.fromEntries(
      Object.entries(state.questionTimers).map(([k, v]) => [k, v.remaining])
    ),
    updatedAt: new Date().toISOString()
  });
  settingsPopover.hidden = true;
  showToast('Draft saved!', 'success');
});

document.addEventListener('keydown', (e) => {
  if (viewExam.hidden || !state.quiz) return;
  if (['INPUT', 'TEXTAREA', 'SELECT'].includes(e.target.tagName)) return;

  if (e.key === 'ArrowRight' || e.key === 'n' || e.key === 'N') {
    e.preventDefault();
    setActiveQuestion(state.activeQuestionIndex + 1, true);
  } else if (e.key === 'ArrowLeft' || e.key === 'p' || e.key === 'P') {
    e.preventDefault();
    setActiveQuestion(state.activeQuestionIndex - 1, true);
  } else if (e.key === 'f' || e.key === 'F') {
    e.preventDefault();
    const card = questionListEl.querySelector(`.q-card[data-q-idx="${state.activeQuestionIndex}"]`);
    card?.querySelector('.flag-btn')?.click();
  }
});

// ---- Submission ----

const confirmModal = document.getElementById('confirm-submit-modal');

document.getElementById('submit-exam-btn').addEventListener('click', () => {
  if (!state.quiz) return;
  const answers = collectAnswersFromDom();
  const questions = state.quiz.questions || [];
  let unanswered = 0;
  questions.forEach((q, idx) => {
    if (!isQuestionAnswered(answers, idx, q)) unanswered += 1;
  });

  const parts = [];
  if (state.flaggedQuestions.size > 0) {
    parts.push(`${state.flaggedQuestions.size} question(s) are still flagged.`);
  }
  if (unanswered > 0) {
    parts.push(`${unanswered} question(s) appear unanswered.`);
  }
  if (parts.length === 0) {
    parts.push('All questions answered. Once submitted, answers cannot be edited.');
  }

  document.getElementById('submit-modal-message').textContent = parts.join(' ');
  confirmModal.hidden = false;
});

document.getElementById('cancel-submit-btn').addEventListener('click', () => {
  confirmModal.hidden = true;
});

document.getElementById('confirm-submit-yes-btn').addEventListener('click', async () => {
  confirmModal.hidden = true;
  await submitExam(false, null);
});

async function submitExam(autoSubmitted, timeoutReason) {
  if (state.submitting || !state.participantId || !state.quiz) return;
  state.submitting = true;
  const submitBtn = document.getElementById('submit-exam-btn');
  submitBtn.disabled = true;
  submitBtn.textContent = autoSubmitted ? 'Auto-Submitting...' : 'Submitting...';

  const answers = collectAnswersFromDom();

  try {
    const res = await fetchJson('/api/submit', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        participantId: state.participantId,
        sessionId: state.sessionId,
        answers,
        timeSpent: state.elapsedSeconds,
        autoSubmitted,
        timeoutReason
      })
    });

    stopAllTimers();
    const draftKey = getDraftStorageKey();
    if (draftKey) localStorage.removeItem(draftKey);
    renderSubmittedResult(res);
    showView('result');
  } catch (err) {
    showToast(err.message, 'error');
    submitBtn.disabled = false;
    submitBtn.textContent = 'Submit Exam';
  } finally {
    state.submitting = false;
  }
}

function renderSubmittedResult(summary) {
  const headline = document.getElementById('result-headline');
  const scoreEl = document.getElementById('result-score');
  const pctEl = document.getElementById('result-percent');
  const noteEl = document.getElementById('result-note');

  if (summary.endedByTeacher) {
    headline.textContent = 'Session Ended';
    scoreEl.textContent = 'Closed';
    pctEl.textContent = 'Teacher finalized the session';
    noteEl.textContent = 'Check with your teacher or wait for the next classroom quiz.';
    return;
  }

  const score = summary.score ?? 0;
  const total = summary.totalGradeable ?? 0;
  const pct = summary.percentage ?? (total > 0 ? Math.round((score / total) * 100) : 0);

  headline.textContent = pct >= 85 ? 'Outstanding Work!' : pct >= 60 ? 'Exam Submitted!' : 'Submission Recorded!';
  scoreEl.textContent = total > 0 ? `${score} / ${total}` : 'Submitted';
  pctEl.textContent = total > 0 ? `${pct}% Score` : 'Recorded';
  noteEl.textContent = 'Your MCQ responses have been saved offline for Cognitive-Aware Knowledge Tracing.';
}

function connectExamEvents() {
  if (state.eventSource) state.eventSource.close();
  const source = new EventSource('/api/exam/events');
  source.addEventListener('status', async (event) => {
    try {
      const payload = JSON.parse(event.data);
      if (payload.type === 'init') return;
      if (payload.type === 'ended' && !viewExam.hidden && state.participantId) {
        await submitExam(true, 'Session ended by teacher');
        return;
      }
      await syncSessionState();
    } catch (_) {}
  });
  state.eventSource = source;
}

loadAccessibilityPrefs();
syncSessionState();
window.addEventListener('load', () => {
  setTimeout(connectExamEvents, 120);
});
