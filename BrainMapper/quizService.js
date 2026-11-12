const fs = require('fs');
const path = require('path');
const { SKILLS, readJson } = require('./dataStore');

const VALID_TYPES = new Set(['multiple-choice']);

const DIFFICULTY_PENALTY = {
  Easy: -4,
  Medium: 0,
  Hard: 6
};

function cleanText(value, maxLength) {
  return typeof value === 'string' ? value.trim().slice(0, maxLength) : '';
}

function normalizeDemandVector(rawDemand, difficulty = 'Medium') {
  const base = difficulty === 'Hard' ? 2 : difficulty === 'Easy' ? 1 : 2;
  const vector = {};
  for (const skill of SKILLS) {
    const num = Number(rawDemand?.[skill]);
    vector[skill] = Number.isFinite(num)
      ? Math.max(0, Math.min(3, Math.round(num)))
      : base;
  }
  return vector;
}

function validateQuizPayload(payload) {
  if (!payload || typeof payload !== 'object') return 'Quiz data is required';
  if (!cleanText(payload.name, 150)) return 'Quiz title is required';
  if (!Array.isArray(payload.questions) || payload.questions.length === 0) {
    return 'At least one question is required';
  }
  if (payload.questions.length > 500) {
    return 'A quiz cannot contain more than 500 questions';
  }

  for (let i = 0; i < payload.questions.length; i++) {
    const q = payload.questions[i];
    const num = i + 1;
    if (!q || typeof q !== 'object' || !cleanText(q.question, 2000)) {
      return `Question ${num} must contain question text`;
    }
    const qType = q.type || 'multiple-choice';
    if (!VALID_TYPES.has(qType)) {
      return `Question ${num} uses unsupported type "${qType}". Only Multiple Choice (MCQ) questions are supported.`;
    }

    const opts = q.options && typeof q.options === 'object' ? q.options : {};
    for (const key of ['A', 'B', 'C', 'D']) {
      if (!cleanText(opts[key], 500)) {
        return `Question ${num} is missing option ${key}`;
      }
    }
    if (!['A', 'B', 'C', 'D'].includes(q.correct)) {
      return `Question ${num} requires a valid correct option (A-D)`;
    }
  }

  if (payload.randomization?.useQuestionPool) {
    const poolSize = Number(payload.randomization.poolSize) || 0;
    if (poolSize <= 0 || poolSize >= payload.questions.length) {
      return 'Question pool size must be between 1 and total questions - 1';
    }
  }

  return null;
}

function getDemandBand(score) {
  if (score >= 2.5) return 'High';
  if (score >= 1.5) return 'Moderate';
  if (score >= 0.5) return 'Low';
  return 'Not Required';
}

function computeQuizCognitiveDemand(quiz) {
  const questions = Array.isArray(quiz?.questions) ? quiz.questions : [];
  const totals = Object.fromEntries(SKILLS.map((s) => [s, 0]));

  for (const q of questions) {
    const vec = normalizeDemandVector(q.cognitiveDemand, quiz.difficulty);
    for (const skill of SKILLS) {
      totals[skill] += vec[skill];
    }
  }

  const count = Math.max(1, questions.length);
  return SKILLS.map((skill, idx) => {
    const avg = Math.round((totals[skill] / count) * 10) / 10;
    return {
      order: idx + 1,
      skill,
      score: avg,
      band: getDemandBand(avg)
    };
  });
}

function getPredictionStatus(quiz, students, classInfo) {
  return {
    status: 'work_in_progress',
    workInProgress: true,
    message:
      'Pre-quiz score prediction is still a work in progress. Real predictions will appear once the LLM cognitive demand pipeline and trained MCQ Knowledge Tracing model are connected.',
    quiz: {
      id: quiz.id,
      name: quiz.name,
      category: quiz.category || 'Mathematics',
      difficulty: quiz.difficulty || 'Medium',
      questionCount: Array.isArray(quiz.questions) ? quiz.questions.length : 0,
      totalTimeLimit: quiz.totalTimeLimit || 0
    },
    classInfo: classInfo
      ? { id: classInfo.id, name: classInfo.name, subject: classInfo.subject }
      : { id: 'all', name: 'All Classes', subject: 'General Cohort' },
    summary: {
      studentCount: Array.isArray(students) ? students.length : 0
    }
  };
}

function listAllQuizzes(quizzesDir) {
  if (!fs.existsSync(quizzesDir)) return [];
  const files = fs.readdirSync(quizzesDir).filter((f) => f.endsWith('.json'));
  return files
    .map((file) => {
      const data = readJson(path.join(quizzesDir, file));
      if (!data) return null;
      if (!data.id) data.id = path.basename(file, '.json');
      return data;
    })
    .filter(Boolean)
    .sort((a, b) => new Date(b.updatedAt || b.createdAt || 0) - new Date(a.updatedAt || a.createdAt || 0));
}

function listQuestionBank(quizzesDir, classId = '') {
  const quizzes = listAllQuizzes(quizzesDir).filter(
    (q) => !q.isArchived && (!classId || q.classId === classId)
  );
  const bankMap = new Map();

  for (const quiz of quizzes) {
    for (const q of quiz.questions || []) {
      const key = String(q.question || '').toLowerCase().trim();
      if (!key) continue;
      if (!bankMap.has(key)) {
        bankMap.set(key, {
          ...q,
          category: quiz.category || 'Other',
          difficulty: quiz.difficulty || 'Medium',
          quizCount: 1
        });
      } else {
        bankMap.get(key).quizCount += 1;
      }
    }
  }

  return Array.from(bankMap.values());
}

module.exports = {
  cleanText,
  normalizeDemandVector,
  validateQuizPayload,
  computeQuizCognitiveDemand,
  getPredictionStatus,
  listAllQuizzes,
  listQuestionBank
};
