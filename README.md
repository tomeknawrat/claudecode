# 🎯 Dorovnávaná 501 – šipkové počítadlo

Webová appka (jeden soubor `index.html`, bez závislostí) na počítání skóre pro šipkovou hru
**„od nuly do 501 s dorovnáním“** pro 2–5 hráčů. Funguje v mobilu i na počítači.

## Pravidla, která appka hlídá

- Všichni začínají na **0** a body se sčítají. Vyhrává, kdo se první dostane **přesně** na cíl (výchozí 501).
  Zavírá se libovolným polem (single, double, triple, bull).
- **Přetažení:** kdo hodí víc, než potřebuje, tomu **celé kolo neplatí** – skóre všech hráčů se vrátí
  na stav před jeho kolem.
- **Dorovnání:** když hráč trefí přesně aktuální skóre soupeře (např. soupeř má 184, já mám 123 a hodím 61),
  soupeř jde **zpátky na 0**. Když má stejné skóre víc soupeřů, jdou na nulu všichni. Nula se nedorovnává.
  V nastavení lze zvolit, zda se dorovnání vyhodnocuje po každé šipce (výchozí), nebo až po celém kole.
- 3 šipky na kolo, tlačítko **Zpět** vrátí poslední šipku (včetně případného vynulování soupeře).

## Zadávání hodů

1. **Terč** – klepni na pole na nakresleném terči (single / double / triple / bull / 25), tlačítko „Mimo“.
2. **Klávesnice** – vyber Single/Double/Triple a číslo, nebo rovnou zapiš součet celého kola.
3. **Kamera (experimentální)** – viz níže.

Rozehraná hra se ukládá do prohlížeče, po obnovení stránky lze pokračovat.

## Kamera – automatické snímání terče

Appka umí snímat terč kamerou telefonu a **navrhovat** zásahy, které jedním klepnutím potvrdíš
(nebo opravíš klepnutím na správné pole na terči). Postup:

1. Stránka musí běžet přes **HTTPS** (nebo `localhost`) – jinak prohlížeč kameru nepovolí.
2. Telefon postav do stojánku **zpředu proti terči** tak, aby byl celý terč v záběru, a už s ním nehýbej.
3. Rozbal sekci *Kamera* → **Spustit kameru**.
4. **Kalibrovat terč** – klepni postupně na vnější okraj double kruhu u čísel **20, 6, 3 a 11**.
   Zelený obrys se musí krýt s terčem (dlouhé klepnutí = krok zpět). Kalibrace se pamatuje.
5. S prázdným terčem stiskni **Terč je prázdný** (referenční snímek).
6. Házej. Po každé šipce, jakmile je obraz v klidu, appka navrhne pole → **Potvrdit** / **Ignorovat** /
   klepnout správné pole na terči.
7. Po kole šipky vyndej – appka to sama pozná (nebo znovu stiskni **Terč je prázdný**).

Jak to funguje: 4 kalibrační body dávají homografii (perspektivní transformaci) obraz → terč v mm.
Nová šipka se hledá jako největší souvislá změna oproti referenčnímu snímku; poloha hrotu se odhaduje jako
bod změny nejblíž středu (nebo těžiště změny) a přepočte na segment/prstenec.

Omezení (jedna kamera ≠ Scolia/Autodarts): přesnost na hraně drátů je omezená, vadí změny světla, stíny
a pohnutý telefon. Detekce je proto vždy jen **návrh k potvrzení**; ruční vstup je základ. Citlivost
a způsob odhadu hrotu lze ladit v nastavení kamery.

## Spuštění

Stačí otevřít `index.html`. Pro kameru na mobilu je potřeba HTTPS – nejjednodušší je zapnout GitHub Pages
pro tento repozitář, nebo lokálně např. `npx serve` + tunel/HTTPS.
