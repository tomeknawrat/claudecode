# PTZ Camera Controller — Roadmap

> Přehled hotového, rozpracovaného a dalšího směru. Doplňuje
> `KONTEXT_PRO_NOVY_CHAT.md` (popis projektu) a `SESSION_HANDOFF.md` (stav práce).
> Aktualizováno: **14. 10. 2026**. Hlavní větev: `ptzcameracontroller`.
> Hlavní soubor appky: **`SL Meeting_Ovládání PTZ kamer.html`**.

---

## ✅ Hotovo a ověřeno naostro

| Oblast | Popis | Commit |
|--------|-------|--------|
| Větve | Konsolidace veškeré PTZ práce do `ptzcameracontroller` | — |
| **Stop kamery** ⭐ | Pan/tilt stop je `?ptzcmd&ptzstop`, ne `stop` (VHD/PTZOptics). Ověřeno `stop_test.py` | `1f6f440`, `81c71a9` |
| **Video náhled** | WHEP CORS proxy v `ptz_server.py` (:8890) obchází CORS MediaMTX 1.20 | `846ce68` |
| Presety | Deduplikace preset karet při načtení z IndexedDB | `2a1ca70` |
| Rozpoznávání | Diagnostika, dedup osob, `minConfidence` 0.3 | `bbcc353` |
| Sken — tlačítko | Oprava „Spustit skenování" (ReferenceError `_scanSectors`) | `96f1154` |
| Sken — zacílení | Výběr tváře podle velikosti/pozice, brána obsazenosti (dx/hFrac) | `8e1ca64` |
| „Smazat všechny fotky" | Hromadné smazání karet CAM2 (jen fotky, ne presety v kameře) | `56145e8`, `a24dbfc` |
| Soubory | Přejmenování HTML → `SL Meeting_Ovládání PTZ kamer.html` | `ea9657a` |

## ✅ Hotovo v kódu — čeká na živý test (čtvrtek, lidé v sále)

| Oblast | Popis | Commit |
|--------|-------|--------|
| **Sken „po souřadnicích"** ⭐ | VISCA-over-IP (UDP 1259): kalibrace uloží absolutní pan/tilt/zoom, sken i recall najíždějí přímo na souřadnice — **nezávisle na preset paměti** (joystick ji přepisoval). Ověřeno round-tripem `coords_test.py` | `44bf1d4` |
| Zoom-in sken | Opt-in režim: na sedadle přiblíží a od nejtěsnějšího oddaluje, bere jen velkou centrální tvář. Cílí **top-center**, mírnější zoom (zoomSteps 2) | `7002a00`, `a236827`, `d4bf5a0` |
| Fotka sedadla | Ořez vycentrovaný na obličej (4:3), **top-center** framing, bez detekčního rámečku | `2f75614`, `c43b025`, `c062d98` |
| Volitelný tilt nudge | `_scan.scanTiltMs` (default off) — framing obličeje výš | `c43b025` |

## ✅ Panel Pódium (CAM1) — 5 pevných presetů (hotovo)

- „Přidat sedadlo" → **Přidat preset**; odstraněna hláška „Zatím žádné presety" (CAM1 i CAM2).
- **5 pevných, nemazatelných presetů** (bez kontext menu), stylem jako tlačítko „Přidat preset" (modré dlaždice, popisek jménem): **Scénka sedící** (2× pose-sedící) vlevo zarovnaná s „Uložit preset" v Komentářích; **Řečník nižší / Předsedající / Řečník vyšší** uprostřed; **Scénka stojící** (2× pose-stojící) zrcadlově vpravo (`CAM1_FIXED`, `renderCam1FixedPresets`, `layoutCam1Scenes` — přepočet přes fonts.ready + ResizeObserver).
- Chování „Přidat preset" (přidávání dalších) zatím odloženo.
- Popisky 5 presetů sjednoceny do velikosti/stylu tlačítek (DM Sans 13.5px, 700, uppercase, `.3px`). Všech 5 dlaždic má **stejnou šířku podle nejširší** (`equalizeCam1Tiles`), větší mezera ikona↔popisek (gap 9px). Tlačítka „Přidat preset"/„Uložit preset" jsou content-width (snug) jako v Komentářích. Tlačítko „Nastavení" kapitálkami. Fonty: UI = DM Sans, technické/číselné = DM Mono, logo „Ovládání kamer" = Bebas Neue (ponecháno).

## ✅ Panel Pódium (CAM1) — kompaktní lišta (hotovo)

- Zrušeno „Přesunout"; „Přidat" → **Přidat sedadlo**. Přidáno **Uložit preset** (`saveLastPresetManual(1)` — uloží ruční doladění do posledního vyvolaného presetu). Obě tlačítka stylem totožná s Komentáři (`cam2-tool-btn`).
- Tlačítka ve **sloupci pod sebou vlevo**, presety ve **vodorovném stripu vpravo**. Karta presetu je **stejně vysoká jako sloupec obou tlačítek** (horní border zarovnaný s „Přidat sedadlo", spodní s „Uložit preset" = 92 px), s **textovým popiskem (jménem)**, bez čísel.
- Nové presety se přidávají **od středu** — nejnovější je vždy uprostřed stripu (`_centerOutOrder`, starší střídavě doleva/doprava).
- **Výška panelu stabilní** — daná sloupcem tlačítek, neroste s počtem presetů. Styl `.cam2-tool-btn` rozšířen na obě kamery (`.cam-presets-section .cam2-tool-btn`).

## ✅ Spuštění jedním krokem (hotovo)

- **`start_ptz.bat`** (+ `start_ptz_bez_okna.vbs` pro běh bez okna) spustí `ptz_server.py`; server při startu **sám otevře appku v prohlížeči** (`_open_app`).
- Prohlížeč (sandbox) server spustit neumí → startuje se server, ten otevře stránku; tlačítko „Připojit server" slouží na (re)connect.

## ✅ Drag & drop fotek mezi sedadly (hotovo)

- Ve výchozím (detailním) zobrazení lze fotku **chytit myší a přetáhnout** na jiné sedadlo **bez přepínání do režimu „Přesunout"**.
- Tažení se spustí až po pohybu nad práh (6 px) — krátký klik (vyvolat preset) i hold (uložit pozici) zůstávají funkční.
- Tlačítko „Přesunout" je v seat layoutu skryté (v klasickém/kompaktním gridu zůstává).
- Ověřeno simulací v Playwrightu (přesun přiřazení + nulový posun při kliku).

## ✅ UI lišta CAM2 + „Uložit preset" (hotovo)

- 4 nástrojová tlačítka sladěná do **stejné kompozice jako „Kompaktní zobrazení"** (světlá soft výplň + střední ohraničení + tmavý sytý text = dobrá čitelnost), každé vlastní barva přes `--btn-bg/--btn-border/--btn-text`: **Skenovat hlediště** (fialová), **Přidat sedadlo** (modrá), **Uložit preset** (zelená), **Smazat všechny fotky** (červená).
- **Uložit preset** (`saveSeatPresetManual`) — po kliku na sedadlo a ručním doladění joystickem uloží **aktuální polohu** kamery do presetu posledního vyvolaného sedadla (setpreset + VISCA souřadnice).
- Mazání **jen fotky** vráceno do levého horního rohu karty sedadla (`deleteSlotPhoto`) — preset/pozice zůstává.
- Status serveru = jen tečka (zelená/červená), hláška připojeno/nepřipojeno jako tooltip. „Manuální ovládání kamery" místo „Ovládací prvky".
- Tlačítko **Připojit / Restartovat server** přesunuto z hlavičky do **Nastavení úplně nahoru** — jen tlačítko (bez boxu), na plnou šířku.
- Box **Záloha presetů** přebarven na **modrý** (vč. Import/Export tlačítek).
- Pose tlačítka 🧍🪑 (Sedící/Stojící) přesunuta do **lišty vlevo od „Kompaktní zobrazení"** (pravý cluster). Výplň = výplň toho boxu (`#fef3c7`), panáček/židle i rámeček = barva slov (`#92400e`; ikona přes CSS filtr s `!important` nad inline šedým filtrem).
- **Všechna tlačítka lišty CAM2 sjednocena na stejnou výšku** (42 px, `box-sizing:border-box`).
- **Border každého tlačítka = barva jeho písma/ikony** (nástrojová tlačítka přes `--btn-text`, „Kompaktní" i pose v amber `#92400e`).
- **Zrušen mód „Editace presetů sedadel" i pravý klik (kontext menu) na sedadle.** Workflow bez módů: kalibrace/úprava polohy = **Uložit preset**, přesun = drag&drop, smazání fotky = ikona koše. Funkce módu zůstávají v kódu „uspané" (nevolatelné) — snadný návrat, kdyby chyběly. V kompaktním gridu pravý klik (editace presetu) zůstává.

## ✅ UI přepracování (hotovo, čistě vizuální)

- Karta sedadla: číslo vpravo nahoře, bez „Sedadlo XX", jednotná velikost, úprava/smazání přes pravý klik (`8cc5e28`, `bc4dad7`, `958a319`).
- Seat layout: 0/1 v 6. řadě pod 38/37, řada 57-51 zarovnaná, větší mezera mezi sektory (`5acd509`, `e10bd4a`).
- Hlavička CAM2: „SKENOVAT HLEDIŠTĚ" vlevo (jednotný styl), „KOMPAKTNÍ ZOBRAZENÍ" vpravo, bez „Skrytých presetů", pose ikonky 🧍🪑 pod Skenovat (`2b05313`, `11d95b6`, `32254ce`, `c51299c`, `b0bf2b8`).
- Modal presetu: image box 4:3 na plnou šířku (`5a875b1`).

---

## 📋 Čeká na čtvrtek (živý test u kamer, s lidmi)

1. **Restart `ptz_server.py`** (kvůli VISCA) + **překalibrace sedadel** → sken po souřadnicích. Toto je priorita — vyřeší posun/cizí obličeje.
2. Ověřit **zoom sken top-center + mírnější zoom**, doladit `pickAnchorY`, `zoomSteps`, `zoomMinAcceptFrac`.
3. Fotky **top-center + bez rámečku**, doladit `facePhotoFaceAt`.
4. Případně `scanTiltMs` (fyzický tilt nudge) — vyzkoušet směr/velikost.
6. **Zoom sken: tilt nahoru před zoomem** (`zoomTiltUpMs`, default 700 ms, laditelné polem ve scan modalu) — zoom se zaměří na obličej v top-center, ne na střed/hruď. Doladit hodnotu podle záběru.
8. **Práh jistoty obličeje** (`minFaceConfidence`, default 0.90, laditelné polem) — odfiltruje falešné detekce (ruce). Log ukazuje confidence přijatých i odfiltrovaných, podle toho doladit.
7. Zadní řada (51–57) + některá sedadla (46, 43) mají **rozhozené uložené souřadnice** → překalibrovat (klik na sedadlo → joystick → Uložit preset). Prázdná sedadla chytající souseda (12, 46) = smazat fotku.
5. Rozpoznávání: nahrát osoby, doladit práh z `dist:` hodnot.

---

## 🧩 Zaparkované / otevřené nápady

- **Přidat/smazat sedadlo + přečíslování** — dynamický layout místo pevného `SEAT_LAYOUT`. Architektonické, k rozmyšlení.
- **Export/import osob** (vč. embeddingů) — ať se neztrácí lidé při přesunu složky / nové instanci (IndexedDB je per-origin).
- **Víc referenčních fotek na osobu** — robustnější rozpoznávání.

---

## 🔭 OBS integrace (nový směr)

OBS je v sále aktivní (program na TV, virtuální kamera do Zoomu, nahrávání).
- **Browser dock** (doporučeno) — appku hostovat jako Custom Browser Dock uvnitř OBS, skoro beze změny kódu (CORS proxy se přenese). Ne nativní C/C++ plugin.
- **`obs-websocket`** — propojení preset/souřadnice kamery ↔ scéna (rozpoznaný řečník → kamera + přepnutí programu = poloautomatická režie).

---

## Poznámky

- Živé testování PTZ i rozpoznávání běží **jen lokálně** na PC v sále (LAN ke kamerám). Cloud/remote session je na úpravy kódu + render UI náhledů.
- **VISCA-over-IP běží na portu 1259 (raw)**, CGI na portu 80. Stop přes CGI = `ptzstop`.
- Hardware joystick (AVMatrix PKC3500) jede přes RS485/Pelco-D a **sdílí preset paměť kamery** s appkou — proto přechod na sken po souřadnicích.
- Diagnostické skripty: `stop_test.py` (stop příkaz), `coords_test.py` (VISCA pozice/abs najetí).
