const params = new URLSearchParams(window.location.search);
const classId = params.get('classId') || 'class-1';

const state = {
  quizzes: [],
  currentTab: 'quizzes'
};

const classPill = document.getElementById('class-pill');
const backLink = document.getElementById('back-link');
const createQuizLink = document.getElementById('create-quiz-link');
const libraryContent = document.getElementById('library-content');

const searchInput = document.getElementById('search-input');
const categoryFilter = document.getElementById('category-filter');
const difficultyFilter = document.getElementById('difficulty-filter');

const importModal = document.getElementById('import-modal');

function escapeHtml(value) {
  const div = document.createElement('div');
  div.textContent = value == null ? '' : String(value);
  return div.innerHTML;
}

function formatDuration(seconds) {
  if (!seconds || seconds <= 0) return 'No limit';
  const mins = Math.round(seconds / 60);
  if (mins < 60) return `${mins} Mins`;
  const hrs = Math.floor(mins / 60);
  const rem = mins % 60;
  return rem ? `${hrs}h ${rem}m` : `${hrs}h`;
}

function formatUpdatedLabel(isoString) {
  if (!isoString) return 'Recently';
  const date = new Date(isoString);
  if (Number.isNaN(date.getTime())) return 'Recently';
  const diffHours = (Date.now() - date.getTime()) / (1000 * 60 * 60);
  if (diffHours >= 0 && diffHours < 2) return 'Just now';
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

function initLinks() {
  const encoded = encodeURIComponent(classId);
  backLink.href = `/class_dashboard.html?classId=${encoded}`;
  createQuizLink.href = `/create_quiz.html?classId=${encoded}`;
}

async function loadClassMeta() {
  try {
    const res = await fetch(`/api/classes/${encodeURIComponent(classId)}`);
    if (res.ok) {
      const cls = await res.json();
      classPill.textContent = `${cls.name} • ${cls.subject}`;
    }
  } catch (_) {
    // fallback pill remains
  }
}

async function loadQuizzes() {
  const res = await fetch(`/api/quizzes?classId=${encodeURIComponent(classId)}`);
  state.quizzes = res.ok ? await res.json() : [];
  renderLibrary();
}

function getFilteredQuizzes() {
  const q = searchInput.value.trim().toLowerCase();
  const cat = categoryFilter.value;
  const diff = difficultyFilter.value;

  return state.quizzes.filter((quiz) => {
    if (state.currentTab === 'templates' && !quiz.isTemplate) return false;
    if (state.currentTab === 'archived' && !quiz.isArchived) return false;
    if (state.currentTab === 'quizzes' && (quiz.isArchived || quiz.isTemplate)) return false;

    if (q) {
      const haystack = `${quiz.name} ${quiz.description || ''} ${quiz.category || ''}`.toLowerCase();
      if (!haystack.includes(q)) return false;
    }
    if (cat && quiz.category !== cat) return false;
    if (diff && quiz.difficulty !== diff) return false;
    return true;
  });
}

function renderLibrary() {
  const items = getFilteredQuizzes();

  if (items.length === 0) {
    const emptyMsg =
      state.currentTab === 'templates'
        ? 'Save a quiz as a template to reuse it here'
        : state.currentTab === 'archived'
          ? 'No archived quizzes in this class'
          : 'Create a new quiz to get started';

    libraryContent.innerHTML = `
      <div class="empty-state-box">
        <div class="empty-inbox-badge" aria-hidden="true">
          <img src="/assets/icons/inbox-empty.svg" alt="" width="32" height="32">
        </div>
        <h3 class="empty-state-title">No quizzes found</h3>
        <p class="empty-state-desc">${escapeHtml(emptyMsg)}</p>
        <a href="/create_quiz.html?classId=${encodeURIComponent(classId)}" class="empty-create-btn">
          <img src="/assets/icons/lib-plus-indigo.svg" alt="" width="16" height="16">
          <span>Create New Quiz</span>
        </a>
      </div>
    `;
    return;
  }

  const cardsHtml = items.map((quiz) => renderQuizCard(quiz)).join('');
  libraryContent.innerHTML = `
    <div style="display: flex; flex-direction: column; gap: 16px;">
      <div class="quiz-grid-header">
        <span class="quiz-grid-label">Class Quizzes</span>
        <span class="quiz-count-pill">${items.length} ${items.length === 1 ? 'Quiz' : 'Quizzes'}</span>
      </div>
      <div class="quiz-grid">${cardsHtml}</div>
    </div>
  `;

  libraryContent.querySelectorAll('[data-action]').forEach((btn) => {
    btn.addEventListener('click', () => handleQuizAction(btn.dataset.action, btn.dataset.quizId));
  });
}

function renderQuizCard(quiz) {
  const qCount = Array.isArray(quiz.questions) ? quiz.questions.length : 0;
  const diff = quiz.difficulty || 'Medium';
  const diffClass = `diff-${diff.toLowerCase()}`;
  const isNew = Boolean(quiz.isNew);
  const encodedQuiz = encodeURIComponent(quiz.id);
  const encodedClass = encodeURIComponent(classId);

  return `
    <article class="quiz-card ${isNew ? 'is-new' : ''}">
      <div>
        <div class="quiz-card-badges">
          <div class="badge-group">
            <span class="cat-badge">${escapeHtml(quiz.category || 'Mathematics')}</span>
            ${isNew ? '<span class="new-badge">NEW</span>' : ''}
          </div>
          <span class="diff-badge ${diffClass}">${escapeHtml(diff)}</span>
        </div>

        <h3 class="quiz-card-title">${escapeHtml(quiz.name)}</h3>
        <p class="quiz-card-desc">${escapeHtml(quiz.description || 'No description provided.')}</p>
      </div>

      <div class="quiz-card-footer">
        <div class="quiz-stats-row">
          <span class="quiz-stat">
            <img src="/assets/icons/card-questions.svg" alt="" width="14" height="14">
            <span>${qCount} ${qCount === 1 ? 'Question' : 'Questions'}</span>
          </span>
          <span class="quiz-stat">
            <img src="/assets/icons/card-clock.svg" alt="" width="14" height="14">
            <span>${formatDuration(quiz.totalTimeLimit)}</span>
          </span>
        </div>

        <a
          href="/predicted_results.html?quizId=${encodedQuiz}&classId=${encodedClass}"
          class="predict-btn"
        >
          <img src="/assets/icons/predict-bars.svg" alt="" width="16" height="16">
          <span>Predict Scores</span>
        </a>

        <div class="quiz-card-actions">
          <span class="quiz-updated">Updated ${escapeHtml(formatUpdatedLabel(quiz.updatedAt))}</span>
          <div class="card-link-group">
            <a href="/create_quiz.html?quizId=${encodedQuiz}&classId=${encodedClass}" class="card-link card-link--edit" style="text-decoration: none;">Edit</a>
            <button type="button" class="card-link card-link--copy" data-action="copy" data-quiz-id="${escapeHtml(quiz.id)}">Copy</button>
            <button type="button" class="card-link card-link--archive" data-action="${quiz.isArchived ? 'unarchive' : 'archive'}" data-quiz-id="${escapeHtml(quiz.id)}">
              ${quiz.isArchived ? 'Restore' : 'Archive'}
            </button>
            <button type="button" class="card-link card-link--delete" data-action="delete" data-quiz-id="${escapeHtml(quiz.id)}">Delete</button>
          </div>
        </div>
      </div>
    </article>
  `;
}

async function handleQuizAction(action, quizId) {
  const quiz = state.quizzes.find((q) => q.id === quizId);
  if (!quiz) return;

  if (action === 'copy') {
    const newName = prompt('Name for duplicated quiz:', `${quiz.name} (Copy)`);
    if (!newName || !newName.trim()) return;
    await fetch('/api/quizzes/duplicate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ quizId, newName: newName.trim() })
    });
    await loadQuizzes();
  } else if (action === 'archive') {
    await fetch(`/api/quizzes/${encodeURIComponent(quizId)}/archive`, { method: 'PUT' });
    await loadQuizzes();
  } else if (action === 'unarchive') {
    await fetch(`/api/quizzes/${encodeURIComponent(quizId)}/unarchive`, { method: 'PUT' });
    await loadQuizzes();
  } else if (action === 'delete') {
    if (!confirm(`Delete "${quiz.name}" permanently?`)) return;
    await fetch(`/api/quizzes/${encodeURIComponent(quizId)}`, { method: 'DELETE' });
    await loadQuizzes();
  }
}

// CSV Import (handles CRLF and escaped quotes "")
function parseCsvLine(line) {
  const fields = [];
  let current = '';
  let inQuotes = false;

  for (let i = 0; i < line.length; i++) {
    const ch = line[i];
    if (ch === '"') {
      if (inQuotes && line[i + 1] === '"') {
        current += '"';
        i++;
      } else {
        inQuotes = !inQuotes;
      }
    } else if (ch === ',' && !inQuotes) {
      fields.push(current.trim());
      current = '';
    } else {
      current += ch;
    }
  }
  fields.push(current.trim());
  return fields;
}

function parseCsvQuestions(csvText) {
  const lines = csvText.replace(/\r\n/g, '\n').split('\n').map((l) => l.trim()).filter(Boolean);
  if (lines.length === 0) return [];
  const start = lines[0].toLowerCase().includes('question') ? 1 : 0;
  const questions = [];

  for (let i = start; i < lines.length; i++) {
    const fields = parseCsvLine(lines[i]);
    if (fields.length < 6 || !fields[0]) continue;
    const question = fields[0];
    const hasExplicitType =
      fields.length >= 7 &&
      ['multiple-choice', 'true-false', 'multiple-answer', 'fill-blank', 'matching', 'short-answer'].includes(
        fields[1].toLowerCase()
      );

    if (hasExplicitType && fields[1].toLowerCase() !== 'multiple-choice') {
      throw new Error(
        `Row ${i + 1} uses unsupported type "${fields[1]}". BrainMapper only supports Multiple Choice (MCQ) questions.`
      );
    }

    const offset = hasExplicitType ? 2 : 1;
    if (fields.length < offset + 5) continue;

    questions.push({
      type: 'multiple-choice',
      question,
      options: {
        A: fields[offset],
        B: fields[offset + 1],
        C: fields[offset + 2],
        D: fields[offset + 3]
      },
      correct: (fields[offset + 4] || '').toUpperCase(),
      explanation: fields[offset + 5] || ''
    });
  }
  return questions;
}

document.querySelectorAll('.lib-tab').forEach((tab) => {
  tab.addEventListener('click', () => {
    state.currentTab = tab.dataset.tab;
    document.querySelectorAll('.lib-tab').forEach((t) => t.classList.toggle('is-active', t === tab));
    renderLibrary();
  });
});

searchInput.addEventListener('input', renderLibrary);
categoryFilter.addEventListener('change', renderLibrary);
difficultyFilter.addEventListener('change', renderLibrary);

document.getElementById('open-import-btn').addEventListener('click', () => { importModal.hidden = false; });
document.getElementById('import-close-x').addEventListener('click', () => { importModal.hidden = true; });
document.getElementById('import-cancel-btn').addEventListener('click', () => { importModal.hidden = true; });

document.getElementById('import-submit-btn').addEventListener('click', async () => {
  const file = document.getElementById('csv-file-input').files[0];
  if (!file) {
    alert('Please select a CSV file.');
    return;
  }
  const text = await file.text();
  let questions;
  try {
    questions = parseCsvQuestions(text);
  } catch (err) {
    alert(err.message);
    return;
  }
  if (questions.length === 0) {
    alert('No valid Multiple Choice (MCQ) questions found in CSV.');
    return;
  }

  const name = document.getElementById('import-quiz-name').value.trim() || file.name.replace(/\.csv$/i, '');
  const res = await fetch('/api/quizzes', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      classId,
      name,
      category: 'Mathematics',
      difficulty: 'Medium',
      questions
    })
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ message: 'Import failed' }));
    alert(err.message);
    return;
  }

  importModal.hidden = true;
  document.getElementById('csv-file-input').value = '';
  document.getElementById('import-quiz-name').value = '';
  await loadQuizzes();
});

importModal.addEventListener('click', (event) => {
  if (event.target === importModal) importModal.hidden = true;
});

initLinks();
loadClassMeta();
loadQuizzes();
