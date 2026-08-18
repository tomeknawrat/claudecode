# PTZ Camera Controller — Kontext pro nový chat

## O co jde

Webová aplikace pro ovládání dvou PTZ kamer v konferenční/jednací sále. Běží jako **lokální HTML soubor** (`file://`) na Windows PC v sále. Komunikuje s Python WebSocket serverem (`ptz_server.py`), který posílá HTTP CGI příkazy na kamery přes LAN.

---

## Architektura

```
SL Meeting_Ovládání PTZ kamer.html   (UI, běží v Edge/Chrome)
        │
        │ WebSocket ws://localhost:8765
        ▼
ptz_server.py   (Python, běží na pozadí jako systray app)
        │
        │ HTTP CGI
        ├──▶ Kamera 1 – Pódium    (IP např. 192.168.1.51)
        └──▶ Kamera 2 – Komentáře (IP např. 192.168.1.52)
                │
                │ RTSP → MediaMTX → WebRTC/WHEP → prohlížeč
                └──▶ Live náhled ve scan modalu
```

**Kamery:** VHD V600 (nebo podobné), CGI protokol:
- Pohyb: `GET /cgi-bin/ptzctrl.cgi?ptzcmd&up&5`
- Stop: `GET /cgi-bin/ptzctrl.cgi?ptzcmd&stop` (bez rychlosti)
- Preset uložit: `GET /cgi-bin/ptzctrl.cgi?ptzcmd&posset&N`
- Preset vyvolat: `GET /cgi-bin/ptzctrl.cgi?ptzcmd&poscall&N`
- Preset smazat: `GET /cgi-bin/ptzctrl.cgi?ptzcmd&posdel&N`

---

## Soubory

| Soubor | Popis |
|-------|-------|
| `SL Meeting_Ovládání PTZ kamer.html` | Hlavní appka (~5300 řádků), standalone HTML |
| `ptz_server.py` | Python WebSocket server + MediaMTX manager |
| `mediamtx.exe` + `mediamtx.yml` | RTSP→WebRTC konvertor (vedle ptz_server.py) |

**Instalace:** `pip install websockets pillow pystray`, spusť `ptz_server.py` (zobrazí se v systray), otevři HTML v prohlížeči.

---

## Funkce appky

### CAM 1 — Pódium (levý panel)
- Manuální ovládání: šipky, zoom, focus (hold = plynulý pohyb, klik = krátký pohyb 350ms)
- Presety: karty s fotkou a jménem, klik = vyvolat preset, hold 2s = uložit aktuální polohu
- Přidávání presetů: tlačítko „+ Přidat", modal se jménem, číslem (1–99), fotkou
- Editace pořadí drag&drop
- Skrytí presetů (hide mode)
- Rozsah čísel presetů: 1–99

### CAM 2 — Komentáře (pravý panel)
- Stejné ovládání jako CAM 1
- **Seat layout** — zobrazení hlediště s rozmístěním sedadel (Blok A + Blok B)
- **Editace presetů sedadel** — každé sedadlo = slot, hold 2s = uloží polohu kamery pro toto sedadlo
- Rozsah čísel presetů: 175–255

### Seat layout
Původní pevný layout z jednacího hlediště (obnovený na žádost):

**Blok A (levý):**
```
Řada 1: [15,14,13,12,11]           odsazení ~1.5×krok
Řada 2: [27,26,25,24,23,22,21]     odsazení ~0.5×krok
Řada 3: [38,37,36,35,34,33,32,31]  bez odsazení
Řada 4: [47,46,45,44,43,42,41]     odsazení ~0.5×krok
Řada 5: [0,1] mezera [57..51]      bez odsazení
```

**Blok B (pravý):**
```
Řada 1: [111..115]   odsazení ~1.5×krok (pyramida)
Řada 2: [121..126]   odsazení ~1×krok
Řada 3: [131..137]   odsazení ~0.5×krok
Řada 4: [141..148]   bez odsazení
Řada 5: [151..158]   bez odsazení
Řada 6: [161..168]   bez odsazení
```

Čísla sedadel = čísla presetů na CAM2 (přímé mapování).

### Scan modal (skenování hlediště)
- Otevře se z panelu CAM2
- Zobrazí live WebRTC stream z CAM2 (přes MediaMTX WHEP endpoint `http://localhost:8889/cam2/whep`)
- Kamera projíždí kalibrovanými sedadly a fotí tváře
- Rozpoznávání tváří přes face-api.js (ssdMobilenetv1 + faceLandmark68Net + faceRecognitionNet)
- Modely se stáhnou z CDN při prvním použití (~12MB)
- Rozpoznané osoby = presety (fotka + jméno), uložené v IndexedDB

### Osoby (rozpoznávání tváří)
- Sekce v nastavení (boční panel)
- Přidání osoby: jméno + fotka + automatický facial embedding
- Threshold slider 0.3–0.8 (default 0.5)
- Osoby uložené v IndexedDB (`ptz_persons`)

### Nastavení (boční panel)
- Záloha presetů (export/import JSON)
- Kamera 1 – IP, user, pass, rychlosti, test připojení
- Kamera 2 – IP, user, pass, rychlosti, test, RTSP URL, „✓ Použít RTSP URL" (spustí MediaMTX)
- Pozice sedí/stojí (čísla presetů pro speciální pozice)
- Osoby (rozpoznávání)
- Log

---

## Technický stack

- **Frontend:** Vanilla JS, CSS custom properties, IndexedDB
- **Fonty:** DM Sans, DM Mono, Bebas Neue (Google Fonts)
- **Face detection:** @vladmandic/face-api@1.7.15, TensorFlow.js@4.17.0, BlazeFace@0.0.7
- **Backend:** Python 3, `websockets`, `pillow`, `pystray`, `asyncio`
- **Video:** MediaMTX (RTSP→WebRTC), WHEP protokol

---

## Úložiště dat

| Data | Kde |
|------|-----|
| Presety CAM1+CAM2 | IndexedDB `ptz_controller` → `presets` (cam1/cam2) |
| Osoby + embeddingy | IndexedDB `ptz_persons` |
| Slot assignments (sedadlo→preset) | localStorage `ptz_slot_assignments` |
| Slot presets (sedadlo→číslo presetu) | localStorage `ptz_slot_presets` |
| Nastavení (IP, pass atd.) | localStorage `ptz_settings` |

---

## ptz_server.py — klíčové detaily

- Naslouchá na `ws://localhost:8765`
- Každý PTZ příkaz běží jako samostatný `asyncio.ensure_future` task (aby stop nečekal za pomalým HTTP requestem)
- Příkazy pro danou kameru se serializují přes `cam_locks` (per-camera `asyncio.Lock`), aby stop nepředběhl move na síti
- Stop příkazy se posílají **bez parametru rychlosti** (`?ptzcmd&stop` ne `?ptzcmd&stop&5`)
- MediaMTX: auto-start při spuštění pokud existuje `mediamtx.yml`, auto-stop při ukončení
- `set_rtsp` WS příkaz: přepíše `mediamtx.yml` + restartuje MediaMTX
- `mediamtx.yml` obsahuje `webrtcAllowOrigin: '*'` (CORS pro file://)
- Systray menu: „Otevřít v prohlížeči", „Ukončit"

---

## Vyřešené problémy (historie)

| Problém | Řešení |
|---------|----------|
| Kamera nejde zastavit | **VYŘEŠENO:** pan/tilt stop je `?ptzcmd&ptzstop` (ne `stop`) — konvence PTZOptics/VHD, ověřeno `stop_test.py`. K tomu: PTZ příkazy jsou async tasks, stop se posílá 3× (0/150/400 ms), stop URL bez rychlosti, per-camera serializace přes `cam_locks`. |
| Duplikát presetů při přidání | `type="button"` na modal buttons, `state._saving` guard, kontrola duplicitního num |
| WebRTC stream nefungoval ve scan modalu | `ontrack` se nastavuje PŘED `createOffer`, čekání na ICE gathering, CORS v mediamtx.yml |
| face-api zaseknutí | Modely se načítají sériově s 30s timeoutem, progress feedback |
| Seat layout sloty neklikatelné | Click handler na všech slotech (i occupied) |
| Duplikáty console warnings (TF.js) | Potlačené přes console.warn override |
| face-api „Počítám embedding" zamrzne | **face-api.js@0.22.2 → @vladmandic/face-api@1.7.15** (kompatibilní s TF.js 4.x). MODEL_URL změněno na vladmandic váhy. Přidán 20s timeout do `_computeDescriptor`. Otestováno — funguje, tváře se rozpoznávají. |

---

## Aktuální stav (aktualizace 30.7.2026)

Tato sekce je novější než zbytek dokumentu — zachycuje práci z posledních chatů.

### Zastavování kamery — VYŘEŠENO
- **Kořen problému:** pan/tilt stop CGI příkaz byl `?ptzcmd&stop`, ale VHD kamera (firmware PTZOptics/HuddleCam) chce **`?ptzcmd&ptzstop`**. Ověřeno přímým CGI testem (`stop_test.py`). Oprava v `build_cgi_path` (`ptz_server.py`): `'stop' → 'ptzstop'`.
- Doplňkové úpravy (zůstávají): per-camera `asyncio.Lock` (`cam_locks`) v serveru; v HTML skutečný **hold/release** (krátký klik ~350 ms a sám zastaví, držení jede dokud pustíš), stop se posílá 3× (0/150/400 ms).

### Face recognition — VYŘEŠENO
- Swap na `@vladmandic/face-api@1.7.15` (viz tabulka výše). Testovací tváře procházejí.

### Prostředí (Windows PC uživatele)
- **Python 3.12.10** doinstalovaný přes winget do `C:\Users\thome\AppData\Local\Programs\Python\Python312` (původní instalace byla rozbitá). Balíčky `websockets 16.1.1`, `pillow`, `pystray` — server naostro ověřen (WS 8765 odpovídá). Python přidán do user PATH.
- **Kamery na LAN:** CAM1 Pódium `192.168.1.51`, CAM2 Komentáře `192.168.1.52` — obě online (ping OK, HTTP 401, server `thttpd/2.25b`). Login default admin/admin, reálné heslo nastavené v appce.
- **GitHub CLI (`gh` 2.97)** nainstalovaný a přihlášený jako `tomeknawrat`.

### ⚠️ Cloud session vs. lokální kamery
Tento projekt reálně potřebuje **lokální síť ke kamerám + `ptz_server.py` běžící na tom PC v sále**. Cloud session (claude.ai/code) běží na vzdáleném stroji, takže na kamery ani na lokální server **nedosáhne** — hodí se na úpravy kódu, ale živé testování PTZ musí proběhnout lokálně na tom počítači.

---

## Ostatní nedořešené problémy

1. **Duplikát preset karet** — `savePresetModal` se volá jednou (potvrzeno přes console.trace), `push` proběhne jednou (0→1), ale na obrazovce jsou 2 karty. Podezření: `loadPresets()` doběhne asynchronně po save a překreslí s duplikátem z IndexedDB (kde můžou být staré duplikáty z předchozích bugů). **Doporučené řešení:** v Edge F12 → Application → IndexedDB → `ptz_controller` → Delete database, pak zkusit znovu.

---

## Verzování a soubory

Projekt je nyní **git repozitář** na GitHubu:
- Remote: `https://github.com/tomeknawrat/claudecode.git`, větev **`ptzcameracontroller`**
- `SL Meeting_Ovládání PTZ kamer.html` — hlavní appka
- `ptz_server.py` — WS server
- `mediamtx.yml` je v `.gitignore` (auto-generovaný serverem)

Při pokračování: repo je zdroj pravdy, netřeba přikládat soubory ručně.

---

## Jazyk

Celý projekt (kód, komentáře, UI, dokumentace) je v **češtině**. Technické identifikátory v kódu (názvy proměnných/funkcí, CGI příkazy, HTML ID/třídy) zůstávají v angličtině.
