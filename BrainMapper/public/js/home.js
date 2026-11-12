const DEFAULT_VISIBLE_STUDENTS = 6;

const state = {
  classes: [],
  activeRosterClass: null,
  rosterStudents: [],
  showAllStudents: false,
  selectedAccent: 'indigo'
};

const classesGrid = document.getElementById('classes-grid');
const lanStatusPill = document.getElementById('lan-status-pill');
const lanStatusText = document.getElementById('lan-status-text');

const rosterModal = document.getElementById('roster-modal');
const rosterTitle = document.getElementById('roster-modal-title');
const rosterSubtitle = document.getElementById('roster-modal-subtitle');
const rosterSearch = document.getElementById('roster-search');
const rosterList = document.getElementById('roster-list');
const rosterCountText = document.getElementById('roster-count-text');
const rosterToggleAllBtn = document.getElementById('roster-toggle-all');

const addClassModal = document.getElementById('add-class-modal');
const addClassForm = document.getElementById('add-class-form');
const addClassError = document.getElementById('add-class-error');
const newClassName = document.getElementById('new-class-name');
const newClassSubject = document.getElementById('new-class-subject');

const addStudentModal = document.getElementById('add-student-modal');
const addStudentForm = document.getElementById('add-student-form');
const addStudentError = document.getElementById('add-student-error');
const addStudentSubtitle = document.getElementById('add-student-subtitle');

function escapeHtml(value) {
  const div = document.createElement('div');
  div.textContent = value == null ? '' : String(value);
  return div.innerHTML;
}

function getScoreClass(score) {
  if (score >= 75) return 'score-high';
  if (score >= 60) return 'score-mid';
  return 'score-low';
}

function openClassDashboard(classId) {
  window.location.href = `/class_dashboard.html?classId=${encodeURIComponent(classId)}`;
}

async function checkServerHealth() {
  try {
    const res = await fetch('/api/health');
    if (!res.ok) throw new Error('Health check failed');
    const data = await res.json();
    lanStatusPill.classList.remove('is-offline');
    const ipHint = data.localIPs && data.localIPs[0] ? ` (${data.localIPs[0].address})` : '';
    lanStatusText.textContent = `LAN server ready. No internet required${ipHint}`;
  } catch (_) {
    lanStatusPill.classList.add('is-offline');
    lanStatusText.textContent = 'LAN server offline — check local service';
  }
}

async function loadClasses() {
  const res = await fetch('/api/classes');
  if (!res.ok) throw new Error('Failed to load classes');
  state.classes = await res.json();
  renderClasses();
}

function renderClasses() {
  const cardsHtml = state.classes
    .map((cls) => {
      const accent = escapeHtml(cls.accentColor || 'indigo');
      const studentWord = cls.studentCount === 1 ? 'Student' : 'Students';
      const quizWord = cls.quizCount === 1 ? 'Quiz' : 'Quizzes';

      return `
        <article
          class="class-card"
          data-class-id="${escapeHtml(cls.id)}"
          data-accent="${accent}"
          tabindex="0"
          role="button"
          aria-label="Open ${escapeHtml(cls.name)} dashboard"
        >
          <div class="class-strip" aria-hidden="true"></div>
          <div>
            <div class="class-top-row">
              <h3 class="class-name">${escapeHtml(cls.name)}</h3>
              <span class="status-badge">${escapeHtml(cls.status || 'Active')}</span>
            </div>
            <p class="class-subject">${escapeHtml(cls.subject)}</p>

            <div class="class-stats">
              <button
                type="button"
                class="stat-roster-btn"
                data-roster-id="${escapeHtml(cls.id)}"
                title="View Student Roster"
              >
                <img src="/assets/icons/students.svg" alt="" width="16" height="16" class="stat-icon">
                <span>${cls.studentCount} ${studentWord}</span>
              </button>

              <div class="stat-row">
                <img src="/assets/icons/quizzes.svg" alt="" width="16" height="16" class="stat-icon">
                <span>${cls.quizCount} ${quizWord}</span>
              </div>
            </div>
          </div>

          <div class="class-footer">
            <span class="last-session">
              <img src="/assets/icons/clock.svg" alt="" width="14" height="14" class="clock-icon">
              <span>Last session: ${escapeHtml(cls.lastSessionLabel || 'Not started')}</span>
            </span>
          </div>
        </article>
      `;
    })
    .join('');

  const addCardHtml = `
    <button type="button" class="add-class-card" id="open-add-class-btn">
      <span class="add-plus-circle" aria-hidden="true">
        <img src="/assets/icons/plus.svg" alt="" width="24" height="24" class="plus-icon">
      </span>
      <span class="add-class-label">Add New Class</span>
    </button>
  `;

  classesGrid.innerHTML = cardsHtml + addCardHtml;

  classesGrid.querySelectorAll('.class-card').forEach((card) => {
    const classId = card.dataset.classId;
    card.addEventListener('click', () => openClassDashboard(classId));
    card.addEventListener('keydown', (event) => {
      if (event.key === 'Enter' || event.key === ' ') {
        event.preventDefault();
        openClassDashboard(classId);
      }
    });
  });

  classesGrid.querySelectorAll('.stat-roster-btn').forEach((btn) => {
    btn.addEventListener('click', (event) => {
      event.stopPropagation();
      openRosterModal(btn.dataset.rosterId);
    });
  });

  document.getElementById('open-add-class-btn').addEventListener('click', openAddClassModal);
}

async function openRosterModal(classId, searchQuery = '') {
  const query = searchQuery ? `?q=${encodeURIComponent(searchQuery)}` : '';
  const res = await fetch(`/api/classes/${encodeURIComponent(classId)}/students${query}`);
  if (!res.ok) return;

  const data = await res.json();
  state.activeRosterClass = data.classInfo;
  state.rosterStudents = data.students;
  if (!searchQuery) state.showAllStudents = false;

  const cls = data.classInfo;
  rosterTitle.textContent = `${cls.name}: Student Roster`;
  rosterSubtitle.textContent = `${cls.subject} • ${data.totalCount} Students Enrolled • ${cls.quizCount} Quizzes Completed`;
  rosterModal.hidden = false;
  renderRosterRows(data.totalCount, Boolean(searchQuery));
}

function renderRosterRows(totalCount, isSearching) {
  const list = state.rosterStudents;
  const visible = isSearching || state.showAllStudents
    ? list
    : list.slice(0, DEFAULT_VISIBLE_STUDENTS);

  if (visible.length === 0) {
    rosterList.innerHTML = '<div class="empty-roster">No students match your search.</div>';
  } else {
    rosterList.innerHTML = visible
      .map((student, index) => {
        const tone = index % 6;
        const scoreClass = getScoreClass(student.overallScore);
        return `
          <div class="roster-row">
            <div class="student-ident">
              <div class="avatar-circle avatar-tone-${tone}">${escapeHtml(student.initials)}</div>
              <div>
                <div class="student-name">${escapeHtml(student.name)}</div>
                <div class="student-code">${escapeHtml(student.code)}</div>
              </div>
            </div>
            <span class="skill-pill">${escapeHtml(student.dominantSkill)}</span>
            <div class="student-metrics">
              <span class="score-pill ${scoreClass}">${student.overallScore}%</span>
              <button type="button" class="view-link-btn" data-student-id="${escapeHtml(student.id)}">View</button>
            </div>
          </div>
        `;
      })
      .join('');

    rosterList.querySelectorAll('.view-link-btn').forEach((btn) => {
      btn.addEventListener('click', () => {
        const classId = state.activeRosterClass.id;
        window.location.href = `/class_dashboard.html?classId=${encodeURIComponent(classId)}&studentId=${encodeURIComponent(btn.dataset.studentId)}`;
      });
    });
  }

  rosterCountText.textContent = `Showing ${visible.length} of ${totalCount} students`;
  const hasMore = !isSearching && list.length > DEFAULT_VISIBLE_STUDENTS;
  rosterToggleAllBtn.hidden = !hasMore;
  rosterToggleAllBtn.textContent = state.showAllStudents ? 'Show top 6' : `Show all ${list.length}`;
}

function closeRosterModal() {
  rosterModal.hidden = true;
  rosterSearch.value = '';
}

function openAddClassModal() {
  addClassError.hidden = true;
  addClassForm.reset();
  state.selectedAccent = 'indigo';
  document.querySelectorAll('#accent-swatches .swatch-btn').forEach((btn) => {
    btn.classList.toggle('is-selected', btn.dataset.accent === 'indigo');
  });
  addClassModal.hidden = false;
  newClassName.focus();
}

function closeAddClassModal() {
  addClassModal.hidden = true;
}

function openAddStudentModal() {
  if (!state.activeRosterClass) return;
  addStudentError.hidden = true;
  addStudentForm.reset();
  addStudentSubtitle.textContent = `Enroll a student into ${state.activeRosterClass.name}`;
  addStudentModal.hidden = false;
  document.getElementById('new-student-name').focus();
}

function closeAddStudentModal() {
  addStudentModal.hidden = true;
}

// Event bindings
rosterSearch.addEventListener('input', () => {
  if (!state.activeRosterClass) return;
  openRosterModal(state.activeRosterClass.id, rosterSearch.value.trim());
});

rosterToggleAllBtn.addEventListener('click', () => {
  state.showAllStudents = !state.showAllStudents;
  renderRosterRows(state.activeRosterClass.studentCount, false);
});

document.getElementById('roster-close-x').addEventListener('click', closeRosterModal);
document.getElementById('roster-close-btn').addEventListener('click', closeRosterModal);
document.getElementById('view-analytics-btn').addEventListener('click', () => {
  if (state.activeRosterClass) openClassDashboard(state.activeRosterClass.id);
});

document.getElementById('export-roster-btn').addEventListener('click', () => {
  if (!state.activeRosterClass) return;
  window.location.href = `/api/classes/${encodeURIComponent(state.activeRosterClass.id)}/students/export`;
});

document.getElementById('open-add-student-btn').addEventListener('click', openAddStudentModal);

document.querySelectorAll('#accent-swatches .swatch-btn').forEach((btn) => {
  btn.addEventListener('click', () => {
    state.selectedAccent = btn.dataset.accent;
    document.querySelectorAll('#accent-swatches .swatch-btn').forEach((other) => {
      other.classList.toggle('is-selected', other === btn);
    });
  });
});

document.getElementById('add-class-close-x').addEventListener('click', closeAddClassModal);
document.getElementById('add-class-cancel').addEventListener('click', closeAddClassModal);

addClassForm.addEventListener('submit', async (event) => {
  event.preventDefault();
  addClassError.hidden = true;

  const res = await fetch('/api/classes', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      name: newClassName.value,
      subject: newClassSubject.value,
      accentColor: state.selectedAccent
    })
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ message: 'Could not create class' }));
    addClassError.textContent = err.message;
    addClassError.hidden = false;
    return;
  }

  closeAddClassModal();
  await loadClasses();
});

document.getElementById('add-student-close-x').addEventListener('click', closeAddStudentModal);
document.getElementById('add-student-cancel').addEventListener('click', closeAddStudentModal);

addStudentForm.addEventListener('submit', async (event) => {
  event.preventDefault();
  if (!state.activeRosterClass) return;
  addStudentError.hidden = true;

  const studentName = document.getElementById('new-student-name').value.trim();
  const studentCode = document.getElementById('new-student-code').value.trim();

  if (!studentName) {
    addStudentError.textContent = 'Student full name is required.';
    addStudentError.hidden = false;
    return;
  }
  if (!studentCode) {
    addStudentError.textContent = 'Unique Student ID is required.';
    addStudentError.hidden = false;
    document.getElementById('new-student-code').focus();
    return;
  }

  const res = await fetch(`/api/classes/${encodeURIComponent(state.activeRosterClass.id)}/students`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      name: studentName,
      code: studentCode,
      dominantSkill: document.getElementById('new-student-skill').value
    })
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ message: 'Could not enroll student' }));
    addStudentError.textContent = err.message;
    addStudentError.hidden = false;
    return;
  }

  closeAddStudentModal();
  await loadClasses();
  await openRosterModal(state.activeRosterClass.id, rosterSearch.value.trim());
});

[rosterModal, addClassModal, addStudentModal].forEach((backdrop) => {
  backdrop.addEventListener('click', (event) => {
    if (event.target === backdrop) backdrop.hidden = true;
  });
});

document.addEventListener('keydown', (event) => {
  if (event.key === 'Escape') {
    closeAddStudentModal();
    closeAddClassModal();
    closeRosterModal();
  }
});

checkServerHealth();
loadClasses().then(() => {
  const rosterParam = new URLSearchParams(window.location.search).get('roster');
  if (rosterParam) {
    openRosterModal(rosterParam);
  }
});
