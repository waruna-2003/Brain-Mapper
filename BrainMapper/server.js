const express = require('express');
const fs = require('fs');
const os = require('os');
const path = require('path');
const QRCode = require('qrcode');
const { v4: uuidv4 } = require('uuid');
const {
  SKILLS,
  readJson,
  writeJson,
  getInitials,
  buildCognitiveProfile,
  ensureInitialSeed
} = require('./dataStore');
const {
  cleanText,
  normalizeDemandVector,
  validateQuizPayload,
  getPredictionStatus,
  listAllQuizzes,
  listQuestionBank
} = require('./quizService');
const {
  makeSafeSessionId,
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
} = require('./sessionService');

const ACCENT_PALETTE = ['indigo', 'blue', 'emerald', 'violet'];
const DIFFICULTIES = new Set(['Easy', 'Medium', 'Hard']);

function isSafeId(value) {
  return typeof value === 'string' && /^[A-Za-z0-9_-]{1,200}$/.test(value);
}

function getQuizPath(quizzesDir, quizId) {
  return isSafeId(quizId) ? path.join(quizzesDir, `${quizId}.json`) : null;
}

function csvCell(value) {
  let text = value == null ? '' : String(value);
  if (/^[=+\-@]/.test(text)) text = `'${text}`;
  return `"${text.replace(/"/g, '""')}"`;
}

function getLocalIPs() {
  const nets = os.networkInterfaces();
  const ips = [];
  for (const name of Object.keys(nets)) {
    const lower = name.toLowerCase();
    if (
      lower.includes('vmware') ||
      lower.includes('virtual') ||
      lower.includes('hyper') ||
      lower.includes('vbox') ||
      lower.includes('loopback')
    ) {
      continue;
    }
    for (const net of nets[name] || []) {
      if (net.family === 'IPv4' && !net.internal) {
        ips.push({ name, address: net.address });
      }
    }
  }
  return ips;
}

function isHostAddress(rawAddress, localIps = getLocalIPs()) {
  if (!rawAddress) return true;
  const normalized = String(rawAddress).replace(/^::ffff:/, '').trim();
  if (!normalized || normalized === '127.0.0.1' || normalized === '::1') {
    return true;
  }
  return localIps.some((ip) => ip.address === normalized);
}

const EDUCATOR_PAGES = new Set([
  '/',
  '/index.html',
  '/class_dashboard.html',
  '/quiz_library.html',
  '/create_quiz.html',
  '/predicted_results.html',
  '/session_monitor.html',
  '/analyze.html'
]);

function sanitizeQuestions(questions, difficulty) {
  return questions.map((q) => ({
    type: 'multiple-choice',
    question: cleanText(q.question, 2000),
    explanation: cleanText(q.explanation, 2000),
    image: typeof q.image === 'string' && /^data:image\/(png|jpeg|gif|webp);base64,/i.test(q.image)
      ? q.image
      : null,
    timeLimit: Math.max(0, Number(q.timeLimit) || 0),
    options: {
      A: cleanText(q.options?.A, 500),
      B: cleanText(q.options?.B, 500),
      C: cleanText(q.options?.C, 500),
      D: cleanText(q.options?.D, 500)
    },
    correct: q.correct,
    cognitiveDemand: normalizeDemandVector(q.cognitiveDemand, difficulty)
  }));
}

function createApp(customDataDir) {
  const dataDir = path.resolve(
    customDataDir || process.env.BRAINMAPPER_DATA_DIR || path.join(__dirname, 'data')
  );
  ensureInitialSeed(dataDir);

  const classesPath = path.join(dataDir, 'classes.json');
  const studentsPath = path.join(dataDir, 'students.json');
  const quizzesDir = path.join(dataDir, 'quizzes');
  const sessionsDir = path.join(dataDir, 'sessions');
  const sessionRefPath = path.join(dataDir, 'currentSession.json');
  const runtimeStatePath = path.join(dataDir, 'runtimeState.json');

  let runtimeState = loadRuntimeState(runtimeStatePath);
  const monitorClients = new Set();
  const examClients = new Set();

  function requireHostAccess(req, res, next) {
    if (isHostAddress(req.socket?.remoteAddress, getLocalIPs())) {
      return next();
    }
    return res.status(403).json({
      message: 'Educator access is restricted to the host machine. Students should use /exam.'
    });
  }

  function buildMonitorSnapshot() {
    const participants = runtimeState.participants || [];
    const submitted = participants.filter((p) => p.status === 'submitted');
    const avgPct =
      submitted.length > 0
        ? Math.round(
            submitted.reduce((sum, p) => sum + (Number(p.percentage) || 0), 0) / submitted.length
          )
        : null;

    let quizSummary = null;
    if (runtimeState.quizId) {
      const qPath = getQuizPath(quizzesDir, runtimeState.quizId);
      const q = qPath ? readJson(qPath) : null;
      if (q) {
        quizSummary = {
          id: q.id,
          name: q.name,
          category: q.category || 'Mathematics',
          difficulty: q.difficulty || 'Medium',
          questionCount: Array.isArray(q.questions) ? q.questions.length : 0,
          effectiveQuestionCount: getEffectivePoolCount(q),
          totalTimeLimit: Math.max(0, Number(q.totalTimeLimit) || 0),
          randomization: q.randomization || {}
        };
      }
    }

    return {
      status: runtimeState.status,
      sessionId: runtimeState.sessionId,
      classId: runtimeState.classId,
      quizId: runtimeState.quizId,
      quizName: runtimeState.quizName,
      pin: runtimeState.pin || '',
      pinRequired: Boolean(runtimeState.pin),
      selectedIp: runtimeState.selectedIp || '',
      joinUrl: runtimeState.joinUrl || '',
      openedAt: runtimeState.openedAt,
      startedAt: runtimeState.startedAt,
      endedAt: runtimeState.endedAt,
      quizSummary,
      participants,
      stats: {
        totalJoined: participants.length,
        waitingCount: participants.filter((p) => p.status === 'waiting').length,
        inProgressCount: participants.filter((p) => p.status === 'in-progress').length,
        submittedCount: submitted.length,
        averagePercent: avgPct
      }
    };
  }

  function notifyMonitorClients() {
    const payload = `event: session\ndata: ${JSON.stringify(buildMonitorSnapshot())}\n\n`;
    for (const client of monitorClients) {
      try {
        client.write(payload);
      } catch (_) {
        monitorClients.delete(client);
      }
    }
  }

  function notifyExamClients(eventType = 'status') {
    const classes = readJson(classesPath, []);
    const cls = classes.find((c) => c.id === runtimeState.classId);
    const data = {
      type: eventType,
      status: runtimeState.status,
      sessionId: runtimeState.sessionId,
      quizName: runtimeState.quizName,
      className: cls ? `${cls.name} • ${cls.subject}` : '',
      pinRequired: Boolean(runtimeState.pin)
    };
    const payload = `event: status\ndata: ${JSON.stringify(data)}\n\n`;
    for (const client of examClients) {
      try {
        client.write(payload);
      } catch (_) {
        examClients.delete(client);
      }
    }
  }

  const app = express();
  app.use(express.json({ limit: '10mb' }));

  app.use((req, res, next) => {
    if (EDUCATOR_PAGES.has(req.path) && !isHostAddress(req.socket?.remoteAddress, getLocalIPs())) {
      return res.redirect('/exam');
    }
    return next();
  });

  app.get(['/exam', '/exam/'], (req, res) => {
    res.sendFile(path.join(__dirname, 'public', 'exam.html'));
  });

  app.use(express.static(path.join(__dirname, 'public')));
  app.use(
    '/vendor/inter',
    express.static(path.join(__dirname, 'node_modules', '@fontsource', 'inter'))
  );

  app.use(
    [
      '/api/classes',
      '/api/quizzes',
      '/api/question-bank',
      '/api/qrcode',
      '/api/sessions',
      '/api/session/current',
      '/api/session/open-lobby',
      '/api/session/start',
      '/api/session/end',
      '/api/session/reset',
      '/api/session/kick',
      '/api/session/events'
    ],
    requireHostAccess
  );

  app.get('/api/health', (req, res) => {
    res.json({
      ok: true,
      app: 'BrainMapper',
      offline: true,
      port: req.socket?.localPort || PORT,
      localIPs: getLocalIPs()
    });
  });

  // ---- Classes & Roster ----

  app.get('/api/classes', (req, res) => {
    const classes = readJson(classesPath, []);
    const students = readJson(studentsPath, []);
    const quizzes = listAllQuizzes(quizzesDir).filter((q) => !q.isArchived);

    const enriched = classes.map((cls) => ({
      ...cls,
      studentCount: students.filter((s) => s.classId === cls.id).length,
      quizCount: quizzes.filter((q) => q.classId === cls.id).length
    }));
    res.json(enriched);
  });

  app.get('/api/classes/:classId', (req, res) => {
    const { classId } = req.params;
    if (!isSafeId(classId)) return res.status(400).json({ message: 'Invalid class ID' });

    const classes = readJson(classesPath, []);
    const cls = classes.find((c) => c.id === classId);
    if (!cls) return res.status(404).json({ message: 'Class not found' });

    const studentCount = readJson(studentsPath, []).filter((s) => s.classId === classId).length;
    const quizCount = listAllQuizzes(quizzesDir).filter(
      (q) => !q.isArchived && q.classId === classId
    ).length;

    res.json({ ...cls, studentCount, quizCount });
  });

  app.post('/api/classes', (req, res) => {
    const name = cleanText(req.body?.name, 80);
    const subject = cleanText(req.body?.subject, 120);
    const accentColor = ACCENT_PALETTE.includes(req.body?.accentColor)
      ? req.body.accentColor
      : null;

    if (!name) return res.status(400).json({ message: 'Class name is required' });
    if (!subject) return res.status(400).json({ message: 'Subject or grade is required' });

    const classes = readJson(classesPath, []);
    const newClass = {
      id: `class-${uuidv4().slice(0, 8)}`,
      name,
      subject,
      status: 'Active',
      accentColor: accentColor || ACCENT_PALETTE[classes.length % ACCENT_PALETTE.length],
      quizCount: 0,
      lastSessionLabel: 'Not started',
      createdAt: new Date().toISOString()
    };

    classes.push(newClass);
    writeJson(classesPath, classes);

    res.status(201).json({ ...newClass, studentCount: 0 });
  });

  app.get('/api/classes/:classId/students', (req, res) => {
    const { classId } = req.params;
    if (!isSafeId(classId)) return res.status(400).json({ message: 'Invalid class ID' });

    const classes = readJson(classesPath, []);
    const cls = classes.find((item) => item.id === classId);
    if (!cls) return res.status(404).json({ message: 'Class not found' });

    const allStudents = readJson(studentsPath, []).filter((s) => s.classId === classId);
    const quizCount = listAllQuizzes(quizzesDir).filter(
      (q) => !q.isArchived && q.classId === classId
    ).length;

    const query = cleanText(req.query?.q, 100).toLowerCase();
    const filtered = query
      ? allStudents.filter(
          (s) =>
            s.name.toLowerCase().includes(query) ||
            s.code.toLowerCase().includes(query) ||
            s.dominantSkill.toLowerCase().includes(query)
        )
      : allStudents;

    res.json({
      classInfo: { ...cls, studentCount: allStudents.length, quizCount },
      totalCount: allStudents.length,
      students: filtered
    });
  });

  app.post('/api/classes/:classId/students', (req, res) => {
    const { classId } = req.params;
    if (!isSafeId(classId)) return res.status(400).json({ message: 'Invalid class ID' });

    const classes = readJson(classesPath, []);
    const cls = classes.find((item) => item.id === classId);
    if (!cls) return res.status(404).json({ message: 'Class not found' });

    const name = cleanText(req.body?.name, 100);
    const rawCode = cleanText(req.body?.code, 24);
    const dominantSkill = SKILLS.includes(req.body?.dominantSkill)
      ? req.body.dominantSkill
      : SKILLS[0];
    const parsedScore = Number(req.body?.overallScore);
    const overallScore = Number.isFinite(parsedScore)
      ? Math.max(0, Math.min(100, Math.round(parsedScore)))
      : 75;

    if (!name) return res.status(400).json({ message: 'Student name is required' });

    const codeKey = normalizeStudentCodeKey(rawCode);
    if (!codeKey) {
      return res.status(400).json({ message: 'Unique Student ID is required' });
    }
    if (!/^[A-Za-z0-9_-]{2,20}$/.test(codeKey)) {
      return res.status(400).json({
        message: 'Student ID must be 2–20 characters using letters, numbers, hyphens, or underscores'
      });
    }

    const allStudents = readJson(studentsPath, []);
    const duplicate = allStudents.find((s) => normalizeStudentCodeKey(s.code) === codeKey);
    if (duplicate) {
      return res.status(409).json({
        message: `Student ID "${duplicate.code}" is already assigned to ${duplicate.name}. Please choose a unique ID.`
      });
    }

    const classStudents = allStudents.filter((s) => s.classId === classId);
    const code = formatStudentCode(rawCode);

    const student = {
      id: `st-${uuidv4().slice(0, 8)}`,
      code,
      classId,
      name,
      initials: getInitials(name),
      dominantSkill,
      overallScore,
      cognitiveProfile: buildCognitiveProfile(dominantSkill, overallScore, classStudents.length)
    };

    allStudents.push(student);
    writeJson(studentsPath, allStudents);

    res.status(201).json(student);
  });

  app.get('/api/classes/:classId/students/export', (req, res) => {
    const { classId } = req.params;
    if (!isSafeId(classId)) return res.status(400).json({ message: 'Invalid class ID' });

    const classes = readJson(classesPath, []);
    const cls = classes.find((item) => item.id === classId);
    if (!cls) return res.status(404).json({ message: 'Class not found' });

    const students = readJson(studentsPath, []).filter((s) => s.classId === classId);
    const rows = [
      'Student ID,Name,Dominant Cognitive Skill,Overall Score (%)',
      ...students.map((s) =>
        [csvCell(s.code), csvCell(s.name), csvCell(s.dominantSkill), s.overallScore].join(',')
      )
    ];

    res.setHeader('Content-Type', 'text/csv; charset=utf-8');
    res.setHeader('Content-Disposition', `attachment; filename="${cls.id}_roster.csv"`);
    res.send(rows.join('\n'));
  });

  // ---- Quizzes, Question Bank & Pre-Quiz Prediction ----

  app.get('/api/quizzes', (req, res) => {
    const classId = cleanText(req.query?.classId, 100);
    if (classId && !isSafeId(classId)) {
      return res.status(400).json({ message: 'Invalid class ID' });
    }
    const quizzes = listAllQuizzes(quizzesDir).filter(
      (q) => !classId || !q.classId || q.classId === classId
    );
    res.json(quizzes);
  });

  app.get('/api/quizzes/:quizId', (req, res) => {
    const { quizId } = req.params;
    const quizPath = getQuizPath(quizzesDir, quizId);
    if (!quizPath) return res.status(400).json({ message: 'Invalid quiz ID' });

    const quiz = readJson(quizPath);
    if (!quiz) return res.status(404).json({ message: 'Quiz not found' });
    res.json(quiz);
  });

  app.post('/api/quizzes', (req, res) => {
    const payload = req.body;
    const validationError = validateQuizPayload(payload);
    if (validationError) return res.status(400).json({ message: validationError });

    const classId = cleanText(payload.classId, 100);
    if (classId && !isSafeId(classId)) {
      return res.status(400).json({ message: 'Invalid class ID' });
    }

    const difficulty = DIFFICULTIES.has(payload.difficulty) ? payload.difficulty : 'Medium';
    const quizId = `quiz-${uuidv4().slice(0, 12)}`;
    const now = new Date().toISOString();

    const quiz = {
      id: quizId,
      classId: classId || null,
      name: cleanText(payload.name, 150),
      description: cleanText(payload.description, 2000),
      category: cleanText(payload.category, 100) || 'Mathematics',
      difficulty,
      questions: sanitizeQuestions(payload.questions, difficulty),
      totalTimeLimit: Math.max(0, Number(payload.totalTimeLimit) || 0),
      randomization: {
        shuffleQuestions: Boolean(payload.randomization?.shuffleQuestions),
        shuffleOptions: Boolean(payload.randomization?.shuffleOptions),
        useQuestionPool: Boolean(payload.randomization?.useQuestionPool),
        poolSize: Number(payload.randomization?.poolSize) || 0
      },
      isTemplate: Boolean(payload.isTemplate),
      isArchived: false,
      isNew: true,
      createdAt: now,
      updatedAt: now
    };

    writeJson(path.join(quizzesDir, `${quizId}.json`), quiz);
    res.status(201).json(quiz);
  });

  app.put('/api/quizzes/:quizId', (req, res) => {
    const { quizId } = req.params;
    const quizPath = getQuizPath(quizzesDir, quizId);
    if (!quizPath) return res.status(400).json({ message: 'Invalid quiz ID' });

    const existing = readJson(quizPath);
    if (!existing) return res.status(404).json({ message: 'Quiz not found' });

    const payload = req.body || {};
    const merged = { ...existing, ...payload };
    const validationError = validateQuizPayload(merged);
    if (validationError) return res.status(400).json({ message: validationError });

    const difficulty = DIFFICULTIES.has(payload.difficulty)
      ? payload.difficulty
      : existing.difficulty || 'Medium';

    const updated = {
      ...existing,
      name: cleanText(payload.name, 150) || existing.name,
      description: payload.description !== undefined
        ? cleanText(payload.description, 2000)
        : (existing.description || ''),
      category: cleanText(payload.category, 100) || existing.category || 'Mathematics',
      difficulty,
      questions: Array.isArray(payload.questions)
        ? sanitizeQuestions(payload.questions, difficulty)
        : existing.questions,
      totalTimeLimit: payload.totalTimeLimit !== undefined
        ? Math.max(0, Number(payload.totalTimeLimit) || 0)
        : (existing.totalTimeLimit || 0),
      randomization: payload.randomization !== undefined
        ? {
            shuffleQuestions: Boolean(payload.randomization?.shuffleQuestions),
            shuffleOptions: Boolean(payload.randomization?.shuffleOptions),
            useQuestionPool: Boolean(payload.randomization?.useQuestionPool),
            poolSize: Number(payload.randomization?.poolSize) || 0
          }
        : existing.randomization,
      isTemplate: payload.isTemplate !== undefined ? Boolean(payload.isTemplate) : existing.isTemplate,
      updatedAt: new Date().toISOString()
    };

    writeJson(quizPath, updated);
    res.json(updated);
  });

  app.post('/api/quizzes/duplicate', (req, res) => {
    const { quizId, newName } = req.body || {};
    const quizPath = getQuizPath(quizzesDir, quizId);
    const cleanedName = cleanText(newName, 150);
    if (!quizPath || !cleanedName) {
      return res.status(400).json({ message: 'A valid quiz ID and new name are required' });
    }

    const original = readJson(quizPath);
    if (!original) return res.status(404).json({ message: 'Quiz not found' });

    const newId = `quiz-${uuidv4().slice(0, 12)}`;
    const now = new Date().toISOString();
    const copy = {
      ...original,
      id: newId,
      name: cleanedName,
      isTemplate: false,
      isArchived: false,
      isNew: true,
      createdAt: now,
      updatedAt: now
    };

    writeJson(path.join(quizzesDir, `${newId}.json`), copy);
    res.status(201).json(copy);
  });

  app.put('/api/quizzes/:quizId/archive', (req, res) => {
    const quizPath = getQuizPath(quizzesDir, req.params.quizId);
    if (!quizPath) return res.status(400).json({ message: 'Invalid quiz ID' });
    const quiz = readJson(quizPath);
    if (!quiz) return res.status(404).json({ message: 'Quiz not found' });

    quiz.isArchived = true;
    quiz.archivedAt = new Date().toISOString();
    quiz.updatedAt = quiz.archivedAt;
    writeJson(quizPath, quiz);
    res.json(quiz);
  });

  app.put('/api/quizzes/:quizId/unarchive', (req, res) => {
    const quizPath = getQuizPath(quizzesDir, req.params.quizId);
    if (!quizPath) return res.status(400).json({ message: 'Invalid quiz ID' });
    const quiz = readJson(quizPath);
    if (!quiz) return res.status(404).json({ message: 'Quiz not found' });

    quiz.isArchived = false;
    delete quiz.archivedAt;
    quiz.updatedAt = new Date().toISOString();
    writeJson(quizPath, quiz);
    res.json(quiz);
  });

  app.put('/api/quizzes/:quizId/template', (req, res) => {
    const quizPath = getQuizPath(quizzesDir, req.params.quizId);
    if (!quizPath) return res.status(400).json({ message: 'Invalid quiz ID' });
    const quiz = readJson(quizPath);
    if (!quiz) return res.status(404).json({ message: 'Quiz not found' });

    quiz.isTemplate = true;
    quiz.updatedAt = new Date().toISOString();
    writeJson(quizPath, quiz);
    res.json(quiz);
  });

  app.delete('/api/quizzes/:quizId', (req, res) => {
    const quizPath = getQuizPath(quizzesDir, req.params.quizId);
    if (!quizPath) return res.status(400).json({ message: 'Invalid quiz ID' });
    if (!fs.existsSync(quizPath)) return res.status(404).json({ message: 'Quiz not found' });

    fs.unlinkSync(quizPath);
    res.json({ message: 'Quiz deleted successfully' });
  });

  app.get('/api/question-bank', (req, res) => {
    const classId = cleanText(req.query?.classId, 100);
    if (classId && !isSafeId(classId)) {
      return res.status(400).json({ message: 'Invalid class ID' });
    }
    res.json(listQuestionBank(quizzesDir, classId));
  });

  app.get('/api/quizzes/:quizId/predict', (req, res) => {
    const { quizId } = req.params;
    const quizPath = getQuizPath(quizzesDir, quizId);
    if (!quizPath) return res.status(400).json({ message: 'Invalid quiz ID' });

    const quiz = readJson(quizPath);
    if (!quiz) return res.status(404).json({ message: 'Quiz not found' });

    const requestedClassId = cleanText(req.query?.classId, 100) || quiz.classId || '';
    if (requestedClassId && !isSafeId(requestedClassId)) {
      return res.status(400).json({ message: 'Invalid class ID' });
    }

    const classes = readJson(classesPath, []);
    const classInfo = classes.find((c) => c.id === requestedClassId) || classes[0] || null;
    const targetClassId = classInfo?.id || requestedClassId;

    const allStudents = readJson(studentsPath, []);
    const classStudents = targetClassId
      ? allStudents.filter((s) => s.classId === targetClassId)
      : allStudents;

    res.json(getPredictionStatus(quiz, classStudents, classInfo));
  });

  // ---- Phase 3: Live Session Monitor, QR Code & Student Exam Delivery ----

  app.get('/api/qrcode', async (req, res) => {
    const target = cleanText(req.query?.url, 500);
    if (!/^https?:\/\/(localhost|(?:\d{1,3}\.){3}\d{1,3}):\d{1,5}(?:\/exam)?\/?$/i.test(target)) {
      return res.status(400).json({ message: 'Invalid local BrainMapper URL' });
    }
    const rawSize = Number(req.query?.size);
    const width = Number.isFinite(rawSize)
      ? Math.max(180, Math.min(720, Math.round(rawSize)))
      : 240;
    try {
      const dataUrl = await QRCode.toDataURL(target, {
        width,
        margin: 1,
        color: { dark: '#1e293b', light: '#ffffff' }
      });
      res.json({ dataUrl, url: target });
    } catch (_) {
      res.status(500).json({ message: 'Failed to generate QR code' });
    }
  });

  app.get('/api/session/current', (req, res) => {
    res.json(buildMonitorSnapshot());
  });

  app.get('/api/session/events', (req, res) => {
    res.setHeader('Content-Type', 'text/event-stream');
    res.setHeader('Cache-Control', 'no-cache');
    res.setHeader('Connection', 'keep-alive');
    res.flushHeaders?.();

    res.write(`event: session\ndata: ${JSON.stringify(buildMonitorSnapshot())}\n\n`);
    monitorClients.add(res);
    req.on('close', () => {
      monitorClients.delete(res);
    });
  });

  app.get('/api/exam/events', (req, res) => {
    res.setHeader('Content-Type', 'text/event-stream');
    res.setHeader('Cache-Control', 'no-cache');
    res.setHeader('Connection', 'keep-alive');
    res.flushHeaders?.();

    const classes = readJson(classesPath, []);
    const cls = classes.find((c) => c.id === runtimeState.classId);
    res.write(
      `event: status\ndata: ${JSON.stringify({
        type: 'init',
        status: runtimeState.status,
        sessionId: runtimeState.sessionId,
        quizName: runtimeState.quizName,
        className: cls ? `${cls.name} • ${cls.subject}` : '',
        pinRequired: Boolean(runtimeState.pin)
      })}\n\n`
    );
    examClients.add(res);
    req.on('close', () => {
      examClients.delete(res);
    });
  });

  app.post('/api/session/open-lobby', (req, res) => {
    if (runtimeState.status === 'active') {
      return res.status(409).json({
        message: 'End the current active session before opening a new lobby.'
      });
    }

    const quizId = cleanText(req.body?.quizId, 150);
    const quizPath = getQuizPath(quizzesDir, quizId);
    if (!quizPath) return res.status(400).json({ message: 'A valid quiz ID is required' });

    const quiz = readJson(quizPath);
    if (!quiz || !Array.isArray(quiz.questions) || quiz.questions.length === 0) {
      return res.status(404).json({ message: 'Quiz not found or contains no questions' });
    }

    const requestedClassId = cleanText(req.body?.classId, 100) || quiz.classId || null;
    if (requestedClassId && !isSafeId(requestedClassId)) {
      return res.status(400).json({ message: 'Invalid class ID' });
    }

    const selectedIp = cleanText(req.body?.selectedIp, 64) || '127.0.0.1';
    const listenPort = Number(req.body?.port) || req.socket?.localPort || PORT;
    const joinUrl = `http://${selectedIp}:${listenPort}/exam`;
    const pin = cleanText(req.body?.pin, 12);
    const shouldResetParticipants =
      Boolean(req.body?.resetParticipants) ||
      runtimeState.status !== 'lobby' ||
      runtimeState.quizId !== quiz.id;

    if (shouldResetParticipants) {
      const nextSessionId = makeSafeSessionId(quiz);
      runtimeState = {
        ...createEmptyRuntimeState(),
        sessionId: nextSessionId,
        status: 'lobby',
        classId: requestedClassId,
        quizId: quiz.id,
        quizName: quiz.name,
        pin,
        selectedIp,
        joinUrl,
        openedAt: new Date().toISOString()
      };
    } else {
      runtimeState.classId = requestedClassId;
      runtimeState.pin = pin;
      runtimeState.selectedIp = selectedIp;
      runtimeState.joinUrl = joinUrl;
    }

    saveRuntimeState(runtimeStatePath, runtimeState);
    notifyMonitorClients();
    notifyExamClients('lobby');
    res.json(buildMonitorSnapshot());
  });

  app.post('/api/session/start', (req, res) => {
    if (runtimeState.status === 'active') {
      return res.status(409).json({
        message: 'A quiz session is already running. End it first before starting another.'
      });
    }

    const quizId = cleanText(req.body?.quizId, 150) || runtimeState.quizId;
    const quizPath = getQuizPath(quizzesDir, quizId);
    if (!quizPath) return res.status(400).json({ message: 'Select a valid quiz to start' });

    const quiz = readJson(quizPath);
    if (!quiz || !Array.isArray(quiz.questions) || quiz.questions.length === 0) {
      return res.status(404).json({ message: 'Quiz not found or has no questions' });
    }

    const requestedClassId =
      cleanText(req.body?.classId, 100) || runtimeState.classId || quiz.classId || null;
    if (requestedClassId && !isSafeId(requestedClassId)) {
      return res.status(400).json({ message: 'Invalid class ID' });
    }

    const keepLobby = runtimeState.status === 'lobby' && runtimeState.quizId === quiz.id && runtimeState.sessionId;
    const sessionId = keepLobby ? runtimeState.sessionId : makeSafeSessionId(quiz);
    const now = new Date().toISOString();
    const selectedIp = cleanText(req.body?.selectedIp, 64) || runtimeState.selectedIp || '127.0.0.1';
    const listenPort = Number(req.body?.port) || req.socket?.localPort || PORT;
    const joinUrl = runtimeState.joinUrl || `http://${selectedIp}:${listenPort}/exam`;
    const pin = req.body?.pin !== undefined ? cleanText(req.body.pin, 12) : (runtimeState.pin || '');
    const expectedCount = getEffectivePoolCount(quiz);

    const existingParticipants = keepLobby ? runtimeState.participants : [];
    const updatedParticipants = existingParticipants.map((p) => ({
      ...p,
      status: p.status === 'submitted' ? 'submitted' : 'in-progress',
      totalQuestions: expectedCount
    }));

    const sessionData = {
      ...quiz,
      sessionId,
      classId: requestedClassId,
      quizId: quiz.id,
      sessionDate: now,
      startedAt: now,
      endedAt: null,
      status: 'active',
      results: []
    };

    const sessionPath = path.join(sessionsDir, `${sessionId}.json`);
    writeJson(sessionPath, sessionData);
    writeJson(sessionRefPath, { sessionId, sessionPath });

    runtimeState = {
      ...createEmptyRuntimeState(),
      sessionId,
      status: 'active',
      classId: requestedClassId,
      quizId: quiz.id,
      quizName: quiz.name,
      pin,
      selectedIp,
      joinUrl,
      openedAt: keepLobby ? runtimeState.openedAt : now,
      startedAt: now,
      endedAt: null,
      participants: updatedParticipants,
      studentQuizMappings: keepLobby ? runtimeState.studentQuizMappings : {}
    };

    saveRuntimeState(runtimeStatePath, runtimeState);
    notifyMonitorClients();
    notifyExamClients('started');
    res.json(buildMonitorSnapshot());
  });

  app.post('/api/session/end', (req, res) => {
    if (runtimeState.status === 'idle') {
      return res.json(buildMonitorSnapshot());
    }

    const now = new Date().toISOString();
    if (runtimeState.sessionId) {
      const sessionPath = path.join(sessionsDir, `${runtimeState.sessionId}.json`);
      const sessionData = readJson(sessionPath);
      if (sessionData) {
        sessionData.status = 'ended';
        sessionData.endedAt = now;
        writeJson(sessionPath, sessionData);
      }
    }

    if (fs.existsSync(sessionRefPath)) {
      fs.unlinkSync(sessionRefPath);
    }

    if (runtimeState.classId && runtimeState.startedAt) {
      const classes = readJson(classesPath, []);
      const idx = classes.findIndex((c) => c.id === runtimeState.classId);
      if (idx !== -1) {
        classes[idx].lastSessionLabel = formatShortMonthDay(new Date());
        writeJson(classesPath, classes);
      }
    }

    runtimeState.status = 'ended';
    runtimeState.endedAt = now;
    saveRuntimeState(runtimeStatePath, runtimeState);

    notifyMonitorClients();
    notifyExamClients('ended');
    res.json(buildMonitorSnapshot());
  });

  app.post('/api/session/reset', (req, res) => {
    if (runtimeState.status === 'active') {
      return res.status(409).json({ message: 'End the active quiz session before resetting.' });
    }
    if (fs.existsSync(sessionRefPath)) {
      fs.unlinkSync(sessionRefPath);
    }
    runtimeState = createEmptyRuntimeState();
    saveRuntimeState(runtimeStatePath, runtimeState);
    notifyMonitorClients();
    notifyExamClients('reset');
    res.json(buildMonitorSnapshot());
  });

  app.post('/api/session/kick', (req, res) => {
    const participantId = cleanText(req.body?.participantId, 120);
    if (!isSafeId(participantId)) {
      return res.status(400).json({ message: 'Invalid participant ID' });
    }
    runtimeState.participants = runtimeState.participants.filter((p) => p.id !== participantId);
    delete runtimeState.studentQuizMappings[participantId];
    saveRuntimeState(runtimeStatePath, runtimeState);
    notifyMonitorClients();
    res.json(buildMonitorSnapshot());
  });

  app.get('/api/sessions', (req, res) => {
    const classId = cleanText(req.query?.classId, 100);
    if (classId && !isSafeId(classId)) {
      return res.status(400).json({ message: 'Invalid class ID' });
    }
    res.json(listClassSessions(sessionsDir, classId));
  });

  app.get('/api/sessions/:sessionId', (req, res) => {
    const { sessionId } = req.params;
    if (!isSafeId(sessionId)) return res.status(400).json({ message: 'Invalid session ID' });
    const sessionPath = path.join(sessionsDir, `${sessionId}.json`);
    const data = readJson(sessionPath);
    if (!data) return res.status(404).json({ message: 'Session not found' });
    res.json(data);
  });

  // ---- Student Exam Endpoints (Safe, No Answer Keys) ----

  app.get('/api/session/status', (req, res) => {
    const classes = readJson(classesPath, []);
    const cls = classes.find((c) => c.id === runtimeState.classId);

    let quizMeta = null;
    if (runtimeState.quizId) {
      const qPath = getQuizPath(quizzesDir, runtimeState.quizId);
      const q = qPath ? readJson(qPath) : null;
      if (q) {
        quizMeta = {
          questionCount: getEffectivePoolCount(q),
          totalTimeLimit: Math.max(0, Number(q.totalTimeLimit) || 0),
          difficulty: q.difficulty || 'Medium'
        };
      }
    }

    const participantId = cleanText(req.query?.participantId, 120);
    let participantState = null;
    if (participantId && isSafeId(participantId)) {
      const found = runtimeState.participants.find((p) => p.id === participantId);
      if (found) {
        participantState = {
          registered: true,
          id: found.id,
          name: found.name,
          studentCode: found.studentCode,
          status: found.status,
          score: found.score,
          totalGradeable: found.totalGradeable,
          pendingManualGrading: found.pendingManualGrading,
          percentage: found.percentage
        };
      } else {
        participantState = { registered: false };
      }
    }

    res.json({
      status: runtimeState.status,
      sessionId: runtimeState.sessionId,
      quizName: runtimeState.quizName,
      className: cls ? `${cls.name} • ${cls.subject}` : '',
      pinRequired: Boolean(runtimeState.pin),
      quizMeta,
      participant: participantState
    });
  });

  app.post('/api/join', (req, res) => {
    if (runtimeState.status !== 'lobby' && runtimeState.status !== 'active') {
      return res.status(409).json({
        message: 'No exam session is open right now. Wait for your teacher to open the session.'
      });
    }

    const submittedPin = cleanText(req.body?.pin, 12);
    if (runtimeState.pin && submittedPin !== runtimeState.pin) {
      return res.status(403).json({ message: 'Incorrect session PIN.' });
    }

    const studentCodeInput = cleanText(
      req.body?.studentCode || req.body?.studentId || req.body?.code,
      24
    );
    if (!normalizeStudentCodeKey(studentCodeInput)) {
      return res.status(400).json({ message: 'Your assigned Student ID is required.' });
    }

    const students = readJson(studentsPath, []);
    const matchedStudent = matchRosterStudentByCode(students, runtimeState.classId, studentCodeInput);
    if (!matchedStudent) {
      return res.status(404).json({
        message: 'Student ID not found in this class roster. Check your assigned ID or ask your teacher to enroll you.'
      });
    }

    const existingParticipant = runtimeState.participants.find(
      (p) => p.rosterStudentId === matchedStudent.id
    );
    if (existingParticipant) {
      if (existingParticipant.status === 'submitted') {
        return res.status(409).json({
          message: `Student ID ${matchedStudent.code} (${matchedStudent.name}) has already submitted this exam.`
        });
      }
      return res.status(200).json({
        participantId: existingParticipant.id,
        name: existingParticipant.name,
        studentCode: existingParticipant.studentCode,
        rosterStudentId: existingParticipant.rosterStudentId,
        sessionId: runtimeState.sessionId,
        sessionStatus: runtimeState.status,
        reconnected: true
      });
    }

    let totalQuestions = 0;
    if (runtimeState.quizId) {
      const qPath = getQuizPath(quizzesDir, runtimeState.quizId);
      const quiz = qPath ? readJson(qPath) : null;
      if (quiz) totalQuestions = getEffectivePoolCount(quiz);
    }

    const participantId = uuidv4();
    const participant = {
      id: participantId,
      name: matchedStudent.name,
      studentCode: matchedStudent.code,
      rosterStudentId: matchedStudent.id,
      joinedAt: new Date().toISOString(),
      status: runtimeState.status === 'active' ? 'in-progress' : 'waiting',
      answeredCount: 0,
      totalQuestions,
      score: null,
      totalGradeable: null,
      pendingManualGrading: 0,
      percentage: null,
      submittedAt: null
    };

    runtimeState.participants.push(participant);
    saveRuntimeState(runtimeStatePath, runtimeState);
    notifyMonitorClients();

    res.status(201).json({
      participantId,
      name: participant.name,
      studentCode: participant.studentCode,
      rosterStudentId: participant.rosterStudentId,
      sessionId: runtimeState.sessionId,
      sessionStatus: runtimeState.status
    });
  });

  app.post('/api/leave', (req, res) => {
    const participantId = cleanText(req.body?.participantId, 120);
    if (!isSafeId(participantId)) {
      return res.status(400).json({ message: 'Invalid participant ID' });
    }
    const participant = runtimeState.participants.find((p) => p.id === participantId);
    if (participant && participant.status === 'submitted') {
      return res.status(409).json({ message: 'Submitted exams cannot leave the session.' });
    }
    runtimeState.participants = runtimeState.participants.filter((p) => p.id !== participantId);
    delete runtimeState.studentQuizMappings[participantId];
    saveRuntimeState(runtimeStatePath, runtimeState);
    notifyMonitorClients();
    res.json({ ok: true });
  });

  app.get('/api/currentQuiz', (req, res) => {
    if (runtimeState.status !== 'active' || !fs.existsSync(sessionRefPath)) {
      return res.status(404).json({ message: 'No active quiz session right now.' });
    }

    const sessionRef = readJson(sessionRefPath);
    const fullQuiz = sessionRef?.sessionPath ? readJson(sessionRef.sessionPath) : null;
    if (!fullQuiz) {
      return res.status(404).json({ message: 'Session quiz data not found.' });
    }

    const studentId = cleanText(req.query?.studentId, 120);
    if (!studentId) {
      return res.json(sanitizeQuizForStudent(fullQuiz));
    }
    if (!isSafeId(studentId)) {
      return res.status(400).json({ message: 'Invalid student ID' });
    }

    const participant = runtimeState.participants.find((p) => p.id === studentId);
    if (!participant) {
      return res.status(403).json({ message: 'Participant is not registered for this session.' });
    }
    if (participant.status === 'submitted') {
      return res.status(409).json({
        message: 'You have already submitted this exam.',
        submitted: true,
        resultSummary: {
          score: participant.score,
          totalGradeable: participant.totalGradeable,
          pendingManualGrading: participant.pendingManualGrading,
          percentage: participant.percentage
        }
      });
    }

    let entry = runtimeState.studentQuizMappings[studentId];
    if (!entry) {
      const prepared = prepareStudentQuiz(fullQuiz);
      entry = {
        quiz: prepared.quiz,
        mapping: prepared.mapping,
        startedAt: new Date().toISOString(),
        draft: null
      };
      runtimeState.studentQuizMappings[studentId] = entry;
      participant.status = 'in-progress';
      participant.totalQuestions = prepared.quiz.questions.length;
      saveRuntimeState(runtimeStatePath, runtimeState);
      notifyMonitorClients();
    } else if (!entry.startedAt) {
      entry.startedAt = new Date().toISOString();
      saveRuntimeState(runtimeStatePath, runtimeState);
    }

    const totalTimeLimit = Math.max(0, Number(entry.quiz.totalTimeLimit) || 0);
    const elapsedSeconds = Math.max(
      0,
      Math.floor((Date.now() - new Date(entry.startedAt).getTime()) / 1000)
    );
    const remainingSeconds = totalTimeLimit > 0 ? Math.max(0, totalTimeLimit - elapsedSeconds) : 0;

    res.json({
      ...entry.quiz,
      participant: {
        id: participant.id,
        name: participant.name,
        studentCode: participant.studentCode,
        startedAt: entry.startedAt
      },
      elapsedSeconds,
      remainingSeconds,
      draft: entry.draft || null
    });
  });

  app.post('/api/student/draft', (req, res) => {
    const participantId = cleanText(req.body?.participantId, 120);
    if (!isSafeId(participantId)) {
      return res.status(400).json({ message: 'Invalid participant ID' });
    }
    if (runtimeState.status !== 'active') {
      return res.status(409).json({ message: 'Session is no longer active' });
    }

    const participant = runtimeState.participants.find((p) => p.id === participantId);
    const entry = runtimeState.studentQuizMappings[participantId];
    if (!participant || !entry) {
      return res.status(403).json({ message: 'Participant session not initialized' });
    }
    if (participant.status === 'submitted') {
      return res.status(409).json({ message: 'Exam already submitted' });
    }

    const answers = Array.isArray(req.body?.answers) ? req.body.answers : [];
    const flaggedQuestions = Array.isArray(req.body?.flaggedQuestions)
      ? req.body.flaggedQuestions.filter((n) => Number.isInteger(n) && n >= 0)
      : [];
    const activeQuestionIndex = Math.max(0, Number(req.body?.activeQuestionIndex) || 0);
    const questionTimersRemaining =
      req.body?.questionTimersRemaining && typeof req.body.questionTimersRemaining === 'object'
        ? req.body.questionTimersRemaining
        : {};

    entry.draft = {
      answers,
      flaggedQuestions,
      activeQuestionIndex,
      questionTimersRemaining,
      updatedAt: new Date().toISOString()
    };

    participant.answeredCount = countAnsweredQuestions(answers, entry.quiz.questions);
    saveRuntimeState(runtimeStatePath, runtimeState);
    notifyMonitorClients();

    res.json({ ok: true, answeredCount: participant.answeredCount });
  });

  app.post('/api/submit', (req, res) => {
    const { participantId, answers, timeSpent, autoSubmitted, timeoutReason } = req.body || {};
    if (!isSafeId(participantId) || !Array.isArray(answers)) {
      return res.status(400).json({ message: 'A valid participant and answers array are required' });
    }

    const participant = runtimeState.participants.find((p) => p.id === participantId);
    if (!participant) {
      return res.status(403).json({ message: 'Participant is not registered' });
    }

    const sessionRef = readJson(sessionRefPath);
    const sessionPath = sessionRef?.sessionPath ||
      (runtimeState.sessionId ? path.join(sessionsDir, `${runtimeState.sessionId}.json`) : null);
    if (!sessionPath || !fs.existsSync(sessionPath)) {
      return res.status(400).json({ message: 'No active quiz session' });
    }

    const sessionData = readJson(sessionPath);
    if (!sessionData) {
      return res.status(400).json({ message: 'Session file could not be read' });
    }
    if (!Array.isArray(sessionData.results)) sessionData.results = [];

    if (
      participant.status === 'submitted' ||
      sessionData.results.some((r) => r.participantId === participantId)
    ) {
      return res.status(409).json({ message: 'This participant has already submitted' });
    }

    const mappingEntry = runtimeState.studentQuizMappings[participantId] || null;
    const mapping = mappingEntry?.mapping || null;
    const mappedAnswers = reverseMapAnswers(answers, sessionData, mapping);
    const graded = gradeSubmission({ fullQuiz: sessionData, mappedAnswers, mapping });
    const now = new Date().toISOString();

    const resultRecord = {
      participantId,
      participantName: participant.name,
      studentCode: participant.studentCode,
      rosterStudentId: participant.rosterStudentId,
      score: graded.score,
      totalQuestions: graded.totalQuestions,
      totalGradeable: graded.totalGradeable,
      pendingManualGrading: graded.pendingManualGrading,
      percentage: graded.percentage,
      submittedAt: now,
      answers: mappedAnswers,
      originalAnswers: answers,
      detailedResults: graded.detailedResults,
      timeSpent: Math.max(0, Math.round(Number(timeSpent) || 0)),
      autoSubmitted: Boolean(autoSubmitted),
      timeoutReason: cleanText(timeoutReason, 200) || null,
      timeLimit: sessionData.totalTimeLimit || 0,
      wasRandomized: Boolean(mapping),
      questionMapping: mapping?.questionMapping || null
    };

    sessionData.results.push(resultRecord);
    writeJson(sessionPath, sessionData);

    participant.status = 'submitted';
    participant.answeredCount = countAnsweredQuestions(answers, mappingEntry?.quiz?.questions || sessionData.questions);
    participant.score = graded.score;
    participant.totalGradeable = graded.totalGradeable;
    participant.pendingManualGrading = graded.pendingManualGrading;
    participant.percentage = graded.percentage;
    participant.submittedAt = now;
    if (mappingEntry) {
      delete mappingEntry.draft;
    }

    saveRuntimeState(runtimeStatePath, runtimeState);
    notifyMonitorClients();

    res.json({
      sessionId: sessionData.sessionId,
      participantId,
      score: graded.score,
      totalQuestions: graded.totalQuestions,
      totalGradeable: graded.totalGradeable,
      pendingManualGrading: graded.pendingManualGrading,
      percentage: graded.percentage
    });
  });

  app.locals.closeSseStreams = () => {
    for (const client of monitorClients) {
      try {
        client.end();
      } catch (_) {}
    }
    for (const client of examClients) {
      try {
        client.end();
      } catch (_) {}
    }
    monitorClients.clear();
    examClients.clear();
  };

  return app;
}

const PORT = Number(process.env.PORT) || 3000;

if (require.main === module) {
  const app = createApp();
  app.listen(PORT, '0.0.0.0', () => {
    console.log(`BrainMapper listening at http://0.0.0.0:${PORT}`);
  });
}

module.exports = { createApp, isSafeId, csvCell, isHostAddress };
