# Session Handoff — PTZ Camera Controller

> Strukturované shrnutí práce z pracovní session (Claude Code, lokálně na Windows PC).
> **Není to doslovný přepis chatu** — je to kontext pro pokračování v nové (i remote) session.
> Doplňuje `KONTEXT_PRO_NOVY_CHAT.md`, který popisuje celý projekt. Tento soubor popisuje, co se dělo naposledy a co zbývá.

## TL;DR — kde to stojí (aktualizace 14. 10. 2026)

- ✅ **Zastavování kamery — VYŘEŠENO a ověřeno naostro** — pan/tilt stop je `ptzstop`, ne `stop`.
- ✅ **Video náhled (WHEP) — VYŘEŠENO** — CORS proxy v `ptz_server.py` (:8890) obchází CORS MediaMTX.
- ✅ **Face recognition opraveno** — appka už nezamrzá na „Počítám embedding".
- ✅ **UI přepracování hotové** — karty sedadel, seat layout, hlavička CAM2, pose ikonky.
- ⏳ **Sken „po souřadnicích" (VISCA-over-IP) hotový v kódu** — čeká na živý test ve čtvrtek (restart serveru + překalibrace sedadel). Vznikl proto, že hardware joystick (AVMatrix PKC3500) přepsal sdílenou preset paměť kamery.
- ⏳ **Zoom-in sken + fotky top-center/bez rámečku** — hotové v kódu, čeká na doladění naostro.
- ✅ **Drag&drop fotek mezi sedadly** ve výchozím zobrazení (bez módu „Přesunout") — hotovo.
- ✅ **Zrušen mód „Editace presetů sedadel" + pravý klik na sedadle** — workflow bez módů (Uložit preset / drag&drop / ikona koše). Funkce módu zůstávají v kódu uspané.
- ✅ **Spuštění jedním krokem** — `start_ptz.bat` / `start_ptz_bez_okna.vbs`; server při startu sám otevře appku v prohlížeči.
- ✅ **Tlačítko Připojit/Restartovat server** přesunuto z hlavičky do Nastavení (úplně nahoru, sekce „Server").

> Detailní přehled stavu a dalšího směru je v `ROADMAP.md`.

---

## Co se v této session udělalo (chronologicky)

### 1. Oprava zastavování kamery (VYŘEŠENO, ověřeno naostro)
Problém: kamera se po kliknutí/puštění šipky nezastaví („jede dál nekonečně").
**Kořen:** pan/tilt stop CGI příkaz byl `?ptzcmd&stop`, ale VHD kamera (firmware PTZOptics/HuddleCam) chce **`?ptzcmd&ptzstop`**. Zjištěno přímým CGI testem `stop_test.py` (obešel appku i server, zkoušel varianty stop příkazu). Oprava v `build_cgi_path` (`ptz_server.py`): mapování `'stop' → 'ptzstop'`.
Doplňkové úpravy (zůstávají v platnosti):
- **`ptz_server.py`** — per-camera `asyncio.Lock` (`cam_locks`), aby stop na síti nepředběhl move.
- **`SL Meeting_Ovládání PTZ kamer.html`** (`startCmd`/`stopCmd`) — skutečný **hold/release**: krátký klik jede ~350 ms a sám zastaví; držení jede dokud pustíš. Stop se posílá 3× (0/150/400 ms).

**Stav:** ověřeno uživatelem naostro — `ptzstop` kameru zastaví. Hotovo.

### 2. Oprava face recognition (VYŘEŠENO)
Problém: přidání osoby zamrzlo na „Počítám embedding…".
Příčina: `face-api.js@0.22.2` (z r. 2020, stavěné pro TF.js 1.7) je nekompatibilní s načteným **TF.js 4.17.0** → inference zamrzne.
Oprava: swap na udržovaný fork **`@vladmandic/face-api@1.7.15`** (kompatibilní s TF.js 4.x, stejné API i formát vah). `MODEL_URL` přesměrováno na vladmandicovy váhy. Přidán 20s timeout do `_computeDescriptor` jako pojistka.
**Stav:** otestováno uživatelem, tváře se rozpoznávají. Hotovo.
(Pozn.: hláška „tvář se nepodařilo detekovat" znamená jen, že na konkrétní fotce nebyl nalezen obličej — ne chybu; případně lze zmírnit práh `minConfidence 0.5`.)

### 3. Zprovoznění prostředí
- **Python 3.12.10** doinstalován přes winget do `C:\Users\thome\AppData\Local\Programs\Python\Python312` (původní instalace byla rozbitá — složka Python313 bez exe, WindowsApps stub). Balíčky `websockets 16.1.1`, `pillow`, `pystray`. Přidán do user PATH. Server naostro ověřen (WS 8765 odpovídá na `status`).
- **Kamery na LAN ověřeny online:** CAM1 Pódium `192.168.1.51`, CAM2 Komentáře `192.168.1.52` (ping OK, HTTP 401, server `thttpd/2.25b`). PC má IP `192.168.1.150`.
- **GitHub CLI `gh` 2.97** nainstalován + přihlášen jako `tomeknawrat`.

### 4. Git + GitHub
- Založen git repozitář, projekt na větvi **`ptzcameracontroller`** v `https://github.com/tomeknawrat/claudecode.git`.
- `.gitignore` (ignoruje `__pycache__`, `mediamtx.yml`, `.claude/settings.local.json`).
- Identita commitů: `tomeknawrat`.

### 5. Překlad do češtiny (VYŘEŠENO)
- Celý projekt (server + HTML + dokumentace) přeložen ze slovenštiny do češtiny — komentáře, UI, logy, docs.
- Identifikátory kódu, HTML ID/třídy a CGI příkazy (`stop`, `up`, `ptzcmd`…) ponechány anglicky.
- `KONTEXT_PRE_NOVY_CHAT.md` přejmenován → `KONTEXT_PRO_NOVY_CHAT.md`.
- Ověřeno přes lokální http.server + prohlížeč (žádné chyby v konzoli), `py_compile` OK. Commit `c778a15`.

### 6. Práce po překladu (srpen–říjen 2026)

**Video náhled (WHEP) — VYŘEŠENO.** MediaMTX 1.20 neodpovídá na preflight OPTIONS z `file://` (Origin: null). Přidán malý CORS proxy do `ptz_server.py` (port 8890, `_WhepProxyHandler`/`run_whep_proxy`), přes který appka volá WHEP. Stream naskočil, ověřeno naostro.

**Sken hlediště — zacílení a fotky.**
- Oprava tlačítka „Spustit skenování" (ReferenceError).
- Výběr tváře: `_pickSeatFace` bere obličej nejblíž **top-center** (ne největší uprostřed), brána obsazenosti (dx/hFrac/minFaceFrac).
- Fotka sedadla: `_faceCropPhoto` — 4:3 ořez vycentrovaný na obličej, framing top-center, **z čistého video zdroje bez detekčního rámečku**.
- Opt-in **zoom-in sken** (`_scan.zoomScan`): na sedadle přiblíží a od nejtěsnějšího oddaluje, bere jen velkou centrální tvář.
- „Smazat všechny fotky" — maže jen fotky karet, **ne** presety v kameře.

**Sken „po souřadnicích" (VISCA-over-IP) — nová architektura, čeká na živý test.**
- Důvod: hardware joystick **AVMatrix PKC3500** (RS485/Pelco-D) sdílí preset paměť kamery s appkou → přepsal uložené presety, sken najížděl mimo sedadla.
- Řešení: číst a nastavovat **absolutní polohu** přes VISCA-over-IP (raw, UDP **1259**), nezávisle na presetech. Kalibrace sedadla uloží pan/tilt/zoom do `slotCoords` (localStorage `ptz_slot_coords`); sken i recall najíždějí přímo na souřadnice (`_wsAbsMove`), s fallbackem na preset.
- Server: `visca_get_pos`, `visca_abs_move`, WS příkazy `getpos`/`absmove`. HTML: `_wsGetPos`/`_wsAbsMove`, `_captureSlotCoords`.
- Ověřeno round-tripem (`coords_test.py`) na kameře uživatele: odchylka 0 (pan=-266, tilt=212, zoom=16384). **Zbývá naostro:** restart serveru (VISCA) + překalibrace všech sedadel.

**UI přepracování (čistě vizuální, hotové).** Karty sedadel (číslo vpravo nahoře, bez „Sedadlo XX", jednotná velikost, edit/delete přes pravý klik), seat layout (0/1 v 6. řadě, zarovnané řady, větší mezera mezi sektory), hlavička CAM2 („SKENOVAT HLEDIŠTĚ" vlevo, „KOMPAKTNÍ ZOBRAZENÍ" vpravo, bez Skrytých presetů, pose ikonky 🧍🪑 pod Skenovat), modal presetu (image box 4:3 na plnou šířku).

---

## ⚠️ Důležité pro REMOTE / cloud session

Tento projekt reálně potřebuje **lokální síť ke kamerám + `ptz_server.py` běžící na PC v sále**. Cloud session (claude.ai/code) běží na vzdáleném stroji Anthropicu — **na kamery (192.168.1.51/52) ani na lokální WebSocket server nedosáhne**.
- Cloud/remote session je dobrá na **úpravy kódu** (repo si naklonuje z GitHubu).
- **Živé testování PTZ (hlavně ten stop problém) musí proběhnout lokálně** na tom počítači. Změny z cloudu si stáhneš přes `git pull` a otestuješ naostro v sále.

---

## Nedořešené body / čeká na čtvrtek (živý test u kamer)
1. **Restart `ptz_server.py` + překalibrace sedadel** → sken po souřadnicích (VISCA). Priorita — vyřeší posun a cizí obličeje.
2. **Doladit zoom sken** (top-center, mírnější zoom) a **fotky** (top-center, bez rámečku) — `pickAnchorY`, `zoomSteps`, `zoomMinAcceptFrac`, `facePhotoFaceAt`, případně `scanTiltMs`.
3. **Rozpoznávání** — nahrát osoby, doladit práh z `dist:` hodnot v logu.
