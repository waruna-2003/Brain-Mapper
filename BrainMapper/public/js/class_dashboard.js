(async function initClassDashboard() {
  const params = new URLSearchParams(window.location.search);
  const requestedId = params.get('classId') || 'class-1';

  const classPill = document.getElementById('active-class-pill');
  const rosterLink = document.getElementById('roster-quick-link');
  const btnLibrary = document.getElementById('btn-library');
  const btnCreate = document.getElementById('btn-create');
  const btnSession = document.getElementById('btn-session');
  const btnAnalyze = document.getElementById('btn-analyze');

  function applyClassLinks(cls) {
    const id = encodeURIComponent(cls.id);
    classPill.textContent = `${cls.name} • ${cls.subject}`;
    rosterLink.textContent = `Roster (${cls.studentCount})`;
    rosterLink.href = `/?roster=${id}`;
    btnLibrary.href = `/quiz_library.html?classId=${id}`;
    btnCreate.href = `/create_quiz.html?classId=${id}`;
    btnSession.href = `/session_monitor.html?classId=${id}`;
    btnAnalyze.href = `/analyze.html?classId=${id}`;
  }

  try {
    const res = await fetch(`/api/classes/${encodeURIComponent(requestedId)}`);
    if (res.ok) {
      applyClassLinks(await res.json());
      return;
    }
    const listRes = await fetch('/api/classes');
    if (listRes.ok) {
      const all = await listRes.json();
      if (all[0]) applyClassLinks(all[0]);
    }
  } catch (error) {
    console.error('Failed to load class dashboard metadata:', error);
  }
})();
