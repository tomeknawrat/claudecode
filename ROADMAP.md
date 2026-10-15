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
- **Všechna tlačítka lišty CAM2 sjednocena na stejnou výšku** (32 px, `box-sizing:border-box`).
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
