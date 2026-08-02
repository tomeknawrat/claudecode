# Garmin MCP Server

MCP (Model Context Protocol) server, který zpřístupní data z tvého
**Garmin Connect** účtu MCP klientům jako je **Claude** (Claude Desktop,
Claude Code) nebo jakýkoli jiný MCP klient.

Garmin zatím nevydává vlastní oficiální MCP server, takže tenhle server
čte data přes (neoficiální) knihovnu [`garminconnect`](https://github.com/cyberjunky/python-garminconnect),
která používá stejné privátní API jako webová aplikace Garmin Connect.

Server je **pouze pro čtení** – žádná data v Garminu neupravuje ani nemaže.

## Co umí

Pokrývá aktivity, zdraví a wellness, tělesné složení, souhrny a
výkonnostní/tréninkové metriky:

| Nástroj | Popis |
| --- | --- |
| `garmin_get_profile` | Základní údaje účtu (jméno, jednotky) – rychlé ověření přihlášení |
| `garmin_list_activities` | Seznam aktivit (běhy, kolo, plavání…), nejnovější nebo dle rozsahu dat + filtr typu |
| `garmin_get_activity` | Detail jedné aktivity (tempo, tep, převýšení, výkon), volitelně úseky a počasí |
| `garmin_get_daily_summary` | Denní souhrn (kroky, kalorie, klidový tep, stres, Body Battery, intenzitní minuty…) |
| `garmin_get_heart_rate` | Srdeční tep za den (klidový, min/max, intraday) |
| `garmin_get_sleep` | Spánek za noc (fáze, skóre, HRV) |
| `garmin_get_stress` | Stres za den (průměr, max, čas v pásmech) |
| `garmin_get_body_battery` | Body Battery za rozsah dat (nabito/vybito, průběh) |
| `garmin_get_steps` | Kroky během dne po 15minutových intervalech |
| `garmin_get_body_composition` | Tělesné složení z chytré váhy (váha, % tuku, BMI, svaly, voda) |
| `garmin_get_training_readiness` | Připravenost k tréninku (0–100) ze spánku, HRV, zátěže a stresu |
| `garmin_get_hrv` | HRV status přes noc (průměr, 7denní průměr, baseline, stav) |
| `garmin_get_vo2max` | VO2 max (běh + kolo), fitness age, aklimatizace |
| `garmin_get_weekly_summary` | Týdenní (1–31 dní) agregace: kroky, kalorie, klidový tep, stres, intenzitní minuty |

Každý nástroj podporuje `response_format`: `markdown` (přehledné shrnutí,
default) nebo `json` (kompletní strukturovaná data).

## Požadavky

- Python **3.10+**
- Účet na **Garmin Connect** (e-mail + heslo)

## Instalace

```bash
git clone https://github.com/tomeknawrat/claudecode.git
cd claudecode

python3 -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Nastavení přihlášení

Server čte přihlašovací údaje z proměnných prostředí. Nejjednodušší je
zkopírovat si vzorový soubor:

```bash
cp .env.example .env
# vyplň GARMIN_EMAIL a GARMIN_PASSWORD
```

| Proměnná | Povinná | Popis |
| --- | --- | --- |
| `GARMIN_EMAIL` | ano | E-mail k účtu Garmin Connect |
| `GARMIN_PASSWORD` | ano | Heslo k účtu |
| `GARMIN_TOKEN_STORE` | ne | Kam se ukládají tokeny (default `~/.garminconnect`) |
| `GARMIN_MFA_CODE` | ne | Jednorázový 2FA kód – jen při **prvním** přihlášení, pokud máš zapnuté dvoufázové ověření |
| `GARMIN_IS_CN` | ne | `1` pokud je účet na čínské doméně `garmin.cn` |

> **Přihlášení proběhne jen jednou.** Po prvním úspěšném přihlášení se
> OAuth tokeny uloží do `GARMIN_TOKEN_STORE` a server je používá i po
> restartu, takže heslo ani MFA kód už nejsou při dalších spuštěních potřeba
> (dokud tokeny nevyexpirují).

### Dvoufázové ověření (2FA)

Pokud máš na účtu zapnuté 2FA, nastav při prvním spuštění `GARMIN_MFA_CODE`
na aktuální kód z aplikace/SMS. Po úspěšném přihlášení se tokeny uloží a
kód už není potřeba.

## Napojení na Claude

### Claude Desktop

Přidej server do konfiguračního souboru Claude Desktop
(`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "garmin": {
      "command": "/absolutni/cesta/claudecode/.venv/bin/python",
      "args": ["-m", "garmin_mcp.server"],
      "env": {
        "PYTHONPATH": "/absolutni/cesta/claudecode/src",
        "GARMIN_EMAIL": "ty@example.com",
        "GARMIN_PASSWORD": "tvoje-heslo"
      }
    }
  }
}
```

Po uložení restartuj Claude Desktop.

### Claude Code (CLI)

```bash
claude mcp add garmin \
  --env GARMIN_EMAIL=ty@example.com \
  --env GARMIN_PASSWORD=tvoje-heslo \
  --env PYTHONPATH=$(pwd)/src \
  -- $(pwd)/.venv/bin/python -m garmin_mcp.server
```

## Rychlý test

Ověření, že se server naimportuje a nástroje se zaregistrují:

```bash
PYTHONPATH=src .venv/bin/python -c \
  "import asyncio; from garmin_mcp.server import mcp; \
   print([t.name for t in asyncio.run(mcp.list_tools())])"
```

Spuštění serveru (běží přes stdio, čeká na MCP klienta):

```bash
PYTHONPATH=src .venv/bin/python -m garmin_mcp.server
```

Pak už stačí v Claudovi napsat třeba:
- „Ukaž mi mých posledních 5 běhů.“
- „Jaký byl můj spánek a Body Battery včera?“
- „Jak se vyvíjela moje váha za poslední měsíc?“

## Bezpečnost a omezení

- **Neoficiální API.** Server používá privátní Garmin Connect API přes
  knihovnu `garminconnect`. Garmin ho může kdykoli změnit; nejde o oficiálně
  podporované rozhraní.
- **Přihlašovací údaje** drž jen lokálně (v `.env` nebo v konfiguraci klienta).
  Soubor `.env` a adresář s tokeny jsou v `.gitignore` – **necommituj je**.
- **Rate limiting.** Garmin může omezit počet požadavků. Nástroje hlásí
  chybu „rate limit“, když k tomu dojde – chvíli počkej a zkus to znovu.

## Struktura projektu

```
claudecode/
├── src/garmin_mcp/
│   ├── __init__.py
│   ├── client.py      # přihlášení + cache tokenů (garth/garminconnect)
│   └── server.py      # definice MCP nástrojů (FastMCP)
├── requirements.txt
├── pyproject.toml
├── .env.example
└── README.md
```

## Licence

MIT
