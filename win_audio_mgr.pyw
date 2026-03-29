import http.server, json, threading, ctypes, time, os, webbrowser, random

user32 = ctypes.windll.user32

# --- Mouse event flags ---
ME_LEFTDOWN   = 0x0002;  ME_LEFTUP   = 0x0004
ME_RIGHTDOWN  = 0x0008;  ME_RIGHTUP  = 0x0010
ME_MIDDLEDOWN = 0x0020;  ME_MIDDLEUP = 0x0040

# --- Virtual-key code table ---
VK = {}
for i in range(26): VK[chr(65 + i)] = 65 + i
for i in range(10): VK[str(i)] = 48 + i
for i in range(12): VK[f'F{i+1}'] = 0x70 + i
for i in range(10): VK[f'NUMPAD{i}'] = 0x60 + i
VK.update({
    'SPACE': 0x20, 'ENTER': 0x0D, 'TAB': 0x09, 'ESC': 0x1B,
    'BACKSPACE': 0x08, 'DELETE': 0x2E, 'INSERT': 0x2D,
    'HOME': 0x24, 'END': 0x23, 'PAGEUP': 0x21, 'PAGEDOWN': 0x22,
    'UP': 0x26, 'DOWN': 0x28, 'LEFT': 0x25, 'RIGHT': 0x27,
    'SHIFT': 0x10, 'CTRL': 0x11, 'ALT': 0x12,
    'CAPSLOCK': 0x14, 'NUMLOCK': 0x90, 'SCROLLLOCK': 0x91,
    'SEMICOLON': 0xBA, 'EQUALS': 0xBB, 'COMMA': 0xBC,
    'MINUS': 0xBD, 'PERIOD': 0xBE, 'SLASH': 0xBF,
    'BACKTICK': 0xC0, 'BRACKETLEFT': 0xDB, 'BACKSLASH': 0xDC,
    'BRACKETRIGHT': 0xDD, 'QUOTE': 0xDE,
})

PORT = 47391
HTML_FILE = 'dash.html'

class Clicker:
    def __init__(self):
        self.running = False
        self.cps = 10
        self.button = 'left'
        self.double = False
        self.hotkey = 'F6'
        self.mode = 'toggle'
        self.humanize = 50
        self.clicks = 0
        self._lock = threading.Lock()
        self._thread = None

    def _flags(self):
        if self.button == 'right':  return ME_RIGHTDOWN, ME_RIGHTUP
        if self.button == 'middle': return ME_MIDDLEDOWN, ME_MIDDLEUP
        return ME_LEFTDOWN, ME_LEFTUP

    def _do_click(self):
        d, u = self._flags()
        h = self.humanize / 100.0
        hold = random.uniform(0.02, 0.025 + h * 0.095) if h > 0 else 0
        user32.mouse_event(d, 0, 0, 0, 0)
        if hold: time.sleep(hold)
        user32.mouse_event(u, 0, 0, 0, 0)
        if self.double:
            gap = random.uniform(0.03, 0.04 + h * 0.06) if h > 0 else 0.005
            time.sleep(gap)
            hold2 = hold * random.uniform(0.7, 1.3) if h > 0 else 0
            user32.mouse_event(d, 0, 0, 0, 0)
            if hold2: time.sleep(hold2)
            user32.mouse_event(u, 0, 0, 0, 0)

    def _loop(self):
        while self.running:
            self._do_click()
            with self._lock:
                self.clicks += 1
            base = 1.0 / self.cps
            h = self.humanize / 100.0
            if h > 0:
                jitter = random.gauss(0, h * 0.28) * base
                wait = base + jitter
                if random.random() < h * 0.07:
                    wait += random.uniform(0.05, 0.12 + h * 0.38)
                elif random.random() < h * 0.05:
                    wait *= random.uniform(0.45, 0.7)
                time.sleep(max(0.004, wait))
            else:
                time.sleep(base)

    def start(self):
        if self.running: return
        self.running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        self.running = False

    def toggle(self):
        (self.stop if self.running else self.start)()

    def configure(self, **kw):
        was_running = self.running
        if was_running: self.stop(); time.sleep(0.03)
        if 'cps'      in kw: self.cps      = max(1, min(200, int(kw['cps'])))
        if 'button'    in kw: self.button    = kw['button']
        if 'double'    in kw: self.double    = bool(kw['double'])
        if 'hotkey'    in kw: self.hotkey    = str(kw['hotkey']).upper()
        if 'mode'      in kw: self.mode      = kw['mode']
        if 'humanize'  in kw: self.humanize  = max(0, min(100, int(kw['humanize'])))
        if was_running: self.start()

    def reset(self):
        self.stop()
        with self._lock: self.clicks = 0

    def status(self):
        with self._lock: c = self.clicks
        return dict(running=self.running, cps=self.cps, button=self.button,
                    double=self.double, hotkey=self.hotkey, mode=self.mode,
                    humanize=self.humanize, totalClicks=c)

clicker = Clicker()

def hotkey_listener():
    prev = False
    last_key = None
    while True:
        key = clicker.hotkey.upper()
        vk = VK.get(key)
        if vk is None:
            time.sleep(0.05); continue
        if key != last_key:
            prev = False
            last_key = key
        pressed = (user32.GetAsyncKeyState(vk) & 0x8000) != 0
        if clicker.mode == 'toggle':
            if pressed and not prev: clicker.toggle()
        else:
            if pressed and not prev: clicker.start()
            elif not pressed and prev: clicker.stop()
        prev = pressed
        time.sleep(0.015)

threading.Thread(target=hotkey_listener, daemon=True).start()

HERE = os.path.dirname(os.path.abspath(__file__))

class H(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a): pass

    def _cors(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET,POST,OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')

    def _json(self, obj, code=200):
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self._cors(); self.end_headers()
        self.wfile.write(json.dumps(obj).encode())

    def do_OPTIONS(self):
        self.send_response(200); self._cors(); self.end_headers()

    def do_GET(self):
        if self.path in ('/', '/index.html'):
            p = os.path.join(HERE, HTML_FILE)
            try:
                with open(p, 'rb') as f: data = f.read()
                self.send_response(200)
                self.send_header('Content-Type', 'text/html; charset=utf-8')
                self.end_headers(); self.wfile.write(data)
            except FileNotFoundError:
                self.send_response(404); self.end_headers()
        elif self.path == '/api/status':
            self._json(clicker.status())
        elif self.path == '/api/kill':
            self._json({'status': 'bye'})
            threading.Thread(target=lambda: (time.sleep(0.3), os._exit(0)), daemon=True).start()
        else:
            self.send_response(404); self.end_headers()

    def do_POST(self):
        n = int(self.headers.get('Content-Length', 0))
        body = json.loads(self.rfile.read(n)) if n else {}
        route = {
            '/api/start':     lambda: clicker.start(),
            '/api/stop':      lambda: clicker.stop(),
            '/api/toggle':    lambda: clicker.toggle(),
            '/api/configure': lambda: clicker.configure(**body),
            '/api/reset':     lambda: clicker.reset(),
        }
        fn = route.get(self.path)
        if fn:
            fn()
            self._json(clicker.status())
        else:
            self.send_response(404); self.end_headers()

srv = http.server.HTTPServer(('127.0.0.1', PORT), H)
webbrowser.open(f'http://localhost:{PORT}')
srv.serve_forever()
