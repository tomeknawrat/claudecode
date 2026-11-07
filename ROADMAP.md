# PTZ Camera Controller — Roadmap

> Přehled hotového, rozpracovaného a dalšího směru. Doplňuje
> `KONTEXT_PRO_NOVY_CHAT.md` (popis projektu) a `SESSION_HANDOFF.md` (stav práce).
> Aktualizováno: **7. 11. 2026**. Hlavní větev: `ptzcameracontroller`.
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

- **5 pevných, nemazatelných presetů** (bez kontext menu): Scénka sedící / Řečník nižší / Předsedající / Řečník vyšší / Scénka stojící (`CAM1_FIXED`, `renderCam1FixedPresets`).
- **7. 11. — přepracováno na ikonový pruh bez popisků:**
  - **Tlačítko „Přidat preset" na CAM1 úplně odstraněno** (vč. `addPresetBtn1` a jeho viditelnosti). Zůstalo jen **Uložit preset**.
  - Všech **5 presetů vedle sebe s malými mezerami** (6px, jako mezi sedadly), každá dlaždice samostatně zaoblená, `justify-content:center`.
  - **Textové popisky odstraněny**, jméno jen jako tooltip (`card.title`). Ikony **zmenšené** (person 28px, PNG scénky 26px, dlaždice v 50px).
  - **Rozlišené ikony** pro 3 „osobní" presety (`_cam1Icon`) — **jeden a tentýž panáček v saku s kravatou** (`_CAM1_SUIT`), rozlišený: **Předsedající** = panáček + vodorovná čárka (pultík) pod ním; **Řečník vyšší** = panáček + šipka nahoru vpravo (bez čárky); **Řečník nižší** = panáček + šipka dolů vlevo (bez čárky). Scénky = 2× pose-sedící / 2× pose-stojící (PNG, přebarvené na modrou).
  - **Responzivně:** na úzkém okně se pruh presetů **zalomí pod tlačítko „Uložit preset"** (`cam1-preset-layout` → `flex-wrap`). Odstraněno absolutní polohování; `equalizeCam1Tiles`/`layoutCam1Scenes` jsou no-op (layout řeší CSS flex).

## ✅ Panel Pódium (CAM1) — kompaktní lišta (hotovo)

> *Pozn. 7. 11.: tato lišta byla zjednodušena — „Přidat preset" na CAM1 zcela zrušeno, presety jsou teď malý ikonový pruh bez popisků (viz sekce výše). Body níže popisují předchozí stav.*

- Zrušeno „Přesunout". Přidáno **Uložit preset** (`saveLastPresetManual(1)` — uloží ruční doladění do posledního vyvolaného presetu). Tlačítko stylem totožné s Komentáři (`cam2-tool-btn`).
- Tlačítko vlevo, presety vpravo. *(Dřív: textový popisek, výška 92 px, přidávání od středu — nyní nahrazeno ikonovým pruhem.)*
- Styl `.cam2-tool-btn` rozšířen na obě kamery (`.cam-presets-section .cam2-tool-btn`).

## ✅ Spuštění jedním krokem (hotovo)

- **`start_ptz.bat`** (+ `start_ptz_bez_okna.vbs` pro běh bez okna) spustí `ptz_server.py`; server při startu **sám otevře appku v prohlížeči** (`_open_app`).
- Prohlížeč (sandbox) server spustit neumí → startuje se server, ten otevře stránku; tlačítko „Připojit server" slouží na (re)connect.

## 🚧 Výchozí pozice sedadel (větev `vychozi-pozice-sedadel`)

Každé sedadlo má kromě pracovní pozice i **výchozí (baseline)** pozici:
- Nové úložiště `slotDefaultCoords` (localStorage `ptz_slot_default_coords`), paralelní k `slotCoords`.
- **Režim nastavení výchozích pozic** (tlačítko „Výchozí pozice" / „Hotovo", `defaultPosMode`): klik na sedadlo najede na jeho výchozí pozici, „Uložit výchozí" uloží aktuální polohu jako výchozí (nesáhne na pracovní pozici ani preset kamery). Banner + tečkované zvýraznění gridu.
- **Normální režim** (jako dřív): úprava/ukládání pracovních pozic (`slotCoords` + setpreset).
- Vrácení pracovních pozic na výchozí (`slotCoords ← slotDefaultCoords`) je **sloučené do dialogu „Smazat všechny fotky"** — viz sekce níže (samostatné tlačítko „Vrátit výchozí" zrušeno).
- Ověřeno Playwrightem (ukládání do správného úložiště, reset, přepínání módu). Čeká na živý test.

## ✅ Mazání fotky + sloučené „Smazat všechny fotky" (hotovo 7. 11.)

- **Mazání jedné fotky = pravý klik (contextmenu) na kartě sedadla** (`makePresetCardForSlot` → `deleteSlotPhoto`); preset/pozice zůstává. **Ikonka koše na kartě odstraněna** (vč. CSS `.slot-del-photo`).
- **Tlačítko „Vrátit výchozí" sloučeno do „Smazat všechny fotky".** Klik otevře dialog (`openClearResetDialog` / `clearResetResolve`, overlay `#clearResetOverlay`) s vysvětlením:
  - Vždy: hromadné smazání všech uložených fotek/karet CAM2 (pozice presetů v kameře zůstávají).
  - **Checkbox** (`#clearResetAlsoReset`, defaultně nezaškrtnutý): *„Vrátit i pracovní pozice sedadel na uložené výchozí"* → navíc `slotCoords ← slotDefaultCoords` (`_applyResetSeatsToDefault`). Volba se zobrazí jen když existují uložené výchozí pozice.
- Ověřeno Playwrightem (reset tlačítko pryč, dialog + checkbox fungují).

## ✅ Sken — diagnostika přeskočených sedadel (hotovo 7. 11.)

- Sken prochází **jen kalibrovaná sedadla** (mají `slotCoords` nebo `slotPresets`). Nekalibrovaná se přeskakují (kamera nemá kam najet) — **nejčastější příčina „v pravém sektoru neskenuje všechna sedadla"**.
- Přidán log: `Kalibrovaných sedadel: X z Y` + `Přeskočeno (bez kalibrace): …` (výpis čísel sedadel) → hned je vidět, co dokalibrovat.

## ✅ Drag & drop fotek mezi sedadly (hotovo)

- Ve výchozím (detailním) zobrazení lze fotku **chytit myší a přetáhnout** na jiné sedadlo **bez přepínání do režimu „Přesunout"**.
- Tažení se spustí až po pohybu nad práh (6 px) — krátký klik (vyvolat preset) i hold (uložit pozici) zůstávají funkční.
- Tlačítko „Přesunout" je v seat layoutu skryté (v klasickém/kompaktním gridu zůstává).
- Ověřeno simulací v Playwrightu (přesun přiřazení + nulový posun při kliku).

## ✅ UI lišta CAM2 + „Uložit preset" (hotovo)

- 4 nástrojová tlačítka sladěná do **stejné kompozice jako „Kompaktní zobrazení"** (světlá soft výplň + střední ohraničení + tmavý sytý text = dobrá čitelnost), každé vlastní barva přes `--btn-bg/--btn-border/--btn-text`: **Skenovat hlediště** (fialová), **Přidat sedadlo** (modrá), **Uložit preset** (zelená), **Smazat všechny fotky** (červená).
- **Uložit preset** (`saveSeatPresetManual`) — po kliku na sedadlo a ručním doladění joystickem uloží **aktuální polohu** kamery do presetu posledního vyvolaného sedadla (setpreset + VISCA souřadnice).
- Mazání **jen fotky** (`deleteSlotPhoto`) — preset/pozice zůstává. *(7. 11.: přesunuto z ikony koše na **pravý klik** na kartě, viz novější sekce.)*
- Status serveru = jen tečka (zelená/červená), hláška připojeno/nepřipojeno jako tooltip. „Manuální ovládání kamery" místo „Ovládací prvky".
- Tlačítko **Připojit / Restartovat server** přesunuto z hlavičky do **Nastavení úplně nahoru** — jen tlačítko (bez boxu), na plnou šířku.
- Box **Záloha presetů** přebarven na **modrý** (vč. Import/Export tlačítek).
- Pose tlačítka 🧍🪑 (Sedící/Stojící) přesunuta do **lišty vlevo od „Kompaktní zobrazení"** (pravý cluster). Výplň = výplň toho boxu (`#fef3c7`), panáček/židle i rámeček = barva slov (`#92400e`; ikona přes CSS filtr s `!important` nad inline šedým filtrem).
- **Všechna tlačítka lišty CAM2 sjednocena na stejnou výšku** (42 px, `box-sizing:border-box`).
- **Border každého tlačítka = barva jeho písma/ikony** (nástrojová tlačítka přes `--btn-text`, „Kompaktní" i pose v amber `#92400e`).
- **Zrušen mód „Editace presetů sedadel".** Workflow bez módů: kalibrace/úprava polohy = **Uložit preset**, přesun = drag&drop. *(7. 11.: smazání fotky vráceno na **pravý klik** na kartě; ikona koše odstraněna.)* Funkce módu zůstávají v kódu „uspané" (nevolatelné). V kompaktním gridu pravý klik (editace presetu) zůstává.

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

## ✅ Změna layoutu sedadel (#4) + responsivita (#5) — hotovo 7. 11.

- **#4 Úprava `SEAT_LAYOUT`** (po upřesnění: přidat 16, 116, 127, 138; „smazat 16" byl překlep → smazat **168**). Výsledek: levá řada 1 `[16..11]`, pravá řada 1 `[111..116]`, řada 2 `[121..127]`, řada 3 `[131..138]`, řada 6 `[161..167]`. **TOTAL_SEATS 78 → 81.** Zvoleno **bez migrace** — úložiště se jen přepočítá na novou délku, hodnoty se posunou → **nutná překalibrace** (uživatel akceptoval). Výpočet velikosti sedadla přepracován, aby se vešly i delší řady (robustní `_blockW`/`_seatTotalSide`/`_seatTotalStacked`, měřeno z reálné `clientWidth` gridu → žádné přetečení).
- **#5 Responsivní viewport — HOTOVO (CAM2).** Dosud `applyZoom`/`calcCardW` sedadla jen **zmenšoval**, aby se oba sektory vešly vedle sebe (na úzkém okně byla nečitelná). Nově: když by sedadla vedle sebe byla < 64 px, přepne se do **STACKED** režimu (třída `seat-stacked` na `<html>`): pravý sektor spadne **pod** levý (`.seat-hall-live` → sloupec) a sedadla se **zvětší** (`calcCardWStacked`, strop `STACK_MAX_C` → card ≈ 83 px). CAM1 (Pódium) odpojen od stacked velikosti (`cam1Base`), aby se nenafoukl. Ověřeno Playwrightem (1600 vedle sebe 92 px; 950 stacked 83 px, bloky nad sebou).
- **Vycentrování sektorů (7. 11.):** řady v obou blocích jsou **vycentrované** (symetrická pyramida místo zarovnání vlevo; `align-items:center`), odsazení řad (`INDENT_L/R`) vynulováno. **Výjimka: řada [0,1]** zůstává zarovnaná vlevo (`align-self:flex-start`). Celá skupina sektorů je vycentrovaná v panelu (`.seat-hall-live` `justify-content:center`, ve stacked `align-items:center`).
  - *Pozn.:* na ~960 px se v **Pódiu** překrývá první dlaždice „Scénka sedící" s tlačítkem „Uložit preset" — **pre-existující** layout CAM1 (ne regrese z této změny), k doladění zvlášť.

## 🧩 Zaparkované / otevřené nápady

- **Dynamický layout** místo pevného `SEAT_LAYOUT` (plné přidání/mazání/přečíslování sedadel z UI). Architektonické.
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
