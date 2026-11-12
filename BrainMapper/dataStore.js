const fs = require('fs');
const path = require('path');

const SKILLS = [
  'Attention',
  'Working Memory',
  'Logical Reasoning',
  'Language Processing',
  'Critical Thinking',
  'Metacognition'
];

const FIRST_NAMES = [
  'Nethmi', 'Kasun', 'Sanduni', 'Ravindu', 'Thimali', 'Chamath',
  'Ishara', 'Dineth', 'Oshadi', 'Pasindu', 'Nimasha', 'Kavindu',
  'Hiruni', 'Shehan', 'Malsha', 'Supun', 'Amaya', 'Lahiru',
  'Rashmi', 'Gihan', 'Tharushi', 'Sahan', 'Ayodya', 'Chathura',
  'Nadeesha', 'Janith'
];

const LAST_NAMES = [
  'Fernando', 'Perera', 'Jayasinghe', 'Bandara', 'Wickramasinghe',
  'Gunasekara', 'Ratnayake', 'Herath', 'Dissanayake', 'Senanayake',
  'Karunaratne', 'Rajapaksha', 'Amarasinghe'
];

function readJson(filePath, fallback = null) {
  try {
    return JSON.parse(fs.readFileSync(filePath, 'utf8'));
  } catch (error) {
    if (error.code !== 'ENOENT') {
      console.error(`Failed to read ${filePath}:`, error.message);
    }
    return fallback;
  }
}

function writeJson(filePath, value) {
  fs.mkdirSync(path.dirname(filePath), { recursive: true });
  const tempPath = `${filePath}.tmp`;
  fs.writeFileSync(tempPath, JSON.stringify(value, null, 2), 'utf8');
  fs.renameSync(tempPath, filePath);
}

function getInitials(name) {
  const parts = String(name || '').trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return 'ST';
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return `${parts[0][0]}${parts[parts.length - 1][0]}`.toUpperCase();
}

function buildCognitiveProfile(dominantSkill, baseScore, seedIndex = 0) {
  const profile = {};
  SKILLS.forEach((skill, idx) => {
    if (skill === dominantSkill) {
      profile[skill] = Math.min(98, baseScore + 6);
    } else {
      const variance = ((seedIndex * 5 + idx * 9) % 24) - 14;
      profile[skill] = Math.max(40, Math.min(94, baseScore + variance));
    }
  });
  return profile;
}

function buildCohortStudents(classId, featured, totalCount, seedOffset = 0) {
  const students = [...featured];
  for (let i = featured.length; i < totalCount; i++) {
    const first = FIRST_NAMES[(i + seedOffset) % FIRST_NAMES.length];
    const last = LAST_NAMES[(i * 3 + seedOffset) % LAST_NAMES.length];
    const name = `${first} ${last}`;
    const num = 1001 + i + (seedOffset * 100);
    const skill = SKILLS[(i + seedOffset) % SKILLS.length];
    const score = 55 + ((i * 7 + seedOffset * 11) % 41);
    students.push({
      id: `st-${classId}-${num}`,
      code: `#ST-${num}`,
      classId,
      name,
      initials: getInitials(name),
      dominantSkill: skill,
      overallScore: score,
      cognitiveProfile: buildCognitiveProfile(skill, score, i + seedOffset)
    });
  }
  return students;
}

function createSampleQuizzes() {
  return [
    {
      id: 'quiz-g10-algebra-1',
      classId: 'class-1',
      name: 'Grade 10 Algebra: Term 1 Test',
      description: 'Algebraic expressions, factorization, and linear equations.',
      category: 'Mathematics',
      difficulty: 'Easy',
      totalTimeLimit: 1800,
      randomization: {
        shuffleQuestions: false,
        shuffleOptions: false,
        useQuestionPool: false,
        poolSize: 0
      },
      isTemplate: false,
      isArchived: false,
      isNew: false,
      createdAt: '2026-10-02T09:00:00.000Z',
      updatedAt: '2026-10-14T09:00:00.000Z',
      questions: [
        {
          type: 'multiple-choice',
          question: 'Factorize completely: x² - 9',
          options: { A: '(x - 3)(x + 3)', B: '(x - 9)(x + 1)', C: '(x - 3)²', D: 'x(x - 9)' },
          correct: 'A',
          explanation: 'Difference of two squares: a² - b² = (a - b)(a + b).',
          timeLimit: 0,
          cognitiveDemand: { Attention: 1, 'Working Memory': 1, 'Logical Reasoning': 2, 'Language Processing': 1, 'Critical Thinking': 1, Metacognition: 1 }
        },
        {
          type: 'multiple-choice',
          question: 'Solve for x: 3x - 7 = 14',
          options: { A: '5', B: '7', C: '9', D: '21' },
          correct: 'B',
          explanation: 'Add 7 to both sides (3x = 21), then divide by 3 (x = 7).',
          timeLimit: 0,
          cognitiveDemand: { Attention: 1, 'Working Memory': 2, 'Logical Reasoning': 2, 'Language Processing': 1, 'Critical Thinking': 1, Metacognition: 1 }
        }
      ]
    },
    {
      id: 'quiz-g10-geometry-2',
      classId: 'class-1',
      name: 'Grade 10 Geometry & Trigonometry: Term 2 Test',
      description: 'Circle theorems, Pythagoras, and trigonometric ratios.',
      category: 'Mathematics',
      difficulty: 'Medium',
      totalTimeLimit: 2700,
      randomization: {
        shuffleQuestions: true,
        shuffleOptions: false,
        useQuestionPool: false,
        poolSize: 0
      },
      isTemplate: false,
      isArchived: false,
      isNew: false,
      createdAt: '2026-10-05T09:00:00.000Z',
      updatedAt: '2026-10-11T09:00:00.000Z',
      questions: [
        {
          type: 'multiple-choice',
          question: 'In a right triangle with legs 6 cm and 8 cm, what is the hypotenuse?',
          options: { A: '10 cm', B: '12 cm', C: '14 cm', D: '48 cm' },
          correct: 'A',
          explanation: '√(6² + 8²) = √(36 + 64) = √100 = 10 cm.',
          timeLimit: 0,
          cognitiveDemand: { Attention: 2, 'Working Memory': 2, 'Logical Reasoning': 2, 'Language Processing': 1, 'Critical Thinking': 2, Metacognition: 1 }
        }
      ]
    },
    {
      id: 'quiz-g10-functions-3',
      classId: 'class-1',
      name: 'Grade 10 Quadratic Functions & Graphs: Term 3 Test',
      description: 'Parabolas, vertex form, roots, and discriminant analysis.',
      category: 'Mathematics',
      difficulty: 'Hard',
      totalTimeLimit: 3600,
      randomization: {
        shuffleQuestions: true,
        shuffleOptions: true,
        useQuestionPool: false,
        poolSize: 0
      },
      isTemplate: false,
      isArchived: false,
      isNew: false,
      createdAt: '2026-09-20T09:00:00.000Z',
      updatedAt: '2026-09-28T09:00:00.000Z',
      questions: [
        {
          type: 'multiple-choice',
          question: 'For f(x) = 2x² - 8x + 6, what is the x-coordinate of the vertex?',
          options: { A: '1', B: '2', C: '4', D: '-2' },
          correct: 'B',
          explanation: 'Vertex x = -b / (2a) = 8 / 4 = 2.',
          timeLimit: 0,
          cognitiveDemand: { Attention: 2, 'Working Memory': 3, 'Logical Reasoning': 3, 'Language Processing': 2, 'Critical Thinking': 2, Metacognition: 2 }
        }
      ]
    },
    {
      id: 'quiz-g10-statistics-4',
      classId: 'class-1',
      name: 'Grade 10 Statistics & Probability: Quiz 4',
      description: 'Descriptive statistics, variance, standard deviation, and probability distributions.',
      category: 'Mathematics',
      difficulty: 'Medium',
      totalTimeLimit: 2400,
      randomization: {
        shuffleQuestions: true,
        shuffleOptions: true,
        useQuestionPool: false,
        poolSize: 0
      },
      isTemplate: false,
      isArchived: false,
      isNew: true,
      createdAt: '2026-10-15T10:00:00.000Z',
      updatedAt: '2026-10-15T10:00:00.000Z',
      questions: [
        {
          type: 'multiple-choice',
          question: 'Given data set [4, 8, 6, 5, 3, 2, 8, 9, 2, 5], what is the sample median?',
          options: { A: '4.5', B: '5.0', C: '5.2', D: '6.0' },
          correct: 'B',
          explanation: 'Sorted: 2, 2, 3, 4, 5, 5, 6, 8, 8, 9 — average of 5th and 6th items is 5.0.',
          timeLimit: 0,
          cognitiveDemand: { Attention: 2, 'Working Memory': 3, 'Logical Reasoning': 3, 'Language Processing': 1, 'Critical Thinking': 2, Metacognition: 2 }
        },
        {
          type: 'multiple-choice',
          question: 'Why does standard deviation increase when an extreme outlier is added to a symmetric dataset?',
          options: {
            A: 'The sample median doubles regardless of sample size',
            B: 'Squared deviations from the mean amplify outliers substantially',
            C: 'Interquartile range automatically becomes zero',
            D: 'Extreme values are counted twice in frequency tables'
          },
          correct: 'B',
          explanation: 'Standard deviation averages squared deviations from the mean, so extreme values magnify variance and SD.',
          timeLimit: 0,
          cognitiveDemand: { Attention: 2, 'Working Memory': 3, 'Logical Reasoning': 3, 'Language Processing': 1, 'Critical Thinking': 2, Metacognition: 2 }
        }
      ]
    },
    {
      id: 'quiz-g11-calculus-1',
      classId: 'class-2',
      name: 'Grade 11 Calculus & Probability: Term 1 Test',
      description: 'Differentiation basics, sets, and probability problems.',
      category: 'Mathematics',
      difficulty: 'Hard',
      totalTimeLimit: 3600,
      randomization: {
        shuffleQuestions: false,
        shuffleOptions: false,
        useQuestionPool: false,
        poolSize: 0
      },
      isTemplate: false,
      isArchived: false,
      isNew: false,
      createdAt: '2026-10-08T09:00:00.000Z',
      updatedAt: '2026-10-11T09:00:00.000Z',
      questions: [
        {
          type: 'multiple-choice',
          question: 'What is the derivative of f(x) = 3x² + 5x - 2?',
          options: { A: '6x + 5', B: '3x + 5', C: '6x - 2', D: 'x³ + 5' },
          correct: 'A',
          explanation: 'Apply the power rule term by term.',
          timeLimit: 0,
          cognitiveDemand: { Attention: 2, 'Working Memory': 2, 'Logical Reasoning': 3, 'Language Processing': 1, 'Critical Thinking': 2, Metacognition: 2 }
        }
      ]
    },
    {
      id: 'quiz-g11-vectors-2',
      classId: 'class-2',
      name: 'Grade 11 Vectors & Matrices: Quiz 2',
      description: 'Dot products, vector projection, and 2×2 matrix determinants.',
      category: 'Mathematics',
      difficulty: 'Medium',
      totalTimeLimit: 2400,
      randomization: {
        shuffleQuestions: false,
        shuffleOptions: false,
        useQuestionPool: false,
        poolSize: 0
      },
      isTemplate: false,
      isArchived: false,
      isNew: false,
      createdAt: '2026-10-04T09:00:00.000Z',
      updatedAt: '2026-10-09T09:00:00.000Z',
      questions: [
        {
          type: 'multiple-choice',
          question: 'Find the determinant of matrix [[4, 2], [3, 5]].',
          options: { A: '14', B: '26', C: '10', D: '-14' },
          correct: 'A',
          explanation: '(4 × 5) - (2 × 3) = 20 - 6 = 14.',
          timeLimit: 0,
          cognitiveDemand: { Attention: 2, 'Working Memory': 2, 'Logical Reasoning': 2, 'Language Processing': 1, 'Critical Thinking': 2, Metacognition: 1 }
        }
      ]
    }
  ];
}

function ensureInitialSeed(dataDir) {
  const classesPath = path.join(dataDir, 'classes.json');
  const studentsPath = path.join(dataDir, 'students.json');
  const quizzesDir = path.join(dataDir, 'quizzes');
  const sessionsDir = path.join(dataDir, 'sessions');

  fs.mkdirSync(quizzesDir, { recursive: true });
  fs.mkdirSync(sessionsDir, { recursive: true });

  if (!fs.existsSync(classesPath)) {
    const defaultClasses = [
      {
        id: 'class-1',
        name: 'Class 1',
        subject: 'Grade 10 Mathematics',
        status: 'Active',
        accentColor: 'indigo',
        quizCount: 4,
        lastSessionLabel: 'Oct 14',
        createdAt: '2026-10-01T08:00:00.000Z'
      },
      {
        id: 'class-2',
        name: 'Class 2',
        subject: 'Grade 11 Mathematics',
        status: 'Active',
        accentColor: 'blue',
        quizCount: 2,
        lastSessionLabel: 'Oct 11',
        createdAt: '2026-10-02T08:00:00.000Z'
      }
    ];
    writeJson(classesPath, defaultClasses);
  }

  if (!fs.existsSync(studentsPath)) {
    const class1Featured = [
      {
        id: 'st-class-1-1001',
        code: '#ST-1001',
        classId: 'class-1',
        name: 'Pramudi Biyonika',
        initials: 'PB',
        dominantSkill: 'Logical Reasoning',
        overallScore: 88,
        cognitiveProfile: {
          Attention: 78,
          'Working Memory': 66,
          'Logical Reasoning': 90,
          'Language Processing': 82,
          'Critical Thinking': 84,
          Metacognition: 86
        }
      },
      {
        id: 'st-class-1-1002',
        code: '#ST-1002',
        classId: 'class-1',
        name: 'Waruna Silva',
        initials: 'WS',
        dominantSkill: 'Logical Reasoning',
        overallScore: 94,
        cognitiveProfile: {
          Attention: 86,
          'Working Memory': 64,
          'Logical Reasoning': 92,
          'Language Processing': 84,
          'Critical Thinking': 88,
          Metacognition: 82
        }
      },
      {
        id: 'st-class-1-1003',
        code: '#ST-1003',
        classId: 'class-1',
        name: 'Dilshan Samarakoone',
        initials: 'DS',
        dominantSkill: 'Attention',
        overallScore: 71,
        cognitiveProfile: {
          Attention: 72,
          'Working Memory': 50,
          'Logical Reasoning': 49,
          'Language Processing': 62,
          'Critical Thinking': 51,
          Metacognition: 58
        }
      },
      {
        id: 'st-class-1-1004',
        code: '#ST-1004',
        classId: 'class-1',
        name: 'Tharindu Kothalawala',
        initials: 'TK',
        dominantSkill: 'Metacognition',
        overallScore: 58,
        cognitiveProfile: {
          Attention: 64,
          'Working Memory': 72,
          'Logical Reasoning': 74,
          'Language Processing': 54,
          'Critical Thinking': 68,
          Metacognition: 76
        }
      },
      {
        id: 'st-class-1-1005',
        code: '#ST-1005',
        classId: 'class-1',
        name: 'Anuki Perera',
        initials: 'AP',
        dominantSkill: 'Critical Thinking',
        overallScore: 82,
        cognitiveProfile: {
          Attention: 80,
          'Working Memory': 74,
          'Logical Reasoning': 81,
          'Language Processing': 78,
          'Critical Thinking': 88,
          Metacognition: 80
        }
      },
      {
        id: 'st-class-1-1006',
        code: '#ST-1006',
        classId: 'class-1',
        name: 'Kaveen Jayasuriya',
        initials: 'KJ',
        dominantSkill: 'Language Processing',
        overallScore: 76,
        cognitiveProfile: {
          Attention: 74,
          'Working Memory': 68,
          'Logical Reasoning': 72,
          'Language Processing': 84,
          'Critical Thinking': 75,
          Metacognition: 73
        }
      }
    ];

    const class1Students = buildCohortStudents('class-1', class1Featured, 32, 0);
    const class2Students = buildCohortStudents('class-2', [], 28, 2);
    writeJson(studentsPath, [...class1Students, ...class2Students]);
  } else {
    // Backfill cognitiveProfile for any pre-Phase-2 students on disk
    const existing = readJson(studentsPath, []);
    let changed = false;
    const updated = existing.map((s, idx) => {
      if (!s.cognitiveProfile) {
        changed = true;
        return {
          ...s,
          cognitiveProfile: buildCognitiveProfile(s.dominantSkill, s.overallScore || 75, idx)
        };
      }
      return s;
    });
    if (changed) writeJson(studentsPath, updated);
  }

  const existingQuizFiles = fs.readdirSync(quizzesDir).filter((f) => f.endsWith('.json'));
  if (existingQuizFiles.length === 0) {
    for (const quiz of createSampleQuizzes()) {
      writeJson(path.join(quizzesDir, `${quiz.id}.json`), quiz);
    }
  }
}

module.exports = {
  SKILLS,
  readJson,
  writeJson,
  getInitials,
  buildCognitiveProfile,
  ensureInitialSeed
};
