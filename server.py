import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

clients = set()
lock = threading.Lock()


def serialize_count():
    with lock:
        return len(clients)


def broadcast_count():
    payload = json.dumps({"count": serialize_count()}).encode("utf-8")
    message = b"data: " + payload + b"\n\n"

    dead_clients = set()
    for client in list(clients):
        try:
            client.wfile.write(message)
            client.wfile.flush()
        except (BrokenPipeError, ConnectionResetError, OSError):
            dead_clients.add(client)

    if dead_clients:
        with lock:
            for dead_client in dead_clients:
                clients.discard(dead_client)


class CounterHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/online-count':
            self._send_json({"count": serialize_count()})
            return

        if self.path == '/online-events':
            self._sse_stream()
            return

        if self.path in ('/', '/index.html'):
            with open('index.html', 'rb') as f:
                content = f.read()
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(content)
            return

        if self.path.endswith('.js'):
            with open(self.path.lstrip('/'), 'rb') as f:
                content = f.read()
            self.send_response(200)
            self.send_header('Content-Type', 'application/javascript; charset=utf-8')
            self.end_headers()
            self.wfile.write(content)
            return

        if self.path.endswith('.css'):
            with open(self.path.lstrip('/'), 'rb') as f:
                content = f.read()
            self.send_response(200)
            self.send_header('Content-Type', 'text/css; charset=utf-8')
            self.end_headers()
            self.wfile.write(content)
            return

        if self.path.endswith(('.png', '.jpg', '.jpeg', '.gif', '.svg')):
            try:
                with open(self.path.lstrip('/'), 'rb') as f:
                    content = f.read()
                self.send_response(200)
                self.send_header('Content-Type', 'image/png' if self.path.endswith('.png') else 'image/jpeg')
                self.end_headers()
                self.wfile.write(content)
                return
            except FileNotFoundError:
                pass

        self.send_response(404)
        self.end_headers()

    def _send_json(self, payload):
        body = json.dumps(payload).encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _sse_stream(self):
        self.send_response(200)
        self.send_header('Content-Type', 'text/event-stream')
        self.send_header('Cache-Control', 'no-cache, no-transform')
        self.send_header('Connection', 'keep-alive')
        self.end_headers()

        with lock:
            clients.add(self)

        try:
            broadcast_count()
            while True:
                time.sleep(20)
                self.wfile.write(b': ping\n\n')
                self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError, OSError):
            pass
        finally:
            with lock:
                clients.discard(self)
            broadcast_count()

    def log_message(self, format, *args):
        return


if __name__ == '__main__':
    server = ThreadingHTTPServer(('0.0.0.0', 8000), CounterHandler)
    print('Live counter server running on http://localhost:8000')
    server.serve_forever()
