"""
Diagnostika: umí kamera vrátit aktuální pozici (pan/tilt/zoom)?
Když ano, dá se sken postavit „po souřadnicích" nezávisle na presetech
(které přepsal joystick).

Zkouší dvě cesty:
  A) HTTP CGI dotazy na pozici (kandidátní endpointy VHD/PTZOptics)
  B) VISCA-over-IP pan/tilt inquiry přes UDP (porty 52381 Sony-wrapper, 1259/5678 raw)

Použití:
    python coords_test.py 192.168.1.52 admin HESLO

Hledáme: který příkaz vrátí rozumná čísla pozice. Výstup pošli zpět.
"""

import sys, socket, base64, urllib.request, urllib.error

def cgi(ip, user, pw, path, timeout=3):
    url = f'http://{ip}{path}'
    req = urllib.request.Request(url)
    req.add_header('Authorization', 'Basic ' + base64.b64encode(f'{user}:{pw}'.encode()).decode())
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read().decode('utf-8', 'ignore').strip()
    except urllib.error.HTTPError as e:
        return e.code, (e.read().decode('utf-8','ignore')[:200] if e.fp else e.reason)
    except Exception as e:
        return None, str(e)

# ── A) CGI kandidáti na dotaz pozice ──
CGI_QUERIES = [
    '/cgi-bin/ptzctrl.cgi?ptzcmd&poscheck',
    '/cgi-bin/ptzctrl.cgi?ptzcmd&posquery',
    '/cgi-bin/ptzctrl.cgi?ptzcmd&getpos',
    '/cgi-bin/ptzctrl.cgi?ptzcmd&poscurr',
    '/cgi-bin/param.cgi?get_ptz_pos',
    '/cgi-bin/param.cgi?f=get_position',
    '/cgi-bin/param.cgi?get_position',
]

def visca_inquiry(ip, port, wrapper, timeout=1.5):
    """Pošle VISCA pan/tilt position inquiry (81 09 06 12 FF) přes UDP a vrátí raw odpověď."""
    payload = bytes([0x81, 0x09, 0x06, 0x12, 0xFF])
    if wrapper:  # Sony VISCA-over-IP hlavička (typ 0x0110, délka, seq)
        pkt = bytes([0x01, 0x10, 0x00, len(payload), 0x00, 0x00, 0x00, 0x01]) + payload
    else:
        pkt = payload
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(timeout)
        s.sendto(pkt, (ip, port))
        data, _ = s.recvfrom(64)
        s.close()
        return data.hex()
    except Exception as e:
        return f'(nic / {e})'

def main():
    if len(sys.argv) < 4:
        print('Použití: python coords_test.py IP user heslo'); return
    ip, user, pw = sys.argv[1], sys.argv[2], sys.argv[3]
    print(f'=== Kamera {ip} ===\n')

    print('--- A) CGI dotazy na pozici ---')
    for p in CGI_QUERIES:
        st, body = cgi(ip, user, pw, p)
        print(f'  {p}\n      → HTTP {st}: {body[:160]}')
    print()

    print('--- B) VISCA-over-IP pan/tilt inquiry (UDP) ---')
    print('  Správná odpověď vypadá cca: 905 0 0p 0q 0r 0s 0t 0u 0v 0w FF  (pqrs=pan, tuvw=tilt)')
    for port, wrap in [(52381, True), (1259, False), (5678, False), (52381, False)]:
        resp = visca_inquiry(ip, port, wrap)
        print(f'  port {port} {"(Sony wrapper)" if wrap else "(raw)"}: {resp}')
    print()
    print('👉 Pošli mi celý tenhle výstup. Který řádek vrátil rozumná čísla = tudy to postavíme.')

if __name__ == '__main__':
    main()
