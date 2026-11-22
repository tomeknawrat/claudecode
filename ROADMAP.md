# PTZ Camera Controller — Roadmap

> Přehled hotového, rozpracovaného a dalšího směru. Doplňuje
> `KONTEXT_PRO_NOVY_CHAT.md` (popis projektu) a `SESSION_HANDOFF.md` (stav práce).
> Aktualizováno: **22. 11. 2026**. Hlavní větev: `ptzcameracontroller`.
> Hlavní soubor appky: **`SL Meeting_Ovládání PTZ kamer.html`**.

---

## ✅ Server-centrické úložiště + web přes LAN (hotovo v kódu — čeká na živý test)

Appka už nemusí běžet z `file://`. `ptz_server.py` ji servíruje přes HTTP a drží
data na serveru → dostupná z **jakéhokoli zařízení v síti** přes IP sálového PC.

- **Adresa:** `http://<IP-sálového-PC>/` (server ji po startu sám vypíše a otevře). Port je `APP_PORT` v `ptz_server.py` — **default 80** (standardní HTTP, v adrese se nepíše); když je 80 obsazený, lze změnit (pak `http://IP:<port>/`).
- **Úložiště na serveru:** složka `ptz_data/`, 4 JSON „kbelíky" — `settings`, `slots`
  (přiřazení/presety/souřadnice/layout), `presets` (cam1/cam2 vč. fotek),
  `persons` (osoby vč. fotek). API: `GET /api/data` (vše), `GET/PUT /api/data/<bucket>`
  (atomický zápis temp+rename). Jednouživatelské, **bez zámků** (v sále obsluhuje jeden člověk).
- **Appka:** `SERVER_MODE` podle `http(s)://` vs `file://`. Při startu `_hydrateFromServer()`
  natáhne data do localStorage/IndexedDB (stávající load funkce beze změny), při každém
  uložení jde „write-through" na server (`_srvPut`). Host pro WS/video je dynamický
  (`ws://${location.hostname}:8765`, WHEP `:8890`, video `:8889`). Bindy serveru přepnuty
  na `0.0.0.0` (WS, WHEP proxy, HTTP appky).
- **Migrace tvých dat:** `file://` a `http://` mají oddělené úložiště prohlížeče. Jednorázově:
  ve staré verzi **Export** → přes IP **Import** → tím se naplní server (Import pushuje všechny kbelíky).
- **`file://` zůstává jako fallback** (beze změny chování; Playwright testy dál běží z file://).
- **Otestováno v cloudu:** Python API (GET/PUT/hydrate, 400/404) + Playwright end-to-end proti
  `http://localhost/` (write-through nastavení i osoby → soubor na serveru → reload → hydrate vrátí).
  Kamery/video netestováno (nejsou v dosahu) → **nedělní živý test**.
- **🐞 Fix 22. 11. — „IP adresa není nastavena" (race condition):** v `SERVER_MODE` se `autoConnect()`
  spouštěl dřív, než async `_hydrateFromServer()` + `loadSettings()` stihly vyplnit pole IP kamer →
  `_sendCamConfigs()` v `onopen` poslal serveru **prázdnou IP** a každý PTZ/preset povel vracel
  „CAM1: IP adresa není nastavena". Opraveno: `autoConnect()` se volá **až v `_boot()` po `loadSettings()`**
  (ne na top-level), takže `onopen` čte už vyplněný DOM. Ve `file://` se chyba neprojevila (bez hydratace).
  Ověřeno Playwrightem (simulace pomalé hydratace 600 ms → na WS dorazí config se správnými IP).
- **Bez autentizace** (LAN-only, důvěryhodná síť v sále). `ptz_data/` je v `.gitignore` (osobní údaje nikdy do repa).

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
| **Přidání sedadla** | Vkládá se v číselné posloupnosti řady (17 vlevo k 16, 149 vpravo k 148), ne na kraj — `_insertSeatOrdered` | `22. 11.` |
| **Póza Sedící/Stojící** | Recall sedadla odznačí pózu (`resetPose(2)`) → po přesunu jde rovnou kliknout Stojící bez mezikroku Sedící | `22. 11.` |

## ✅ Hotovo v kódu — čeká na živý test (čtvrtek, lidé v sále)

| Oblast | Popis | Commit |
|--------|-------|--------|
| **Sken „po souřadnicích"** ⭐ | VISCA-over-IP (UDP 1259): kalibrace uloží absolutní pan/tilt/zoom, sken i recall najíždějí přímo na souřadnice — **nezávisle na preset paměti** (joystick ji přepisoval). Ověřeno round-tripem `coords_test.py` | `44bf1d4` |
| Zoom-in sken | Opt-in režim: na sedadle přiblíží a od nejtěsnějšího oddaluje, bere jen velkou centrální tvář. Cílí **top-center**, mírnější zoom (zoomSteps 2) | `7002a00`, `a236827`, `d4bf5a0` |
| Fotka sedadla | Ořez vycentrovaný na obličej (4:3), **top-center** framing, bez detekčního rámečku | `2f75614`, `c43b025`, `c062d98` |
| Volitelný tilt nudge | `_scan.scanTiltMs` (default off) — framing obličeje výš | `c43b025` |
| **Čekání na doostření** 🎯 | Varianta A (ostrost z obrazu): `_frameSharpness` + `_waitForFocus` počkají po přejezdu/zoomu, až se obraz doostří (řeší rozmazání mezi řadami), teprve pak detekce+fotka. Přepínač + max. čas v Nastavení. **Doladit prahy naostro** | `22. 11.` |
| **Dedup obličejů ve skenu** 👥 | Stejný obličej nafocený víckrát (sken odpředu → tvář z přední řady i u sedadla za ní) se přeskočí — porovnání embeddingů v rámci skenu (`capturedDescriptors`), funguje i bez DB osob. Přepínač + práh shody v Nastavení. **Doladit práh naostro** | `22. 11.` |

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

## ✅ Plovoucí okno manuálního ovládání (hotovo 19. 11.)

- **Hlavičky „PÓDIUM" / „KOMENTÁŘE" a rozbalovací lišta „Manuální ovládání kamery" odebrány** — úspora vertikálního místa (half-screen).
- Manuální ovládání se otevírá **ikonkou joysticku** v liště (CAM1 `#ctrlFloatBtn1` modrá, CAM2 `#ctrlFloatBtn2` amber) jako **plovoucí okno** (modal `position:fixed` + podklad `#ctrlBackdrop`), horní pruh v barvě kamery, hlavička s titulkem + křížek. Zavření: křížek / podklad / Escape; otevřít jedno zavře druhé.
- JS: `toggleCam1/2Controls`, `_openCtrlWindow`, `closeAllCtrlWindows`; CSS: `.cam2-controls-collapsible` (modal) + `.ctrl-backdrop` + `.ctrl-window-*`.
- Přepínač zobrazení `#seatLayoutBtn2` je nově **jen ikonka** (bez slova Detailní/Kompaktní; stav v `title`).
- *Ikonka joysticku: plně vyplněný SVG (kulička + páka + podstavec s tlačítkem) dle dodané předlohy, obarvení přes `currentColor` (CAM1 modrá, CAM2 amber).*

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

- **Pravý klik na sedadlo** (`_showSeatCtxMenu`). Sedadlo **s fotkou** → dialog „Smazat fotku?" (`#deletePhotoOverlay` — smaže fotku + checkbox „Vrátit preset na výchozí pozici?"); sedadlo **bez fotky** → kontextové menu „Skenovat a přidat fotku" (`scanSingleSeat` → `startScan(si)` jen pro jedno sedadlo). Ikonka koše na kartě odstraněna.
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

## ✅ CAM2 toolbar na ikony + zápatí 2.0 (hotovo 9. 11.)

- **Toolbar CAM2 = jen ikony** (bez textových popisků), popisek jako **tooltip**. Sladěno na **čtverec 42×42** (třída `icon-only`), pose 🧍🪑 taky 42×42. **„Kompaktní zobrazení" ponecháno s textem.** Přepínání režimu výchozích pozic mění `title` (ne text).
- **Zápatí v Nastavení** → „Ovládání kamer 2.0", datum 9. 11. 2026, bez „HTTP CGI · IP/LAN".

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

## ✅ Živý test u kamer — ověřeno (20. 11. 2026)

- ✅ **Restart `ptz_server.py` (VISCA) + překalibrace sedadel** → sken po souřadnicích funguje (vyřešen posun / cizí obličeje).
- ✅ **Zoom sken top-center + mírnější zoom** + tilt nahoru před zoomem (`zoomTiltUpMs`).
- ✅ **Fotky top-center + bez rámečku** (`facePhotoFaceAt`).
- ✅ **Překalibrace rozhozených sedadel** (zadní řada 51–57 apod.).
- ☑️ **Práh jistoty obličeje** (`minFaceConfidence` 0.90) — zatím OK.

## 🚧 Urychlení skenu — hotovo v kódu, čeká na živý test (neděle)

Zoom žebřík (tilt-up → zoom-in → oddalování s detekcí) se dřív jel i na **prázdných** sedadlech. Implementováno jako **base pre-gate** v `_zoomFindOccupant` (před nakláněním/zoomem):
- ✅ **Early-exit** (`fastSkipEmpty`): na širokém base presetu rychlá detekce s **volnějším prahem** (`baseGateConfidence` 0.50); žádná tvář → sedadlo prázdné → **přeskočí celý zoom**.
- ✅ **Přijmout base bez zoomu** (`baseAcceptFrac` 0.30): tvář už dost velká + u středu + dost jistá → fotka rovnou ze širokého záběru (přední/blízká sedadla).
- Laditelná pole **přesunuta do Nastavení → „Skenování hlediště"** (⏩ rychlý sken, 🔎 base práh obsazenosti, 🤏 přijmout od velikosti, ↑ tilt, 🙂 min. jistota).
- **Doladit naživo:** `baseGateConfidence` (když přeskakuje reálné lidi → snížit), `baseAcceptFrac` (fotky z base moc široké → zvýšit).

### Scan okno = vyskakovací popup nad boxem Komentáře (hotovo v kódu)
- Scan okno už není fullscreen přes celou appku — je to **vyskakovací karta přirozené velikosti** nad boxem Komentáře (CAM2). Backdrop box **jen zašedne/zneaktivní** (layout sedadel zůstává vidět), **Pódium (CAM1) zůstává aktivní** (`#scanOverlay` přesunut do `.panel--cam2`, třída `cam2-scanning`).
- Layout okna: **vlevo RTSP náhled (16:9, 1080), vpravo úzký vysoký sloupec stejně vysoký jako video** — nahoře statistiky, pod tím log.
- Parametry skenu přesunuty ze scan okna do Nastavení.
- Zbývá (volitelné): detekovat **během zoom-inu** a zastavit dřív; zkrátit `settleMs`/`zoomStepMs`/`zoomSettleMs`; **inkrementální sken** (přeskočit už vyfocená).

---

## ✅ Změna layoutu sedadel (#4) + responsivita (#5) — hotovo 7. 11.

- **#4 Úprava `SEAT_LAYOUT`** (po upřesnění: přidat 16, 116, 127, 138; „smazat 16" byl překlep → smazat **168**). Výsledek: levá řada 1 `[16..11]`, pravá řada 1 `[111..116]`, řada 2 `[121..127]`, řada 3 `[131..138]`, řada 6 `[161..167]`. **TOTAL_SEATS 78 → 81.** Zvoleno **bez migrace** — úložiště se jen přepočítá na novou délku, hodnoty se posunou → **nutná překalibrace** (uživatel akceptoval). Výpočet velikosti sedadla přepracován, aby se vešly i delší řady (robustní `_blockW`/`_seatTotalSide`/`_seatTotalStacked`, měřeno z reálné `clientWidth` gridu → žádné přetečení).
- **#5 Responsivní viewport — HOTOVO (CAM2).** Dosud `applyZoom`/`calcCardW` sedadla jen **zmenšoval**, aby se oba sektory vešly vedle sebe (na úzkém okně byla nečitelná). Nově: když by sedadla vedle sebe byla < 64 px, přepne se do **STACKED** režimu (třída `seat-stacked` na `<html>`): pravý sektor spadne **pod** levý (`.seat-hall-live` → sloupec) a sedadla se **zvětší** (`calcCardWStacked`, strop `STACK_MAX_C` → card ≈ 83 px). CAM1 (Pódium) odpojen od stacked velikosti (`cam1Base`), aby se nenafoukl. Ověřeno Playwrightem (1600 vedle sebe 92 px; 950 stacked 83 px, bloky nad sebou).
- **Vycentrování sektorů (7. 11.):** řady v obou blocích jsou **vycentrované** (symetrická pyramida místo zarovnání vlevo; `align-items:center`), odsazení řad (`INDENT_L/R`) vynulováno. **Výjimka: řada [0,1]** zůstává zarovnaná vlevo (`align-self:flex-start`). Celá skupina sektorů je vycentrovaná v panelu (`.seat-hall-live` `justify-content:center`, ve stacked `align-items:center`).
  - *Pozn.:* dřívější překryv „Scénka sedící" × „Uložit preset" na úzkém okně **vyřešen** přepracováním CAM1 na kompaktní ikonový pruh (viz sekce Pódium).

## ✅ Dynamický layout — minimum (hotovo 9. 11.)

- `SEAT_LAYOUT` je teď **měnitelný** (`let`), ukládá se do `localStorage` **`ptz_seat_layout`** (default = tovární rozložení `_SEAT_LAYOUT_DEFAULT`). `SEAT_NUMBERS`/`SEAT_NUM_TO_IDX`/`TOTAL_SEATS` se přepočítají přes `_rebuildSeatMaps()`.
- **Přidat/smazat sedadlo** přes dialog „Upravit sedadla" (tlačítko `+` v liště CAM2, `openSeatEditor`): přidat číslo do zvoleného bloku/řady, smazat podle čísla. Validace (duplicita/neexistence).
- **Úložiště keyované číslem sedadla:** `_remapSeatStorageByNumber` po změně layoutu přemapuje `slotCoords`/`slotPresets`/`slotDefaultCoords`/`slotAssignments` podle čísla sedadla → **kalibrace/fotky drží u svého sedadla** (ověřeno Playwrightem). Co zmizí, se zahodí.
- Layout je součástí **zálohy** (export/import v2, aplikuje se před slot poli).
- *Zatím minimum:* bez přesunu/přejmenování/2D editoru a bez „obnovit výchozí layout" (připraveno `_SEAT_LAYOUT_DEFAULT`). Smazání obsazeného sedadla nechá osiřelou preset-kartu v `state.presets[2]` (vyčistí „Smazat všechny fotky").

## 🧩 Budoucí verze

- **Databáze osob — layout hotový (20. 11.):** sloupec osob řazený podle příjmení, oficiální fotka (file picker + lightbox s tužkou), „Přidat osobu" dole. *Fotka ze skenu = placeholder, přidání nepočítá embedding. Hromadné přidání a popisek nahoře odebrány.*
- **V3.0 — Face recognition:**
  - Rozpoznávání při skenu — propojit oficiální fotky s detekcí, doladit práh z `dist:` hodnot.
  - „Přidat fotku ze skenu" dodělat (zatím placeholder).
  - Víc referenčních fotek na osobu (robustnější rozpoznávání).
- **V4.0 — OBS integrace (`obs-websocket`):** propojení preset/souřadnice kamery ↔ scéna (rozpoznaný řečník → kamera + přepnutí programu = poloautomatická režie). Alternativa hostování: **Browser dock** (appka jako Custom Browser Dock uvnitř OBS, skoro beze změny kódu). *Server-centrické úložiště (viz nahoře) je pro to ideální základ — žádný konflikt.*
- ~~**Dynamický layout — rozšíření**~~ — zahozeno (stávající přidat/smazat sedadlo zůstává).

---

## Poznámky

- Živé testování PTZ i rozpoznávání běží **jen lokálně** na PC v sále (LAN ke kamerám). Cloud/remote session je na úpravy kódu + render UI náhledů.
- **VISCA-over-IP běží na portu 1259 (raw)**, CGI na portu 80. Stop přes CGI = `ptzstop`.
- Hardware joystick (AVMatrix PKC3500) jede přes RS485/Pelco-D a **sdílí preset paměť kamery** s appkou — proto přechod na sken po souřadnicích.
- Diagnostické skripty: `stop_test.py` (stop příkaz), `coords_test.py` (VISCA pozice/abs najetí).
