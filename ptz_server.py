"""
PTZ Camera WebSocket Server — IP/LAN verze
Přeposílá příkazy z HTML aplikace na IP kamery přes HTTP CGI.
"""

import asyncio
import json
import threading
import urllib.request
import urllib.error
import base64
import websockets
import os
import sys
import webbrowser
import subprocess
import http.server
import socketserver

WS_PORT  = 8765

# CORS proxy pro WHEP handshake (video náhled). MediaMTX 1.20 nevrací CORS hlavičky
# na preflight OPTIONS, takže přímý fetch z file:// (Origin: null) padá na CORS.
# Appka proto posílá SDP handshake sem, proxy ho přepošle na MediaMTX (server↔server,
# bez CORS) a doplní Access-Control-* hlavičky. Video pak teče WebRTC/UDP napřímo.
WHEP_PROXY_PORT       = 8890
MEDIAMTX_WEBRTC_HOST  = '127.0.0.1'
MEDIAMTX_WEBRTC_PORT  = 8889

# Složka kde se hledá HTML soubor — stejná jako ptz_server.py
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MEDIAMTX_EXE  = os.path.join(BASE_DIR, 'mediamtx.exe')
MEDIAMTX_CONF = os.path.join(BASE_DIR, 'mediamtx.yml')

# Globální proces MediaMTX
_mediamtx_proc = None
_mediamtx_lock = threading.Lock()

def _write_mediamtx_conf(rtsp_url: str, stream_name: str = 'cam2'):
    """Zapíše mediamtx.yml s danou RTSP URL."""
    conf = f"""# Auto-generovaný konfig — upravený přes PTZ appku
logLevel: error
logDestinations: [stdout]

rtspAddress: :8554
webrtcAddress: :8889

webrtcAllowOrigin: '*'

paths:
  {stream_name}:
    source: {rtsp_url}
"""
    with open(MEDIAMTX_CONF, 'w', encoding='utf-8') as f:
        f.write(conf)

def _start_mediamtx():
    """Spustí proces MediaMTX."""
    global _mediamtx_proc
    if not os.path.exists(MEDIAMTX_EXE):
        return False, 'mediamtx.exe nenalezen v ' + BASE_DIR
    try:
        _mediamtx_proc = subprocess.Popen(
            [MEDIAMTX_EXE, MEDIAMTX_CONF],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0,
        )
        return True, 'OK'
    except Exception as e:
        return False, str(e)

def _stop_mediamtx():
    """Zastaví proces MediaMTX."""
    global _mediamtx_proc
    if _mediamtx_proc and _mediamtx_proc.poll() is None:
        _mediamtx_proc.terminate()
        try: _mediamtx_proc.wait(timeout=3)
        except: _mediamtx_proc.kill()
    _mediamtx_proc = None

def _restart_mediamtx(rtsp_url: str, stream_name: str = 'cam2'):
    """Přepíše konfig a restartuje MediaMTX."""
    with _mediamtx_lock:
        _stop_mediamtx()
        _write_mediamtx_conf(rtsp_url, stream_name)
        ok, msg = _start_mediamtx()
        return ok, msg

cameras = {
    1: { 'ip': '', 'user': 'admin', 'password': 'admin', 'speed': 5 },
    2: { 'ip': '', 'user': 'admin', 'password': 'admin', 'speed': 5 },
}

connected_clients = set()

# Každá kamera musí dostávat PTZ příkazy striktně v pořadí, v jakém byly odeslány —
# jinak se např. "stop" poslaný krátce po "move" může na síti předběhnout a kamera
# pak pokračuje v pohybu, dokud nepřijde další příkaz (nekonečný pohyb po puštění šipky).
cam_locks = {1: asyncio.Lock(), 2: asyncio.Lock()}

def cgi_request(ip, user, password, path):
    url = f'http://{ip}{path}'
    req = urllib.request.Request(url)
    credentials = base64.b64encode(f'{user}:{password}'.encode()).decode()
    req.add_header('Authorization', f'Basic {credentials}')
    try:
        with urllib.request.urlopen(req, timeout=3) as resp:
            return True, resp.read().decode('utf-8', errors='ignore')
    except urllib.error.HTTPError as e:
        return False, f'HTTP {e.code}: {e.reason}'
    except urllib.error.URLError as e:
        return False, f'URL chyba: {e.reason}'
    except Exception as e:
        return False, str(e)

def build_cgi_path(cmd, speed=5, preset=None):
    base = '/cgi-bin/ptzctrl.cgi'
    s = speed
    # Pohyb — /cgi-bin/ptzctrl.cgi?ptzcmd&<směr>&<rychlost>
    move_map = {
        'up':        'up',
        'down':      'down',
        'left':      'left',
        'right':     'right',
        'ul':        'leftup',
        'ur':        'rightup',
        'dl':        'leftdown',
        'dr':        'rightdown',
        'stop':      'ptzstop',   # pan/tilt stop je 'ptzstop' (konvence PTZOptics/VHD), ne 'stop' — ověřeno stop_test.py
        'zoomin':    'zoomin',
        'zoomout':   'zoomout',
        'zoomstop':  'zoomstop',
        'focusfar':  'focusfar',
        'focusnear': 'focusnear',
        'focusstop': 'focusstop',
        'autofocus': 'focusauto',
        'focuslock': 'focuslock',
    }
    if cmd in move_map:
        if cmd in ('stop', 'zoomstop', 'focusstop', 'focusauto', 'focuslock'):
            return f'{base}?ptzcmd&{move_map[cmd]}'  # stop bez rychlosti
        return f'{base}?ptzcmd&{move_map[cmd]}&{s}'
    if cmd == 'gotopreset' and preset is not None:
        return f'{base}?ptzcmd&poscall&{preset}'
    if cmd == 'setpreset' and preset is not None:
        return f'{base}?ptzcmd&posset&{preset}'
    if cmd == 'clearpreset' and preset is not None:
        return f'{base}?ptzcmd&posdel&{preset}'
    if cmd == 'home':
        return f'{base}?ptzcmd&poscall&0'
    return None

class _WhepProxyHandler(http.server.BaseHTTPRequestHandler):
    """Přeposílá WHEP požadavky (SDP handshake) na MediaMTX a doplňuje CORS hlavičky.

    Appka běží z file:// (Origin: null) a MediaMTX 1.20 nevrací CORS hlavičky na
    preflight OPTIONS → přímý fetch padá. Tady OPTIONS zodpovíme sami a POST/ostatní
    metody přepošleme na MediaMTX (server↔server, kde CORS neplatí) a k odpovědi
    přidáme Access-Control-*. Video jde WebRTC/UDP mimo tuto proxy."""

    protocol_version = 'HTTP/1.1'

    def _send_cors(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'OPTIONS, GET, POST, PATCH, DELETE')
        self.send_header('Access-Control-Allow-Headers', '*')
        self.send_header('Access-Control-Expose-Headers', '*')

    def do_OPTIONS(self):
        self.send_response(204)
        self._send_cors()
        self.send_header('Content-Length', '0')
        self.end_headers()

    def _forward(self, method):
        try:
            length = int(self.headers.get('Content-Length', 0) or 0)
        except ValueError:
            length = 0
        body = self.rfile.read(length) if length else None
        target = f'http://{MEDIAMTX_WEBRTC_HOST}:{MEDIAMTX_WEBRTC_PORT}{self.path}'
        req = urllib.request.Request(target, data=body, method=method)
        ct = self.headers.get('Content-Type')
        if ct:
            req.add_header('Content-Type', ct)
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                data      = resp.read()
                status    = resp.status
                resp_ct   = resp.headers.get('Content-Type', 'application/sdp')
        except urllib.error.HTTPError as e:
            data    = e.read()
            status  = e.code
            resp_ct = e.headers.get('Content-Type', 'text/plain')
        except Exception as e:
            msg = f'WHEP proxy: MediaMTX nedostupný ({e})'.encode('utf-8')
            self.send_response(502)
            self._send_cors()
            self.send_header('Content-Type', 'text/plain; charset=utf-8')
            self.send_header('Content-Length', str(len(msg)))
            self.end_headers()
            self.wfile.write(msg)
            return
        self.send_response(status)
        self._send_cors()
        self.send_header('Content-Type', resp_ct)
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        if data:
            self.wfile.write(data)

    def do_POST(self):   self._forward('POST')
    def do_PATCH(self):  self._forward('PATCH')
    def do_DELETE(self): self._forward('DELETE')
    def do_GET(self):    self._forward('GET')

    def log_message(self, *args):
        pass  # ticho — jinak spamuje konzoli u každého segmentu


class _ThreadingHTTPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True
    allow_reuse_address = True


def run_whep_proxy():
    """Spustí CORS proxy pro WHEP handshake na localhost:WHEP_PROXY_PORT."""
    try:
        srv = _ThreadingHTTPServer(('127.0.0.1', WHEP_PROXY_PORT), _WhepProxyHandler)
    except Exception as e:
        print(f'[WHEP-PROXY] Nepodařilo se spustit na :{WHEP_PROXY_PORT} — {e}')
        return
    print(f'[WHEP-PROXY] Naslouchá na http://127.0.0.1:{WHEP_PROXY_PORT} → MediaMTX :{MEDIAMTX_WEBRTC_PORT} (obchází CORS)')
    srv.serve_forever()


async def handler(websocket):
    connected_clients.add(websocket)
    ip = websocket.remote_address[0] if websocket.remote_address else '?'
    print(f'[WS] Klient připojen: {ip}')
    try:
        async for message in websocket:
            try:
                msg = json.loads(message)
                cmd_type = msg.get('cmd')

                if cmd_type == 'config':
                    cam = msg.get('cam', 1)
                    if 'ip' in msg:       cameras[cam]['ip']       = msg['ip']
                    if 'user' in msg:     cameras[cam]['user']     = msg['user']
                    if 'password' in msg: cameras[cam]['password'] = msg['password']
                    if 'speed' in msg:    cameras[cam]['speed']    = int(msg['speed'])
                    await websocket.send(json.dumps({'type': 'ok', 'cmd': 'config', 'cam': cam}))

                elif cmd_type == 'ptz':
                    cam    = msg.get('cam', 1)
                    action = msg.get('action', 'stop')
                    preset = msg.get('preset')
                    speed  = msg.get('speed', cameras[cam]['speed'])
                    cfg    = cameras[cam]
                    if not cfg['ip']:
                        await websocket.send(json.dumps({'type': 'error', 'msg': f'CAM{cam}: IP adresa není nastavena'}))
                        continue
                    path = build_cgi_path(action, speed, preset)
                    if path is None:
                        await websocket.send(json.dumps({'type': 'error', 'msg': f'CAM{cam}: Neznámý příkaz: {action}'}))
                        continue

                    # Každý PTZ příkaz spustíme jako samostatný asyncio task, aby stop
                    # nečekal ve frontě za pomalým HTTP requestem od klienta/websocketu.
                    # Vůči kameře ale musí být pořadí příkazů (např. move → stop)
                    # zaručené, proto se každý request pro danou kameru serializuje
                    # přes cam_locks — další příkaz se odešle až když předchozí
                    # dostal HTTP odpověď (nebo vypršel timeout).
                    is_stop = action in ('stop', 'zoomstop', 'focusstop')
                    timeout = 1.5 if is_stop else 4.0

                    async def _send_ptz(cfg=cfg, path=path, action=action, cam=cam, timeout=timeout, ws=websocket):
                        loop = asyncio.get_event_loop()
                        async with cam_locks[cam]:
                            try:
                                ok, resp = await asyncio.wait_for(
                                    loop.run_in_executor(None, cgi_request, cfg['ip'], cfg['user'], cfg['password'], path),
                                    timeout=timeout
                                )
                            except asyncio.TimeoutError:
                                ok, resp = False, 'timeout'
                        try:
                            await ws.send(json.dumps({
                                'type': 'ptz_result', 'cam': cam, 'ok': ok,
                                'action': action, 'response': resp[:200] if resp else ''
                            }))
                        except Exception:
                            pass

                    asyncio.ensure_future(_send_ptz())

                elif cmd_type == 'test':
                    cam = msg.get('cam', 1)
                    cfg = cameras[cam]
                    if not cfg['ip']:
                        await websocket.send(json.dumps({'type': 'test_result', 'cam': cam, 'ok': False, 'msg': 'IP adresa není nastavena'}))
                        continue
                    loop = asyncio.get_event_loop()
                    ok, resp = await loop.run_in_executor(None, cgi_request, cfg['ip'], cfg['user'], cfg['password'], '/')
                    await websocket.send(json.dumps({
                        'type': 'test_result', 'cam': cam, 'ok': ok,
                        'msg': 'Kamera dostupná' if ok else resp
                    }))

                elif cmd_type == 'set_rtsp':
                    rtsp_url    = msg.get('rtsp_url', '')
                    stream_name = msg.get('stream_name', 'cam2')
                    if not rtsp_url:
                        await websocket.send(json.dumps({'type': 'rtsp_result', 'ok': False, 'msg': 'RTSP URL je prázdná'}))
                        continue
                    loop = asyncio.get_event_loop()
                    ok, err = await loop.run_in_executor(None, _restart_mediamtx, rtsp_url, stream_name)
                    await websocket.send(json.dumps({'type': 'rtsp_result', 'ok': ok, 'msg': err}))

                elif cmd_type == 'status':
                    await websocket.send(json.dumps({
                        'type': 'status',
                        'cam1_ip': cameras[1]['ip'],
                        'cam2_ip': cameras[2]['ip'],
                    }))

            except json.JSONDecodeError:
                pass
            except Exception as e:
                print(f'[ERR] Handler: {e}')
                try:
                    await websocket.send(json.dumps({'type': 'error', 'msg': str(e)}))
                except:
                    pass
    except websockets.exceptions.ConnectionClosed:
        pass
    finally:
        connected_clients.discard(websocket)
        print(f'[WS] Klient odpojen: {ip}')

def run_server():
    """Spustí asyncio WebSocket server v samostatném vlákně."""
    async def _main():
        print(f'[START] PTZ IP Server běží na ws://localhost:{WS_PORT}')
        async with websockets.serve(handler, 'localhost', WS_PORT):
            await asyncio.Future()
    asyncio.run(_main())

def _find_html_file():
    """Najde HTML soubor appky v BASE_DIR."""
    for name in ['SL Meeting_Ovládání PTZ kamer.html', 'Ovládání_kamer_1_2_IP.html', 'Ovládání_kamer_1_1_IP.html']:
        if os.path.exists(os.path.join(BASE_DIR, name)):
            return name
    for f in os.listdir(BASE_DIR):
        if f.endswith('.html') and 'kamer' in f.lower():
            return f
    return None

if __name__ == '__main__':
    # Pokud existuje mediamtx.yml, spusť MediaMTX hned při startu
    if os.path.exists(MEDIAMTX_CONF) and os.path.exists(MEDIAMTX_EXE):
        ok, msg = _start_mediamtx()
        print(f'[MEDIAMTX] {"Spuštěn" if ok else "Chyba: " + msg}')
    else:
        print(f'[MEDIAMTX] mediamtx.exe nebo mediamtx.yml nenalezen — nakonfigurujte v appce')

    # WebSocket server — v samostatném vlákně
    ws_thread = threading.Thread(target=run_server, daemon=True)
    ws_thread.start()

    # CORS proxy pro WHEP handshake — v samostatném vlákně
    whep_thread = threading.Thread(target=run_whep_proxy, daemon=True)
    whep_thread.start()

    # pystray MUSÍ běžet v hlavním vlákně (požadavek Windows)
    try:
        import pystray
        from PIL import Image, ImageDraw

        def make_icon(color):
            img = Image.new('RGBA', (64, 64), (0, 0, 0, 0))
            d = ImageDraw.Draw(img)
            d.ellipse([8, 8, 56, 56], fill=color)
            return img

        def on_quit(icon, item):
            _stop_mediamtx()
            icon.stop()
            os._exit(0)

        def on_open_browser(icon, item):
            html_file = _find_html_file()
            if html_file:
                webbrowser.open(f'file:///{os.path.join(BASE_DIR, html_file).replace(os.sep, "/")}')

        icon = pystray.Icon(
            'PTZ IP Server',
            make_icon('#22c55e'),
            'PTZ IP Server – běží',
            menu=pystray.Menu(
                pystray.MenuItem('PTZ IP Server – běží', None, enabled=False),
                pystray.MenuItem(f'ws://localhost:{WS_PORT}', None, enabled=False),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem('Otevřít v prohlížeči', on_open_browser),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem('Ukončit', on_quit),
            )
        )
        icon.run()  # blokuje hlavní vlákno
    except ImportError:
        print('[INFO] pystray není dostupný — server běží bez ikonky')
        ws_thread.join()
