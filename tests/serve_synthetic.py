#!/usr/bin/env python3
"""합성 자료만 메모리에서 제공하는 로컬 UI 검증 서버. 실제 data.enc는 열지 않는다."""
import base64
import json
import os
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes

PASSWORD = 'synthetic-test-only'
ROOT = Path(__file__).resolve().parent.parent
salt, iv = os.urandom(16), os.urandom(12)
key = PBKDF2HMAC(hashes.SHA256(), 32, salt, 600000).derive(PASSWORD.encode())
plain = {'places': [{'id': 'synthetic-1', 'name': '합성 테스트 식당', 'status': '가 봄',
                    'kind': '테스트', 'minutes': 30, 'area': '합성 지역', 'menu': '테스트 메뉴',
                    'note': '합성 메모', 'date': '2026-01-01', 'link': '',
                    'lat': 37.5, 'lon': 127.0, 'photos': []}]}
enc = {'v': 1, 'iter': 600000, 'salt': base64.b64encode(salt).decode(),
       'iv': base64.b64encode(iv).decode(),
       'ct': base64.b64encode(AESGCM(key).encrypt(iv, json.dumps(plain).encode(), None)).decode()}

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path in ('/', '/index.html'):
            data, mime = (ROOT / 'index.html').read_bytes(), 'text/html; charset=utf-8'
        elif self.path == '/data.enc':
            data, mime = json.dumps(enc).encode(), 'application/json'
        else:
            self.send_error(404)
            return
        self.send_response(200)
        self.send_header('Content-Type', mime)
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(data)

if __name__ == '__main__':
    print('합성 UI: http://127.0.0.1:18743 / 비밀번호: ' + PASSWORD, flush=True)
    HTTPServer(('127.0.0.1', 18743), Handler).serve_forever()
