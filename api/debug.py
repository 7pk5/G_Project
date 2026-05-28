from http.server import BaseHTTPRequestHandler
import json, urllib.request, os, time

PROJECT_ID = os.environ.get('FIREBASE_PROJECT_ID', 'gujrat-project-6653d')
SCHOOL_ID  = os.environ.get('SCHOOL_ID',           'demo-school')
API_KEY    = os.environ.get('FIREBASE_API_KEY',    'AIzaSyC-0kK1L9wVTDSfiQmBVTw6Ul1_jAKqDKM')
FIRESTORE  = f'https://firestore.googleapis.com/v1/projects/{PROJECT_ID}/databases/(default)/documents'


def parse_value(val):
    if 'stringValue'  in val: return val['stringValue']
    if 'integerValue' in val: return int(val['integerValue'])
    if 'doubleValue'  in val: return float(val['doubleValue'])
    if 'booleanValue' in val: return val['booleanValue']
    if 'arrayValue'   in val: return [parse_value(v) for v in val['arrayValue'].get('values', [])]
    if 'mapValue'     in val: return {k: parse_value(v) for k, v in val['mapValue'].get('fields', {}).items()}
    return None


def fetch_session():
    url = f'{FIRESTORE}/schools/{SCHOOL_ID}/meta/current_session?key={API_KEY}'
    with urllib.request.urlopen(url, timeout=4) as r:
        doc = json.loads(r.read())
        return {k: parse_value(v) for k, v in doc.get('fields', {}).items()}


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            session = fetch_session()
            raw = session.get('students', [])
            count = len(raw) if isinstance(raw, list) else 0
            info = {
                'firestore_reachable': True,
                'current_session': {
                    'subject':      session.get('subject'),
                    'chapter':      session.get('chapter'),
                    'class':        session.get('class'),
                    'studentCount': session.get('studentCount', count),
                    'first_3_students': raw[:3] if isinstance(raw, list) else [],
                },
            }
        except Exception as e:
            info = {'firestore_reachable': False, 'error': str(e)}

        data = json.dumps(info, ensure_ascii=False, indent=2).encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type',  'application/json')
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(data)
