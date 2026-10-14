# CLAUDE.md — pravidla projektu PTZ Camera Controller

## Dokumentace — VŽDY aktualizovat (bez vyzvání)
Při **každé** změně kódu/funkce v tomto projektu rovnou (ve stejném commitu, bez
čekání na pokyn uživatele) aktualizuj dokumentaci tak, aby odpovídala realitě:
- `ROADMAP.md` — stav hotového/rozpracovaného, parkované nápady, checklist na živý test
- `KONTEXT_PRO_NOVY_CHAT.md` — popis architektury, souborů, protokolů, úložišť
- `SESSION_HANDOFF.md` — TL;DR + chronologie práce + nedořešené body

Aktualizuj jen to, co se změny týká; drž datum „Aktualizováno" v ROADMAP aktuální.

## Větev
Veškerá práce jde na větev **`ptzcameracontroller`** (zdroj pravdy). Commituj a
pushuj; PR jen na výslovné vyžádání.

## Jazyk
Vše (kód, komentáře, UI, dokumentace) **česky**. Technické identifikátory
(proměnné/funkce, HTML ID/třídy, CGI/VISCA příkazy) zůstávají anglicky.

## Testování
- Živé testy PTZ/rozpoznávání běží jen lokálně na PC v sále (LAN ke kamerám);
  cloud/remote session na kamery nedosáhne.
- Po úpravách HTML: `node --check` na vytažených inline skriptech + ověření
  vzhledu/funkce přes Playwright (chromium `/opt/pw-browsers/...`, externí CDN
  blokovat přes `page.route`).
