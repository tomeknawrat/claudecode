# Session Handoff — PTZ Camera Controller

> Strukturované shrnutí práce z pracovní session (Claude Code, lokálně na Windows PC).
> **Není to doslovný přepis chatu** — je to kontext pro pokračování v nové (i remote) session.
> Doplňuje `KONTEXT_PRO_NOVY_CHAT.md`, který popisuje celý projekt. Tento soubor popisuje, co se dělo naposledy a co zbývá.

## TL;DR — kde to stojí (aktualizace 7. 11. 2026)

- ✅ **Zastavování kamery — VYŘEŠENO a ověřeno naostro** — pan/tilt stop je `ptzstop`, ne `stop`.
- ✅ **Video náhled (WHEP) — VYŘEŠENO** — CORS proxy v `ptz_server.py` (:8890) obchází CORS MediaMTX.
- ✅ **Face recognition opraveno** — appka už nezamrzá na „Počítám embedding".
- ✅ **UI přepracování hotové** — karty sedadel, seat layout, hlavička CAM2, pose ikonky.
- ⏳ **Sken „po souřadnicích" (VISCA-over-IP) hotový v kódu** — čeká na živý test ve čtvrtek (restart serveru + překalibrace sedadel). Vznikl proto, že hardware joystick (AVMatrix PKC3500) přepsal sdílenou preset paměť kamery.
- ⏳ **Zoom-in sken + fotky top-center/bez rámečku** — hotové v kódu, čeká na doladění naostro.
- ✅ **Drag&drop fotek mezi sedadly** ve výchozím zobrazení (bez módu „Přesunout") — hotovo.
- ✅ **Zrušen mód „Editace presetů sedadel"** — workflow bez módů (Uložit preset / drag&drop). Funkce módu zůstávají v kódu uspané.
- ✅ **Mazání jedné fotky = pravý klik na kartě** (7. 11.) — ikonka koše na kartě zrušena.
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

### 10. 11. 2026 — UI úpravy po lokálním testu layoutu
- **Stacked:** odstraněna dělicí lajna mezi sektory (gap zvětšen na 26px).
- **Fix:** tužka/koš se už nezmenšují na úzkém okně — v `@media max-width:1100px` přidán override `.icon-only svg` (26px, scan 30px) přes `!important` (předtím `.add-preset-btn svg`/`.hide-presets-btn svg` 13px !important vyhrávalo).
- **Tooltipy:** Uložit → „Uložit aktuální pozici do posledního vybraného presetu"; Výchozí pozice → „Nastavit výchozí pozice sedadel"; Koš → „Smazat všechny fotky" (i v `toggleDefaultPosMode`).
- **Dialog „Smazat všechny fotky":** titulek s otazníkem, text zkrácen na „Smažou se všechny momentálně uložené fotky na sedadlech.", odstraněno „Akce je nevratná.", checkbox **vždy viditelný** s textem „Vrátit presety na výchozí pozice?".
- **Přepínač zobrazení:** „Detailní"/„Kompaktní" (vyhozeno „ZOBRAZENÍ").
- **Hlavička:** přidáno **neaktivní tlačítko „Databáze osob"** (`personsDbBtn`, users ikona, opacity .6) mezi stavovou tečku a Nastavení — zaparkované místo pro budoucí správu osob/rozpoznávání (klik = toast „zatím nedostupné").
- **Dialog sedadel:** titulek „Přidat/smazat sedadlo", odstraněna věta pod ním.
- **Fix kompaktní lišty:** tlačítko „Přesunout" (`editOrderBtn2`) **skryto** z lišty (`_updateCam2BtnVisibility` ho vždy `hide`) — pozůstatek starého workflow, v kompaktním gridu se mu přepisoval obsah na text a rozbíjelo lištu. Funkce (reorder karet) zůstává v kódu „uspaná".

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
