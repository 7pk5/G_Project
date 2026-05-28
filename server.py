#!/usr/bin/env python3
"""
Miko Web Portal Server
  /setup      →  setup.html
  /schedular  →  Schedular HTML
  /student    →  Flutter web app with live Firestore data injected
"""

import http.server
import socketserver
import mimetypes
import json
import time
import urllib.request
from pathlib import Path

PORT     = 8080
BASE_DIR = Path(__file__).parent

# ── Firebase ──
PROJECT_ID = 'gujrat-project-6653d'
SCHOOL_ID  = 'demo-school'
API_KEY    = 'AIzaSyC-0kK1L9wVTDSfiQmBVTw6Ul1_jAKqDKM'
FIRESTORE  = f'https://firestore.googleapis.com/v1/projects/{PROJECT_ID}/databases/(default)/documents'

MIME = {
    '.html': 'text/html; charset=utf-8',
    '.js':   'application/javascript',
    '.mjs':  'application/javascript',
    '.json': 'application/json',
    '.wasm': 'application/wasm',
    '.css':  'text/css',
    '.png':  'image/png',
    '.ico':  'image/x-icon',
    '.m4a':  'audio/mp4',
    '.ttf':  'font/ttf',
    '.otf':  'font/otf',
    '.bin':  'application/octet-stream',
    '.map':  'application/json',
}

ASSET_EXTS = {'.js', '.wasm', '.png', '.json', '.css', '.ttf',
              '.otf', '.m4a', '.bin', '.map', '.ico', '.mjs'}

# ── Firestore helpers ──

_cache = {'session': None, 'ts': 0}

def parse_value(val):
    if 'stringValue'    in val: return val['stringValue']
    if 'integerValue'   in val: return int(val['integerValue'])
    if 'doubleValue'    in val: return float(val['doubleValue'])
    if 'booleanValue'   in val: return val['booleanValue']
    if 'timestampValue' in val: return val['timestampValue']
    if 'arrayValue'     in val: return [parse_value(v) for v in val['arrayValue'].get('values', [])]
    if 'mapValue'       in val: return parse_doc(val['mapValue'])
    return None

def parse_doc(doc):
    return {k: parse_value(v) for k, v in doc.get('fields', {}).items()}

def fetch_session():
    """Fetch current_session from Firestore. Cached for 30s."""
    now = time.time()
    if now - _cache['ts'] < 30 and _cache['session']:
        return _cache['session']
    try:
        url = f'{FIRESTORE}/schools/{SCHOOL_ID}/meta/current_session?key={API_KEY}'
        with urllib.request.urlopen(url, timeout=4) as r:
            doc  = json.loads(r.read())
            data = parse_doc(doc)
            _cache['session'] = data
            _cache['ts']      = now
            print(f'  [Firestore] Loaded session → subject: {data.get("subject")} · students: {len(data.get("students", []))}')
            return data
    except Exception as e:
        print(f'  [Firestore] Could not fetch session: {e}')
        return None


# ── Request handler ──

class MikoHandler(http.server.BaseHTTPRequestHandler):

    def do_GET(self):
        path = self.path.split('?')[0]

        if path in ('/', ''):
            self.redirect('/student/')

        elif path == '/student':
            self.redirect('/student/')

        elif path in ('/setup', '/setup/'):
            self.serve_file(BASE_DIR / 'setup.html')

        elif path in ('/schedular', '/schedular/'):
            self.serve_file(BASE_DIR / 'Schedular' / 'assessment-planner-school.html')

        elif path in ('/today', '/today/'):
            self.serve_file(BASE_DIR / 'student' / 'today.html')

        elif path in ('/app', '/app/'):
            self.serve_file(BASE_DIR / 'student' / 'app.html')

        elif path in ('/debug', '/debug/'):
            self.serve_debug()

        elif 'today_session.json' in path:
            self.serve_today_session()

        elif 'simulated_session_dialogue.json' in path:
            self.serve_dialogue()

        elif 'class_sample.json' in path:
            self.serve_class_sample()

        elif path.startswith('/student'):
            rel = path[len('/student'):].lstrip('/')
            self.serve_file(BASE_DIR / 'student' / rel if rel else BASE_DIR / 'student' / 'index.html')

        else:
            self.send_error(404)

    # ── Dynamic JSON endpoints ──

    def serve_today_session(self):
        mock_path = (BASE_DIR / 'student' / 'assets' / 'packages' /
                     'shared_core' / 'assets' / 'mock' / 'today_session.json')
        mock = json.loads(mock_path.read_text())

        # Always show every student — never let Flutter slice by day_of_week/total_days
        mock['total_days']  = 1
        mock['day_of_week'] = 1

        session = fetch_session()
        if session:
            mock['subject'] = session.get('subject', mock.get('subject'))
            mock['chapter'] = session.get('chapter', mock.get('chapter', ''))

            raw_students = session.get('students', [])
            student_count = session.get('studentCount', 0)

            if isinstance(raw_students, list) and len(raw_students) > 0:
                mock['students'] = [
                    {
                        'id':                 str(s.get('id', f's{i+1:03d}')),
                        'name':               s.get('name', f'Student {i+1}'),
                        'level':              s.get('level', 'L1'),
                        'status':             'pending',
                        'time_spent_seconds': 0,
                        'last_question':      ''
                    }
                    for i, s in enumerate(raw_students)
                ]
            elif student_count > 0:
                # Firestore session exists but students array is empty — generate placeholders
                mock['students'] = [
                    {
                        'id':                 f's{i+1:03d}',
                        'name':               f'Student {i+1}',
                        'level':              'L1',
                        'status':             'pending',
                        'time_spent_seconds': 0,
                        'last_question':      ''
                    }
                    for i in range(student_count)
                ]

        self.send_json(mock)

    def serve_dialogue(self):
        mock_path = (BASE_DIR / 'student' / 'assets' / 'packages' /
                     'shared_core' / 'assets' / 'mock' / 'simulated_session_dialogue.json')
        dialogue = json.loads(mock_path.read_text())

        session = fetch_session()
        if session:
            subject = session.get('subject', 'Mathematics')
            for step in dialogue:
                if step.get('stage') == 'greeting':
                    step['text'] = f"Hi! Today we're going to talk about {subject}. Ready?"
                elif step.get('stage') == 'closing':
                    step['text'] = f"Excellent work on {subject} today! See you next session."

        self.send_json(dialogue)

    def serve_class_sample(self):
        mock_path = (BASE_DIR / 'student' / 'assets' / 'packages' /
                     'shared_core' / 'assets' / 'mock' / 'class_sample.json')
        mock = json.loads(mock_path.read_text())

        session = fetch_session()
        if session:
            raw_students = session.get('students', [])
            if isinstance(raw_students, list) and len(raw_students) > 0:
                COLORS = ['#E85D55', '#4A3FB7', '#1D9E75', '#EF9F27']
                mock['grade'] = session.get('class', mock.get('grade', 5))
                mock['students'] = []
                for i, s in enumerate(raw_students):
                    lvl_str = s.get('level', 'L1')
                    try:
                        lvl = int(str(lvl_str).replace('L', ''))
                    except (ValueError, AttributeError):
                        lvl = 1
                    mock['students'].append({
                        'id':           str(s.get('id', f's{i+1:03d}')),
                        'roll_no':      s.get('rollNo', i + 1),
                        'name':         s.get('name', f'Student {i+1}'),
                        'avatar_color': COLORS[i % len(COLORS)],
                        'current_levels': {
                            'Mathematics':    lvl,
                            'Science':        lvl,
                            'Language':       lvl,
                            'Social Studies': lvl,
                        },
                        'flagged_concepts': [],
                        'recent_sessions':  [],
                    })

        self.send_json(mock)

    def serve_debug(self):
        session = fetch_session()
        mock_path = (BASE_DIR / 'student' / 'assets' / 'packages' /
                     'shared_core' / 'assets' / 'mock' / 'today_session.json')
        mock = json.loads(mock_path.read_text())

        if session:
            raw = session.get('students', [])
            student_count = session.get('studentCount', 0)
            students_in_session = len(raw) if isinstance(raw, list) else 0
        else:
            raw = []
            student_count = 0
            students_in_session = 0

        info = {
            'firestore_reachable': session is not None,
            'current_session': {
                'subject':        session.get('subject')      if session else None,
                'chapter':        session.get('chapter')      if session else None,
                'class':          session.get('class')        if session else None,
                'studentCount':   student_count,
                'students_in_session': students_in_session,
                'first_3_students': (raw[:3] if isinstance(raw, list) else []),
            } if session else None,
            'mock_fallback_student_count': len(mock.get('students', [])),
            'what_flutter_gets': {
                'students': students_in_session if session and students_in_session > 0
                            else (student_count if session and student_count > 0
                            else len(mock.get('students', []))),
                'source': 'firestore' if (session and students_in_session > 0) else
                          ('firestore_generated' if (session and student_count > 0) else 'mock'),
            }
        }
        data = json.dumps(info, ensure_ascii=False, indent=2).encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(data)

    # ── Static file serving ──

    def serve_file(self, full_path):
        full_path = Path(full_path)
        if full_path.is_dir():
            full_path = full_path / 'index.html'
        if not full_path.exists():
            self.send_error(404, f'Not found: {full_path.name}')
            return
        mime = MIME.get(full_path.suffix.lower()) \
               or mimetypes.guess_type(str(full_path))[0] \
               or 'application/octet-stream'
        data = full_path.read_bytes()
        self.send_response(200)
        self.send_header('Content-Type', mime)
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Service-Worker-Allowed', '/')
        # Never cache the service worker itself so updates take effect immediately
        if full_path.name == 'miko-bridge-sw.js':
            self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate')
        self.end_headers()
        self.wfile.write(data)

    def send_json(self, obj):
        data = json.dumps(obj, ensure_ascii=False).encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(data)

    def redirect(self, location):
        self.send_response(302)
        self.send_header('Location', location)
        self.end_headers()

    def log_message(self, fmt, *args):
        # args[0] is a request line string only for normal requests;
        # for send_error() calls it can be a format string or an int — skip those
        if not args or not isinstance(args[0], str) or not args[0].startswith(('GET', 'POST', 'PUT', 'DELETE', 'HEAD', 'OPTIONS')):
            return
        parts  = args[0].split()
        path   = parts[1] if len(parts) > 1 else args[0]
        status = args[1] if len(args) > 1 else '-'
        if Path(path).suffix.lower() in ASSET_EXTS:
            return
        print(f'  [{status}]  {path}')


socketserver.TCPServer.allow_reuse_address = True

if __name__ == '__main__':
    with socketserver.TCPServer(('', PORT), MikoHandler) as httpd:
        print(f'\n  Miko Web Portal')
        print(f'  ────────────────────────────────────')
        print(f'  Setup      →  http://localhost:{PORT}/setup')
        print(f'  Schedular  →  http://localhost:{PORT}/schedular')
        print(f'  App        →  http://localhost:{PORT}/app')
        print(f'  Today      →  http://localhost:{PORT}/today')
        print(f'  Student    →  http://localhost:{PORT}/student/')
        print(f'  Debug      →  http://localhost:{PORT}/debug')
        print(f'  ────────────────────────────────────')
        print(f'  Press Ctrl+C to stop\n')
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print('\n  Server stopped.')
