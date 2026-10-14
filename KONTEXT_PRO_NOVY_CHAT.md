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

**Kamery:** VHD V600 (nebo podobné), **CGI protokol** (port 80):
- Pohyb: `GET /cgi-bin/ptzctrl.cgi?ptzcmd&up&5`
- Stop pan/tilt: `GET /cgi-bin/ptzctrl.cgi?ptzcmd&ptzstop` ⭐ (NE `stop` — konvence PTZOptics/VHD)
- Stop zoom/focus: `zoomstop` / `focusstop`
- Preset uložit: `GET /cgi-bin/ptzctrl.cgi?ptzcmd&posset&N`
- Preset vyvolat: `GET /cgi-bin/ptzctrl.cgi?ptzcmd&poscall&N`
- Preset smazat: `GET /cgi-bin/ptzctrl.cgi?ptzcmd&posdel&N`

**VISCA-over-IP** (raw, bez Sony hlavičky, UDP **1259**) — pro sken „po souřadnicích":
- Dotaz pan/tilt: `81 09 06 12 FF` → `90 50 <pan 4 nib> <tilt 4 nib> FF` (signed 16-bit)
- Dotaz zoom: `81 09 04 47 FF`
- Abs pan/tilt: `81 01 06 02 VV WW <pan 4 nib> <tilt 4 nib> FF`
- Abs zoom: `81 01 04 47 <zoom 4 nib> FF`
- Ověřeno naostro `coords_test.py` (round-trip, odchylka 0).

> ⚠️ **Hardware joystick AVMatrix PKC3500** (RS485/Pelco-D) **sdílí preset paměť kamery** s appkou — přepíše uložené presety. Proto sken „po souřadnicích" přes VISCA místo presetů.

---

## Soubory

| Soubor | Popis |
|-------|-------|
| `SL Meeting_Ovládání PTZ kamer.html` | Hlavní appka (~5300 řádků), standalone HTML |
| `ptz_server.py` | Python WebSocket server + MediaMTX manager |
| `mediamtx.exe` + `mediamtx.yml` | RTSP→WebRTC konvertor (vedle ptz_server.py) |

**Instalace:** `pip install websockets pillow pystray`.

**Spuštění (jeden krok):** dvojklik na **`start_ptz.bat`** (nebo `start_ptz_bez_okna.vbs` pro běh bez černého okna). Server naběhne, zobrazí se v systray a **sám otevře appku v prohlížeči** (po ~1 s, ať stihne naběhnout WS). Prohlížeč nedokáže server spustit sám (sandbox), proto se startuje server a ten otevře stránku; tlačítko „Připojit server" v appce slouží na (re)connect.

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
- **Kalibrace sedadla bez módu** — klikni na sedadlo (kamera najede/nic), dolaď joystickem a dej **Uložit preset** → uloží polohu do presetu + VISCA souřadnice. (Dřívější mód „Editace presetů sedadel" a pravý klik na sedadle byly zrušeny; jejich funkce zůstávají v kódu „uspané".)
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
- Kamera projíždí kalibrovanými sedadly (**po VISCA souřadnicích** `slotCoords`, fallback preset) a fotí tváře
- Výběr tváře: nejblíž **top-center** (`_pickSeatFace`), brána obsazenosti
- Fotka sedadla: 4:3 ořez vycentrovaný na obličej, top-center, **bez detekčního rámečku** (`_faceCropPhoto`)
- Opt-in **zoom-in sken** (`_scan.zoomScan`) — přiblíží a od nejtěsnějšího oddaluje
- Rozpoznávání tváří přes face-api.js (ssdMobilenetv1 + faceLandmark68Net + faceRecognitionNet)
- Modely se stáhnou z CDN při prvním použití (~12MB)
- Rozpoznané osoby = presety (fotka + jméno), uložené v IndexedDB

### Osoby (rozpoznávání tváří)
- Sekce v nastavení (boční panel)
- Přidání osoby: jméno + fotka + automatický facial embedding
- Threshold slider 0.3–0.8 (default 0.5)
- Osoby uložené v IndexedDB (`ptz_persons`)

### Nastavení (boční panel)
- **Připojit / Restartovat server** (úplně nahoře) — samostatné tlačítko (`connectBtn`, `toggleConnect`), přesunuto z hlavičky; v hlavičce zůstala jen stavová tečka.
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
| **Slot coords (sedadlo→VISCA pan/tilt/zoom)** | localStorage `ptz_slot_coords` |
| Nastavení (IP, pass atd.) | localStorage `ptz_settings` |

---

## ptz_server.py — klíčové detaily

- Naslouchá na `ws://localhost:8765`
- Každý PTZ příkaz běží jako samostatný `asyncio.ensure_future` task (aby stop nečekal za pomalým HTTP requestem)
- Příkazy pro danou kameru se serializují přes `cam_locks` (per-camera `asyncio.Lock`), aby stop nepředběhl move na síti
- `build_cgi_path`: pan/tilt stop → **`ptzstop`** (ne `stop`), bez parametru rychlosti
- **WHEP CORS proxy** (`_WhepProxyHandler`, `run_whep_proxy`, port **8890**) — obchází CORS MediaMTX pro `file://` náhled
- **VISCA-over-IP** (`visca_get_pos`, `visca_abs_move`, UDP 1259) + WS příkazy `getpos` / `absmove` pro sken po souřadnicích
- MediaMTX: auto-start při spuštění pokud existuje `mediamtx.yml`, auto-stop při ukončení
- `set_rtsp` WS příkaz: přepíše `mediamtx.yml` + restartuje MediaMTX
- `mediamtx.yml` obsahuje `webrtcAllowOrigin: '*'` (CORS pro file://)
- Při startu **sám otevře appku v prohlížeči** (`_open_app`, `threading.Timer(1.0,…)`) — stačí spustit server
- Systray menu: „Otevřít v prohlížeči", „Ukončit"
- Launchery: `start_ptz.bat` (s konzolí/logy), `start_ptz_bez_okna.vbs` (skrytě přes `pythonw`)

---

## Vyřešené problémy (historie)

| Problém | Řešení |
|---------|----------|
| Kamera nejde zastavit | **VYŘEŠENO:** pan/tilt stop je `?ptzcmd&ptzstop` (ne `stop`) — konvence PTZOptics/VHD, ověřeno `stop_test.py`. K tomu: PTZ příkazy jsou async tasks, stop se posílá 3× (0/150/400 ms), stop URL bez rychlosti, per-camera serializace přes `cam_locks`. |
| Duplikát presetů při přidání | `type="button"` na modal buttons, `state._saving` guard, kontrola duplicitního num |
| WebRTC stream nefungoval ve scan modalu | `ontrack` se nastavuje PŘED `createOffer`, čekání na ICE gathering, CORS v mediamtx.yml. **Navíc:** MediaMTX 1.20 neodpovídá na preflight OPTIONS z `file://` → přidán WHEP CORS proxy v serveru (port 8890). |
| Sken najížděl mimo sedadla | Joystick AVMatrix PKC3500 přepsal preset paměť kamery → přechod na sken „po souřadnicích" přes VISCA-over-IP (slotCoords, abs move). |
| Fotka sedadla měla detekční rámeček | Ořez `_faceCropPhoto` z čistého video zdroje, framing top-center. |
| face-api zaseknutí | Modely se načítají sériově s 30s timeoutem, progress feedback |
| Seat layout sloty neklikatelné | Click handler na všech slotech (i occupied) |
| Duplikáty console warnings (TF.js) | Potlačené přes console.warn override |
| face-api „Počítám embedding" zamrzne | **face-api.js@0.22.2 → @vladmandic/face-api@1.7.15** (kompatibilní s TF.js 4.x). MODEL_URL změněno na vladmandic váhy. Přidán 20s timeout do `_computeDescriptor`. Otestováno — funguje, tváře se rozpoznávají. |

---

## Aktuální stav

> Nejaktuálnější přehled stavu, čeká-na-čtvrtek bodů a dalšího směru je v **`ROADMAP.md`** a **`SESSION_HANDOFF.md`**. Tato sekce drží základní dořešené problémy.

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
