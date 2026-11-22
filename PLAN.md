# Plan: ÖkoFEN Pellematic für Home Assistant

Stand: 22.11.2026 · Status: freigegeben am 22.11.2026 · Erstellt mit privat-app-kickoff 0.7.1

## Ziel

Eine eigene Home-Assistant-Integration (Custom Integration, Domain `oekofen`) liest die ÖkoFEN Pellematic Compact über ihre lokale JSON-Schnittstelle aus. Die Werte stehen danach als Geräte und Entitäten in HA zur Verfügung.

Die Integration liefert drei Dinge, die der Pellet-Monitor nicht kann. Damit ist die offene Frage aus Heimserver-Ausbau 6.5.3 beantwortet:

1. Push aufs iPhone bei Kesselstörung (Automation in HA)
2. Wärme- bzw. Pelletenergie in kWh im Energie-Dashboard
3. Kesselwerte auf den HA-Dashboards (Energiefluss, Esszimmer-Display)

Erfolgreich ist sie, wenn sie 14 Tage ohne Eingriff läuft und dabei:

- keine Fehlerflut im HA-Log erzeugt,
- den Pellet-Monitor nicht stört,
- dieselben Brennerstarts und Laufzeiten zeigt wie der Pellet-Monitor.

Qualitätsmaßstab ist die Integration Quality Scale von Home Assistant. Ziel ist Platin, soweit die Regeln auf eine Custom Integration zutreffen. Der Stand wird in `quality_scale.yaml` gepflegt.

## Nutzer

Nur Jens, an der eigenen Home-Assistant-Instanz (HA OS 2026.11.1, VM 100 auf dem Heimserver). Das Repository ist öffentlich auf GitHub, damit der eingebaute Marketplace es als benutzerdefiniertes Repository einbinden kann. Es kommt nicht in den offiziellen Katalog, und es gibt keinen Support für andere.

## Anlage (aus Pellet-Monitor und SecondBrain)

| Teil | JSON-Bereich | Bemerkung |
|---|---|---|
| Kessel Pellematic Compact PES 212, 12 kW | `pe1` | `L_br` zeigt bei dieser Anlage den Brenner nicht an. „Brenner an“ wird aus `L_state` 0–4 abgeleitet (bestätigt 15.10.2026). |
| Heizkreis 1 | `hk1` | Kein Raumfühler. `L_roomtemp_act` wird nicht angeboten. |
| Puffer 1 | `pu1` | Oben (`tpo`) und Mitte (`tpm`) |
| Warmwasser 1 | `ww1` | |
| Zirkulation 1 | `circ1` | Key heißt `L_pummp` (Tippfehler der Firmware) |
| System, Wetter | `system`, `weather` | `weather.L_location` wird verworfen (Datenschutz) |
| Pelletlager | `pe1.L_storage_*` | Nicht verwendbar: fester Einstellwert, der Kessel misst keinen Verbrauch |
| Firmware | – | Touch V4.00b (abgelesen am Touch unter „Software“, 22.11.2026). Passt zu den numerischen Werten. Älter als V4.02, deshalb tritt der Fehler mit dem fehlenden Anführungszeichen bei `L_statetext` hier nicht auf. Die Reparatur bleibt für spätere Updates drin. |

Die Integration erkennt beim Einrichten, welche Bereiche vorhanden sind (`hk1..6`, `pu1..3`, `ww1..3`, `sk1..6`, `circ1..3`, `pe1..4`), und legt nur dafür Geräte an. Getestet wird nur gegen die eigene Anlage. Weitere Bereiche wie Solar oder Wärmepumpe bekommen Grundsensoren, sind aber ungeprüft.

## Umfang der ersten Version

Enthalten:

- **Einrichtung über die HA-Oberfläche** (Config Flow):
  - Eingaben: Host, Port (Standard 4321), JSON-Passwort.
  - Verbindungstest beim Einrichten.
  - Erkennung doppelter Einrichtung.
  - Reauth bei falschem Passwort.
  - Reconfigure, um Host und Port zu ändern.
- **Optionen:** Abfrageintervall (Standard 60 s, mindestens 30 s), Nennleistung (12 kW), Wirkungsgrad, Heizwert Pellets.
- **Geräte:**
  - Kessel als Hauptgerät.
  - Heizkreis, Puffer, Warmwasser und Zirkulation als Untergeräte (Child Devices).
- **Sensoren:**
  - Temperaturen (Kessel, Vorlauf, Abgas, Außen, Puffer oben/Mitte, Warmwasser) mit `device_class` und `state_class` für Langzeitstatistik.
  - Modulation, Unterdruck, Saugzug.
  - Kesselphase, Heizkreis-, Puffer- und Warmwasser-Zustand als übersetzte Enum- bzw. Textsensoren.
- **Binärsensoren:** Brenner an, Pumpen (Heizkreis, Puffer, Warmwasser, Zirkulation).
- **Extra „Störungsmeldung“:**
  - Binärsensor „Störung“ (`problem`) und Sensor mit Fehlercode und Fehlertext aus dem Bereich `error`.
  - Bei einer aktiven Störung erscheint ein Reparatur-Hinweis (Repair) in HA, nach Behebung verschwindet er.
  - Eine Beispiel-Automation für den Push aufs iPhone liegt in der README.
- **Extra „Brenner-Statistik“:**
  - Brennerstarts gesamt (`pe1.L_starts`, `total_increasing`) und Betriebsstunden.
  - Starts heute, Brennerlaufzeit heute.
  - Dauer des letzten Laufs, Kurzläufe heute (Grenze wie im Pellet-Monitor).
  - Die Tageswerte überstehen einen HA-Neustart (RestoreSensor).
- **Extra „Energie in kWh“:**
  - Geschätzte Wärmeenergie und Pelletverbrauch (kWh und kg), `total_increasing`.
  - Gerechnet als Nennleistung × Brennzeit, umgerechnet über Wirkungsgrad und Heizwert. Das ist dasselbe Modell wie im Pellet-Monitor.
  - Tauglich fürs Energie-Dashboard.
  - In Name und Beschreibung als Schätzung gekennzeichnet.
- **Extra „Robuste Abfrage“:**
  - Genau eine Anfrage pro Intervall (`all`). Metadaten (`all?`: Faktor, Einheit, Format) beim Start und danach einmal täglich.
  - Bei „Wait at least 2500ms“ bzw. HTTP 401 durch eine Kollision mit dem Pellet-Monitor: eine Wiederholung nach 3 s, danach Backoff.
  - Erster Ausfall nur als INFO im Log, Entitäten „nicht verfügbar“ statt Fehlerflut. Eine Meldung, wenn der Kessel wieder erreichbar ist.
  - Diagnose-Download mit geschwärztem Passwort, Host und Standort.
- **Sprachen:** Deutsch und Englisch.
- **Installation** über den eingebauten Marketplace als benutzerdefiniertes Repository, Updates über GitHub-Releases.

Bewusst nicht enthalten (später, siehe Abschnitt „Später“):

- Jedes Schreiben auf den Kessel, also Betriebsart, Sollwerte und „Warmwasser einmal laden“. Begründung siehe Data Privacy und Risiken. Kommt frühestens nach 1.0.0, mit eigener Planrunde.
- Climate- und Water-Heater-Entitäten. Ohne Schreiben bringen sie keinen Mehrwert. Ein Climate-Heizkreis ohne Raumfühler wäre außerdem fachlich falsch.
- Pelletvorrat und Lagerstand: Den rechnet weiter der Pellet-Monitor (Lieferungen, Kalibrierung).
- Modbus TCP, Cloud-Portal my.oekofen.info, `json.properties`-Erweiterung per USB-Stick.
- Aufnahme in den offiziellen Katalog bzw. den HA-Core.

## Data Privacy

Grundsatz: Die Daten bleiben im eigenen Netz. Die Integration spricht nur mit dem Kessel im LAN.

| Datenart | Schutzstufe | Herkunft | Speicherort | Aufbewahrung |
|---|---|---|---|---|
| Betriebswerte (Temperaturen, Zustände, Starts) | Vertraulich (Smart-Home-Daten) | Kessel, JSON | HA-Recorder (Datenbank in HA) | Nach den Recorder-Einstellungen von HA, Langzeitstatistik unbegrenzt |
| Störungen und Fehlertexte | Vertraulich | Kessel, `error` | HA-Recorder, Repair-Hinweis | wie oben |
| Einstellwerte der Heizung (aus `all?`) | Vertraulich | Kessel | Nur im Arbeitsspeicher und in der Diagnose | nicht dauerhaft |
| Standort der Wetterquelle (`weather.L_location`) | Vertraulich | Kessel | Wird beim Lesen verworfen | nie gespeichert |
| JSON-Passwort, IP-Adresse | Streng vertraulich bzw. vertraulich | Eingabe im Config Flow | Config Entry in HA (`.storage`) | bis die Integration entfernt wird |
| Echte Kesselantwort (Rohdaten für Tests) | Vertraulich | Kessel | Nur lokal in `local/` (in `.gitignore`) | bis Projektende |

Datenflüsse nach außen:

| Ziel | Welche Daten | Schutzstufe | Zweck | Genehmigt von / am |
|---|---|---|---|---|
| keine | – | – | Die Integration ruft nichts außerhalb des LAN auf | – |
| GitHub (öffentliches Repo) | Nur Quellcode, erfundene bzw. anonymisierte Testdaten | Öffentlich | Verteilung über den Marketplace | Jens, 22.11.2026 (Repo öffentlich) |

Maßnahmen:

- Alle Zugriffe auf den Kessel laufen über ein zentrales Modul (`api/client.py`). Es gibt keine weiteren Netzwerkaufrufe.
- Das Passwort steht im URL-Pfad (ÖkoFEN-Vorgabe, kein HTTPS). Es wird deshalb in allen Logmeldungen, Exceptions und der Diagnose maskiert. Ein Test prüft das.
- `weather.L_location` und andere Ortsangaben verwirft schon der Parser.
- Test-Fixtures sind aus einer echten Antwort abgeleitet, aber anonymisiert (Ort, Wetterquelle, Namen ersetzt). Ein Test bricht ab, wenn Fixtures Muster wie die eigene Straße oder IP enthalten.
- Keine Telemetrie, keine externen Dienste, keine CDN-Ressourcen.
- Schreiben ist in Version 1 technisch nicht möglich: Der Client hat keine Schreibfunktion.

Risiken:

- Der Pellet-Monitor und HA fragen gleichzeitig an (das Limit von 2,5 s gilt gemeinsam). → Eine Wiederholung nach 3 s, Backoff, kein Fehler beim ersten Treffer. Beobachtung in Meilenstein 0.6.0.
- Das Passwort ist im LAN im Klartext lesbar. → ÖkoFEN-Vorgabe, nicht änderbar. Wird mit dem IoT-VLAN (12.21) entschärft. Ein eigenes JSON-Passwort verwenden, nicht das Web-Passwort.
- Ein späteres Schreiben kann die Anlage beschädigen: Ein Fall mit Fehler 1020 erforderte einen Werksreset (Issue #178 bei dominikamann). → In Version 1 kein Schreiben. Später nur mit Freigabeliste, Min/Max-Prüfung und gesperrten Fühler-Keys.
- Das öffentliche Repo verrät Details der eigenen Anlage. → Keine IP, kein Ort, keine Seriennummer im Repo. Die Anlagentabelle oben ist allgemein gehalten und unkritisch.

## KI-Einbindung

Keine. Die Integration braucht keine KI.

## Zielsysteme

Laufzeit ist Home Assistant OS (Linux). Entwickelt wird auf Windows 11 (ThinkPad) mit Docker auf Rancher Desktop.

- Tests, Linting und die HA-Testinstanz laufen in Containern. Auf Windows muss außer Docker, Git und VS Code nichts installiert sein.
- Ein Devcontainer für VS Code ist optional. Unter Windows wird er als „Named Container Volume“ betrieben, damit Dateizugriffe schnell sind.
- Zeilenenden LF (`.gitattributes`), wie beim Pellet-Monitor gelernt.

## Sprache der Oberfläche

Entitätsnamen, Config Flow, Fehlermeldungen und Repair-Hinweise gibt es auf Deutsch und Englisch (`translations/de.json`, `translations/en.json`), keine Texte im Code. Code und Kommentare sind auf Englisch, README und CHANGELOG auf Deutsch.

## Design

Abweichung vom OFFICE55-Design: Die Integration hat keine eigene Oberfläche, sie erscheint im Design von Home Assistant. OFFICE55 taucht nur als Autor bzw. `codeowners` auf. Icons kommen aus `icons.json` (Material Design Icons). Brand-Bilder (`brand/`) mit eigenem neutralem Flammen- oder Pellet-Symbol, kein ÖkoFEN-Logo (Markenrecht).

Dokumente aus der App: keine.

## Tech-Stack

| Baustein | Wahl | Begründung |
|---|---|---|
| Sprache | Python 3.14 | Mindestversion von HA 2026.11 (laut Recherche, in 0.1.0 prüfen) |
| HTTP | `aiohttp` mit der Session von HA (`async_get_clientsession`) | Vorgabe der Quality Scale (inject-websession, async-dependency) |
| Protokoll-Code | Eigenes Paket `custom_components/oekofen/api/` ohne HA-Imports | Für den Eigengebrauch genügt Code im Integrationsordner. Ohne HA-Abhängigkeit lässt er sich später als PyPI-Bibliothek herauslösen und einzeln testen. |
| Datenmodell | `dataclasses` mit vollständigen Typen, mypy strict | Vorgabe strict-typing (Platin), fängt Fehler bei Faktoren und Typen früh ab |
| Projektwerkzeuge | `uv`, Ruff, mypy, prek (pre-commit) | Wie im HA-Core |
| Tests | pytest, `pytest-homeassistant` (bzw. `pytest-homeassistant-custom-component`, in 0.1.0 prüfen), syrupy-Snapshots, `aioresponses` | Echte HA-Testumgebung. Snapshots machen jede Änderung an Entitäten sichtbar. |
| CI | GitHub Actions: hassfest, HACS-Action, Ruff, mypy, pytest mit Coverage | Unabhängige, wiederholbare Prüfung bei jedem Push |
| Testinstanz | `compose.yaml` mit HA-Container 2026.11.x, `custom_components` eingebunden, Port `127.0.0.1:8123` | Ausprobieren ohne Risiko für die echte HA |

Vorbilder im Core: Peblar und Elgato für Aufbau und Tests, HomeWizard für Energie-Sensoren, BSB-LAN fachlich für Heizungsregler.

## Architektur

`OekofenClient` (im Ordner `api/`) holt `all` bzw. `all?`. Es dekodiert die Bytes (erst UTF-8 strikt, sonst Latin-1), repariert das bekannte kaputte JSON und normalisiert die Typen. Dazu gehören Strings gegenüber Zahlen, `"true"` gegenüber 1, Sentinel-Werte wie -32768 und Faktoren aus den Metadaten. Das Ergebnis ist ein typisiertes `OekofenData`. Eine Sperre sorgt dafür, dass nie zwei Anfragen gleichzeitig laufen, und hält mindestens 3 s Abstand.

Ein `DataUpdateCoordinator` ruft den Client im eingestellten Intervall ab. `BurnerTracker` leitet aus jeder neuen Messung die Brennerläufe, Tageswerte und die Energie ab. Er ist rein und ohne HA testbar, angelehnt an `burner.py` im Pellet-Monitor, aber neu geschrieben. Die Entitäten werden aus Beschreibungslisten (`EntityDescription`) erzeugt, mit `translation_key` und `has_entity_name`.

```
HA-OekoFEN-Integration/
├── custom_components/oekofen/
│   ├── __init__.py          Setup, runtime_data
│   ├── manifest.json        domain oekofen, iot_class local_polling, version
│   ├── config_flow.py       user, reauth, reconfigure, options
│   ├── coordinator.py
│   ├── entity.py            Basisklasse, DeviceInfo
│   ├── sensor.py, binary_sensor.py
│   ├── burner.py            Brennerläufe, Tageswerte, Energie (rein)
│   ├── diagnostics.py, repairs.py
│   ├── icons.json, quality_scale.yaml
│   ├── translations/de.json, en.json
│   ├── brand/
│   └── api/                 client.py, decode.py, models.py, exceptions.py (ohne HA-Imports)
├── tests/
│   ├── api/                 Dekodierung, Fehlerfälle, Maskierung
│   ├── fixtures/            anonymisierte Kesselantworten (V4, V3, kaputt)
│   └── test_*.py            Config Flow, Sensoren (Snapshots), Diagnose, Repairs
├── local/                   echte Rohdaten, nie im Repo
├── devenv/compose.yaml      HA-Testinstanz
├── docs/recherche/          Recherche-Ergebnisse
├── .github/workflows/       validate.yaml, tests.yaml, release.yaml
├── hacs.json, pyproject.toml, README.md, CHANGELOG.md, VERSION, CLAUDE.md
```

## Deployment

Abweichend von der Kickoff-Vorlage gibt es keine eigene Docker-App, keine Start- und Stopp-Dateien und keine Weitergabe-Zips. Die Integration läuft in Home Assistant.

- **Entwicklung:** `devenv/compose.yaml` startet eine HA-Testinstanz auf Rancher Desktop (`127.0.0.1:8123`) mit dem eingebundenen Integrationsordner. Sie kann den echten Kessel im LAN erreichen, für den Praxistest.
- **VS-Code-Tasks:**
  - Testinstanz starten und stoppen
  - Testinstanz neu starten (nach Codeänderung)
  - Logs der Testinstanz
  - Tests ausführen
  - Lint und Typprüfung
- **Produktion:**
  - GitHub-Release mit Tag `vX.Y.Z`.
  - In der echten HA über Marketplace → Benutzerdefiniertes Repository → Integration installieren, danach einrichten.
  - Updates erscheinen im Marketplace und brauchen einen HA-Neustart.

## Git

Remote: GitHub, öffentliches Repository (Name zum Beispiel `ha-oekofen`), Branch `main`. Die Kickoff-Regel „Repository immer privat“ ist hier bewusst aufgehoben, weil der Marketplace nur öffentliche Repos einbinden kann (Entscheidung Jens, 22.11.2026). Dafür gilt: keine privaten Daten im Repo, siehe Data Privacy.

## Tests

- Testbefehl im Container: `docker run --rm -v "$PWD":/repo -w /repo python:3.14-slim sh -c "pip install uv && uv run pytest"`. Dafür kommt ein VS-Code-Task.
- **`api/`:**
  - Dekodierung von UTF-8, Latin-1 und doppelt kodiertem `Â°C`.
  - Reparatur von kaputtem JSON (`L_statetext:`, Zeilenumbrüche in `error_1`, „Variable does not exist“).
  - Typen in V3 und V4, Sentinel-Werte, Faktoren aus `all?`.
  - Verhalten bei „Wait at least 2500ms“ und 401, Timeouts, Verbindungsabbruch.
  - Maskierung des Passworts in jeder Exception.
- **`burner.py`:**
  - Brennerläufe aus erfundenen Abfolgen: Lauf über Mitternacht, Lauf in einer Aufzeichnungslücke, HA-Neustart mitten im Lauf, Zählersprung bei `L_starts`.
- **Integration:**
  - Config Flow mit allen Pfaden (Erfolg, nicht erreichbar, falsches Passwort, doppelt, reauth, reconfigure).
  - Snapshot aller Entitäten.
  - Diagnose ohne Passwort, Host und Ort.
  - Repair erscheint und verschwindet.
  - Unload und Reload.
- **Ziel:** Coverage mindestens 95 % insgesamt und 100 % für `config_flow.py` (Quality-Scale-Regel test-coverage).

## Tiefencheck

1. **Profi-Extras:**
   - Ausgewählt (alle vier vorgeschlagenen): Störungsmeldung, Energie in kWh, Brenner-Statistik, Robuste Abfrage. Aufwand geschätzt gut 3 Tage zusätzlich.
   - Nicht vorgeschlagen, steht unter „Später“: Schreiben.
2. **Rohdaten:**
   - Echte Antworten des eigenen Kessels: `all`, `all?` und `error` sowie eine Antwort während einer Störung (falls eine auftritt).
   - Ein lokales Skript `local/capture.py` holt sie mit 5 s Abstand und speichert sie in `local/` (in `.gitignore`).
   - Weil die Daten vertraulich sind, liest Claude sie nicht selbst. Ein lokales Anonymisierungsskript erzeugt daraus die Fixtures. Claude sieht nur das Ergebnis der Prüfung, ob noch Ortsangaben drin sind, und die Struktur (Keys, Typen).
   - Zusätzlich dient die Datenbank des Pellet-Monitors als Vergleichsbasis. Ausgewertet werden nur Kennzahlen, keine Inhalte.
3. **Methoden und Werkzeuge:**
   - `aioresponses`: simuliert den Kessel einschließlich der Eigenheiten, ohne echtes Netzwerk.
   - syrupy: Snapshots aller Entitäten mit Einheiten und Klassen, damit Regressionen sofort auffallen.
   - hassfest und HACS-Action: offizielle Prüfwerkzeuge für Manifest, Übersetzungen und Marketplace-Fähigkeit.
   - mypy strict: Typfehler bei den Faktoren und Werten.
   - `freezegun` bzw. `async_fire_time_changed`: Tageswechsel und Intervalle deterministisch testen.
4. **Unabhängige Prüfung für Version 1.0.0:**
   - CI grün: hassfest, HACS-Action, Ruff, mypy und pytest mit mindestens 95 % Coverage.
   - **Abgleich mit dem Pellet-Monitor über 7 Tage**, ausgeführt mit einem lokalen Skript, das nur Kennzahlen ausgibt:
     - Brennerstarts je Tag identisch,
     - Brennerlaufzeit je Tag ±2 %,
     - Energie je Tag ±5 % gegenüber dem Pelletmodell des Monitors.
   - **Betrieb 14 Tage an der echten HA:**
     - Verfügbarkeit mindestens 99 %,
     - höchstens 1 WARNING pro Tag von `custom_components.oekofen`,
     - keine Lücken oder neuen Fehler im Pellet-Monitor.
   - Ergänzend prüft eine frische Claude-Sitzung, ob man die Integration nur mit der README installieren und einrichten kann.

## Meilensteine

1. **0.1.0 Projektstart:** Plan, Git und öffentliches GitHub-Repo, CLAUDE.md, CHANGELOG, Gerüst der Integration (lädt ohne Entitäten), CI mit hassfest und HACS-Action, HA-Testinstanz läuft. Die offenen Punkte zu Python 3.14 und dem Testpaket sind geklärt.
   - Abnahme: CI grün, Integration erscheint in der Testinstanz unter „Integration hinzufügen“.
   - **Abgenommen am 22.11.2026:** CI grün (hassfest, HACS, Tests mit 100 % Coverage). Jens hat die Integration in der Testinstanz eingerichtet.
2. **0.2.0 Protokoll-Client:** `api/` mit Dekodierung, Reparatur, Typen, Metadaten, Rate-Limit und Maskierung. Rohdaten erfasst und anonymisierte Fixtures erzeugt.
   - Abnahme: 100 % Coverage in `api/`. Ein lokaler Praxistest gegen den echten Kessel liest alle Bereiche ohne Parse-Fehler (Ausgabe nur Anzahl der Werte und Dauer).
   - Tiefencheck vor dem Start (22.11.2026):
     - Rohdaten: `tools/capture.py` holt `all`, `all?` und `error` mit 5 s Abstand nach `local/raw/`. Die Zugangsdaten liest es aus dem Config Entry der Testinstanz, Claude sieht sie nicht. `tools/inspect_structure.py` gibt nur Bereiche, Keys, Typen, Faktoren und Einheiten aus, keine Werte.
     - Unabhängige Prüfung: pytest mit 100 % Branch-Coverage in `api/`, Fixtures aus den echten Antworten anonymisiert (`tools/anonymize.py`) und ein Test gegen Ortsangaben. Dazu `tools/live_check.py` mit dem echten Client gegen den Kessel, Ausgabe nur Anzahl der Werte je Bereich, Dauer und Fehler.
   - **Abgenommen am 22.11.2026:**
     - 35 Tests bestanden, 100 % Branch-Coverage, mypy strict ohne Befund.
     - Praxistest: 7 Bereiche (system, weather, hk1, pu1, ww1, circ1, pe1), 108 Werte, 105 Feldbeschreibungen, keine Parse-Fehler, Antwortzeit 0,6 s.
   - Befunde am echten Kessel:
     - Antworten als gültiges JSON. `all` kommt in reinem ASCII, `all?` in Latin-1.
     - Werte numerisch wie bei Firmware 4.x. Die Firmware-Version selbst steht nicht in der Antwort.
     - `error` ist derzeit leer.
     - Wichtig: aiohttp entfernt das `?` von `all?`, deshalb wird `all??` abgefragt (am Kessel geprüft, gleiche Antwort).
3. **0.3.0 Einrichtung und Grundsensoren:** Config Flow (user, reauth, reconfigure, options), Coordinator, Geräte und Untergeräte, Sensoren und Binärsensoren, Übersetzungen, Icons.
   - Abnahme: Snapshot-Tests grün. In der Testinstanz stimmen die Werte mit der Anzeige am Touch bzw. im Pellet-Monitor überein (Stichprobe von 10 Werten, Jens prüft).
   - Tiefencheck vor dem Start (22.11.2026):
     - Rohdaten: die anonymisierten Fixtures aus 0.2.0 und die Enum-Texte des Kessels. Kesselphase `pe1.L_state`: 0 Dauerlauf bis 12 Einmessen, 97–101 Aus. Kesseltyp `pe1.L_type`: 9 COMPACT.
     - Unabhängige Prüfung:
       - syrupy-Snapshots aller Entitäten (Einheit, Klasse, Gerät).
       - hassfest prüft Übersetzungen und Manifest.
       - Config Flow zu 100 % getestet.
       - Jens vergleicht 10 Werte in der Testinstanz mit dem Touch bzw. dem Pellet-Monitor.
       - Zusätzlich prüft ein Subagent den Code gegen die Quality-Scale-Regeln. Das ist ergänzend und zählt nicht als unabhängige Prüfung.
   - Stand 22.11.2026:
     - 83 Tests grün, 100 % Coverage. Testinstanz am echten Kessel mit 38 Entitäten ohne Fehler.
     - Review umgesetzt (siehe CHANGELOG 0.3.0).
     - **Abgenommen am 22.11.2026:** Jens hat 10 Werte in der Testinstanz mit dem Touch bzw. dem Pellet-Monitor verglichen, sie stimmen.
   - Aus dem Review übernommen in 0.4.0:
     - Modell des Kessels nach jeder Metadaten-Aktualisierung im Geräteregister nachziehen.
     - Einheit aus den Metadaten gegen die erwartete Einheit prüfen und bei Abweichung warnen.
     - Bei den Zählern `L_starts` und `L_runtime` einen kleineren Wert als den letzten verwerfen, außer bei einem echten Reset.
     - Firmware als `sw_version` aus dem Kopf der Hilfeseite („Oekofen JSON Interface V4.00“) lesen, einmal beim Start.
4. **0.4.0 Störung und Diagnose:** Störungs-Binärsensor, Fehlertext, Repair-Hinweis, Diagnose-Download, robuste Abfrage mit Backoff.
   - Abnahme: Tests mit einer Störungs-Fixture. Die Diagnose enthält nachweislich weder Passwort, Host noch Ort (Test).
5. **0.5.0 Brenner-Statistik und Energie:** `burner.py`, Tageswerte mit Restore, Energie- und Pelletsensor mit Optionen.
   - Abnahme: Tests der Grenzfälle grün. Das Vergleichsskript gegen den Pellet-Monitor über 3 Tage in der Testinstanz erfüllt die Toleranzen.
6. **0.6.0 Echtbetrieb:** Release über GitHub, Installation über den Marketplace an der echten HA. Energie-Dashboard und Push-Automation für Störungen eingerichtet.
   - Abnahme: 7 Tage Betrieb mit den Kennzahlen aus Tiefencheck 4.
7. **1.0.0:** `quality_scale.yaml` vollständig (done oder exempt mit Begründung), README fertig, alle Prüfungen aus Tiefencheck 4 bestanden, Ergebnis im CHANGELOG.

## Später

- Schreiben: Betriebsart Heizkreis und Warmwasser (`select`), Warmwasser-Soll (`number`), „Warmwasser einmal laden“ (`button`), eventuell `water_heater`. Nur mit Freigabeliste, Min/Max-Prüfung aus `all?`, Echo-Prüfung und gesperrten Fühler-Keys. Eigene Planrunde mit Tiefencheck.
- Protokoll-Code als eigene PyPI-Bibliothek herauslösen (Voraussetzung für Core oder den offiziellen Katalog).
- Discovery: Die ÖkoFEN hat vermutlich kein mDNS. Die Regel ist bis dahin `exempt`.
- Pelletvorrat aus dem Pellet-Monitor nach HA (per MQTT oder REST), falls der Monitor bleibt.
- Unterstützung und Tests für Solar, Wärmepumpe und mehrere Kessel.

## Offene Fragen

- ~~Firmware-Version des Touch~~ Geklärt am 22.11.2026: Touch V4.00b.
- **Firmware-Update am Kessel:** Steht eins an? Dann vorher Rohdaten sichern, um die Unterschiede zu sehen.
- ~~Unbestätigte Angaben aus der Recherche~~ Geklärt am 22.11.2026:
  - HA 2026.11.2 verlangt Python ≥ 3.14.2 (PyPI, bestätigt).
  - Testpaket ist `pytest-homeassistant-custom-component` 0.13.375. Es pinnt HA 2026.10.4 und läuft. `pytest-homeassistant` war auf PyPI nicht prüfbar und wird nicht genutzt.
  - Schemas mit `probatio` statt `voluptuous`, wie im Core (mypy verlangt das).
  - Die HACS-Action verlangt GitHub-Topics und `categories` im Manifest. Beides ist gesetzt.
- **IP und Port des Kessels:** Stehen in der `.env` des Pellet-Monitors. Jens trägt sie selbst im Config Flow ein, Claude liest die `.env` nicht.
- **Repo-Name auf GitHub und GitHub-Konto:** Ist `gh` angemeldet?
- **Pellet-Monitor:** Bleibt das Intervall von 60 s? Wenn er später wegfällt, entfällt auch die Kollisionsgefahr.
