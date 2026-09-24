#!/usr/bin/env python3
"""Small self-hosted count API; place it behind HTTPS before configuring clients.

Clients POST a hash derived from their machine ID. The admin count requires a
private token. Rows expire after 30 days without another check-in. This server
binds to loopback by default so a reverse proxy can provide TLS and rate limits.
"""
import hmac
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
import re
import sqlite3
import time
from urllib.parse import urlsplit

DATABASE = os.environ.get('RICE_COUNTER_DB', 'rice-counter.sqlite3')
ADMIN_TOKEN = os.environ.get('RICE_COUNTER_ADMIN_TOKEN', '')
PORT = int(os.environ.get('RICE_COUNTER_PORT', '8765'))
ACTIVE_SECONDS = 30 * 86400


def connect():
    db = sqlite3.connect(DATABASE, timeout=5)
    db.execute('CREATE TABLE IF NOT EXISTS machines (id TEXT PRIMARY KEY, seen INTEGER NOT NULL)')
    return db


class Handler(BaseHTTPRequestHandler):
    def log_message(self, _format, *_args):
        # The count needs only pseudonymous IDs and timestamps, not IP logs.
        pass

    def reply(self, status, body=b'', content_type='application/json'):
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        if self.path != '/check-in':
            return self.reply(404)
        try:
            size = int(self.headers.get('Content-Length', '0'))
            if not 0 < size <= 256:
                return self.reply(400)
            value = json.loads(self.rfile.read(size))
            identifier = value.get('id', '')
            if not isinstance(identifier, str) or not re.fullmatch('[0-9a-f]{64}', identifier):
                return self.reply(400)
            now = int(time.time())
            with connect() as db:
                db.execute('INSERT INTO machines (id, seen) VALUES (?, ?) '
                           'ON CONFLICT(id) DO UPDATE SET seen=excluded.seen', (identifier, now))
                db.execute('DELETE FROM machines WHERE seen < ?', (now - ACTIVE_SECONDS,))
            return self.reply(204)
        except (OSError, ValueError, sqlite3.Error):
            return self.reply(500)

    def do_GET(self):
        parsed = urlsplit(self.path)
        if parsed.path != '/count':
            return self.reply(404)
        supplied = self.headers.get('Authorization', '').removeprefix('Bearer ').strip()
        if not ADMIN_TOKEN or not hmac.compare_digest(supplied, ADMIN_TOKEN):
            return self.reply(403)
        try:
            now = int(time.time())
            with connect() as db:
                db.execute('DELETE FROM machines WHERE seen < ?', (now - ACTIVE_SECONDS,))
                count = db.execute('SELECT COUNT(*) FROM machines').fetchone()[0]
            return self.reply(200, json.dumps({'active_machines': count,
                                              'window_days': 30,
                                              'at': now}).encode())
        except sqlite3.Error:
            return self.reply(500)


def main():
    if not ADMIN_TOKEN:
        raise SystemExit('Set RICE_COUNTER_ADMIN_TOKEN before starting the server')
    ThreadingHTTPServer(('127.0.0.1', PORT), Handler).serve_forever()


if __name__ == '__main__':
    main()
