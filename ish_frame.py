#!/usr/bin/env python3
"""iSH test beam — fake 2600 frame server."""
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

WIDTH, HEIGHT = 160, 192
FRAME = WIDTH * HEIGHT
BG, PF, P0, P1, BAR = 2, 6, 14, 20, 4

joy = bytearray(b'00000')
lock = threading.Lock()
tick = 0

_base = bytearray([BG]) * FRAME
_wall = [0xF0, 0x00, 0x00, 0x00, 0x0F]
for y in range(24, 169):
    row = y * WIDTH
    for i, bits in enumerate(_wall):
        for b in range(8):
            if bits & (0x80 >> b):
                x0 = (i * 8 + b) * 4
                for k in range(4):
                    x = x0 + k
                    if x < 80:
                        _base[row + x] = PF
                        _base[row + (159 - x)] = PF

_spr = (
    0b00111100,
    0b01111110,
    0b11111111,
    0b11011011,
    0b11111111,
    0b01111110,
    0b00111100,
    0b00011000,
)


def paint():
    global tick
    tick += 1
    buf = bytearray(_base)

    with lock:
        j = joy[:]

    px = 40 + (4 if j[3] == 49 else 0) - (4 if j[2] == 49 else 0)
    py = 80 - (3 if j[0] == 49 else 0) + (3 if j[1] == 49 else 0)
    px = 8 if px < 8 else (140 if px > 140 else px)
    py = 20 if py < 20 else (160 if py > 160 else py)
    fire = j[4] == 49

    for sy, bits in enumerate(_spr):
        yy = py + sy * 2
        if yy >= HEIGHT:
            break
        row = yy * WIDTH
        row2 = row + WIDTH
        for b in range(8):
            if bits & (0x80 >> b):
                xx = px + b
                buf[row + xx] = P0
                if yy + 1 < HEIGHT:
                    buf[row2 + xx] = P0

    if fire:
        mx = px + 9
        if 0 <= mx < WIDTH:
            y0 = py - 20
            if y0 < 0:
                y0 = 0
            for y in range(y0, py):
                buf[y * WIDTH + mx] = P1

    row = (tick % HEIGHT) * WIDTH
    buf[row:row + WIDTH] = bytes([BAR]) * WIDTH
    return bytes(buf)


class BeamHandler(BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.0'

    def log_message(self, fmt, *args):
        pass

    def _ok(self, body):
        try:
            self.send_response(200)
            self.send_header('Content-Type', 'application/octet-stream')
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Connection', 'close')
            self.end_headers()
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError, OSError):
            pass

    def do_GET(self):
        if self.path.startswith('/frame'):
            self._ok(paint())
        elif self.path.startswith('/joy'):
            with lock:
                self._ok(bytes(joy))
        else:
            try:
                self.send_error(404)
            except (BrokenPipeError, ConnectionResetError, OSError):
                pass

    def do_POST(self):
        n = int(self.headers.get('Content-Length', '0') or 0)
        data = self.rfile.read(n) if n else b''
        if self.path.startswith('/joy') and len(data) >= 5:
            with lock:
                joy[:5] = data[:5]
        try:
            self.send_response(204)
            self.send_header('Content-Length', '0')
            self.end_headers()
        except (BrokenPipeError, ConnectionResetError, OSError):
            pass


if __name__ == '__main__':
    httpd = HTTPServer(('0.0.0.0', 8000), BeamHandler)
    print('beam on :8000  GET /frame  POST /joy')
    httpd.serve_forever()
