"""
Round-trip test VISCA-over-IP (port 1259, raw) — ověří, že kamera umí:
  1) vrátit aktuální pan/tilt/zoom (inquiry)
  2) absolutně najet na zadané souřadnice (abs move)

Když po pohnutí kamerou najede zpět přesně na původní pozici, je potvrzené,
že lze postavit sken „po souřadnicích" nezávisle na presetech.

Použití:
    python coords_test.py 192.168.1.52 admin HESLO
"""

import sys, socket, base64, time, urllib.request

VISCA_PORT = 1259

def visca(ip, payload, timeout=1.5, want_reply=True):
    """Pošle raw VISCA payload přes UDP 1259, vrátí odpověď (bytes) nebo None."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(timeout)
        s.sendto(bytes(payload), (ip, VISCA_PORT))
        if not want_reply:
            s.close(); return b''
        data, _ = s.recvfrom(64)
        s.close()
        return data
    except Exception as e:
        return None

def signed16(v):
    return v - 0x10000 if v >= 0x8000 else v

def parse_nibbles(data, start, count):
    """Složí číslo z low-nibblů count bajtů od indexu start."""
    val = 0
    for i in range(count):
        val = (val << 4) | (data[start + i] & 0x0F)
    return val

def query_pantilt(ip):
    r = visca(ip, [0x81, 0x09, 0x06, 0x12, 0xFF])
    if not r or len(r) < 11 or r[0] != 0x90: return None
    # r = 90 50 p p p p t t t t FF
    pan = signed16(parse_nibbles(r, 2, 4))
    tilt = signed16(parse_nibbles(r, 6, 4))
    return pan, tilt, r.hex()

def query_zoom(ip):
    r = visca(ip, [0x81, 0x09, 0x04, 0x47, 0xFF])
    if not r or len(r) < 7 or r[0] != 0x90: return None
    zoom = parse_nibbles(r, 2, 4)
    return zoom, r.hex()

def nibbles_of(val16):
    v = val16 & 0xFFFF
    return [(v >> 12) & 0xF, (v >> 8) & 0xF, (v >> 4) & 0xF, v & 0xF]

def abs_move(ip, pan, tilt, pan_speed=0x10, tilt_speed=0x10):
    p = nibbles_of(pan); t = nibbles_of(tilt)
    cmd = [0x81, 0x01, 0x06, 0x02, pan_speed, tilt_speed] + p + t + [0xFF]
    return visca(ip, cmd, timeout=2.0)

def abs_zoom(ip, zoom):
    z = nibbles_of(zoom)
    return visca(ip, [0x81, 0x01, 0x04, 0x47] + z + [0xFF])

def cgi_move(ip, user, pw, query, timeout=3):
    url = f'http://{ip}/cgi-bin/ptzctrl.cgi?{query}'
    req = urllib.request.Request(url)
    req.add_header('Authorization', 'Basic ' + base64.b64encode(f'{user}:{pw}'.encode()).decode())
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r: r.read()
    except Exception: pass

def main():
    if len(sys.argv) < 4:
        print('Použití: python coords_test.py IP user heslo'); return
    ip, user, pw = sys.argv[1], sys.argv[2], sys.argv[3]
    print(f'=== Kamera {ip} (VISCA UDP {VISCA_PORT}) ===\n')

    pt = query_pantilt(ip)
    zm = query_zoom(ip)
    if not pt:
        print('❌ Dotaz na pan/tilt nevrátil platnou odpověď — napiš mi to.'); return
    pan, tilt, rawpt = pt
    print(f'Aktuální pozice: pan={pan} (0x{pan & 0xFFFF:04X}), tilt={tilt} (0x{tilt & 0xFFFF:04X})   [raw {rawpt}]')
    if zm:
        print(f'Aktuální zoom:   {zm[0]} (0x{zm[0]:04X})   [raw {zm[1]}]')
    print()

    input('Enter = pohnu kamerou doleva na 1.5 s, pak najedu ZPĚT na tuhle pozici přes VISCA abs…')
    cgi_move(ip, user, pw, 'ptzcmd&left&10')
    time.sleep(1.5)
    cgi_move(ip, user, pw, 'ptzcmd&ptzstop')
    time.sleep(0.5)
    print('  Kamera by teď měla být posunutá doleva. Najíždím zpět…')
    r = abs_move(ip, pan, tilt)
    if zm: abs_zoom(ip, zm[0])
    print(f'  abs_move odpověď: {r.hex() if r else "(žádná)"}')
    time.sleep(2)
    pt2 = query_pantilt(ip)
    if pt2:
        print(f'  Pozice po najetí: pan={pt2[0]}, tilt={pt2[1]}')
        dp, dt = abs(pt2[0]-pan), abs(pt2[1]-tilt)
        print(f'  Odchylka: pan {dp}, tilt {dt}')
    print()
    print('👉 Vrátila se kamera POHLEDEM na původní místo? [a/n] a jak přesně?')
    print('   (napiš mi i celý výstup) — podle toho postavím sken po souřadnicích.')

if __name__ == '__main__':
    main()
