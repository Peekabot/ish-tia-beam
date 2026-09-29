#!/usr/bin/env python3
"""iSH test beam — fake 2600 frame server.
   python3 ish_frame.py
   Pythonista CRT hits http://127.0.0.1:8000/frame
"""
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

WIDTH, HEIGHT = 160, 192
FRAME = WIDTH * HEIGHT
joy = bytearray(b'00000')
lock = threading.Lock()
tick = 0

# prebuild playfield mask (1 = wall)
_pf = bytearray(FRAME)
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
                        _pf[row + x] = 1
                        _pf[row + (159 - x)] = 1

_spr = [
    0b00111100,
    0b01111110,
    0b11111111,
    0b11011011,
    0b11111111,
    0b01111110,
    0b00111100,
    0b00011000,
]


def paint():
    global tick
    tick += 1
    buf = bytearray(_pf)  # 0/1 mask
    # 0 -> bg 2, 1 -> pf 6
    for i, v in enumerate(buf):
        buf[i] = 6 if v else 2

    with lock:
        j = bytes(joy)

    px = 40 + (4 if j[3:4] == b'1' else 0) - (4 if j[2:3] == b'1' else 0)
    py = 80 - (3 if j[0:1] == b'1' else 0) + (3 if j[1:2] == b'1' else 0)
    px = max(8, min(140, px))
    py = max(20, min(160, py))
    fire = j[4:5] == b'1'

    for sy, bits in enumerate(_spr):
        yy = py + sy * 2
        if yy >= HEIGHT:
            break
        for b in range(8):
            if bits & (0x80 >> b):
                xx = px + b
                if 0 <= xx < WIDTH:
                    buf[yy * WIDTH + xx] = 14
                    if yy + 1 < HEIGHT:
                        buf[(yy + 1) * WIDTH + xx] = 14

    if fire:
        mx = px + 9
        y0 = max(0, py - 20)
        for y in range(y0, py):
            if 0 <= mx < WIDTH:
                buf[y * WIDTH + mx] = 20

    yb = tick % HEIGHT
    row = yb * WIDTH
    buf[row:row + WIDTH] = b'\x04' * WIDTH
    return bytes(buf)


class BeamHandler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    def _ok(self, body, code=200):
        try:
            self.send_response(code)
            self.send_header('Content-Type', 'application/octet-stream')
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Connection', 'close')
            self.end_headers()
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            pass

    def do_GET(self):
        if self.path.startswith('/frame'):
            self._ok(paint())
            return
        if self.path.startswith('/joy'):
            with lock:
                body = bytes(joy)
            self._ok(body)
            return
        try:
            self.send_response(404)
            self.end_headers()
        except (BrokenPipeError, ConnectionResetError):
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
        except (BrokenPipeError, ConnectionResetError):
            pass


if __name__ == '__main__':
    httpd = HTTPServer(('0.0.0.0', 8000), BeamHandler)
    print('beam on :8000  GET /frame  POST /joy')
    httpd.serve_forever()
