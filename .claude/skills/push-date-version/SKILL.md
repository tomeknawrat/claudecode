---
name: push-date-version
description: Orazítkuje PTZ Camera Controller aktuálním datem a vypushuje verzi. Uživatel ho vyvolá přes /push-date-version (typicky jako finální krok při pushování nové verze). Do footeru appky v Nastavení ("Poslední aktualizace") vloží dnešní datum, srovná datum v ROADMAP.md a commitne + pushne na větev ptzcameracontroller.
---

# push-date-version

Orazítkuje appku **PTZ Camera Controller** aktuálním datem (= datum poslední
úpravy) a vypushuje verzi. Hlavní soubor: `SL Meeting_Ovládání PTZ kamer.html`.

Postupuj takto:

## 1. Zjisti dnešní datum
Vezmi **aktuální datum prostředí** (ne natvrdo z paměti). Naformátuj ho **česky**
jako `D. M. YYYY` bez úvodních nul — např. `16. 11. 2026`, `1. 3. 2027`.

## 2. Aktualizuj footer v Nastavení
V `SL Meeting_Ovládání PTZ kamer.html` najdi řádek ve `drawer-app-info-meta`:

```html
<span>Poslední aktualizace <STARÉ DATUM></span>
```

a nahraď `<STARÉ DATUM>` dnešním datem. (Je to footer bočního panelu Nastavení —
řetězec „Poslední aktualizace" je unikátní, podle něj ho najdeš.)

## 3. Srovnej datum v ROADMAP.md (konvence projektu dle CLAUDE.md)
V `ROADMAP.md` uprav řádek `> Aktualizováno: **<STARÉ DATUM>**. …` na dnešní datum.

## 4. Commit + push na `ptzcameracontroller`
- Commitni **všechny** připravené změny (footer + ROADMAP + cokoli dalšího
  rozpracovaného, co má jít ven).
- Zpráva commitu stručně shrne změny. Když jde jen o datum, použij např.:
  `chore: orazítkovat verzi datem <DATUM>`.
- Na konec commit message přidej **attribution footer dle instrukcí session**
  (Co-Authored-By + Claude-Session), nehardcoduj ho z téhle skilly.
- Pushni: `git push -u origin ptzcameracontroller` (při síťové chybě retry
  s exponenciálním backoffem 2/4/8/16 s, max 4×).

## Poznámky
- Když footer i ROADMAP už dnešní datum mají a nejsou žádné další změny k pushnutí,
  **nic nedělej** a oznam to — nevytvářej prázdný commit.
- Datum je jen text v HTML/MD, žádný JS se nemění — stačí ověřit, že řetězec
  „Poslední aktualizace" má správné datum (node --check ani Playwright netřeba).
- PR jen na výslovné vyžádání (jinak dle CLAUDE.md).
