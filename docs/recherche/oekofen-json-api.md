# ÖkoFEN Pellematic – lokale JSON-Schnittstelle (Recherche)

Stand: 2026-11-22. ÖkoFEN veröffentlicht keine offizielle Dokumentation der JSON-Schnittstelle. Alles hier stammt aus Community-Quellen, aus der Hilfeseite, die die Schnittstelle selbst ausgibt, und aus echten Antworten von Kesseln (Test-Fixtures der HA-Integration). Unsicheres ist als **Annahme** markiert.

---

## 0. Begriffe und Abgrenzung

| Begriff | Was es ist |
|---|---|
| **Pellematic** | Der Pelletkessel (Compact, Smart XS, Condens usw.); `pe1..pe4` in der API |
| **Pelletronic Touch** | Der Regler mit Touch-Bedienteil. Er stellt die JSON-Schnittstelle bereit. „Pelletronic“ ist also **keine** Cloud. |
| **my.oekofen.info** + App **myPelletronic** | Offizielles Cloud-Portal von ÖkoFEN für Fernzugriff. Die Domain heißt `.info`; für `my.oekofen.com` gab es keinen Beleg. |
| **Modbus TCP** | Offizielle Smart-Home-Schnittstelle (Port 502, Modus „HomeAuto“). Die Parameterliste gibt es bei ÖkoFEN als Download. |
| **Lokales Web-UI** (`/index.cgi`) | Web-Oberfläche des Touch mit Login per Cookie. Wird von einzelnen Integrationen genutzt und hat **nichts mit der JSON-Schnittstelle zu tun**. |

**Cloud-API:** Eine offizielle, öffentliche Telematik- oder Cloud-API gibt es nicht. ÖkoFEN nennt für Smart Home nur Modbus TCP, Loxone und my.oekofen.info/myPelletronic ([oekofen.com/smart-home](https://oekofen.com/en-gb/smart-home)). Inoffiziell nutzt das Projekt `lenoxys/ha-oekofen-portal` die interne Web-App-API des Portals:
- Basis `https://my.oekofen.info/api/pwa`
- Token über OAuth2 Password-Grant an `/v1/oauth2/token`. Client-ID und Secret liest das Projekt aus dem JavaScript der Web-App aus.
- Variablen über `POST /v1/plants/{plant}/remotecontrol/variables`, Namen im Format `CAPPL:…`

Das ist fragil: ÖkoFEN kann die API jederzeit ändern ([api.py](https://github.com/lenoxys/ha-oekofen-portal/blob/HEAD/custom_components/okofen_portal/api.py)).

---

## 1. Aktivierung, Port, Passwort, Firmware

- **Menüpfad am Touch:** Allgemeine Einstellungen → Netzwerkeinstellungen („IP Config“), ganz nach unten scrollen. Eventuell muss vorher der erweiterte Modus über das Schloss-Symbol oben rechts aktiviert werden. Dort gibt es drei Einstellungen:
  - **JSON Modus**: Aus / Ein / „Ein kompatibel“
  - **JSON Port**
  - **JSON Passwort**

  Die Einstellungen lassen sich nur am Gerät ändern. Quellen: [dominikamann README](https://github.com/dominikamann/oekofen-pellematic-compact), [ioBroker-Forum](https://forum.iobroker.net/topic/63120/oekofen).
- **Port:** Üblich ist **4321**. Er ist frei einstellbar und auch der Default in den Integrationen. Ein häufiger Fehler ist der Modbus-Port 502 (dann kommt „Parse Error: Expected HTTP/“).
- **Passwort:** Es gibt ein eigenes **JSON-Passwort**. Es ist **nicht** das Web- bzw. Fernzugriffspasswort für my.oekofen.info ([Issue #200](https://github.com/dominikamann/oekofen-pellematic-compact/issues/200)). Es ist kurz; in den Beispielen hat es 4 bis 5 Zeichen (**Annahme**). Der Touch zeigt die fertige URL `http://<ip>:<port>/<passwort>/all` an.
- **Kompatibilitätsmodus:** Nicht aktivieren. Die dominikamann-Integration unterstützt ihn nicht. Was er genau ändert, ist nicht dokumentiert (**Annahme:** altes Antwortformat ohne Metadaten).
- **Firmware:**
  - JSON gibt es ab Touch-Software **> V2.09** ([openHAB-Thread](https://community.openhab.org/t/oekofen-pellematic-control-via-json-api/57553)). Für Firmware < 2.09 gibt es nur CGI-Parsing (z. B. [kikoulandrim/okofen-cgi-hass-integration](https://github.com/kikoulandrim/okofen-cgi-hass-integration)).
  - Ab **V3.10d** gilt die Schnittstelle als brauchbar ([ioBroker-Adapter](https://github.com/iobroker-community-adapters/ioBroker.oekofen-json)).
  - Ab **V4.x** liefert sie Metadaten mit numerischen Werten.
  - Wärmepumpen-Abschnitte (`wp1`, `wp_data1`) sowie GreenMode sind in neuerer V4/V5-Firmware belegt (z. B. V5.02a, [Issue #130](https://github.com/dominikamann/oekofen-pellematic-compact/issues/130)).
  - In den USA ist **V3.10** die letzte Version.
- **Sicherheit:**
  - Kein HTTPS, nur HTTP.
  - Keine weitere Authentifizierung: Das Passwort steht im Klartext im URL-Pfad.
  - Den Port nie ins Internet freigeben ([SECURITY.md](https://github.com/dominikamann/oekofen-pellematic-compact/blob/HEAD/SECURITY.md)).

---

## 2. Endpunkte

Wenn die Schnittstelle einen Befehl nicht versteht (falsches Passwort, falscher Pfad), liefert sie eine **Klartext-Hilfeseite** statt JSON. Diese Seite ist die einzige „offizielle“ Doku. Unten der Inhalt von Touch V4.04b, zitiert aus [Issue #182](https://github.com/dominikamann/oekofen-pellematic-compact/issues/182). Die Hilfeseite beginnt mit `Oekofen JSON Interface   V4.04b`, danach folgt `usage:`.

### Lesen (mehrere Werte)
`http://IP:PORT/PASSWORT/<befehl>[?]`. Das angehängte `?` liefert zusätzlich **Metadaten**.

| Befehl | Inhalt |
|---|---|
| `all[?]` | alle vorhandenen Komponenten |
| `error` | aktuelle Fehler |
| `log_today`, `log_yesterday`, `log[0..3]` | CSV-Logdateien (Download) |
| `system[?]` | globale Systemvariablen |
| `weather[?]` | aktuelles Wetter |
| `forecast[?]` | Prognose |
| `power[?]` | Stromzähler, PV, power2heat |
| `stirling[?]` | Stirling-Daten |
| `hk[1..6][?]` | Heizkreise |
| `wireless[1..6][?]` | Funksensoren |
| `thirdparty[1..10][?]` | Fremdsensoren |
| `pu[1..3][?]` | Puffer („accu“) |
| `ww[1..3][?]` | Warmwasser |
| `sk[1..6][?]` | Solarkreise |
| `se[1..3][?]` | Solarertrag (Wärmemengenzähler) |
| `circ[1..3][?]` | Zirkulationspumpen |
| `pe[1..4][?]` | Pellematic-Kessel |

Weitere Abschnitte kommen in der `all`-Antwort neuerer Firmware vor, stehen aber nicht in der Hilfeseite von V4.04b:
- `wp1` (Wärmepumpe) und `wp_data1` (JAZ/AZ)
- `greenmode`, `greenmode_price`, `greenmode_carbon`, `greenmode_clouds` (jeweils 24 Stundenwerte)

### Varianten bei Lesen und Metadaten
- `all`: nur Werte, etwa halb so groß. ioBroker nutzt das für zyklische Updates.
- `all?`: Werte plus Metadaten (`val`, `unit`, `factor`, `min`, `max`, `format`, `text`, `length`). ioBroker und dominikamann nutzen das beim Start bzw. dauerhaft.
- `all??`: Nur ältere EU-Firmware (z. B. **V3.10d**) liefert damit reichere Metadaten. Die US-Firmware 3.10 **bricht** bei `??` die Verbindung ab (`IncompleteRead`). Deshalb probiert dominikamann erst `?` und weicht nur dann auf `??` aus, wenn `??` mehr liefert ([`__init__.py`, `_detect_api_config`](https://github.com/dominikamann/oekofen-pellematic-compact/blob/HEAD/custom_components/oekofen_pellematic_compact/__init__.py), [Issue #191](https://github.com/dominikamann/oekofen-pellematic-compact/issues/191)).

### Einzelwert lesen
`http://IP:PORT/PASSWORT/hk1.L_roomtemp_act`. Als Trennzeichen dient `.`.

### Schreiben
- Laut Hilfeseite: `http://IP:PORT/PASSWORT/hk1.mode_auto=0`, also per GET mit `.` als Trennzeichen.
- **Nur Variablen ohne `L_`-Präfix sind schreibbar** (Originaltext der Hilfeseite: „only variables without a leading 'L_' can be set“).
- In der Praxis funktioniert auch der **Unterstrich**: `hk1_temp_heat=225`. Das nutzen dominikamann und lenoxys.
  - Laut lenoxys **echot** der Kessel bei Erfolg genau `hk1_temp_heat=225` ([local.py](https://github.com/lenoxys/ha-oekofen-portal/blob/HEAD/custom_components/okofen_portal/local.py)).
  - Ob das Echo auch bei der Punkt-Syntax kommt, ist eine **Annahme**.
  - ioBroker schreibt mit Punkt-Syntax und wertet nur HTTP 200 aus.
- Werte werden **als Rohwert** geschrieben: 21,5 °C bei Faktor 0.1 wird zu `215`. Enums werden als Zahl geschrieben.

---

## 3. Datenformat-Eigenheiten

- **Zeichensatz:**
  - Meist **ISO-8859-1/latin-1**, ohne `charset` im Header. ioBroker und lenoxys dekodieren fest mit latin-1, dominikamann nimmt das als Default.
  - Einige Firmware-Versionen liefern **UTF-8** oder **gemischt** (meist UTF-8 mit einzelnen latin-1-Bytes). In manchen Fixtures taucht `Â°C` auf, also doppelt kodiert.
  - Fazit: Kodierung heuristisch erkennen. Erst striktes UTF-8 versuchen, sonst latin-1 ([`_charset_from_raw`](https://github.com/dominikamann/oekofen-pellematic-compact/blob/HEAD/custom_components/oekofen_pellematic_compact/__init__.py)).
- **Fehlerhaftes JSON** (Workarounds in dominikamann `fetch_data`):
  - Ab V4.02 fehlt ein Anführungszeichen: `L_statetext:` statt `L_statetext":`. Muss per String-Replace repariert werden.
  - Unescapte Zeilenumbrüche und Tabs in Strings, z. B. in `error_1`. Diese escapen und `json.loads(strict=False)` verwenden.
  - Bei falscher URL oder falschem Passwort kommt eine Klartext-Hilfeseite statt JSON, siehe Abschnitt 2.
  - In manchen Abschnitten tauchen leere Strings oder `"Variable does not exist"` als Wert auf (z. B. `power.L_pv_own_usage`).
- **Wertetypen je nach Firmware:**

  | Firmware | Format |
  |---|---|
  | V3.x mit `?` | `{"val":"84","factor":0.1,"min":"-32768",...}`, Zahlen als **Strings**, bool als `"true"`/`"false"` |
  | V4.x mit `?` | `{"val":84,"factor":0.1,"min":-32768,...}`, numerisch, bool als 0/1 |
  | ohne `?` / US 3.10 | nur `"L_ambient":"-200"`, ohne Metadaten |

- **Faktor:** realer Wert = `val × factor`.
  - Temperaturen haben meist Faktor 0.1.
  - Zeiten stehen in ms: `factor 1.6667e-05`, Einheit „min“.
  - Wärmepumpen-Laufzeit steht in s: `factor 1/3600`, Einheit „h“.
  - Energie bei `power`: `factor 0.0001` in kWh.
  - `se1.L_flow`: Faktor 0.01 in l/min.
  - **Achtung, Wärmepumpe (`wp1`):** Werte kommen schon als Float (z. B. `L_temp_flow_is 40.5`). Die mitgelieferten Faktoren sind teils unplausibel (`L_fan` Faktor 100, `L_compressor_act` Faktor 67 bzw. 149, `L_flowrate` Faktor 60). **Annahme:** Den Faktor hier nicht blind anwenden; gegen das Display prüfen.
- **Sentinel-Werte:** `-32768` (z. B. `pe1.L_ext_temp`, wenn kein Abgasfühler verbaut ist) sowie `32765..32767` bedeuten „ungültig“ bzw. „nicht vorhanden“. Echte Grenzwerte (z. B. 7.200.000 ms = 120 min) dürfen **nicht** gefiltert werden ([Issue #193](https://github.com/dominikamann/oekofen-pellematic-compact/issues/193)). `min`/`max` = `-32768/32767` heißt nur „int16, kein echter Bereich“.
- **Präfixe und Namen:**
  - `L_…`: read-only (Live- bzw. Messwert).
  - Ohne Präfix: Einstellung, schreibbar.
  - `L_cfg_…`: Konfigurationswerte, nur sichtbar per `json.properties` (siehe unten), read-only.
  - `*_info`: Klartext-Beschreibung des Abschnitts (z. B. `"hk_info":"heating circuit data"`).
  - Vorsicht, Tippfehler der Firmware: `hysteresys`, `L_storage_popper` (alt) vs. `L_storage_hopper` (neu), `L_pummp`.
- **Enums:** `"format":"0:Aus|1:Auto|2:Heizen|3:Absenken"`. Paare sind durch `|` getrennt, Wert und Label durch `:`. Die **Labels sind in der Sprache des Touch** (DE/EN/FR …), ebenso `text`. ioBroker ersetzt zusätzlich `#.` durch `|`, eine seltene Variante (**Annahme**).
- **Statusfelder:**
  - `L_state` ist eine Bitmaske, z. B. `16777248`.
  - `L_statetext` ist ein Klartext. Mehrere Meldungen sind durch `|` getrennt, z. B. `"Heizbetrieb aktiv|Komforttemperatur aktiv"`.
- **error:** `{"error_1":"29-01-2026 18:21:32|PE 1 Aschebox in Kürze voll\nBitte …[5050]"}`. Format: Zeitstempel `|` Text `[Code]`, mit rohen Zeilenumbrüchen. `{}` heißt „keine Fehler“.
- **forecast:** `L_w_0..L_w_24`. Jeder Eintrag ist ein String `date|temp|cloud|speed|image|code|unit[|sunrise|sunset]`, der Code entspricht den OpenWeatherMap-Wetter-IDs.
- **thirdparty:** Ein Pipe-String in `L_state`, z. B. `"1|SHHT-1#7076CC#|…|false|0|0|0|0|---.---.---.---"`. Die Struktur ist undokumentiert.
- **json.properties:**
  - Eine Datei `json.properties` im Wurzelverzeichnis eines FAT32-USB-Sticks im Touch fügt rund **90 zusätzliche Werte** zu `/all?` hinzu: Heizkurve, Hysteresen, Laufzeiten, Asche, Wartung.
  - Getestet nur auf V4.02b. Auf V4.04b gab es einen Bericht über eine gestörte Saugzeit-Steuerung.
  - Die Datei sollte nur `L_`-Keys enthalten, sonst werden die Werte schreibbar.
  - Quelle: [Discussion #194](https://github.com/dominikamann/oekofen-pellematic-compact/discussions/194).

---

## 4. Bekannte Einschränkungen

- **Rate-Limit:**
  - Mindestens **2500 ms zwischen zwei Anfragen**, egal ob lesend oder schreibend und egal von welchem Client.
  - Bei Verstoß kommt **HTTP 401** bzw. der Body `Wait at least 2500ms during requests`. Belegt in dominikamann (`_min_fetch_interval = 3.0`, [Issue #170](https://github.com/dominikamann/oekofen-pellematic-compact/issues/170)), ioBroker-README („2,5 seconds between requests“) und lenoxys (`RATE_LIMIT = 2.6`).
  - pyokofen nennt ältere Werte: „soft limitation of 1 request per 10 seconds“. **Annahme:** Das galt für ältere Firmware.
- **Mehrere Clients** (HA, ioBroker, App/Portal) teilen sich das Limit. Daher: Anfragen serialisieren (Lock), Retry nach ≥ 3 s, sinnvolles Poll-Intervall (dominikamann: 30 s Default).
- **Nur eine Verbindung gleichzeitig:** nicht ausdrücklich belegt. Belegt ist nur, dass parallele Anfragen am Limit scheitern (**Annahme**).
- **Abstürze bzw. Hänger:** Es gibt nur Forenberichte über instabile Adapter. Ein Nutzer vermutet, dass App, Herstellerverbindung und JSON zusammen „zu viel“ sind ([ioBroker-Forum](https://forum.iobroker.net/topic/59910/oekofen-json-influx-datenpunkte-abholen/2)). Langsame Antworten und abgebrochene Bodies (`IncompleteRead`) gibt es bei US-Firmware 3.10. dominikamann nutzt deshalb 10 s Timeout und einen Retry. Einen harten „Kessel-Hänger“ belegt keine Quelle (**Annahme**: eher Überlast der Schnittstelle als des Reglers).
- **Schreibrisiko (ernst):** Ungültige Werte bzw. Werte außerhalb des Bereichs können den Regler dauerhaft verstellen.
  - [Issue #178](https://github.com/dominikamann/oekofen-pellematic-compact/issues/178): Eine Warmwasser-Änderung über HA führte zu Fehler 1020 („Geisterfühler“). Er war nicht quittierbar und erst nach Werksreset und kompletter Neukonfiguration weg.
  - Seitdem prüft dominikamann vor jedem Schreiben gegen `min`/`max`.
  - Pflicht für eine eigene Integration: Bereich und Enum-Wert validieren.
- Nicht alles ist schreibbar, z. B. die Heizkurve (`L_cfg_*` ist read-only, [Issue #135](https://github.com/dominikamann/oekofen-pellematic-compact/issues/135)).
- Firmware-Updates können das Passwort oder Keys ändern; dann muss man neu konfigurieren.
- **`L_not` / `L_stb`:** `1` bedeutet vermutlich „Sicherheitskreis geschlossen = OK“ (Öffner-Logik). Als HA-„problem“-Sensor muss der Wert invertiert werden ([Issue #197](https://github.com/dominikamann/oekofen-pellematic-compact/issues/197)).

---

## 5. Bestehende Projekte

| Projekt | Ansatz | Lizenz | Aktivität | Bekannte Schwächen |
|---|---|---|---|---|
| [dominikamann/oekofen-pellematic-compact](https://github.com/dominikamann/oekofen-pellematic-compact) (HACS-Default) | lokales JSON `all?`; dynamische Entity-Erkennung aus Metadaten; sensor/binary_sensor/select/number/climate/button; Diagnose-Modul; Erkennung von Zeichensatz und Suffix | Apache-2.0 | 74★, aktiv (Push 2026-11-16), 0 offene Issues | sync `urllib` im Executor statt aiohttp; Schreiben per `prefix_key=val`; Vorgeschichte mit 401-Fluten (#170), Migrationsproblemen 3.x→4.x (#155–#180), falscher Faktor-Anwendung (#166, #104), Geisterfühler beim Schreiben (#178), invertierten Safety-Sensoren (#197); Climate-„OFF“ sendet `mode_auto=3` (=Absenken, nicht Aus) – **Beobachtung aus dem Code** |
| [sweetcorreze/oekofen-pellematic-compact](https://github.com/sweetcorreze/oekofen-pellematic-compact) | Fork davon | – | inaktiv seit 2024-07 | veraltet |
| [ckarrie/homeassistant-oekofen](https://github.com/ckarrie/homeassistant-oekofen) + [ckarrie/oekofen-api](https://github.com/ckarrie/oekofen-api) (PyPI `oekofen-api`) | lokales JSON `all?`; Python-Lib mit Domains und Attributen | Integration ohne Lizenzangabe, Lib MIT | inaktiv seit 2023-11 | wenige Domains (kein `sk`), Schreiben nur Heizkreis-Temperatur |
| [JbPasquier/pyokofen](https://github.com/JbPasquier/pyokofen) (PyPI `pyokofen`) | asynchrone Python-Lib, nur Lesen | Apache-2.0 | inaktiv seit 2022 | viele Abschnitte fehlen, kein Schreiben |
| [lenoxys/ha-oekofen-portal](https://github.com/lenoxys/ha-oekofen-portal) | **Cloud** my.oekofen.info (inoffizielle PWA-API mit OAuth) plus optional lokales JSON (10-s-Poll, schreibt lokal) | MIT | neu (2026-10), aktiv | hängt von interner Portal-API ab; braucht Cloud-Konto |
| [rschnappi/ha-oekofen](https://github.com/rschnappi/ha-oekofen) | **lokales Web-UI** `POST /index.cgi` (Login, Cookie `pksession`), `POST /?action=get&attr=1` mit `CAPPL:`-Variablen | MIT | aktiv (2026-09) | kann installateur-gesperrte Werte schreiben; Uhrzeit-Offset-Bugs; HTTP 403-Aussperrung nach Fehlwert |
| [iobroker-community-adapters/ioBroker.oekofen-json](https://github.com/iobroker-community-adapters/ioBroker.oekofen-json) (vorher chaozmc) | lokales JSON: `all?` beim Start (Objekte anlegen), danach `all`; latin-1; Faktor-Umrechnung beim Lesen und Schreiben; `L_` = read-only | MIT | gepflegt (v2.0.0 2025-11; offen sind nur Dependency-PRs) | einfache Fehlerbehandlung (nach 10 Fehlern wird der Adapter deaktiviert) |
| [thannaske/oekofen-json-documentation](https://github.com/thannaske/oekofen-json-documentation) bzw. [chaozmc-Fork](https://github.com/chaozmc/oekofen-json-documentation) | Community-Doku der Felder | MIT | 2021, kaum gepflegt | viele Felder undokumentiert |
| openHAB-Binding ([Thread](https://community.openhab.org/t/oekofen-pellematic-control-via-json-api/57553)) | lokales JSON, nur Lesen | – | Snapshot-JAR, kein offizielles Add-on | – |
| weitere | [hoep/SymconPellematic](https://github.com/hoep/SymconPellematic) (IP-Symcon), [LM1LC3N7/gladys-oekofen](https://github.com/LM1LC3N7/gladys-oekofen), [vrischmann/oekofen-pellematic-exporter](https://github.com/vrischmann/oekofen-pellematic-exporter) (Prometheus), [stawen/okovision](https://github.com/stawen/okovision) (Webüberwachung, CSV) | – | – | – |

Es gibt **keine** Integration im Home-Assistant-Core.

---

## 6. Wichtige Datenpunkte pro Bereich

Die Liste stammt aus echten `/all?`-Antworten (Fixtures der dominikamann-Integration, deutsche Touch-Sprache) und der Community-Doku. Schreibbar heißt: kein `L_`-Präfix, also laut Hilfeseite setzbar. Ob jeder dieser Werte tatsächlich angenommen wird, ist nicht einzeln belegt (**Annahme**). Die Notation `n` steht für die Instanznummer.

### system
| Key | Bedeutung | Einheit/Faktor | schreibbar |
|---|---|---|---|
| L_ambient | Außentemperatur | °C ×0.1 | nein |
| L_ambient_avg | Außentemperatur gemittelt (V4) | °C ×0.1 | nein |
| L_errors | Anzahl Fehler (**Annahme**) | – | nein |
| L_usb_stick | USB-Stick erkannt | 0/1 | nein |
| L_existing_boiler / L_boiler_temp | Temperatur Bestandskessel / Kessel | °C ×0.1 | nein |
| mode | Anlagen-Betriebsart `0:Aus\|1:Auto\|2:Warmwasser` | Enum | ja |
| L_energystate | Energiestatus (GreenMode/PV) | Enum | nein |

### weather
- Messwerte: `L_temp` (°C ×0.1), `L_clouds` (%), `L_forecast_temp`, `L_forecast_clouds`, `L_forecast_today` (`0:Heute|1:Morgen`), `L_starttime`/`L_endtime` (hhmm als Zahl, z. B. 920 = 09:20, **Annahme**), `L_source`, `L_location`. Alle nein.
- Einstellungen: `cloud_limit` (%, 0..100), `hysteresys` (K ×0.1), `offtemp` (°C ×0.1), `lead` (min, 0..600), `oekomode` (`0:Aus|1:Ein`), `refresh`. Alle ja.

### forecast
- `L_w_0..L_w_24`: Pipe-Strings (Datum, Temperatur, Bewölkung, Wind, Icon, OWM-Code, Einheit, [Sonnenaufgang, Sonnenuntergang]), nein.

### hk1..hk6 (Heizkreis)
| Key | Bedeutung | Einheit | schreibbar |
|---|---|---|---|
| L_roomtemp_act / L_roomtemp_set | Raumtemperatur Ist / Soll (0 = kein Fühler) | °C ×0.1 | nein |
| L_flowtemp_act / L_flowtemp_set | Vorlauf Ist / Soll | °C ×0.1 | nein |
| L_comfort | Komfort-Offset | K ×0.1 | nein |
| L_pump | Heizkreispumpe | 0/1 | nein |
| L_state / L_statetext | Status-Bitmaske / Text | – | nein |
| mode_auto | Betriebsart `0:Aus\|1:Auto\|2:Heizen\|3:Absenken` | Enum | ja |
| mode_off / mode_dhw | Betriebsart-Slots für Anlagenmodus Aus bzw. Warmwasser (**Annahme**, rschnappi spricht von einer „Slot-Struktur“) | Enum | ja |
| time_prg | Zeitprogramm `0:Zeit 1\|1:Zeit 2` | Enum | ja |
| temp_heat / temp_setback / temp_vacation | Raumsoll Heizen / Absenken / Urlaub | °C ×0.1, 10..40 °C | ja |
| remote_override | Offset der Fernbedienung | K ×0.1 | ja |
| oekomode | `0:Aus\|1:Komfort\|2:Minimum\|3:Ökologisch` | Enum | ja |
| sensor_avg | Fühler-Mittelung | min 0..20 | ja |
| name | Anzeigename (max. 20 Zeichen) | String | ja |
| autocomfort, autocomfort_sunrise/sunset | Auto-Komfort (neuere Firmware) | Enum / min | ja |
| green_mode, L_green_*/L_origin_* | GreenMode-Zeitblöcke (neuere Firmware) | – | green_mode ja |
| solarheat_* | Solarüberschuss-Heizen (Modus, Ein-/Aus-Temperatur) | °C ×0.1 / Enum | ja |
| L_cfg_curve_slope, L_cfg_curve_basepoint, L_cfg_limit_heat … | Heizkurve, Heizgrenzen (nur mit json.properties) | ×0.1 | nein |

### pu1..pu3 (Puffer)
| Key | Bedeutung | Einheit | schreibbar |
|---|---|---|---|
| L_tpo_act / L_tpo_set | Puffer oben (Einschaltfühler) Ist / Soll | °C ×0.1 | nein |
| L_tpm_act / L_tpm_set | Puffer Mitte (Ausschaltfühler) Ist / Soll | °C ×0.1 | nein |
| L_pump_release | Pumpenfreigabe-Temperatur | °C ×0.1 | nein |
| L_pump | Pumpendrehzahl | % | nein |
| L_state / L_statetext | Status | – | nein |
| mintemp_on / mintemp_off, ext_mintemp_on / ext_mintemp_off | Mindesttemperatur Puffer Ein/Aus (ext_* = bei externer Anforderung, **Annahme**) | °C ×0.1, 8..90 | ja |

### ww1..ww3 (Warmwasser)
| Key | Bedeutung | Einheit | schreibbar |
|---|---|---|---|
| L_temp_set | Warmwasser-Soll aktuell | °C ×0.1 | nein |
| L_ontemp_act / L_offtemp_act | Temperatur am Ein- / Ausschaltfühler | °C ×0.1 | nein |
| L_pump | Ladepumpe | 0/1 | nein |
| L_state / L_statetext | Status | – | nein |
| mode_auto (+ mode_off / mode_dhw) | `0:Aus\|1:Auto\|2:Ein` | Enum | ja |
| heat_once | Einmal aufbereiten (setzt sich selbst zurück) | 0/1 | ja |
| temp_min_set / temp_max_set | WW-Temperatur Min / Soll | °C ×0.1, 8..80 | ja |
| time_prg | Zeitprogramm | Enum | ja |
| sensor_on / sensor_off | Fühlerwahl `0:WW\|1:TPO\|2:TPM\|3:SpUnten` | Enum | **ja, aber gefährlich** (vermutliche Ursache des Geisterfühlers in #178) |
| smartstart | Intelligenter Start | min 0..90 | ja |
| use_boiler_heat | Restwärmenutzung | 0/1 | ja |
| oekomode, green_mode, solarheat_* | wie hk | Enum | ja |
| name | Anzeigename | String | ja |

### sk1..sk6 (Solarkreis)
- `L_koll_temp`: Kollektortemperatur, °C ×0.1, nein.
- `L_spu`: Speicher unten, °C ×0.1, nein.
- `L_pump`: Pumpe, %, nein.
- `L_state` / `L_statetext`: Status, nein.
- `mode`: `0:Aus|1:Ein`, ja.
- `cooling`: `0:Aus|1:Ökologisch|2:Ein`, ja.
- `spu_max`: maximale Speichertemperatur, °C ×0.1, 20..90 °C, ja.
- `name`: Anzeigename, ja.

### se1..se3 (Solarertrag)
- `L_flow_temp` / `L_ret_temp`: Vor- / Rücklauf, °C ×0.1.
- `L_flow`: Durchfluss, l/min ×0.01.
- `L_pwr`: aktuelle Leistung, kW ×0.1.
- `L_day` / `L_yesterday` / `L_total`: Ertrag heute / gestern / gesamt, kWh ×0.1.
- `L_counter`: Zählerimpulse (**Annahme**).
- Alle Werte nein.

### circ1..circ3 (Zirkulation)
- `L_pump` (0/1), `L_ret_temp` (Rücklauf, °C ×0.1), `L_release_temp` (Freigabetemperatur, °C ×0.1), `L_state` / `L_statetext`: alle nein.
- `mode` (`0:Aus|1:Auto[|2:Ein]`), `time_prg`, `pump_release` (°C ×0.1), `return_set` (Abschalttemperatur, °C ×0.1), `name`: alle ja.

### pe1..pe4 (Pellematic)
| Key | Bedeutung | Einheit | schreibbar |
|---|---|---|---|
| L_temp_act / L_temp_set | Kesseltemperatur Ist / Soll | °C ×0.1 | nein |
| L_ext_temp | Abgastemperatur (-32768 = kein Fühler) | °C ×0.1 | nein |
| L_frt_temp_act / _set / _end | Feuerraumtemperatur Ist / Soll / End | °C ×0.1 | nein |
| L_br | Brennerkontakt | 0/1 | nein |
| L_ak | Bestandskessel-Kontakt | 0/1 | nein |
| L_not / L_stb | Not-Aus / Sicherheitstemperaturbegrenzer (1 = OK, **Annahme**) | 0/1 | nein |
| L_modulation | Modulationsstufe | % | nein |
| L_fluegas / L_currentairflow | Saugzug- / Lüfterdrehzahl | % | nein |
| L_lowpressure / L_lowpressure_set | Unterdruck Ist / Ende | „EH“ ×0.1 | nein |
| L_runtimeburner / L_resttimeburner | Einschub- / Pausenzeit | „zs“ ×0.01 | nein |
| L_uw / L_uw_speed / L_uw_release | Umwälzpumpe Drehzahl / Freigabe | % / °C ×0.1 | nein |
| L_state / L_statetext | Kesselstatus (z. B. „Leistungsbrand“) | – | nein |
| L_type | Kesseltyp `0:PE … 6:CONDENS\|7:SMART XS\|9:COMPACT … 12:PELLEMATIC HOME` | Enum | nein |
| L_starts / L_runtime / L_avg_runtime | Brennerstarts / Laufzeit h / mittlere Laufzeit min | – | nein |
| L_storage_fill / _min / _max / _hopper (alt `_popper`) | Lager- und Zwischenbehälter-Füllstand | kg | nein |
| L_pellets_today / _yesterday (alt: storage_fill_today / _yesterday) | Pelletverbrauch | kg (32765 = ungültig) | nein |
| suction_clean_time / suction_sec_time | Saugzeiten „hh:mm“ | String | ja (**Annahme**) |
| mode | Kessel-Betriebsart `0:Aus\|1:Auto\|2:Ein` | Enum | ja |
| L_ash_amount, L_maint_left_hours/days, L_cfg_* | Asche, Wartung, Brennerparameter (nur mit json.properties) | – | nein |

### power (Smart PV / Stromzähler)
- `L_usage`, `L_from_grid`, `L_to_grid`, `L_p1..3`, `L_pv_total`, `L_pv_1/2`, `L_batt_in/out` (alle W), `L_batt_chg` (%): nein.
- `L_pwr_out` / `L_pwr_out_per`: power2heat, W / %, nein.
- `L_today_*` / `L_yesterday_*` / `L_total_*`: kWh ×0.0001, nein. Einige `L_total*` sind ohne Einheit.
- `L_range` / `L_offset`: W, nein. Laut Name read-only, obwohl der Wert einen Bereich hat.
- `offtemp`: Abschalttemperatur, °C ×0.1, ja.

### wp1 (Wärmepumpe) / wp_data1
- Messwerte, alle nein:
  - `L_temp_flow_is` / `L_temp_flow_set` / `L_temp_return_is` (°C, schon als Float)
  - `L_cop`, `L_el_energy` (W), `L_temp_heater` (Heizleistung, W)
  - `L_highpressure` / `L_lowpressure` (bar), `L_compressor_in` / `L_compressor_out`, `L_temp_src_in` / `L_temp_src_out`
  - `L_total_runtime` (s→h), `L_activation_count`, `L_sg_ready`, `L_heater_*`
- Einstellungen, alle ja: `mode` (`0:Aus|1:Auto|2:Ein`), `set_sg_ready` (0..4), `ambient_mode`, `ambient_pwr` (%), `night_mode`, `heater` (`0:Aus|1:Heizung|2:Warmwasser|3:Auto`), `heater_act` (°C ×0.1).
- `wp_data1`: `L_jaz_all/heat/cool`, `L_az_all/heat/cool` (Jahres- und Gesamtarbeitszahlen), nein.

### greenmode
- `greenmode`: `0:Aus|1:Strom Arbeitspreis|2:CO₂ Intensität|3:Sonnenstrom`, ja (**Annahme**).
- `greenmode_price` / `greenmode_carbon` / `greenmode_clouds`: je 24 Stundenwerte `L_green_data_*_0..23`, nein.

### wireless1..6, thirdparty1..10, stirling
- Belegt sind nur `thirdparty.L_state` (Pipe-String) und der Abschnittsname. Format und Inhalt sind sonst unbekannt (**Annahme**: Funk-Raumfühler mit Temperatur und Feuchte).

### error
- `error_1..error_n`: `"DD-MM-YYYY HH:MM:SS|Meldungstext [Code]"`. `{}` heißt keine Fehler.

---

## Empfehlungen für eine eigene Integration (abgeleitet)

1. Alle Requests über eine Queue oder einen Lock serialisieren, ≥ 3 s Abstand halten. Die Antworten `401` und `Wait at least…` als „busy“ behandeln und erneut versuchen.
2. Bytes selbst dekodieren (erst UTF-8 strikt, sonst latin-1) und den JSON-Text vor dem Parsen reparieren: `L_statetext:` ergänzen, Steuerzeichen escapen, `strict=False`.
3. `all?` für die Erkennung verwenden. Für zyklische Abfragen `all?` beibehalten (Metadaten sind nötig) oder `all` nutzen und die Metadaten aus dem Start cachen. `??` nur als Fallback.
4. Typen normalisieren (String vs. Zahl, `"true"` vs. 1) und Sentinel-Werte filtern.
5. Schreiben nur für explizit freigegebene Keys erlauben. `min`/`max` und Enum prüfen. Kritische Keys wie `sensor_on`/`sensor_off` sowie Quellen- und Fühlerwahl sperren. Den Erfolg am Echo prüfen.
6. Das Passwort im Log maskieren und die Integration nur im LAN betreiben.
