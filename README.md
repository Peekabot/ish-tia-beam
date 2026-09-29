# ish-tia-beam

iSH fake TIA. Serves 160x192 palette-index frames for the Pythonista CRT stub.

```
GET  /frame  -> 30720 bytes
POST /joy    -> 5 bytes UDLRF as ASCII 0/1
```

## iSH

```sh
apk add git python3
git clone https://github.com/Peekabot/ish-tia-beam.git
cd ish-tia-beam
python3 ish_frame.py
```

Leave iSH in the foreground. Pythonista talks to `127.0.0.1:8000`.
