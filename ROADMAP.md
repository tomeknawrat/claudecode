# PTZ Camera Controller — Roadmap

> Přehled hotového, zaparkovaných nápadů a dalšího směru. Doplňuje
> `KONTEXT_PRO_NOVY_CHAT.md` (popis projektu) a `SESSION_HANDOFF.md` (stav práce).
> Aktualizováno: **18. 8. 2026**. Hlavní větev: `ptzcameracontroller`.

---

## ✅ Hotovo

| Oblast | Popis | Commit |
|--------|-------|--------|
| Větve | Konsolidace veškeré PTZ práce do `ptzcameracontroller` | — |
| Presety | Deduplikace preset karet při načtení z IndexedDB | `2a1ca70` |
| Stop kamery (UI) | Skutečný hold/release, stop 3× (0/150/400 ms) | `2a1ca70` |
| **Video náhled** | WHEP CORS proxy v `ptz_server.py` (:8890) obchází CORS MediaMTX 1.20 | `846ce68` |
| Skenování | Oprava tlačítka „Spustit skenování" (ReferenceError `_scanSectors`) | `96f1154` |
| Rozpoznávání | Diagnostické logování, dedup osob, výběr top-center, `minConfidence` 0.3 | `bbcc353` |
| **Stop kamery (CGI)** ⭐ | Pan/tilt stop je `ptzstop`, ne `stop` (VHD/PTZOptics) — ověřeno `stop_test.py` | `1f6f440`, `81c71a9` |
| Soubory | Přejmenování HTML → `SL Meeting_Ovládání PTZ kamer.html` + srovnání docs | `ea9657a`, `f2e086c` |

**Stav:** hlavní dlouhodobé problémy (stop kamery, video náhled, rozpoznávání) vyřešeny a naostro ověřeny.

---

## 📌 Zaparkované nápady

### Na stávající větvi (`ptzcameracontroller`)
1. **UI „Smazat fotky session"** — tlačítko, které smaže fotky/presety vytvořené v rámci jedné skenovací session, aby byla příště čistá sedadla pro nový sken.

### Do nové testovací větve
2. **Default PTZ souřadnice sedadel** — každé sedadlo má „domácí" polohu kamery, ke které se lze jedním tlačítkem kdykoliv vrátit (pro případ, že si někdo pro danou session preset lehce poupraví). Oddělit „default polohu sedadla" od „session úprav".
3. **Zoom-in → out sken** — dané sedadlo nejdřív více přiblížit a postupně oddalovat, přitom hledat hlavní obličej (lepší detekce/rozpoznání).

---

## 🔭 Nový směr — OBS integrace

OBS je v sále aktivně používán (program na TV, virtuální kamera do Zoomu, nahrávání), takže integrace dává smysl.

- **Browser dock** (doporučeno) — appku hostovat jako Custom Browser Dock uvnitř OBS (CEF). Náhled + ovládání v jednom okně vedle scén, skoro beze změny kódu (servírovat přes lokální http). Naše CORS proxy se přenese.
  - ⚠️ Ne nativní C/C++ plugin — velká dřina, ztráta webového stacku i `face-api.js`.
- **`obs-websocket`** (od OBS v28 vestavěný) — propojení **preset kamery ↔ scéna**. Cíl: rozpoznaný řečník → kamera najede na jeho preset + OBS přepne program na tu kameru = poloautomatická režie.
- Appka může zůstat **současně** standalone HTML i OBS dock (tatáž stránka přes http).

---

## 🎯 Nejbližší kroky

1. **Doladit práh rozpoznávání** — z reálného skenu vzít `dist:` hodnoty z logu a nastavit práh napevno (rychlé).
2. **Rozhodnout priority** zaparkovaných bodů — pořadí: session-cleanup (rychlá výhra) / default souřadnice sedadel / zoom sken / OBS dock.

---

## Poznámky

- Živé testování PTZ i rozpoznávání běží **jen lokálně** na PC v sále (LAN ke kamerám). Cloud/remote session je na úpravy kódu.
- Body 2 a 3 patří do **nové testovací větve**, aby se experimenty nemíchaly do funkční `ptzcameracontroller`.
