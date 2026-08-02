# PTZ Camera Controller — Kontext pre nový chat

## O čo ide

Webová aplikácia pre ovládanie dvoch PTZ kamier v konferenčnej/rokovacej sále. Beží ako **lokálny HTML súbor** (`file://`) na Windows PC v sále. Komunikuje s Python WebSocket serverom (`ptz_server.py`) ktorý posiela HTTP CGI príkazy na kamery cez LAN.

---

## Architektúra

```
Ovládání_kamer_1_2_IP.html   (UI, beží v Edge/Chrome)
        │
        │ WebSocket ws://localhost:8765
        ▼
ptz_server.py   (Python, beží na pozadí ako systray app)
        │
        │ HTTP CGI
        ├──▶ Kamera 1 – Pódium    (IP napr. 192.168.1.51)
        └──▶ Kamera 2 – Komentáre (IP napr. 192.168.1.52)
                │
                │ RTSP → MediaMTX → WebRTC/WHEP → prehliadač
                └──▶ Live náhľad v scan modali
```

**Kamery:** VHD V600 (alebo podobné), CGI protokol:
- Pohyb: `GET /cgi-bin/ptzctrl.cgi?ptzcmd&up&5`
- Stop: `GET /cgi-bin/ptzctrl.cgi?ptzcmd&stop` (bez rýchlosti)
- Preset uložiť: `GET /cgi-bin/ptzctrl.cgi?ptzcmd&posset&N`
- Preset vyvolať: `GET /cgi-bin/ptzctrl.cgi?ptzcmd&poscall&N`
- Preset zmazať: `GET /cgi-bin/ptzctrl.cgi?ptzcmd&posdel&N`

---

## Súbory

| Súbor | Popis |
|-------|-------|
| `Ovládání_kamer_1_2_IP.html` | Hlavná appka (~5300 riadkov), standalone HTML |
| `ptz_server.py` | Python WebSocket server + MediaMTX manager |
| `mediamtx.exe` + `mediamtx.yml` | RTSP→WebRTC konvertor (vedľa ptz_server.py) |

**Inštalácia:** `pip install websockets pillow pystray`, spusti `ptz_server.py` (zobrazí sa v systray), otvor HTML v prehliadači.

---

## Funkcie appky

### CAM 1 — Pódium (ľavý panel)
- Manuálne ovládanie: šípky, zoom, focus (hold = rýchly pohyb, klik = krátky pohyb 350ms)
- Presety: karty s fotkou a menom, klik = vyvolať preset, hold 2s = uložiť aktuálnu polohu
- Pridávanie presetov: tlačidlo „+ Přidat", modal s menom, číslom (1–99), fotkou
- Editácia poradia drag&drop
- Skrytie presetov (hide mode)
- Rozsah čísel presetov: 1–99

### CAM 2 — Komentáre (pravý panel)
- Rovnaké ovládanie ako CAM 1
- **Seat layout** — zobrazenie hľadiska s rozmiestnením sedadiel (Blok A + Blok B)
- **Editace presetů sedadel** — každé sedadlo = slot, hold 2s = uloží polohu kamery pre toto sedadlo
- Rozsah čísel presetov: 175–255

### Seat layout
Pôvodný pevný layout z rokovacieho hľadiska (obnovený na žiadosť):

**Blok A (ľavý):**
```
Rad 1: [15,14,13,12,11]           odsadenie ~1.5×krok
Rad 2: [27,26,25,24,23,22,21]     odsadenie ~0.5×krok
Rad 3: [38,37,36,35,34,33,32,31]  bez odsadenia
Rad 4: [47,46,45,44,43,42,41]     odsadenie ~0.5×krok
Rad 5: [0,1] medzera [57..51]     bez odsadenia
```

**Blok B (pravý):**
```
Rad 1: [111..115]   odsadenie ~1.5×krok (pyramída)
Rad 2: [121..126]   odsadenie ~1×krok
Rad 3: [131..137]   odsadenie ~0.5×krok
Rad 4: [141..148]   bez odsadenia
Rad 5: [151..158]   bez odsadenia
Rad 6: [161..168]   bez odsadenia
```

Čísla sedadiel = čísla presetov na CAM2 (direktné mapovanie).

### Scan modal (skenování hľadiska)
- Otvorí sa z panelu CAM2
- Zobrazí live WebRTC stream z CAM2 (cez MediaMTX WHEP endpoint `http://localhost:8889/cam2/whep`)
- Kamera prechádza kalibrovanými sedadlami a fotí tváre
- Rozpoznávanie tvárí cez face-api.js (ssdMobilenetv1 + faceLandmark68Net + faceRecognitionNet)
- Modely sa stiahnu z CDN pri prvom použití (~12MB)
- Rozpoznané osoby = presety (fotka + meno), uložené v IndexedDB

### Osoby (rozpoznávání tváří)
- Sekcia v nastaveniach (bočný panel)
- Pridanie osoby: meno + fotka + automatický facial embedding
- Threshold slider 0.3–0.8 (default 0.5)
- Osoby uložené v IndexedDB (`ptz_persons`)

### Nastavenia (bočný panel)
- Záloha presetov (export/import JSON)
- Kamera 1 – IP, user, pass, rýchlosti, test pripojenia
- Kamera 2 – IP, user, pass, rýchlosti, test, RTSP URL, „✓ Použít RTSP URL" (spustí MediaMTX)
- Pozice sedí/stojí (preset čísla pre špeciálne pozície)
- Osoby (rozpoznávanie)
- Log

---

## Technický stack

- **Frontend:** Vanilla JS, CSS custom properties, IndexedDB
- **Fonty:** DM Sans, DM Mono, Bebas Neue (Google Fonts)
- **Face detection:** face-api.js@0.22.2, TensorFlow.js@4.17.0, BlazeFace@0.0.7
- **Backend:** Python 3, `websockets`, `pillow`, `pystray`, `asyncio`
- **Video:** MediaMTX (RTSP→WebRTC), WHEP protocol

---

## Úložisko dát

| Dáta | Kde |
|------|-----|
| Presety CAM1+CAM2 | IndexedDB `ptz_controller` → `presets` (cam1/cam2) |
| Osoby + embeddingy | IndexedDB `ptz_persons` |
| Slot assignments (sedadlo→preset) | localStorage `ptz_slot_assignments` |
| Slot presets (sedadlo→číslo presetu) | localStorage `ptz_slot_presets` |
| Nastavenia (IP, pass atď.) | localStorage `ptz_settings` |

---

## ptz_server.py — kľúčové detaily

- Počúva na `ws://localhost:8765`
- Každý PTZ príkaz beží ako samostatný `asyncio.ensure_future` task (aby stop nečakal za pomalým HTTP requestom)
- Stop príkazy sa posielajú **bez parametra rýchlosti** (`?ptzcmd&stop` nie `?ptzcmd&stop&5`)
- MediaMTX: auto-štart pri spustení ak existuje `mediamtx.yml`, auto-stop pri ukončení
- `set_rtsp` WS príkaz: prepíše `mediamtx.yml` + reštartuje MediaMTX
- `mediamtx.yml` obsahuje `webrtcAllowOrigin: '*'` (CORS pre file://)
- Systray menu: „Otevřít v prohlížeči", „Ukončit"

---

## Rozhodnuté problémy (história)

| Problém | Riešenie |
|---------|----------|
| Kamera nejede zastaviť | PTZ príkazy sú async tasks, stop sa posiela 2× (po 350ms + 150ms neskôr), stop URL bez rýchlosti |
| Duplikát presetov pri pridaní | `type="button"` na modal buttons, `state._saving` guard, check duplicitného num |
| WebRTC stream nefungoval v scan modali | `ontrack` sa nastavuje PRED `createOffer`, čakanie na ICE gathering, CORS v mediamtx.yml |
| face-api zaseknutie | Modely sa načítavajú sériovo s 30s timeoutom, progress feedback |
| Seat layout sloty neklikateľné | Click handler na všetkých slotoch (aj occupied) |
| Duplikáty console warnings (TF.js) | Potlačené cez console.warn override |
| face-api „Počítám embedding" zamrzne | **face-api.js@0.22.2 → @vladmandic/face-api@1.7.15** (kompatibilný s TF.js 4.x). MODEL_URL zmenené na vladmandic váhy. Pridaný 20s timeout do `_computeDescriptor`. Otestované — funguje, tváre sa rozpoznávajú. |

---

## Aktuálny stav (aktualizácia 30.7.2026)

Táto sekcia je novšia než zvyšok dokumentu — zachytáva prácu z posledného chatu.

### Opravy urobené (v kóde), ale ešte NEOVERENÉ naostro pri kamere
- **Zastavovanie kamery — 2 zmeny:**
  1. `ptz_server.py` — per-camera `asyncio.Lock` (`cam_locks`), aby sa stop na sieti nepredbehol pred move (príkazy pre danú kameru idú striktne v poradí).
  2. `Ovládání_kamer_1_2_IP.html` (`startCmd`/`stopCmd`, ~ř. 2358) — skutočný **hold/release**: krátky klik jde ~350ms a sám zastaví; držanie jde dokým pustíš. Stop sa posiela 2× (hneď + po 150ms).
  → **Stále hlásené ako nefunkčné** (30.7.). Podozrenie sa presúva na samotný **stop CGI príkaz** kamery (`?ptzcmd&stop`) — možno VHD chce iný formát. **Ďalší krok:** priamy CGI test z Pythonu (move → sleep 1.5s → stop), pozorovať kameru. Treba heslo ku kamere.

### Face recognition — VYRIEŠENÉ
- Swap na `@vladmandic/face-api@1.7.15` (viď tabuľka vyššie). Testovacie tváre prechádzajú.

### Prostredie (Windows PC uživateľa)
- **Python 3.12.10** doinštalovaný cez winget do `C:\Users\thome\AppData\Local\Programs\Python\Python312` (pôvodná inštalácia bola rozbitá). Balíčky `websockets 16.1.1`, `pillow`, `pystray` — server naostro overený (WS 8765 odpovedá). Python pridaný do user PATH.
- **Kamery na LAN:** CAM1 Pódium `192.168.1.51`, CAM2 Komentáre `192.168.1.52` — obe online (ping OK, HTTP 401, server `thttpd/2.25b`). Login default admin/admin, reálne heslo nastavené v appke.
- **GitHub CLI (`gh` 2.97)** nainštalovaný a prihlásený ako `tomeknawrat`.

### ⚠️ Cloud session vs. lokálne kamery
Tento projekt reálne potrebuje **lokálnu sieť ku kameram + `ptz_server.py` bežiaci na tom PC v sále**. Cloud session (claude.ai/code) beží na vzdialenom stroji, takže na kamery ani na lokálny server **nedosiahne** — hodí sa na úpravy kódu, ale živé testovanie PTZ musí prebehnúť lokálne na tom počítači.

---

## Ostatné nedoriešené problémy

1. **Duplikát preset kariet** — `savePresetModal` sa volá raz (potvrdené cez console.trace), `push` prebehne raz (0→1), ale na obrazovke sú 2 karty. Podozrenie: `loadPresets()` dobehne asynchrónne po save a prekreslí s duplikátom z IndexedDB (kde môžu byť staré duplikáty z predchádzajúcich bugov). **Odporúčané riešenie:** v Edge F12 → Application → IndexedDB → `ptz_controller` → Delete database, potom skúsiť znova.

---

## Verzovanie a súbory

Projekt je odteraz **git repozitár** na GitHube:
- Remote: `https://github.com/tomeknawrat/claudecode.git`, vetva **`ptzcameracontroller`**
- `Ovládání_kamer_1_2_IP.html` — hlavná appka
- `ptz_server.py` — WS server
- `mediamtx.yml` je v `.gitignore` (auto-generovaný serverom)

Pri pokračovaní: repo je zdroj pravdy, netreba prikladať súbory ručne.

---

## Jazyk

Komunikácia v tomto projekte prebiehala v **slovenčine a češtine** (zmiešane). UI appky je v češtine.
