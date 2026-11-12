const { v4: uuidv4 } = require('uuid');
const { SKILLS, readJson, writeJson } = require('./dataStore');
const { cleanText, normalizeDemandVector } = require('./quizService');

function makeSafeSessionId(quiz) {
  const source = String(quiz?.id || quiz?.name || 'quiz');
  const slug = source
    .toLowerCase()
    .replace(/[^a-z0-9_-]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .slice(0, 48) || 'quiz';
  const stamp = Date.now().toString(36);
  const tail = uuidv4().slice(0, 6);
  return `sess_${slug}_${stamp}_${tail}`;
}

function shuffleArray(items) {
  const arr = [...items];
  for (let i = arr.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [arr[i], arr[j]] = [arr[j], arr[i]];
  }
  return arr;
}

function sanitizeQuestionForStudent(q, difficulty) {
  return {
    type: 'multiple-choice',
    question: cleanText(q.question, 2000),
    image:
      typeof q.image === 'string' &&
      /^data:image\/(png|jpeg|gif|webp);base64,/i.test(q.image)
        ? q.image
        : null,
    timeLimit: Math.max(0, Number(q.timeLimit) || 0),
    options: q.options && typeof q.options === 'object' ? { ...q.options } : {},
    cognitiveDemand: normalizeDemandVector(q.cognitiveDemand, difficulty)
  };
}

function sanitizeQuizForStudent(quiz) {
  const difficulty = quiz?.difficulty || 'Medium';
  return {
    id: quiz.id,
    sessionId: quiz.sessionId || null,
    classId: quiz.classId || null,
    name: quiz.name,
    description: quiz.description || '',
    category: quiz.category || 'Mathematics',
    difficulty,
    totalTimeLimit: Math.max(0, Number(quiz.totalTimeLimit) || 0),
    startedAt: quiz.startedAt || null,
    questions: (quiz.questions || []).map((q) => sanitizeQuestionForStudent(q, difficulty))
  };
}

function prepareStudentQuiz(fullQuiz) {
  const questionsList = Array.isArray(fullQuiz?.questions) ? fullQuiz.questions : [];
  const rand = fullQuiz?.randomization || {};
  const shuffleQuestions = Boolean(rand.shuffleQuestions);
  const shuffleOptions = Boolean(rand.shuffleOptions);
  const useQuestionPool = Boolean(rand.useQuestionPool);
  const poolSize = Math.max(0, Number(rand.poolSize) || 0);

  let indexed = questionsList.map((question, originalIndex) => ({ question, originalIndex }));

  if (useQuestionPool && poolSize > 0 && poolSize < indexed.length) {
    indexed = shuffleArray(indexed).slice(0, poolSize);
  }

  if (shuffleQuestions) {
    indexed = shuffleArray(indexed);
  }

  const questionMapping = indexed.map((item) => item.originalIndex);
  const optionMappings = [];

  const randomizedQuestions = indexed.map((item, qIdx) => {
    const q = item.question;

    if (shuffleOptions && q.options && typeof q.options === 'object') {
      const origKeys = Object.keys(q.options);
      const shuffledKeys = shuffleArray(origKeys);
      const newOptions = {};
      const optionMap = {};

      shuffledKeys.forEach((origKey, newIdx) => {
        const displayKey = String.fromCharCode(65 + newIdx);
        newOptions[displayKey] = q.options[origKey];
        optionMap[displayKey] = origKey;
      });

      optionMappings[qIdx] = optionMap;
      return { ...q, options: newOptions };
    }

    optionMappings[qIdx] = null;
    return { ...q };
  });

  const hasMapping =
    shuffleQuestions ||
    shuffleOptions ||
    (useQuestionPool && poolSize > 0 && poolSize < questionsList.length);

  const sanitizedQuiz = sanitizeQuizForStudent({
    ...fullQuiz,
    questions: randomizedQuestions
  });

  return {
    quiz: sanitizedQuiz,
    mapping: hasMapping ? { questionMapping, optionMappings } : null
  };
}

function reverseMapAnswers(answers, fullQuiz, mapping) {
  const totalQuestions = Array.isArray(fullQuiz?.questions) ? fullQuiz.questions.length : 0;
  const studentAnswers = Array.isArray(answers) ? answers : [];

  if (!mapping || !Array.isArray(mapping.questionMapping)) {
    return Array.from({ length: totalQuestions }, (_, idx) =>
      studentAnswers[idx] !== undefined ? studentAnswers[idx] : null
    );
  }

  const { questionMapping, optionMappings = [] } = mapping;
  const mappedAnswers = new Array(totalQuestions).fill(null);

  questionMapping.forEach((originalIndex, displayIndex) => {
    if (originalIndex < 0 || originalIndex >= totalQuestions) return;
    const rawAnswer = studentAnswers[displayIndex] !== undefined ? studentAnswers[displayIndex] : null;
    const optionMap = optionMappings[displayIndex];

    if (optionMap && typeof rawAnswer === 'string' && optionMap[rawAnswer]) {
      mappedAnswers[originalIndex] = optionMap[rawAnswer];
    } else {
      mappedAnswers[originalIndex] = rawAnswer;
    }
  });

  return mappedAnswers;
}

function gradeSubmission({ fullQuiz, mappedAnswers, mapping }) {
  const questions = Array.isArray(fullQuiz?.questions) ? fullQuiz.questions : [];
  const difficulty = fullQuiz?.difficulty || 'Medium';
  const askedIndices =
    mapping && Array.isArray(mapping.questionMapping) ? new Set(mapping.questionMapping) : null;

  let score = 0;
  let totalGradeable = 0;
  let totalAsked = 0;
  const detailedResults = [];

  questions.forEach((q, idx) => {
    const cognitiveDemand = normalizeDemandVector(q.cognitiveDemand, difficulty);

    if (askedIndices && !askedIndices.has(idx)) {
      detailedResults.push({
        questionIndex: idx,
        questionType: 'multiple-choice',
        wasAsked: false,
        skippedFromPool: true,
        studentAnswer: null,
        isCorrect: false,
        needsManualGrading: false,
        manualScore: null,
        cognitiveDemand
      });
      return;
    }

    totalAsked += 1;
    totalGradeable += 1;
    const studentAnswer = mappedAnswers[idx] !== undefined ? mappedAnswers[idx] : null;
    const isCorrect = typeof studentAnswer === 'string' && studentAnswer === q.correct;
    if (isCorrect) score += 1;

    detailedResults.push({
      questionIndex: idx,
      questionType: 'multiple-choice',
      wasAsked: true,
      skippedFromPool: false,
      studentAnswer,
      isCorrect,
      needsManualGrading: false,
      manualScore: isCorrect ? 1 : 0,
      cognitiveDemand
    });
  });

  const percentage = totalGradeable > 0 ? Math.round((score / totalGradeable) * 1000) / 10 : 0;

  return {
    score,
    totalQuestions: totalAsked,
    totalGradeable,
    pendingManualGrading: 0,
    percentage,
    detailedResults
  };
}

function countAnsweredQuestions(answers, questions) {
  if (!Array.isArray(answers) || !Array.isArray(questions)) return 0;
  let answered = 0;

  questions.forEach((_, idx) => {
    const val = answers[idx];
    if (typeof val === 'string' && val.trim() !== '') {
      answered += 1;
    }
  });

  return answered;
}

function normalizeStudentCodeKey(rawCode) {
  return cleanText(rawCode, 24).replace(/^#/, '').trim().toUpperCase();
}

function formatStudentCode(rawCode) {
  const key = normalizeStudentCodeKey(rawCode);
  return key ? `#${key}` : '';
}

function matchRosterStudentByCode(students, classId, studentCode) {
  const roster = Array.isArray(students)
    ? students.filter((s) => !classId || s.classId === classId)
    : [];

  const codeKey = normalizeStudentCodeKey(studentCode);
  if (!codeKey) return null;

  return roster.find((s) => normalizeStudentCodeKey(s.code) === codeKey) || null;
}

function createEmptyRuntimeState() {
  return {
    sessionId: null,
    status: 'idle',
    classId: null,
    quizId: null,
    quizName: '',
    pin: '',
    selectedIp: '',
    joinUrl: '',
    openedAt: null,
    startedAt: null,
    endedAt: null,
    participants: [],
    studentQuizMappings: {}
  };
}

function loadRuntimeState(runtimeStatePath) {
  const saved = readJson(runtimeStatePath, null);
  const empty = createEmptyRuntimeState();
  if (!saved || typeof saved !== 'object') return empty;
  return {
    ...empty,
    ...saved,
    participants: Array.isArray(saved.participants) ? saved.participants : [],
    studentQuizMappings:
      saved.studentQuizMappings && typeof saved.studentQuizMappings === 'object'
        ? saved.studentQuizMappings
        : {}
  };
}

function saveRuntimeState(runtimeStatePath, state) {
  writeJson(runtimeStatePath, state);
}

function getEffectivePoolCount(quiz) {
  const count = Array.isArray(quiz?.questions) ? quiz.questions.length : 0;
  const rand = quiz?.randomization;
  if (rand?.useQuestionPool && rand.poolSize > 0 && rand.poolSize < count) {
    return rand.poolSize;
  }
  return count;
}

function formatShortMonthDay(date = new Date()) {
  const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  return `${months[date.getMonth()]} ${date.getDate()}`;
}

function listClassSessions(sessionsDir, classId = '') {
  if (!sessionsDir) return [];
  const fs = require('fs');
  const path = require('path');
  if (!fs.existsSync(sessionsDir)) return [];

  return fs
    .readdirSync(sessionsDir)
    .filter((f) => f.endsWith('.json'))
    .map((file) => {
      const data = readJson(path.join(sessionsDir, file));
      if (!data) return null;
      if (classId && data.classId && data.classId !== classId) return null;
      const results = Array.isArray(data.results) ? data.results : [];
      const avg =
        results.length > 0
          ? Math.round(
              results.reduce((sum, r) => sum + (Number(r.percentage) || 0), 0) / results.length
            )
          : 0;
      return {
        sessionId: data.sessionId,
        classId: data.classId || null,
        quizId: data.quizId || null,
        quizName: data.name || 'Untitled Quiz',
        status: data.status || 'ended',
        sessionDate: data.sessionDate || data.startedAt,
        startedAt: data.startedAt || data.sessionDate || null,
        endedAt: data.endedAt || null,
        participantCount: results.length,
        averagePercent: avg
      };
    })
    .filter(Boolean)
    .sort((a, b) => new Date(b.sessionDate || 0) - new Date(a.sessionDate || 0));
}

module.exports = {
  SKILLS,
  makeSafeSessionId,
  shuffleArray,
  sanitizeQuestionForStudent,
  sanitizeQuizForStudent,
  prepareStudentQuiz,
  reverseMapAnswers,
  gradeSubmission,
  countAnsweredQuestions,
  normalizeStudentCodeKey,
  formatStudentCode,
  matchRosterStudentByCode,
  createEmptyRuntimeState,
  loadRuntimeState,
  saveRuntimeState,
  getEffectivePoolCount,
  formatShortMonthDay,
  listClassSessions
};
