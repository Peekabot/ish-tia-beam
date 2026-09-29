#!/usr/bin/env python3
"""iSH test beam — fake 2600 frame server.
   python3 ish_frame.py
   Pythonista CRT hits http://127.0.0.1:8000/frame
"""
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

WIDTH, HEIGHT = 160, 192
joy = bytearray(b'00000')
lock = threading.Lock()
tick = 0


def paint():
    global tick
    tick += 1
    buf = bytearray(WIDTH * HEIGHT)
    bg = 2
    pf = 6
    p0c = 14
    p1c = 20

    with lock:
        j = bytes(joy)

    px = 40 + (4 if j[3:4] == b'1' else 0) - (4 if j[2:3] == b'1' else 0)
    py = 80 - (3 if j[0:1] == b'1' else 0) + (3 if j[1:2] == b'1' else 0)
    px = max(8, min(140, px + (tick // 2) % 3))
    py = max(20, min(160, py))
    fire = j[4:5] == b'1'

    wall = [0xF0, 0x00, 0x00, 0x00, 0x0F]
    for y in range(HEIGHT):
        row = y * WIDTH
        for x in range(WIDTH):
            buf[row + x] = bg
        if 24 <= y <= 168:
            for i, bits in enumerate(wall):
                for b in range(8):
                    if bits & (0x80 >> b):
                        x0 = (i * 8 + b) * 4
                        for k in range(4):
                            if x0 + k < 80:
                                buf[row + x0 + k] = pf
                                buf[row + (159 - (x0 + k))] = pf

    spr = [
        0b00111100,
        0b01111110,
        0b11111111,
        0b11011011,
        0b11111111,
        0b01111110,
        0b00111100,
        0b00011000,
    ]
    for sy, bits in enumerate(spr):
        yy = py + sy * 2
        if yy >= HEIGHT:
            break
        for b in range(8):
            if bits & (0x80 >> b):
                xx = px + b
                if 0 <= xx < WIDTH:
                    buf[yy * WIDTH + xx] = p0c
                    if yy + 1 < HEIGHT:
                        buf[(yy + 1) * WIDTH + xx] = p0c

    if fire:
        mx = px + 9
        for y in range(py - 20, py):
            if 0 <= y < HEIGHT and 0 <= mx < WIDTH:
                buf[y * WIDTH + mx] = p1c

    yb = tick % HEIGHT
    for x in range(WIDTH):
        buf[yb * WIDTH + x] = 4

    return bytes(buf)


class BeamHandler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    def do_GET(self):
        if self.path.startswith('/frame'):
            body = paint()
            self.send_response(200)
            self.send_header('Content-Type', 'application/octet-stream')
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(body)
            return
        if self.path.startswith('/joy'):
            with lock:
                body = bytes(joy)
            self.send_response(200)
            self.end_headers()
            self.wfile.write(body)
            return
        self.send_response(404)
        self.end_headers()

    def do_POST(self):
        n = int(self.headers.get('Content-Length', '0') or 0)
        data = self.rfile.read(n) if n else b''
        if self.path.startswith('/joy') and len(data) >= 5:
            with lock:
                joy[:5] = data[:5]
        self.send_response(204)
        self.end_headers()


if __name__ == '__main__':
    httpd = HTTPServer(('0.0.0.0', 8000), BeamHandler)
    print('beam on :8000  GET /frame  POST /joy')
    httpd.serve_forever()
