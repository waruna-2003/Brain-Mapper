const params = new URLSearchParams(window.location.search);
const classId = params.get('classId') || 'class-1';
const editQuizId = params.get('quizId') || null;

let questionUid = 0;
let loadedRandomization = null;

const questionsContainer = document.getElementById('questions-container');
const statusBanner = document.getElementById('status-banner');

function escapeHtml(value) {
  const div = document.createElement('div');
  div.textContent = value == null ? '' : String(value);
  return div.innerHTML;
}

function showStatus(message, type) {
  statusBanner.textContent = message;
  statusBanner.className = `status-banner status-banner--${type}`;
  statusBanner.hidden = false;
  statusBanner.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

function addQuestionCard(initial = null) {
  questionUid += 1;
  const uid = questionUid;

  const card = document.createElement('article');
  card.className = 'q-card';
  card.dataset.uid = String(uid);
  if (initial?.cognitiveDemand && typeof initial.cognitiveDemand === 'object') {
    card.dataset.cognitiveDemand = JSON.stringify(initial.cognitiveDemand);
  }

  card.innerHTML = `
    <div class="q-head">
      <div style="display: flex; align-items: center; gap: 10px;">
        <span class="q-badge">Question ${questionsContainer.children.length + 1}</span>
        <span style="font-size: 12px; font-weight: 700; color: var(--indigo-600); background: var(--indigo-50); padding: 4px 10px; border-radius: 999px;">
          Multiple Choice (MCQ A–D)
        </span>
      </div>
      <button type="button" class="q-delete-btn">Remove</button>
    </div>

    <div class="q-top-grid">
      <label class="field">
        <span class="field-label">Question Text</span>
        <input type="text" class="input q-text" placeholder="Enter multiple choice question prompt..." value="${escapeHtml(initial?.question || '')}">
      </label>

      <label class="field">
        <span class="field-label">Time Limit (sec)</span>
        <input type="number" class="input q-time" min="0" value="${Number(initial?.timeLimit) || 0}">
      </label>
    </div>

    <div class="options-grid">
      ${['A', 'B', 'C', 'D']
        .map(
          (key) => `
        <div class="opt-chip">
          <span class="opt-letter">${key}</span>
          <input type="text" class="input q-opt" data-opt="${key}" placeholder="Option ${key}" value="${escapeHtml(initial?.options?.[key] || '')}">
        </div>
      `
        )
        .join('')}
    </div>

    <label class="field" style="max-width: 240px;">
      <span class="field-label">Correct Option</span>
      <select class="select q-mc-correct">
        ${['A', 'B', 'C', 'D']
          .map((key) => `<option value="${key}" ${initial?.correct === key ? 'selected' : ''}>Option ${key}</option>`)
          .join('')}
      </select>
    </label>

    <div class="options-grid">
      <label class="field">
        <span class="field-label">Explanation (Optional)</span>
        <input type="text" class="input q-explanation" placeholder="Shown during review..." value="${escapeHtml(initial?.explanation || '')}">
      </label>

      <div class="field">
        <span class="field-label">Question Image (Optional)</span>
        <input type="file" class="input q-image-input" accept="image/*" style="padding: 7px 10px;">
        <div class="img-preview" ${initial?.image ? '' : 'hidden'}>
          <img src="${escapeHtml(initial?.image || '')}" alt="Question attachment">
          <button type="button" class="q-delete-btn q-clear-img">Remove</button>
        </div>
      </div>
    </div>
  `;

  questionsContainer.appendChild(card);

  const imgInput = card.querySelector('.q-image-input');
  const imgPreview = card.querySelector('.img-preview');
  const imgEl = imgPreview.querySelector('img');
  imgInput.addEventListener('change', () => {
    const file = imgInput.files[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (e) => {
      imgEl.src = e.target.result;
      imgPreview.hidden = false;
    };
    reader.readAsDataURL(file);
  });

  card.querySelector('.q-clear-img').addEventListener('click', () => {
    imgEl.removeAttribute('src');
    imgInput.value = '';
    imgPreview.hidden = true;
  });

  card.querySelector('.q-delete-btn').addEventListener('click', () => {
    card.remove();
    renumberQuestions();
  });

  renumberQuestions();
}

function renumberQuestions() {
  Array.from(questionsContainer.children).forEach((card, idx) => {
    card.querySelector('.q-badge').textContent = `Question ${idx + 1}`;
  });
}

function collectQuizPayload() {
  const name = document.getElementById('quiz-name').value.trim();
  const description = document.getElementById('quiz-description').value.trim();
  const category = document.getElementById('quiz-category').value;
  const difficulty = document.getElementById('quiz-difficulty').value;

  const timeVal = Number(document.getElementById('quiz-time-value').value) || 0;
  const timeUnit = document.getElementById('quiz-time-unit').value;
  const multiplier = timeUnit === 'hours' ? 3600 : timeUnit === 'minutes' ? 60 : 1;

  const questions = Array.from(questionsContainer.children).map((card, idx) => {
    const question = card.querySelector('.q-text').value.trim();
    const explanation = card.querySelector('.q-explanation').value.trim();
    const timeLimit = Math.max(0, Number(card.querySelector('.q-time').value) || 0);
    const imgEl = card.querySelector('.img-preview img');
    const image = imgEl.getAttribute('src') || null;

    let cognitiveDemand;
    if (card.dataset.cognitiveDemand) {
      try {
        cognitiveDemand = JSON.parse(card.dataset.cognitiveDemand);
      } catch (_) {}
    }

    if (!question) throw new Error(`Question ${idx + 1} is missing text.`);

    const options = {};
    for (const key of ['A', 'B', 'C', 'D']) {
      const val = card.querySelector(`.q-opt[data-opt="${key}"]`).value.trim();
      if (!val) throw new Error(`Question ${idx + 1} is missing option ${key}.`);
      options[key] = val;
    }

    return {
      type: 'multiple-choice',
      question,
      options,
      correct: card.querySelector('.q-mc-correct').value,
      explanation,
      image,
      timeLimit,
      ...(cognitiveDemand ? { cognitiveDemand } : {})
    };
  });

  if (!name) throw new Error('Quiz title is required.');
  if (questions.length === 0) throw new Error('Add at least one question before saving.');

  return {
    classId,
    name,
    description,
    category,
    difficulty,
    totalTimeLimit: Math.max(0, Math.round(timeVal * multiplier)),
    isTemplate: document.getElementById('is-template').checked,
    randomization: loadedRandomization || {
      shuffleQuestions: false,
      shuffleOptions: false,
      useQuestionPool: false,
      poolSize: 0
    },
    questions
  };
}

async function saveQuiz(redirectToPredict) {
  statusBanner.hidden = true;
  let payload;
  try {
    payload = collectQuizPayload();
  } catch (err) {
    showStatus(err.message, 'error');
    return;
  }

  const url = editQuizId ? `/api/quizzes/${encodeURIComponent(editQuizId)}` : '/api/quizzes';
  const method = editQuizId ? 'PUT' : 'POST';

  const res = await fetch(url, {
    method,
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ message: 'Failed to save quiz' }));
    showStatus(err.message, 'error');
    return;
  }

  const saved = await res.json();
  if (redirectToPredict) {
    window.location.href = `/predicted_results.html?quizId=${encodeURIComponent(saved.id)}&classId=${encodeURIComponent(classId)}`;
  } else {
    showStatus(`Quiz "${saved.name}" saved! Returning to Quiz Library...`, 'success');
    setTimeout(() => {
      window.location.href = `/quiz_library.html?classId=${encodeURIComponent(classId)}`;
    }, 900);
  }
}

async function initEditor() {
  document.getElementById('back-link').href = `/quiz_library.html?classId=${encodeURIComponent(classId)}`;

  fetch(`/api/classes/${encodeURIComponent(classId)}`)
    .then((r) => (r.ok ? r.json() : null))
    .then((cls) => {
      if (cls) document.getElementById('class-pill').textContent = `${cls.name} • ${cls.subject}`;
    })
    .catch(() => {});

  if (editQuizId) {
    document.getElementById('page-title').textContent = 'Edit Quiz';
    const res = await fetch(`/api/quizzes/${encodeURIComponent(editQuizId)}`);
    if (res.ok) {
      const quiz = await res.json();
      document.getElementById('quiz-name').value = quiz.name || '';
      document.getElementById('quiz-description').value = quiz.description || '';
      document.getElementById('quiz-category').value = quiz.category || 'Mathematics';
      document.getElementById('quiz-difficulty').value = quiz.difficulty || 'Medium';
      document.getElementById('quiz-time-value').value = Math.round((quiz.totalTimeLimit || 0) / 60);
      document.getElementById('quiz-time-unit').value = 'minutes';
      document.getElementById('is-template').checked = Boolean(quiz.isTemplate);
      loadedRandomization = quiz.randomization || null;

      (quiz.questions || []).forEach((q) => addQuestionCard(q));
      return;
    }
  }

  addQuestionCard();
}

document.getElementById('add-question-btn').addEventListener('click', () => addQuestionCard());
document.getElementById('save-quiz-btn').addEventListener('click', () => saveQuiz(false));
document.getElementById('save-predict-btn').addEventListener('click', () => saveQuiz(true));

initEditor();
