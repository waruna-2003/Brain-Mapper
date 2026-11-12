const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');

const { createApp, isSafeId, csvCell, isHostAddress } = require('../server');
const { validateQuizPayload } = require('../quizService');
const { makeSafeSessionId } = require('../sessionService');

let dataDir;
let server;
let baseUrl;

test.before(async () => {
  dataDir = fs.mkdtempSync(path.join(os.tmpdir(), 'brainmapper-test-'));
  const app = createApp(dataDir);
  await new Promise((resolve) => {
    server = app.listen(0, '127.0.0.1', () => {
      baseUrl = `http://127.0.0.1:${server.address().port}`;
      resolve();
    });
  });
});

test.after(async () => {
  await new Promise((resolve) => server.close(resolve));
  fs.rmSync(dataDir, { recursive: true, force: true });
});

test('validates safe IDs, quiz payloads, and CSV cells', () => {
  assert.equal(isSafeId('class-1'), true);
  assert.equal(isSafeId('../secret'), false);
  assert.equal(csvCell('=SUM(A1:A2)'), `"'=SUM(A1:A2)"`);
  assert.equal(csvCell('Pramudi Biyonika'), '"Pramudi Biyonika"');

  assert.equal(validateQuizPayload({}), 'Quiz title is required');
  assert.match(
    validateQuizPayload({
      name: 'Non-MCQ Quiz',
      questions: [{ type: 'short-answer', question: 'Explain variance.' }]
    }),
    /Only Multiple Choice \(MCQ\)/
  );
  assert.match(
    validateQuizPayload({
      name: 'True False Quiz',
      questions: [{ type: 'true-false', question: 'Zero is even?', options: { True: 'True', False: 'False' }, correct: 'True' }]
    }),
    /Only Multiple Choice \(MCQ\)/
  );
  assert.equal(
    validateQuizPayload({
      name: 'Incomplete MC',
      questions: [{ type: 'multiple-choice', question: '2+2?', options: { A: '4' }, correct: 'A' }]
    }),
    'Question 1 is missing option B'
  );
  assert.equal(
    validateQuizPayload({
      name: 'Valid MC',
      questions: [
        {
          type: 'multiple-choice',
          question: '2+2?',
          options: { A: '3', B: '4', C: '5', D: '6' },
          correct: 'B'
        }
      ]
    }),
    null
  );
});

test('serves health check and seeded classes with dynamic quiz & student counts', async () => {
  const healthRes = await fetch(`${baseUrl}/api/health`);
  assert.equal(healthRes.status, 200);
  const health = await healthRes.json();
  assert.equal(health.ok, true);
  assert.equal(health.offline, true);

  const classesRes = await fetch(`${baseUrl}/api/classes`);
  assert.equal(classesRes.status, 200);
  const classes = await classesRes.json();
  assert.equal(classes.length, 2);
  assert.equal(classes[0].name, 'Class 1');
  assert.equal(classes[0].studentCount, 32);
  assert.equal(classes[0].quizCount, 4);
  assert.equal(classes[1].studentCount, 28);
  assert.equal(classes[1].quizCount, 2);
});

test('creates a new class and rejects incomplete class payloads', async () => {
  const badRes = await fetch(`${baseUrl}/api/classes`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name: 'Class 3' })
  });
  assert.equal(badRes.status, 400);

  const createRes = await fetch(`${baseUrl}/api/classes`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      name: 'Class 3',
      subject: 'Grade 12 Physics',
      accentColor: 'emerald'
    })
  });
  assert.equal(createRes.status, 201);
  const created = await createRes.json();
  assert.equal(created.name, 'Class 3');
  assert.equal(created.accentColor, 'emerald');
  assert.equal(created.studentCount, 0);
});

test('lists, filters, enrolls, and exports class roster students', async () => {
  const searchRes = await fetch(`${baseUrl}/api/classes/class-1/students?q=Pramudi`);
  assert.equal(searchRes.status, 200);
  const searchData = await searchRes.json();
  assert.equal(searchData.totalCount, 32);
  assert.equal(searchData.students.length, 1);
  assert.equal(searchData.students[0].code, '#ST-1001');

  const missingCodeRes = await fetch(`${baseUrl}/api/classes/class-1/students`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      name: 'Nimali Gunasekara',
      dominantSkill: 'Critical Thinking'
    })
  });
  assert.equal(missingCodeRes.status, 400);

  const dupCodeRes = await fetch(`${baseUrl}/api/classes/class-1/students`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      name: 'Nimali Gunasekara',
      code: 'st-1001',
      dominantSkill: 'Critical Thinking'
    })
  });
  assert.equal(dupCodeRes.status, 409);

  const addRes = await fetch(`${baseUrl}/api/classes/class-1/students`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      name: 'Nimali Gunasekara',
      code: 'ST-1033',
      dominantSkill: 'Critical Thinking'
    })
  });
  assert.equal(addRes.status, 201);
  const added = await addRes.json();
  assert.equal(added.initials, 'NG');
  assert.equal(added.code, '#ST-1033');

  const exportRes = await fetch(`${baseUrl}/api/classes/class-1/students/export`);
  assert.equal(exportRes.status, 200);
  const csvText = await exportRes.text();
  assert.match(csvText, /Pramudi Biyonika/);
  assert.match(csvText, /Nimali Gunasekara/);
});

test('creates, updates, duplicates, archives, and serves question bank for quizzes', async () => {
  const createRes = await fetch(`${baseUrl}/api/quizzes`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      classId: 'class-1',
      name: 'New Cognitive Quiz',
      description: 'Testing cognitive demand tagging',
      category: 'Mathematics',
      difficulty: 'Medium',
      totalTimeLimit: 1200,
      questions: [
        {
          type: 'multiple-choice',
          question: 'What is 7 * 8?',
          options: { A: '54', B: '56', C: '58', D: '64' },
          correct: 'B',
          cognitiveDemand: {
            Attention: 1,
            'Working Memory': 2,
            'Logical Reasoning': 3,
            'Language Processing': 1,
            'Critical Thinking': 2,
            Metacognition: 1
          }
        }
      ]
    })
  });
  assert.equal(createRes.status, 201);
  const created = await createRes.json();
  assert.equal(created.isNew, true);
  assert.equal(created.questions[0].cognitiveDemand['Logical Reasoning'], 3);

  const dupRes = await fetch(`${baseUrl}/api/quizzes/duplicate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ quizId: created.id, newName: 'New Cognitive Quiz (Copy)' })
  });
  assert.equal(dupRes.status, 201);
  const duplicated = await dupRes.json();
  assert.notEqual(duplicated.id, created.id);

  const archiveRes = await fetch(`${baseUrl}/api/quizzes/${duplicated.id}/archive`, { method: 'PUT' });
  assert.equal(archiveRes.status, 200);
  assert.equal((await archiveRes.json()).isArchived, true);

  const bankRes = await fetch(`${baseUrl}/api/question-bank?classId=class-1`);
  assert.equal(bankRes.status, 200);
  const bank = await bankRes.json();
  assert.ok(bank.some((q) => q.question === 'What is 7 * 8?'));

  const delRes = await fetch(`${baseUrl}/api/quizzes/${duplicated.id}`, { method: 'DELETE' });
  assert.equal(delRes.status, 200);
});

test('returns work-in-progress prediction status without synthetic scores', async () => {
  const predRes = await fetch(`${baseUrl}/api/quizzes/quiz-g10-statistics-4/predict?classId=class-1`);
  assert.equal(predRes.status, 200);
  const forecast = await predRes.json();

  assert.equal(forecast.status, 'work_in_progress');
  assert.equal(forecast.workInProgress, true);
  assert.equal(forecast.quiz.id, 'quiz-g10-statistics-4');
  assert.equal(forecast.quiz.questionCount, 2);
  assert.ok(forecast.summary.studentCount >= 32);
  assert.equal('studentPredictions' in forecast, false);
});

test('generates safe session IDs, QR codes, and enforces LAN host address rules', async () => {
  const safeDupId = makeSafeSessionId({ name: 'Grade 10 Quiz (Copy) #2!' });
  assert.equal(isSafeId(safeDupId), true);

  assert.equal(isHostAddress('127.0.0.1', [{ name: 'Wi-Fi', address: '192.168.1.50' }]), true);
  assert.equal(isHostAddress('::ffff:127.0.0.1', [{ name: 'Wi-Fi', address: '192.168.1.50' }]), true);
  assert.equal(isHostAddress('192.168.1.50', [{ name: 'Wi-Fi', address: '192.168.1.50' }]), true);
  assert.equal(isHostAddress('192.168.1.99', [{ name: 'Wi-Fi', address: '192.168.1.50' }]), false);

  const port = server.address().port;
  const qrRes = await fetch(
    `${baseUrl}/api/qrcode?url=${encodeURIComponent(`http://127.0.0.1:${port}/exam`)}`
  );
  assert.equal(qrRes.status, 200);
  const qrData = await qrRes.json();
  assert.match(qrData.dataUrl, /^data:image\/png;base64,/);

  const badQrRes = await fetch(`${baseUrl}/api/qrcode?url=${encodeURIComponent('https://evil.example/exam')}`);
  assert.equal(badQrRes.status, 400);
});

test('runs lobby, live exam with stripped answer keys, reload safety, pool grading, and session end', async () => {
  const quizRes = await fetch(`${baseUrl}/api/quizzes`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      classId: 'class-1',
      name: 'MCQ Pool Live Exam (Copy)',
      category: 'Mathematics',
      difficulty: 'Medium',
      totalTimeLimit: 600,
      randomization: {
        shuffleQuestions: true,
        shuffleOptions: true,
        useQuestionPool: true,
        poolSize: 2
      },
      questions: [
        {
          type: 'multiple-choice',
          question: 'Q_MC_1: 5 + 5 = ?',
          options: { A: '10', B: '11', C: '12', D: '13' },
          correct: 'A',
          explanation: 'Secret MC 1 explanation'
        },
        {
          type: 'multiple-choice',
          question: 'Q_MC_2: 3 * 4 = ?',
          options: { A: '7', B: '12', C: '15', D: '9' },
          correct: 'B',
          explanation: 'Secret MC 2 explanation'
        },
        {
          type: 'multiple-choice',
          question: 'Q_MC_3: Square root of 81?',
          options: { A: '7', B: '8', C: '9', D: '10' },
          correct: 'C',
          explanation: 'Secret MC 3 explanation'
        },
        {
          type: 'multiple-choice',
          question: 'Q_MC_4: Derivative of x^2 at x = 3?',
          options: { A: '3', B: '6', C: '9', D: '12' },
          correct: 'B',
          explanation: 'Secret MC 4 explanation'
        }
      ]
    })
  });
  assert.equal(quizRes.status, 201);
  const fullQuiz = await quizRes.json();

  // Reject non-MCQ quiz via API
  const badTypeRes = await fetch(`${baseUrl}/api/quizzes`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      classId: 'class-1',
      name: 'Invalid True False Quiz',
      questions: [{ type: 'true-false', question: '1+1=2?', options: { True: 'True', False: 'False' }, correct: 'True' }]
    })
  });
  assert.equal(badTypeRes.status, 400);

  // Open lobby with PIN 4821
  const lobbyRes = await fetch(`${baseUrl}/api/session/open-lobby`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      classId: 'class-1',
      quizId: fullQuiz.id,
      pin: '4821',
      selectedIp: '127.0.0.1'
    })
  });
  assert.equal(lobbyRes.status, 200);
  const lobbyData = await lobbyRes.json();
  assert.equal(lobbyData.status, 'lobby');
  assert.equal(isSafeId(lobbyData.sessionId), true);

  // Wrong PIN rejected
  const wrongPinRes = await fetch(`${baseUrl}/api/join`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ studentCode: 'ST-1001', pin: '0000' })
  });
  assert.equal(wrongPinRes.status, 403);

  // Unknown student ID rejected
  const unknownIdRes = await fetch(`${baseUrl}/api/join`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ studentCode: 'ST-9999', pin: '4821' })
  });
  assert.equal(unknownIdRes.status, 404);

  // Valid ID-only join automatically resolves enrolled student name & profile
  const joinRes = await fetch(`${baseUrl}/api/join`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ studentCode: 'st-1001', pin: '4821' })
  });
  assert.equal(joinRes.status, 201);
  const joined = await joinRes.json();
  assert.equal(joined.name, 'Pramudi Biyonika');
  assert.equal(joined.studentCode, '#ST-1001');
  assert.equal(joined.rosterStudentId, 'st-class-1-1001');
  assert.equal(joined.sessionStatus, 'lobby');

  // Start live quiz
  const startRes = await fetch(`${baseUrl}/api/session/start`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ classId: 'class-1', quizId: fullQuiz.id })
  });
  assert.equal(startRes.status, 200);
  const started = await startRes.json();
  assert.equal(started.status, 'active');
  assert.equal(started.participants.length, 1);
  assert.equal(started.participants[0].status, 'in-progress');

  // Fetch sanitized quiz for student — zero answer keys or explanations
  const examRes1 = await fetch(`${baseUrl}/api/currentQuiz?studentId=${joined.participantId}`);
  assert.equal(examRes1.status, 200);
  const studentQuiz1 = await examRes1.json();
  assert.equal(studentQuiz1.questions.length, 2); // poolSize === 2!
  studentQuiz1.questions.forEach((q) => {
    assert.equal(q.type, 'multiple-choice');
    assert.equal('correct' in q, false);
    assert.equal('explanation' in q, false);
  });

  // Save draft and simulate reload (second GET /api/currentQuiz returns same order + draft)
  const draftRes = await fetch(`${baseUrl}/api/student/draft`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      participantId: joined.participantId,
      sessionId: started.sessionId,
      answers: ['A', null],
      flaggedQuestions: [1],
      activeQuestionIndex: 1
    })
  });
  assert.equal(draftRes.status, 200);

  const examRes2 = await fetch(`${baseUrl}/api/currentQuiz?studentId=${joined.participantId}`);
  const studentQuiz2 = await examRes2.json();
  assert.deepEqual(
    studentQuiz2.questions.map((q) => q.question),
    studentQuiz1.questions.map((q) => q.question)
  );
  assert.deepEqual(studentQuiz2.draft.flaggedQuestions, [1]);

  // Construct 100% right MCQ answers dynamically using shuffled display options
  const expectedAnswerValues = {
    'Q_MC_1: 5 + 5 = ?': '10',
    'Q_MC_2: 3 * 4 = ?': '12',
    'Q_MC_3: Square root of 81?': '9',
    'Q_MC_4: Derivative of x^2 at x = 3?': '6'
  };
  const answers = studentQuiz2.questions.map((q) => {
    const targetVal = expectedAnswerValues[q.question];
    return Object.entries(q.options).find(([, val]) => val === targetVal)[0];
  });

  const submitRes = await fetch(`${baseUrl}/api/submit`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ participantId: joined.participantId, answers, timeSpent: 45 })
  });
  assert.equal(submitRes.status, 200);
  const result = await submitRes.json();
  assert.equal(result.score, 2);
  assert.equal(result.totalGradeable, 2); // NOT 4! Pool grading bug fixed!
  assert.equal(result.percentage, 100);

  // Duplicate submit prevented
  const dupSubmit = await fetch(`${baseUrl}/api/submit`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ participantId: joined.participantId, answers })
  });
  assert.equal(dupSubmit.status, 409);

  // End session cleanly & verify persisted session record
  const endRes = await fetch(`${baseUrl}/api/session/end`, { method: 'POST' });
  assert.equal(endRes.status, 200);
  const endData = await endRes.json();
  assert.equal(endData.status, 'ended');

  const sessRes = await fetch(`${baseUrl}/api/sessions/${started.sessionId}`);
  assert.equal(sessRes.status, 200);
  const sessFile = await sessRes.json();
  assert.equal(sessFile.results.length, 1);
  assert.equal(sessFile.results[0].score, 2);
  assert.equal(sessFile.results[0].totalGradeable, 2);
});
