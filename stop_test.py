"""
Diagnostika zastavování PTZ kamery — přímý CGI test (obchází appku i WS server).

Cíl: zjistit, KTERÝ stop příkaz VHD kamera opravdu poslechne. Podezření je, že
pan/tilt stop není `?ptzcmd&stop`, ale `?ptzcmd&ptzstop` (konvence PTZOptics/VHD),
případně stop vyžaduje parametry rychlosti.

Použití:
    python stop_test.py                 # zeptá se na IP/heslo interaktivně
    python stop_test.py 192.168.1.51 admin heslo

Skript pro každou variantu: rozjede pohyb doleva → počká → pošle testovaný stop
→ ty pozoruješ kameru a zapíšeš si, jestli zastavila. Mezi testy kameru vždy
srovná sérií všech stopů, aby další test začínal v klidu.
"""

import sys
import time
import base64
import urllib.request
import urllib.error

CGI = '/cgi-bin/ptzctrl.cgi'

# Kandidáti na pan/tilt STOP příkaz — otestují se postupně.
# (část za '?' — celá URL bude http://IP/cgi-bin/ptzctrl.cgi?<kandidat>)
STOP_CANDIDATES = [
    'ptzcmd&stop',            # současné řešení v appce
    'ptzcmd&ptzstop',         # PTZOptics/VHD konvence — hlavní podezřelý
    'ptzcmd&stop&5',          # stop s jednou rychlostí
    'ptzcmd&ptzstop&24&20',   # ptzstop se dvěma rychlostmi (pan&tilt)
    'ptzcmd&stop&24&20',      # stop se dvěma rychlostmi
]

# Pohybový příkaz pro rozjetí kamery před každým testem (stejný jako appka: 1 rychlost)
MOVE_QUERY = 'ptzcmd&left&5'


def cgi(ip, user, password, query, timeout=3):
    """Pošle CGI příkaz s Basic auth. Vrací (ok, text/chyba)."""
    url = f'http://{ip}{CGI}?{query}'
    req = urllib.request.Request(url)
    cred = base64.b64encode(f'{user}:{password}'.encode()).decode()
    req.add_header('Authorization', f'Basic {cred}')
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return True, resp.read().decode('utf-8', errors='ignore').strip()
    except urllib.error.HTTPError as e:
        return False, f'HTTP {e.code} {e.reason}'
    except Exception as e:
        return False, str(e)


def all_stops(ip, user, password):
    """Pošle všechny známé stop varianty — pojistka pro srovnání kamery mezi testy."""
    for q in STOP_CANDIDATES:
        cgi(ip, user, password, q)
        time.sleep(0.2)


def main():
    if len(sys.argv) >= 4:
        ip, user, password = sys.argv[1], sys.argv[2], sys.argv[3]
    else:
        ip       = input('IP kamery (např. 192.168.1.51): ').strip()
        user     = input('Uživatel [admin]: ').strip() or 'admin'
        password = input('Heslo: ').strip()

    print(f'\n=== Test kamery {ip} (uživatel {user}) ===')
    ok, resp = cgi(ip, user, password, MOVE_QUERY)
    print(f'Zkušební pohyb ({MOVE_QUERY}): {"OK" if ok else "CHYBA"} — {resp}')
    all_stops(ip, user, password)
    if not ok:
        print('⚠ Pohyb neprošel — zkontroluj IP/heslo/dostupnost a spusť znovu.')
        return
    print('Pohyb funguje. Teď projdeme stop varianty.\n')

    results = {}
    for i, stop_q in enumerate(STOP_CANDIDATES, 1):
        input(f'[{i}/{len(STOP_CANDIDATES)}] Enter = rozjedu kameru doleva na 2 s, pak pošlu stop "{stop_q}" …')
        cgi(ip, user, password, MOVE_QUERY)
        time.sleep(2.0)
        ok, resp = cgi(ip, user, password, stop_q)
        print(f'    → poslán stop "{stop_q}": {"HTTP OK" if ok else "CHYBA"} — {resp}')
        ans = input('    Zastavila se kamera? [a/n]: ').strip().lower()
        results[stop_q] = ans.startswith('a')
        # Srovnej kameru do klidu před dalším testem
        all_stops(ip, user, password)
        print()

    print('═══ VÝSLEDKY ═══')
    working = [q for q, good in results.items() if good]
    for q, good in results.items():
        print(f'  {"✅" if good else "❌"}  {q}')
    print()
    if working:
        print(f'👉 Funkční stop příkaz(y): {", ".join(working)}')
        print('   Napiš mi, který to je — přepíšu podle něj build_cgi_path v ptz_server.py.')
    else:
        print('⚠ Žádná varianta nezastavila. Napiš mi to — zkusíme jiný přístup')
        print('  (jiný CGI endpoint, VISCA přes TCP/UDP, nebo dotaz na manuál kamery).')


if __name__ == '__main__':
    main()
