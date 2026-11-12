const params = new URLSearchParams(window.location.search);
const quizId = params.get('quizId') || 'quiz-g10-statistics-4';
const classId = params.get('classId') || 'class-1';

const encClass = encodeURIComponent(classId);
const encQuiz = encodeURIComponent(quizId);

document.getElementById('back-link').href = `/quiz_library.html?classId=${encClass}`;
document.getElementById('start-session-link').href =
  `/session_monitor.html?quizId=${encQuiz}&classId=${encClass}&from=predict`;
