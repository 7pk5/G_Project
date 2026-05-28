// Miko Bridge Service Worker v7
// Intercepts mock JSON fetches in the Flutter student app
// and replaces them with live Firebase data written by the Assessment Planner.
//
// Data flow:
//   Scheduler confirms plan → writes:
//     schools/{schoolId}/meta/current_session   (subject + full student list)
//     schools/{schoolId}/sessions/{YYYY-MM-DD}  (one per week, keyed to Monday)
//   This SW reads both to assemble today's session.

const SW_VERSION  = 7;
const PROJECT_ID  = 'gujrat-project-6653d';
const API_KEY     = 'AIzaSyC-0kK1L9wVTDSfiQmBVTw6Ul1_jAKqDKM';
const SCHOOL_ID   = 'demo-school';
const FS_BASE     = `https://firestore.googleapis.com/v1/projects/${PROJECT_ID}/databases/(default)/documents`;

function fsURL(path) {
  return `${FS_BASE}${path}?key=${API_KEY}`;
}

// ── Minimal fallback — used only when Firestore AND all retries fail ──
const FALLBACK = {
  today_session: {
    date: new Date().toISOString().split('T')[0],
    subject: 'Mathematics',
    chapter: 'Fractions',
    day_of_week: 1,
    total_days: 1,
    students: [
      { id: 's001', name: 'Aarav Patel',   level: 'L2', status: 'pending', time_spent_seconds: 0, last_question: '' },
      { id: 's002', name: 'Diya Shah',     level: 'L3', status: 'pending', time_spent_seconds: 0, last_question: '' },
      { id: 's003', name: 'Krish Mehta',   level: 'L1', status: 'pending', time_spent_seconds: 0, last_question: '' },
      { id: 's004', name: 'Ananya Joshi',  level: 'L2', status: 'pending', time_spent_seconds: 0, last_question: '' },
      { id: 's005', name: 'Rohan Desai',   level: 'L4', status: 'pending', time_spent_seconds: 0, last_question: '' },
      { id: 's006', name: 'Priya Trivedi', level: 'L2', status: 'pending', time_spent_seconds: 0, last_question: '' },
      { id: 's007', name: 'Arjun Dave',    level: 'L1', status: 'pending', time_spent_seconds: 0, last_question: '' },
      { id: 's008', name: 'Mira Parmar',   level: 'L3', status: 'pending', time_spent_seconds: 0, last_question: '' },
      { id: 's009', name: 'Dev Gandhi',    level: 'L2', status: 'pending', time_spent_seconds: 0, last_question: '' },
      { id: 's010', name: 'Kavya Raval',   level: 'L2', status: 'pending', time_spent_seconds: 0, last_question: '' },
    ],
  },
  class_sample: {
    grade: 5,
    section: 'B',
    students: [
      { id: 's001', roll_no: 1, name: 'Aarav Patel',   avatar_color: '#E85D55', current_levels: { Mathematics: 2, Science: 2, Language: 1, 'Social Studies': 2 }, flagged_concepts: [], recent_sessions: [] },
      { id: 's002', roll_no: 2, name: 'Diya Shah',     avatar_color: '#4A3FB7', current_levels: { Mathematics: 3, Science: 3, Language: 2, 'Social Studies': 3 }, flagged_concepts: [], recent_sessions: [] },
      { id: 's003', roll_no: 3, name: 'Krish Mehta',   avatar_color: '#1D9E75', current_levels: { Mathematics: 1, Science: 2, Language: 1, 'Social Studies': 1 }, flagged_concepts: [], recent_sessions: [] },
      { id: 's004', roll_no: 4, name: 'Ananya Joshi',  avatar_color: '#EF9F27', current_levels: { Mathematics: 2, Science: 2, Language: 2, 'Social Studies': 2 }, flagged_concepts: [], recent_sessions: [] },
      { id: 's005', roll_no: 5, name: 'Rohan Desai',   avatar_color: '#E85D55', current_levels: { Mathematics: 4, Science: 3, Language: 3, 'Social Studies': 2 }, flagged_concepts: [], recent_sessions: [] },
      { id: 's006', roll_no: 6, name: 'Priya Trivedi', avatar_color: '#4A3FB7', current_levels: { Mathematics: 2, Science: 1, Language: 2, 'Social Studies': 2 }, flagged_concepts: [], recent_sessions: [] },
      { id: 's007', roll_no: 7, name: 'Arjun Dave',    avatar_color: '#1D9E75', current_levels: { Mathematics: 1, Science: 1, Language: 1, 'Social Studies': 1 }, flagged_concepts: [], recent_sessions: [] },
      { id: 's008', roll_no: 8, name: 'Mira Parmar',   avatar_color: '#EF9F27', current_levels: { Mathematics: 3, Science: 3, Language: 4, 'Social Studies': 3 }, flagged_concepts: [], recent_sessions: [] },
      { id: 's009', roll_no: 9, name: 'Dev Gandhi',    avatar_color: '#E85D55', current_levels: { Mathematics: 2, Science: 2, Language: 2, 'Social Studies': 2 }, flagged_concepts: [], recent_sessions: [] },
      { id: 's010', roll_no:10, name: 'Kavya Raval',   avatar_color: '#4A3FB7', current_levels: { Mathematics: 2, Science: 2, Language: 2, 'Social Studies': 2 }, flagged_concepts: [], recent_sessions: [] },
    ],
  },
  dialogue: [
    { stage: 'greeting', text: "Hi! Today we're going to talk about Mathematics. Ready?" },
    { stage: 'question', text: 'What is half of 10?' },
    { stage: 'closing',  text: 'Excellent work on Mathematics today! See you next session.' },
  ],
};

self.addEventListener('install',  () => self.skipWaiting());
self.addEventListener('activate', e => e.waitUntil(clients.claim()));

self.addEventListener('fetch', e => {
  const url = e.request.url;
  if (url.includes('today_session.json'))              { e.respondWith(handleTodaySession());  return; }
  if (url.includes('simulated_session_dialogue.json')) { e.respondWith(handleDialogue());      return; }
  if (url.includes('class_sample.json'))               { e.respondWith(handleClassSample());   return; }
});

// ── TODAY SESSION ──
async function handleTodaySession() {
  try {
    const session = await fetchSession();

    const students = session.students.length > 0
      ? session.students.map(s => ({
          id:                 s.id     || s.rollNo || 'unknown',
          name:               s.name   || 'Student',
          level:              s.level  || 'L1',
          status:             s.status || 'pending',
          time_spent_seconds: s.time_spent_seconds || 0,
          last_question:      s.last_question      || '',
        }))
      : FALLBACK.today_session.students;

    const result = {
      date:        session.todayStr,
      subject:     session.subject,
      chapter:     session.chapter,
      day_of_week: session.dayOfWeek,
      total_days:  1,
      students,
    };

    broadcastStatus({ source: 'firestore', count: students.length, subject: result.subject });
    return jsonResponse(result);

  } catch (err) {
    console.warn('[MikoBridge] today_session → fallback:', err.message);
    broadcastStatus({ source: 'fallback', count: FALLBACK.today_session.students.length, error: err.message });
    return jsonResponse({ ...FALLBACK.today_session, date: new Date().toISOString().split('T')[0] });
  }
}

// ── DIALOGUE ──
async function handleDialogue() {
  try {
    const session = await fetchSession();
    const subject = session.subject || 'Mathematics';
    const chapter = session.chapter ? ` — ${session.chapter}` : '';
    return jsonResponse(FALLBACK.dialogue.map(step => {
      if (step.stage === 'greeting') return { ...step, text: `Hi! Today we're going to talk about ${subject}${chapter}. Ready?` };
      if (step.stage === 'closing')  return { ...step, text: `Excellent work on ${subject} today! See you next session.` };
      return step;
    }));
  } catch {
    return jsonResponse(FALLBACK.dialogue);
  }
}

// ── CLASS SAMPLE ──
async function handleClassSample() {
  try {
    const session = await fetchSession();
    if (!session.students.length) throw new Error('No students in session');

    const COLORS = ['#E85D55', '#4A3FB7', '#1D9E75', '#EF9F27'];
    const students = session.students.map((s, i) => ({
      id:           s.id     || `s${String(i + 1).padStart(3, '0')}`,
      roll_no:      s.rollNo || (i + 1),
      name:         s.name   || `Student ${i + 1}`,
      avatar_color: COLORS[i % COLORS.length],
      current_levels: {
        Mathematics:      levelNum(s.level),
        Science:          levelNum(s.level),
        Language:         levelNum(s.level),
        'Social Studies': levelNum(s.level),
      },
      flagged_concepts: [],
      recent_sessions:  [],
    }));

    return jsonResponse({
      ...FALLBACK.class_sample,
      grade:   session.classNum || FALLBACK.class_sample.grade,
      students,
    });

  } catch (err) {
    console.warn('[MikoBridge] class_sample → fallback:', err.message);
    return jsonResponse(FALLBACK.class_sample);
  }
}

// ── CORE: fetch today's session from Firebase ──
//
// Priority:
//   1. sessions/{this-week-monday}  → subject/subjectId/color for current week
//   2. meta/current_session         → subject fallback + full student list
//
// The Scheduler writes both when teacher clicks "Confirm Plan".
async function fetchSession() {
  const now       = new Date();
  const todayStr  = now.toISOString().split('T')[0];
  const mondayStr = getWeekMonday(now);
  const dayOfWeek = now.getDay() || 7; // 1=Mon … 7=Sun

  // Step 1 — try week's session document for today's subject
  let weekSubject   = null;
  let weekSubjectId = null;
  let weekChapter   = null;
  let weekColor     = null;

  try {
    const sessRes = await fetch(fsURL(`/schools/${SCHOOL_ID}/sessions/${mondayStr}`));
    if (sessRes.ok) {
      const sessDoc = await sessRes.json();
      if (sessDoc.fields) {
        const s    = parseDoc(sessDoc);
        weekSubject   = s.subject   || null;
        weekSubjectId = s.subjectId || null;
        weekChapter   = s.chapter   || null;
        weekColor     = s.color     || null;
        console.log('[MikoBridge] sessions doc found for', mondayStr, '→', weekSubject);
      }
    } else {
      console.log('[MikoBridge] No sessions doc for', mondayStr, '(HTTP', sessRes.status, ')');
    }
  } catch (e) {
    console.warn('[MikoBridge] sessions fetch error:', e.message);
  }

  // Step 2 — current_session (always required for students list)
  const csRes = await fetch(fsURL(`/schools/${SCHOOL_ID}/meta/current_session`));
  if (!csRes.ok) throw new Error(`Firestore HTTP ${csRes.status} on current_session`);

  const csDoc  = await csRes.json();
  if (!csDoc.fields) throw new Error('current_session document missing');

  const cs = parseDoc(csDoc);

  const subject = weekSubject || cs.subject;
  if (!subject) throw new Error('No subject in Firebase — confirm the plan in the Scheduler first');

  // students is stored as an arrayValue of mapValues
  const students = parseStudentArray(cs.students);

  return {
    todayStr,
    dayOfWeek,
    subject,
    subjectId: weekSubjectId || cs.subjectId || '',
    chapter:   weekChapter   || cs.chapter   || '',
    color:     weekColor     || cs.color     || '#d97706',
    classNum:  cs.class      || 5,
    mode:      cs.mode       || 'ded',
    students,
  };
}

// ── Parse students — handles both raw array and Firestore arrayValue ──
function parseStudentArray(raw) {
  if (!raw) return [];
  // Already parsed by parseDoc into a JS array
  if (Array.isArray(raw)) return raw;
  // Shouldn't happen, but guard anyway
  return [];
}

// ── Get Monday of the week containing `date` ──
function getWeekMonday(date) {
  const d   = new Date(date);
  const day = d.getDay(); // 0=Sun
  const diff = day === 0 ? -6 : 1 - day;
  d.setDate(d.getDate() + diff);
  return d.toISOString().split('T')[0];
}

// ── Broadcast data-load status to the page ──
function broadcastStatus(payload) {
  self.clients.matchAll({ includeUncontrolled: true, type: 'window' }).then(clients => {
    clients.forEach(c => c.postMessage({ type: 'MIKO_DATA_STATUS', ...payload }));
  });
}

// ── HELPERS ──
function jsonResponse(data) {
  return new Response(JSON.stringify(data), {
    status:  200,
    headers: { 'Content-Type': 'application/json' },
  });
}

function levelNum(levelStr) {
  if (!levelStr) return 1;
  const n = parseInt(String(levelStr).replace(/[Ll]/g, ''), 10);
  return isNaN(n) ? 1 : n;
}

// Parses a Firestore REST document object { fields: { key: value, ... } }
function parseDoc(doc) {
  if (!doc || !doc.fields) return {};
  const result = {};
  for (const [key, val] of Object.entries(doc.fields)) {
    result[key] = parseValue(val);
  }
  return result;
}

// Recursively parses a Firestore REST field value
function parseValue(val) {
  if (!val || typeof val !== 'object') return null;
  if ('stringValue'    in val) return val.stringValue;
  if ('integerValue'   in val) return parseInt(val.integerValue, 10);
  if ('doubleValue'    in val) return val.doubleValue;
  if ('booleanValue'   in val) return val.booleanValue;
  if ('timestampValue' in val) return val.timestampValue;
  if ('nullValue'      in val) return null;
  if ('arrayValue'     in val) return (val.arrayValue.values || []).map(parseValue);
  if ('mapValue'       in val) return parseDoc(val.mapValue);
  return null;
}
