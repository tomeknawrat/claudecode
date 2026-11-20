# Session Handoff — PTZ Camera Controller

> Strukturované shrnutí práce z pracovní session (Claude Code, lokálně na Windows PC).
> **Není to doslovný přepis chatu** — je to kontext pro pokračování v nové (i remote) session.
> Doplňuje `KONTEXT_PRO_NOVY_CHAT.md`, který popisuje celý projekt. Tento soubor popisuje, co se dělo naposledy a co zbývá.

## TL;DR — kde to stojí (aktualizace 20. 11. 2026)

- ✅ **Scan okno = vyskakovací popup nad boxem Komentáře** (20. 11.) — „Skenovat hlediště" už není fullscreen; `#scanOverlay` je přesunutý (JS `_mountScanInCam2`) do `.panel--cam2` jako poloprůhledný backdrop → box Komentáře (CAM2) **jen zašedne/zneaktivní** (layout zůstává vidět), **Pódium (CAM1) zůstává aktivní**. Samotné okno je **karta přirozené velikosti** (ne na celou plochu); panel při skenu dostane třídu `cam2-scanning` (min-height 480px). Layout okna: **vlevo RTSP náhled 16:9 (`width:min(560px,58vw)`), vpravo úzký sloupec stejně vysoký jako video** (`clamp(150px,20vw,200px)`, `align-self:stretch`) — nahoře statistiky (Sedadla/Extra/Přeskočeno + progress), pod tím log. 5 parametrů skenu (tilt, min. jistota, rychlý sken, base práh, přijmout bez zoomu) **přesunuto do Nastavení → sekce „Skenování hlediště"** (stejná ID + onchange na `_scan.*`). Ověřeno Playwrightem (popup < box, video 16:9 560px, log sloupec = výška videa 315px, Pódium klikatelné, params v draweru) + screenshot.

- ⏳ **Server-centrické úložiště + web přes LAN** (20. 11., hotovo v kódu, čeká na nedělní živý test) — `ptz_server.py` servíruje appku přes HTTP (`http://<IP-PC>:8080/`) a drží data na serveru (`ptz_data/`, 4 JSON kbelíky `settings|slots|presets|persons`, API `GET /api/data` + `GET/PUT /api/data/<bucket>`, atomický zápis). Appka: `SERVER_MODE` podle protokolu, `_hydrateFromServer()` při startu + `_srvPut()` write-through; host WS/videa dynamický. Bindy WS/WHEP/HTTP na `0.0.0.0`. `file://` zůstává jako fallback (beze změny). **Jednouživatelské, bez zámků** (uživatel výslovně: víc zařízení najednou nikdy needitovat). Migrace dat: Export (stará verze) → Import (přes IP). Otestováno v cloudu: Python API + Playwright end-to-end (write-through → soubor → reload → hydrate). `ptz_data/` v `.gitignore` (osobní údaje).

- ✅ **Manuální ovládání kamery = plovoucí okno** (19. 11.) — otevírá ikonka joysticku v liště (CAM1 modrá, CAM2 amber); hlavičky „PÓDIUM"/„KOMENTÁŘE" i stará rozbalovací lišta odebrány kvůli úspoře místa na half-screen. Přepínač zobrazení (`#seatLayoutBtn2`) je teď jen ikonka.


- ✅ **Zastavování kamery — VYŘEŠENO a ověřeno naostro** — pan/tilt stop je `ptzstop`, ne `stop`.
- ✅ **Video náhled (WHEP) — VYŘEŠENO** — CORS proxy v `ptz_server.py` (:8890) obchází CORS MediaMTX.
- ✅ **Face recognition opraveno** — appka už nezamrzá na „Počítám embedding".
- ✅ **UI přepracování hotové** — karty sedadel, seat layout, hlavička CAM2, pose ikonky.
- ⏳ **Sken „po souřadnicích" (VISCA-over-IP) hotový v kódu** — čeká na živý test ve čtvrtek (restart serveru + překalibrace sedadel). Vznikl proto, že hardware joystick (AVMatrix PKC3500) přepsal sdílenou preset paměť kamery.
- ⏳ **Zoom-in sken + fotky top-center/bez rámečku** — hotové v kódu, čeká na doladění naostro. **10. 11.: zoom-in sken je teď defaultní auto funkce napevno v kódu (`_scan.zoomScan = true`); zaškrtávátko + hláška ve scan modalu zrušeny.**
- ✅ **Drag&drop fotek mezi sedadly** ve výchozím zobrazení (bez módu „Přesunout") — hotovo.
- ✅ **Zrušen mód „Editace presetů sedadel"** — workflow bez módů (Uložit preset / drag&drop). Funkce módu zůstávají v kódu uspané.
- ✅ **Pravý klik na sedadlo** (16. 11.) — s fotkou: dialog „Smazat fotku?" (smazat + checkbox „Vrátit preset na výchozí pozici?"); bez fotky: menu „Skenovat a přidat fotku" (sken jen jednoho sedadla). Dřív pravý klik rovnou mazal fotku.
- ✅ **„Vrátit výchozí" sloučeno do „Smazat všechny fotky"** (7. 11.) — dialog s checkboxem (hromadné mazání fotek vždy; volitelně i vrácení pozic na výchozí).
- ✅ **Responsivní viewport CAM2** (7. 11.) — na úzkém okně (split-screen) pravý sektor pod levý + zvětšená sedadla (stacked režim).
- ✅ **Layout sedadel upraven** (7. 11.) — přidána 16, 116, 127, 138; odebrána 168 (TOTAL_SEATS 81). Bez migrace → **po nasazení překalibrovat**.
- ✅ **Spuštění jedním krokem** — `start_ptz.bat` / `start_ptz_bez_okna.vbs`; server při startu sám otevře appku v prohlížeči.
- ✅ **Fix recall obsazeného sedadla „do stropu"** — klik posílal `gotopreset` na joystickem přepsaný preset. Nově recall **vždy po souřadnicích** (coords-first), obsluhuje ho **slot** (pointer eventy) pro prázdná i obsazená sedadla — mouse eventy na kartě jsou potlačené preventDefaultem. Souřadnice samotné beze změny.
- ✅ **Panel Pódium (CAM1)** — **5 pevných nemazatelných presetů** (Scénka sedící | Řečník nižší/Předsedající/Řečník vyšší | Scénka stojící). **7. 11.: „Přidat preset" zrušeno; ikonový pruh bez mezer a bez popisků, rozlišené ikony, na úzkém okně se zalomí pod „Uložit preset".** Jen „Uložit preset" vlevo.
- ✅ **Sektory sedadel vycentrované** (7. 11.) — symetrická pyramida, kromě řady [0,1] (vlevo).
- ✅ **Výchozí (baseline) pozice sedadel** — režim nastavení výchozích pozic; vrácení pozic na výchozí je teď v dialogu „Smazat všechny fotky" (sloučeno do `ptzcameracontroller`).
- ✅ **Kompletní záloha/obnova** (export v2) — presety+fotky, souřadnice, výchozí pozice, nastavení, osoby; pro přenos na jiný PC.
- ✅ **Tlačítko Připojit/Restartovat server** přesunuto z hlavičky do Nastavení (úplně nahoru, samostatné tlačítko bez boxu). Box Záloha presetů přebarven na modrý; pose tlačítka 🧍🪑 sladěna s „Kompaktní zobrazení".

> Detailní přehled stavu a dalšího směru je v `ROADMAP.md`.

---

## Záznamy dne

### 20. 11. 2026 — Databáze osob: nový layout seznamu (bez face recognition, to je v3.0)
- **Modal „Databáze osob" předělán:** sloupec osob **řazený podle příjmení** (`_sortPersons`/`_personSurname`, cs collation). Řádek = jméno + **oficiální fotka** + **fotka ze skenu** + koš. „Přidat osobu" (jen jméno) **dole**; po přidání se znovu seřadí.
- **Oficiální fotka:** prázdná = tlačítko → průzkumník souborů; s fotkou = náhled → **lightbox** se zvětšenou fotkou + **tužka** (úprava = znovu průzkumník). Sdílený `#personPhotoInput`, `_pickPersonPhoto`/`handlePersonPhotoFile`/`_openPhotoLightbox`/`_editLightboxPhoto`. Pole `officialPhoto` (fallback na starý `photoDataUrl`).
- **Fotka ze skenu** (`scanPhoto`) — tlačítko zatím placeholder (`_scanPhotoTodo`), dodělá se později.
- Přidání osoby **už nepočítá embedding** (face recognition = v3.0). Ověřeno Playwrightem (řazení, náhled, lightbox, tužka).
- **Hromadný import** (`bulkAddPersons`, `<details>` „Hromadně přidat" + textarea, jedno jméno na řádek, přeskočí duplicity) — protože z cloudu nejde zapsat do IndexedDB v prohlížeči uživatele. Jména ve formátu „Příjmení Jméno", řazení celého jména (cs) = podle příjmení. Ověřeno s reálným seznamem (48 osob, správné české řazení vč. „Ch"). **Reálná jména zůstávají jen v prohlížeči — nejsou v repu** (seznam předán uživateli k vložení).

### 20. 11. 2026 — urychlení skenu: base pre-gate (čeká na nedělní živý test)
- **Early-exit v `_zoomFindOccupant`:** před nakláněním/zoomem rychlá detekce na širokém base presetu s **volnějším prahem** (`baseGateConfidence` 0.50); žádná tvář → `fastSkipEmpty` přeskočí celý zoom žebřík (hlavní úspora, hlavně prázdná sedadla).
- **Přijmout bez zoomu:** tvář na base už dost velká (`baseAcceptFrac` 0.30) + u středu + conf ≥ `minFaceConfidence` → fotka rovnou z base (přední/blízká sedadla).
- `_detectAndDraw(confThr)` má volitelný práh (base pre-gate volá s volnějším). Laditelná pole ve scan modalu (⏩/🔎/🤏). Ověřeno Playwrightem (stuby): prázdné → 0 zoom volání; velká tvář → bez zoomu; malá → projde do zoomu; vypnuto → zpětně kompatibilní.
- **Nedělní live test:** doladit `baseGateConfidence`/`baseAcceptFrac` podle toho, jestli přeskakuje reálné lidi nebo dělá moc široké fotky.

### 20. 11. 2026 — živý test ověřen + roadmap přebucketován
- **Živý test u kamer prošel:** restart serveru + překalibrace (sken po souřadnicích), zoom sken top-center + mírnější zoom + tilt-up, fotky top-center bez rámečku, překalibrace rozhozených sedadel. Práh jistoty obličeje zatím OK.
- **Otevřený bod — urychlení skenu:** zoom žebřík se jede i na prázdných sedadlech. Plán: early-exit (detekce na base presetu s volnějším prahem → bez tváře přeskočit zoom) + přijmout base záběr bez zoomu u velkých/centrovaných tváří. **Čeká na odsouhlasení implementace.**
- **Roadmap:** rozpoznávání/osoby/víc fotek → **V3.0**; `obs-websocket` → **V4.0**; **dynamický layout — rozšíření zahozeno** (stávající přidat/smazat sedadlo zůstává).

### 19. 11. 2026 — plovoucí okno tažitelné + joystick sladěn + přejmenování
- **Plovoucí okno manuálního ovládání je teď tažitelné** — chytni za hlavičku (`_ctrlMakeDraggable`, pointer eventy, `setPointerCapture`) a přetáhni kamkoli (pozice drží i po zavření/otevření). **Backdrop odstraněn** → layout pod oknem zůstává aktivní. Zavření: křížek / Escape / znovu klik na ikonku (klik mimo už nezavírá).
- **Joystick CAM2** má teď třídy `seat-layout-btn seat-layout-btn--main` + override na `#fef3c7`/`#92400e` → vypadá i se chová **úplně stejně jako pose (sedí/stojí) a Kompaktní** (dřív amber `#d97706` / jiný styl `cam2-tool-btn`).
- **Přejmenování popisků (tooltipů):** přepínač zobrazení → „Kompaktní zobrazení" / „Celkové zobrazení"; pose → „Pozice sedící" / „Pozice stojící".

### 19. 11. 2026 — joystick CAM2 amber + ikonka přepínače drží velikost na úzkém okně
- **Joystick CAM2 (Komentáře)** vrácen na **amber** (`--amber-soft`/`--amber-d`) — jako tlačítko Kompaktní (předchozí indigo zrušeno dle upřesnění).
- **Ikonka přepínače zobrazení** se na úzkém okně (`@media max-width:1100px`) zmenšovala (`.seat-layout-btn svg { 13px !important }`). Opraveno: `#seatLayoutBtn2` + `#seatLayoutBtn2 svg` mají velikost s `!important` (42×42 / 26px), takže drží stejně jako na fullscreen a jako ostatní ikonová tlačítka. Ověřeno na 1500px i 820px.

### 19. 11. 2026 — ikonka přepínače (filled) + úpravy detailního přehledu
- **Ikonka přepínače zobrazení** (`#seatLayoutBtn2`) překreslena na **plně vyplněnou mřížku 3×3** (9 `rect fill=currentColor`), ať vizuálně odpovídá ostatním ikonám (dřív tenké obrysové čtverečky).
- **Detailní kartový přehled (`renderPresets`, `presetsGrid2`):**
  - **Bez popisku** — spodní text „Sedadlo XX" (`preset-name`) z karet odstraněn.
  - **Číslo = číslo sedadla** (z názvu „Sedadlo XX"), ne pořadí v gridu (`idx+1`), a **vpravo nahoře** (stejná strana jako v kompaktním plánku; CSS `.panel--cam2 .preset-card .preset-number`).
  - **Jen vyfocená sedadla** — karta bez fotky (`!p.img`) se nevykresluje (po smazání fotky zmizí, nezůstane placeholder s postavičkou). Když po filtru nic nezbude, ukáže se prázdný stav.

### 19. 11. 2026 — doladění joysticků + pevná velikost přepínače zobrazení
- **Joystick CAM1 (Pódium)** přesunut z levého sloupce **doprava** v liště presetů (jako u CAM2) — úspora vertikálního místa. (`#ctrlFloatBtn1` je teď v `.cam1-preset-spacer`, zarovnaný vpravo, 42×42.)
- **Joystick CAM2 (Komentáře)** přebarven na **indigo** (`#eef2ff`/`#c7d2fe`/`#4f46e5`) — odlišná barva od amber tématu, jako ostatní barevná tlačítka v liště.
- **Přepínač zobrazení `#seatLayoutBtn2`** má teď **pevnou velikost 42×42** jako ostatní ikonová tlačítka (dřív 46×42, „měnil velikost"). Ikona filled viz záznam výše (19. 11.).

### 19. 11. 2026 — smazání fotky → sedadlo zpět na defaultní prázdné
- Po smazání fotky sedadla se slot vrací na **defaultní prázdný vzhled** (přerušovaný rámeček + číslo), ne na kartu s placeholder „postavičkou".
- Oprava v renderu: kartu sedadla (`makePresetCardForSlot`) vykresli jen když preset **skutečně má fotku** (`preset.img`); bez fotky → větev prázdného sedadla (`slot-empty-label` + `slot-has-calib`). Skryté presety se v hide-módu ukazují dál. Změna v `_makeViewSlotOld` i dormantním `_makeViewSlot`.
- Preset, souřadnice i přiřazení zůstávají (recall funguje dál; pravý klik na takové sedadlo nabídne „Skenovat a přidat fotku", protože `hasPhoto` už je false). Ověřeno Playwrightem.

### 19. 11. 2026 — plovoucí okno manuálního ovládání + úspora vertikálního místa
- **Hlavičky „PÓDIUM" / „KOMENTÁŘE" odebrány** (lišty `.panel-title` obou panelů). Důvod: úspora vertikálního místa na half-screen. S nimi zmizela i lišta-přepínač „Manuální ovládání kamery ▼".
- **Manuální ovládání kamery = plovoucí okno.** Místo inline rozbalovací sekce se ovládání otevírá přes **ikonku joysticku** v liště:
  - CAM1: `#ctrlFloatBtn1` (modrá) v levém sloupci u „Uložit preset".
  - CAM2: `#ctrlFloatBtn2` (amber) jako první v nástrojové liště.
  - Okno = vycentrovaný modal (`position:fixed`), horní pruh v barvě kamery, hlavička s titulkem „Manuální ovládání kamery — Pódium/Komentáře" + křížek; pod ním původní `controls-row` (PTZ pad, zoom, focus, pozice).
  - Podklad `#ctrlBackdrop` (ztmavení); zavření křížkem, klikem na podklad nebo Escape; otevření jednoho okna zavře druhé. JS: `toggleCam1/2Controls`, `_openCtrlWindow`, `closeAllCtrlWindows` (nahradily starou arrow-collapse logiku).
  - CSS: `.cam2-controls-collapsible` otevřená = modal, `.collapsed` = `display:none`; nové `.ctrl-backdrop`, `.ctrl-window-head/-title/-close`. Prázdné `.panel-body` obou kamer má `padding-top:0` (nezabírá místo).
- **Tlačítko přepnutí zobrazení (Detailní/Kompaktní) = jen ikonka.** `#seatLayoutBtn2` už nemá textový popisek (`#seatLayoutBtnLabel` odstraněn); stav napovídá `title` (přepínán v `toggleSeatLayout`).
- Pozn.: ikonka joysticku = plně vyplněný SVG dle dodané předlohy (19. 11.), `currentColor` (CAM1 modrá, CAM2 amber).
- Ověřeno Playwrightem (otevření/zavření obou oken, backdrop, Escape, přepnutí, ikonkový přepínač) + `node --check`.

### 16. 11. 2026 — rámečky boxů + sjednocené hover chování tlačítek
- **Rámeček panelů:** barevný `border-top: 3px` zůstává jen nahoře (zbytek 1px šedý — barevný rámeček kolem celého boxu byl vyzkoušen, ale uživateli se nelíbil, vráceno). `.panel` dostal **`overflow: hidden`** → vnitřní obsah se ořízne na `border-radius` → **spodní rohy zakulacené** jako horní.
- **Hover tlačítek** sjednocen s `.cam2-tool-btn` (jen lehce ztmavit pozadí, rámeček + opacity zůstanou):
  - CAM1 Pódium ikony (`.cam1-fixed-preset` + `.preset-card`): odstraněno staré `.panel--cam1 .preset-card:hover` (měnilo border na blue-mid + stín-pop) → teď border zůstává blue-d, pozadí ztmaví `#eff6ff→#dbeafe`.
  - `.preset-card:hover` (CAM2 sedadla/presety) → jen `background: var(--surface2)` (dřív amber-soft + amber border + stín).
  - `.cam2-pose .pose-btn:hover` (sedící/stojící) → `color-mix(10% #92400e, #fef3c7)`, border `#92400e` zůstává (dřív se měnil na amber-mid).
  - Prázdná sedadla `.seat-slot.slot-has-calib:hover` → jen ztmavit (`surface3`), border zůstává.
  - Tlačítko **KOMPAKTNÍ** (`.seat-layout-btn--main`): hover v neaktivním i aktivním stavu (`.active:hover`) jen ztmaví výplň (`color-mix`), border zůstává (dřív měnil border na #92400e + stín-pop; v aktivním stavu navíc hover přebíjelo `.active`).
  - Databáze osob / Nastavení **nezměněny** (dle zadání).
- Ověřeno Playwrightem (rámečky + rohy, hover čísla i vizuál).

### 16. 11. 2026 — sjednocení hoveru v manuálním ovládání kamery
- Všechna tlačítka sekce „Manuální ovládání kamery" (šipky `.ptz-btn`, domeček `.ptz-center`, zoom `.zoom-btn`, focus `.focus-btn`, AF/MF `.focus-pill`) v obou boxech měla hover s **barevnou výplní (blue/amber-soft) + změnou borderu + přebarvením ikony + u šipek navíc scale(1.05) + stín-pop**. Sjednoceno na chování jako ostatní: **hover = jen `background: var(--surface3)`** (lehké ztmavení), border, ikona i stín beze změny, bez scale.
- Odstraněny všechny barevné `:hover` (obecné i panel-scoped CAM1/CAM2) i `:hover svg` přebarvení; **AKTIVNÍ/PRESSED stavy** (barevná výplň při kliku, AF/MF `.active`) zůstaly. Smazán i mrtvý `.panel--cam2 .zf-btn:hover` (modrý hover v amber boxu).

### 16. 11. 2026 — symetrické okraje layoutu + zarovnání hlavičky
- `.app` padding `16px 16px 16px 0` → **`16px`** (dřív byly boxy Pódium/Komentáře vlevo nalepené, vpravo 16px). `header` padding `0 24px` → **`0 16px`**.
- Výsledek: title „Ovládání kamer" i levé hrany obou boxů = 16px zleva; NASTAVENÍ i pravé hrany boxů = okraj−16px. Databáze osob + stavová tečka se posunuly s header-right (gap 10px zachován). Ověřeno Playwrightem (vše na 16 / W−16).

### 16. 11. 2026 — mazání fotky sedadla = dialog (místo položek v menu)
- Situace „sedadlo s fotkou" už **neukazuje dvoupoložkové kontextové menu**, ale rovnou **dialog „Smazat fotku?"** (`#deletePhotoOverlay`, `openDeletePhotoDialog`/`deletePhotoResolve`) — modelovaný podle hromadného „Smazat všechny fotky?", ale pro jedno sedadlo: text o jedné fotce + checkbox „Vrátit preset na výchozí pozici?". Potvrzení = `deleteSlotPhoto` (+ volitelně `_resetSeatToDefault`).
- `_resetSeatToDefault` už **nehýbe kamerou** (jen přepíše uloženou pracovní pozici na výchozí, jako hromadný `_applyResetSeatsToDefault`).
- Sedadlo bez fotky zůstává kontextové menu „Skenovat a přidat fotku". Nepoužité ikony `_ICON_TRASH`/`_ICON_RESET` odstraněny.
- Ověřeno `node --check` + Playwright (dialog obsah + akce, prázdné sedadlo menu, bez chyb).

### 16. 11. 2026 — fix bílého pruhu pod PÓDIUM
- Mezi titulkem **PÓDIUM** a modrým pruhem presetů byl **8px bílý pruh** = prázdné `.panel--cam1 .panel-body` (padding-top 8px) obalující SBALENÉ manuální ovládání (0 px). CAM2 problém nemá (titulek je uvnitř body).
- Fix: horní 8px mezera šipek se přesunula z panel-body do `.controls-row` (`padding-top: 8px`, teď sdíleně obě cam) a `.panel--cam1 .panel-body { padding-top: 0 }`. Sbalené manuální ovládání tak nezabírá → modrý pruh jde rovnou pod titulek (jako amber u CAM2). Rozbalené: šipky pořád 8 px nahoře i dole (ověřeno).

### 16. 11. 2026 — kontextové menu sedadla (pravý klik)
- **Pravý klik na sedadlo** (dřív rovnou mazal fotku) teď otevírá **kontextové menu** `_showSeatCtxMenu` (reuse `.ctx-menu`/`_closeCtxMenu`), navázané na úrovni `.seat-slot` ve `_makeViewSlotOld` (ne na kartě — starý `contextmenu` handler na kartě odstraněn, aby nekradl event přes stopPropagation).
- **Dvě situace:**
  - sedadlo **s fotkou** → „Smazat fotku" (`deleteSlotPhoto(2, presetIdx)`) + „Vrátit na výchozí pozici" (`_resetSeatToDefault(si, seatNum)` — `slotCoords[si] ← slotDefaultCoords[si]`, uloží a `_wsAbsMove` fyzicky najede; když chybí výchozí pozice → toast/log, nic se nestane);
  - sedadlo **bez fotky** → „Skenovat a přidat fotku" (`scanSingleSeat(si, seatNum)` → `openScanModal()` + `startScan(si)`).
- **`startScan(targetSlotIdx = null)`** — nový parametr: když je zadán, do `calibrated` jde jen to jedno sedadlo; nekalibrované (bez coords i preset) → log err a konec. `scanSingleSeat` předem ověří kalibraci (jinak toast, scan se neotevře).
- **Ikonky menu** sladěné s hlavním layoutem: „Vrátit na výchozí pozici" = vlajka (jako `defaultModeBtn2`), „Skenovat a přidat fotku" = scan ikona (osoba v rámečku, jako `scanBtn`).
- Ověřeno `node --check` + Playwright: menu se v obou situacích renderuje správně, akce (smazat/reset/guard scanu) fungují bez chyb.

### 10. 11. 2026 — manuální ovládání kamer: čištění + sjednocení CAM1↔CAM2
- **Popisky sekcí** „Pohyb kamery"/„Zoom"/„Zaostřování" odstraněny v obou cam (`ctrl-label`).
- **Tooltipy:** AF → „automatické zaostření", MF → „manuální zaostření". **Smazané tooltipy** šipek + domečku (`.ptz-btn`) a zoom +/- (`.zoom-btn`) v obou panelech (scan modal beze změny).
- **Sjednocení CAM1 podle CAM2:** skupina „Pozice" v manuálním ovládání CAM1 skryta (`hideCam1PoseGroup`) — CAM2 ji taky nemá (pose přesunuto do lišty). `#pose1-sit/#pose1-stand img` **zůstávají v DOM** (display:none) jako zdroj obrázků pro scénka presety v Pódiu.
- **Odstup:** `.ctrl-divider` margin 16→3px (čára blíž k tlačítkům), banner výchozích pozic margin symetricky (8px nahoře i dole).
- **Footer:** datum aktualizace 10. 11. 2026.

### 10. 11. 2026 (pokračování) — doladění manuálního ovládání + scan modal
- **AF/MF tooltipy** (upřesnění oproti výše): velké první písmeno → „Automatické zaostření" / „Manuální zaostření" (`fm1auto/fm1manual/fm2auto/fm2manual`, oba panely).
- **Focus tlačítka Blíže/Dále:** `title` úplně odstraněn z `.focus-btn` (`focusnear`/`focusfar`) v obou panelech — při přepnutí na MF se už hláška neukazuje.
- **Divider-mezera (náhrada margin triku výše):** `.controls-row` změněn na `align-items: center` → kratší skupiny (zoom, focus) se vertikálně vycentrují, takže přerušovaná čára (`.ctrl-divider`, `align-self:stretch`) má stejnou mezeru nad i pod tlačítky (ověřeno Playwrightem: zoom 26 px nahoře i dole, focus 33 px). Platí pro CAM1 i CAM2 (sdílené CSS).
- **Banner výchozích pozic:** spodní margin 8→16 px, aby přerušovaný outline seat gridu (`outline-offset:6px`) seděl 8 px pod boxem = stejně jako mezera nad boxem (dřív outline nalepený přesně na spodní hranu, mezera 0 px).
- **Žlutá pod spodní dashed hranou:** `.seat-layout-grid.default-pos-mode` dostal `margin-bottom: 6px` → žlutý panel (`.cam-presets-section`) pokračuje 8 px pod spodní přerušovanou hranou (symetricky k horní mezeře čára↔banner).
- **Odstup šipek od hran boxu manuálního ovládání (obě cam, symetrie 8 px):** `.controls-row` dostal `padding-bottom: 8px` (spodní šipky byly nalepené na spodní čáru boxu). CAM2 má titulek UVNITŘ panel-body (CAM1 venku), takže horních 8 px chybělo → přidáno `.panel--cam2 .controls-row { padding-top: 8px }`. Ověřeno Playwrightem: obě cam 8 px nahoře i dole.
- **Scan modal „Skenování hlediště":**
  - Titulek zkrácen: „Skenování hlediště — Kamera pro komentáře" → „Skenování hlediště".
  - **Smazáno** kompaktní manuální PTZ ovládání (Pohyb kamery + Zoom) uvnitř modalu — při automatickém skenu není potřeba.
  - **Zoom-in sken napevno jako default** (`_scan.zoomScan = true`); zaškrtávátko `#zoomScanToggle` + hláška smazány. Tuning inputy (tilt před zoomem, min. jistota obličeje) zůstaly.
- Ověřeno `node --check` (OK) + Playwright render.

### 10. 11. 2026 (pokračování 3) — Databáze osob (modal) + designové odstupy
- **„Databáze osob" zprovozněna:** sekce „Osoby (rozpoznávání tváří)" **přesunuta z Nastavení** do samostatného modalu `#personsDbOverlay` (vzor `.modal-overlay`/`.modal`). Tlačítko `personsDbBtn` v hlavičce teď volá `openPersonsDb()` (dřív toast; opacity .6 zrušena), `closePersonsDb()` zavírá. Obsah 1:1 (seznam osob, přidání jméno+fotka, status, práh rozpoznávání). `openPersonsDb` při otevření volá `_renderPersonsList()` + sync hodnoty slideru. Zatím basic — další práce plánovaná na **v3.0**.
- **Manuální ovládání — symetrie 8 px** (viz pokračování 2): `.controls-row` `padding-bottom:8px` + `.panel--cam2 .controls-row { padding-top:8px }`.
- **Žlutá pod dashed hranou** (viz pokračování 2): `.default-pos-mode` `margin-bottom:6px`.

### 10. 11. 2026 — UI úpravy po lokálním testu layoutu
- **Stacked:** odstraněna dělicí lajna mezi sektory (gap zvětšen na 26px).
- **Fix:** tužka/koš se už nezmenšují na úzkém okně — v `@media max-width:1100px` přidán override `.icon-only svg` (26px, scan 30px) přes `!important` (předtím `.add-preset-btn svg`/`.hide-presets-btn svg` 13px !important vyhrávalo).
- **Tooltipy:** Uložit → „Uložit aktuální pozici do posledního vybraného presetu"; Výchozí pozice → „Nastavit výchozí pozice sedadel"; Koš → „Smazat všechny fotky" (i v `toggleDefaultPosMode`).
- **Dialog „Smazat všechny fotky":** titulek s otazníkem, text zkrácen na „Smažou se všechny momentálně uložené fotky na sedadlech.", odstraněno „Akce je nevratná.", checkbox **vždy viditelný** s textem „Vrátit presety na výchozí pozice?".
- **Přepínač zobrazení:** „Detailní"/„Kompaktní" (vyhozeno „ZOBRAZENÍ").
- **Hlavička:** tlačítko **„Databáze osob"** (`personsDbBtn`, users ikona) mezi stavovou tečku a Nastavení. **10. 11. 2026 zprovozněno** — otevírá modal „Databáze osob" (`openPersonsDb()`), do kterého byla přesunuta sekce „Osoby (rozpoznávání tváří)" z Nastavení (dřív jen toast „zatím nedostupné"; opacity .6 zrušena).
- **Dialog sedadel:** titulek „Přidat/smazat sedadlo", odstraněna věta pod ním.
- **Fix kompaktní lišty:** tlačítko „Přesunout" (`editOrderBtn2`) **skryto** z lišty (`_updateCam2BtnVisibility` ho vždy `hide`) — pozůstatek starého workflow, v kompaktním gridu se mu přepisoval obsah na text a rozbíjelo lištu. Funkce (reorder karet) zůstává v kódu „uspaná".
- **Kompaktní zobrazení — jen „Uložit":** nástroje nad hledištěm (scan / upravit sedadla / výchozí pozice / smazat fotky) se v kompaktním gridu **skryjí** (patří k detailnímu zobrazení), zůstane jen Uložit + pose + přepínač. V detailním se ukážou všechny. (Pozn.: karty v kompaktním se řadí podle pořadí v `state.presets[2]`, číslované dle pozice; drag&drop byl jen v režimu „Přesunout" = teď neaktivní.)

### 9. 11. 2026 — ikonový toolbar CAM2 + zápatí „Ovládání kamer 2.0"
1. **CAM2 toolbar na icon-only.** Tlačítka Skenovat / Přidat sedadlo / Přesunout / Uložit preset / Výchozí pozice / Smazat všechny fotky mají **jen ikonu** (textové popisky pryč), popisek je jen **tooltip** (`title`). Sladěno na **čtverec 42×42** (třída `icon-only`, ikona 20px); pose tlačítka 🧍🪑 taky 42×42. **„Kompaktní zobrazení" ponecháno s textem** (dle zadání). „Přidat sedadlo" dostalo `+` ikonu, „Přesunout" move ikonu. Přepínání režimu výchozích pozic teď mění `title` tlačítek (ne text).
2. **Zápatí v Nastavení** → **„Ovládání kamer 2.0"**, „Poslední aktualizace 9. 11. 2026", odstraněn řádek „HTTP CGI · IP/LAN".
3. **Dynamický layout — minimum.** `SEAT_LAYOUT` měnitelný (`let`) + persistence `localStorage['ptz_seat_layout']` (default `_SEAT_LAYOUT_DEFAULT`); `_rebuildSeatMaps()` přepočítá mapy. Tlačítko `+` v liště CAM2 → dialog **„Upravit sedadla"** (`openSeatEditor`): přidat sedadlo (číslo + blok + řada) / smazat (číslo). **Úložiště keyované číslem sedadla** — `_remapSeatStorageByNumber` po změně přemapuje `slotCoords`/`slotPresets`/`slotDefaultCoords`/`slotAssignments` podle čísla → **kalibrace/fotky drží** (ověřeno Playwrightem: seed coords/preset → add/remove → data u správného sedadla). Layout přidán do zálohy (export/import v2, aplikuje se před slot poli). Rozhodnuto: rozpoznávání/AI = v3.0, OBS = v4.0.
   - *Zatím minimum:* bez přesunu/přejmenování/2D editoru; smazání obsazeného sedadla nechá osiřelou preset-kartu (vyčistí „Smazat všechny fotky").
   - *Doladění:* v dialogu „Levý/Pravý sektor" (místo Blok A/B), čísla v závorce řady seřazená od nejmenšího. Ikona tlačítka „Upravit sedadla" v liště CAM2 = **tužka** (dle vzoru uživatele, modrá); **„Skenovat hlediště"** = **scan osoby** (rohový rámeček + postava, fialová) místo lupy. Tooltip „Upravit sedadla — přidat nebo smazat". **CAM1 tlačítko „Uložit preset" sjednoceno designově s CAM2** (icon-only, zelený čtverec 42×42, bez textu). Všechny ikony **zvětšeny** (lépe vyplní rámeček, bez změny velikosti tlačítek): toolbar icon-only 20→26px (scan zvlášť 30px), pose 24→28px, CAM1 presety person 28→36px / scénky 28→31px. **CAM1 ikonový pruh vycentrován na střed panelu** (button-col + spacer `flex:1 1 0`, pruh `flex:0 0 auto`), aby Předsedající seděl do **středové uličky** mezi sektory CAM2. Padding seat gridu změněn na symetrický `8px 24px` (součet 48 = `SEAT_PAD`), takže ulička = střed panelu (ověřeno: střed panelu = Předsedající = ulička = 742 px).

### 7. 11. 2026 (pokračování) — vycentrování sektorů + přepracování CAM1 Pódium
1. **Vycentrování sektorů (Komentáře).** Řady v obou blocích jsou teď **vycentrované** (symetrická pyramida místo zarovnání vlevo) — `align-items:center` na blocích, odsazení `INDENT_L/R` vynulováno. Celá skupina sektorů vycentrovaná v panelu (`.seat-hall-live` `justify-content:center`; ve stacked `align-items:center`). **Výjimka: řada [0,1]** zůstává vlevo (`align-self:flex-start`). Pozor na úskalí: inline `align-items` na hall dřív přebíjel CSS → layout přesunut celý do CSS třídy `.seat-hall-live`.
2. **CAM1 Pódium přepracováno:** „Přidat preset" **úplně odstraněno** (tlačítko + viditelnost). 5 presetů je teď **ikonový pruh s malými mezerami (6px, jako mezi sedadly) a bez textových popisků** (jméno jen tooltip), ikony **zmenšené**. **Ikony 3 „osobních" presetů** (`_cam1Icon`) = jednotný panáček v saku s kravatou (`_CAM1_SUIT`): **předsedající** + čárka (pultík) pod ním; **řečník vyšší** + šipka nahoru vpravo; **řečník nižší** + šipka dolů vlevo. Na úzkém okně se pruh **zalomí pod tlačítko „Uložit preset"** (`flex-wrap`). `equalizeCam1Tiles`/`layoutCam1Scenes` → no-op (layout řeší CSS). Tím zmizel i starý překryv „Scénka sedící" × „Uložit preset" na úzkém okně.
   - *Doladění:* 2 ikony ve scénkách přitaženy blíž (`gap:0` + `margin:0 -3px`), menší odsazení ikony od okraje dlaždice (padding `0 5px`, min-width 42px), šipky nahoru/dolů dál od těla (posun jen uvnitř viewBoxu, velikost dlaždice beze změny).
   - *Doladění 2:* kravata/límec jako **Y** (horní vidlice + svislá čárka ke spodní hraně těla), ne V. Hlava o chlup výš (cy7). Šipka dolů (nižší) posunuta níž.

Ověřeno `node --check` + Playwrightem (1920–800 px bez přetečení, bloky vycentrované, CAM1 ikony čitelné a bez popisků).

### 7. 11. 2026 — mazání fotky pravým klikem, sloučené „Smazat všechny fotky", diagnostika skenu
Víkendová zpětná vazba z reálného použití: záloha OK, sken >90 % OK (log teď neřešit). Všech pět požadavků hotovo:

1. **Mazání jedné fotky zpět na pravý klik** — na kartě sedadla (`makePresetCardForSlot`) přidán `contextmenu` → `deleteSlotPhoto` (preset/pozice zůstává). **Ikonka koše odstraněna** (tlačítko `.slot-del-photo` + jeho CSS). Pozn.: slot `pointerdown` má `if (e.button !== 0) return`, takže pravý klik není potlačen; `_makeViewSlotOld` (živý view) nemá vlastní contextmenu, takže konflikt nehrozí.
2. **„Vrátit výchozí" sloučeno do „Smazat všechny fotky"** — samostatné tlačítko `resetDefaultBtn2` zrušeno. Nový dialog `#clearResetOverlay` (`openClearResetDialog` / `clearResetResolve`): vždy hromadné smazání fotek/karet CAM2; **checkbox** `#clearResetAlsoReset` (default off, zobrazí se jen když existují výchozí pozice) navíc vrátí pracovní pozice na výchozí (`_applyResetSeatsToDefault`: `slotCoords ← slotDefaultCoords`). Odpověď na dotaz „kde jsou výchozí pozice": `slotDefaultCoords`, localStorage `ptz_slot_default_coords`.
3. **Sken přeskakuje sedadla v pravém sektoru = nejsou kalibrovaná.** Sken jede jen přes sedadla s `slotCoords` nebo `slotPresets`; nekalibrovaná nemá kam najet. Přidán log: `Kalibrovaných sedadel: X z Y` + `Přeskočeno (bez kalibrace): …` — hned vidět, co dokalibrovat. (Není to bug, je to mezera v kalibraci.)

5. **Responsivní viewport — HOTOVO (CAM2).** `applyZoom` dřív sedadla jen zmenšoval, aby se oba sektory vešly vedle sebe. Nově: pod prahem (sedadlo „vedle sebe" < 64 px) přepne na **STACKED** — třída `seat-stacked` na `<html>`, bloky pod sebou (`.seat-hall-live` sloupec), sedadla zvětšená (`calcCardWStacked`, strop ~83 px). CAM1 odpojen (`cam1Base`), aby se Pódium nenafouklo. Ověřeno Playwrightem.
   - Pozn.: na ~960 px se v Pódiu překrývá dlaždice „Scénka sedící" s „Uložit preset" — **pre-existující** layout CAM1 (ne regrese), k doladění zvlášť.

4. **Změna layoutu sedadel — HOTOVO.** Po upřesnění: přidat **16, 116, 127, 138**, „smazat 16" byl překlep → smazat **168**. `SEAT_LAYOUT`: levá řada 1 `[16..11]`, pravá řada 1 `[111..116]`, řada 2 `[121..127]`, řada 3 `[131..138]`, řada 6 `[161..167]`. **TOTAL_SEATS 78 → 81.** Zvoleno **bez migrace** — úložiště se jen přepočítá na novou délku (index-based), hodnoty se posunou → **nutná překalibrace** (uživatel akceptoval). Zároveň přepracován výpočet velikosti sedadla (`_blockW`/`_seatTotalSide`/`_seatTotalStacked` z reálné `clientWidth` gridu), aby se vešly i delší řady bez přetečení (ověřeno 1920–800 px). TODO naostro: **překalibrovat** nová i posunutá sedadla.

Ověřeno `node --check` (inline skripty OK) + Playwrightem (reset tlačítko pryč, dialog + checkbox fungují, bez JS chyb mimo blokované CDN/WS).

### 1.–6. 11. 2026 — výchozí pozice + kompletní záloha (nová větev → merge)
Vyvinuto na větvi `vychozi-pozice-sedadel`, poté **sloučeno do `ptzcameracontroller`**.
1. **Výchozí (baseline) pozice sedadel** — nové úložiště `slotDefaultCoords` (localStorage `ptz_slot_default_coords`) paralelní k `slotCoords`. Režim „Výchozí pozice" (tlačítko přepínač + banner): klik najede na výchozí, „Uložit výchozí" uloží aktuální polohu jako výchozí (nesáhne na pracovní ani preset). Tlačítko „Vrátit výchozí" vrátí pracovní pozice všech sedadel na výchozí.
2. **Kompletní záloha/obnova** (export v2) — export/import teď zahrnuje i `slotCoords`, `slotDefaultCoords`, nastavení (`ptz_settings`) a osoby (`ptz_persons` vč. embeddingů); zpětně kompatibilní s v1. Pro přenos appky na jiný PC (jinak jsou data jen v browser storage).
3. Dotaz „co přenést na jiný PC": kód (git clone + checkout / HTML+server+launchery), `mediamtx.exe` (není v Gitu), Python + balíčky, a data přes Export/Import.

### 22. 10. 2026 — živý test skenu + opravy recallu/detekce
Testováno naostro na síti (sken hlediště, vyvolávání sedadel). Tři změny:

1. **Zoom sken: naklonění nahoru před zoomem** (`2a582fc`) — zoom-in dřív mířil na geometrický střed (hruď/sedačka) a obličej ztrácel. Nově se kamera před zoomem nakloní nahoru (`_scan.zoomTiltUpMs`), takže zoom zamíří na obličej v **top-center**. Laditelné polem „↑ Tilt nahoru před zoomem (ms)" ve scan modalu.
2. **Fix: obsazená sedadla zase vyvolatelná + default tilt 700 ms** (`2000bee`) — regrese z předchozího recall fixu: klik na sedadlo s fotkou nedělal nic. Příčina: na kartě sedadla jsou **mouse eventy potlačené** (slot dělá `preventDefault` na pointerdown), takže recall obsluhuje jen slot přes pointer eventy — a ten jsem u obsazených sedadel omylem vypnul. Vráceno: slot vyvolává prázdná i obsazená sedadla, **coords-first** (žádný strop, žádný dvojí pohyb). Ověřeno reálným klikem (1× `absmove`). Default `zoomTiltUpMs` 450 → **700 ms**.
3. **Filtr jistoty obličeje (ruce)** (`24635a0`) — ruce se někdy detekovaly jako obličej a umístily na sedadlo. Přidán práh `_scan.minFaceConfidence` (default **0.90**, laditelné polem „🙂 Min. jistota obličeje (%)"); `_detectAndDraw` odfiltruje nízkou BlazeFace confidence. **Log teď ukazuje confidence** přijatých i odfiltrovaných detekcí → snadné doladění.

**Pozorování z živého skenu (k doladění):**
- Prázdná sedadla občas chytnou **souseda** při oddálení zoomu (12, 46, 43) — metriky dx/vel se překrývají s reálnými vzdálenými lidmi, čistě algoritmicky neoddělitelné → pomůže přesnější kalibrace + smazat falešné fotky.
- **Zadní řada (51–57) ujíždí** (54 najel na 56, 42 vzal člověka z 51) — rozhozené **uložené souřadnice** těch sedadel (ne bug v kódu) → překalibrovat (klik → joystick → Uložit preset).
- Potvrzen mechanismus „do stropu": appka a joystick sdílí **jednu preset paměť v kameře** (appka přes LAN CGI/VISCA, joystick přes RS-485/Pelco-D); joystick ji přepsal → `gotopreset` jel špatně. Souřadnice (VISCA, uložené v appce) jsou vůči joysticku imunní.

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
