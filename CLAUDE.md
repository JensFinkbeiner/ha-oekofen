# ÖkoFEN Pellematic für Home Assistant

Custom Integration `oekofen` für Home Assistant. Sie liest die eigene ÖkoFEN Pellematic Compact über die lokale JSON-Schnittstelle aus, nur lesend. Nutzer ist nur der Eigentümer an seiner eigenen HA (HA OS 2026.11, VM 100 auf dem Heimserver). Das Repo ist öffentlich, damit der eingebaute Marketplace es als benutzerdefiniertes Repository einbinden kann.

- Zielsystem: Home Assistant OS. Entwicklung auf Windows 11 mit Rancher Desktop. Tests und Werkzeuge laufen im Container, lokal ist kein Python nötig.
- Sprache: Entitäten und Config Flow auf Deutsch und Englisch (`custom_components/oekofen/translations/`). Code und Kommentare auf Englisch, README und CHANGELOG auf Deutsch.
- Design: kein eigenes UI. HA-Standard, Icons über `icons.json`. Das OFFICE55-Design gilt hier nicht.
- Tech-Stack: Python 3.14, aiohttp (Session von HA), DataUpdateCoordinator, `pytest-homeassistant-custom-component`, syrupy, aioresponses, Ruff, mypy strict, uv.
- Tests: `docker compose -f devenv/compose.yaml run --rm tools uv run pytest` (VS-Code-Task „Tests ausführen“). Lint: Task „Lint und Typprüfung“.
- HA-Testinstanz: `docker compose -f devenv/compose.yaml up -d ha`, danach http://127.0.0.1:8123. Nach Codeänderung: Task „HA-Testinstanz: Neu starten“.
- Abschluss jeder Änderung: Projekt-Skill `release` (`.claude/skills/release/`).
- Verteilung: GitHub-Release mit Tag `vX.Y.Z`. In HA über Marketplace → Benutzerdefiniertes Repository.
- Plan, Meilensteine und Data-Privacy-Bewertung: `PLAN.md`. Recherche: `docs/recherche/`.
- KI: keine.

## Aufbau

- `custom_components/oekofen/__init__.py`:
  - Setup: Client mit `async_get_clientsession`, danach der erste Abruf, danach wird das Hauptgerät registriert. Erst dann werden die Plattformen geladen.
  - Unload.
  - `async_remove_config_entry_device`: nur Untergeräte, deren Bereich fehlt, und nur, wenn die Integration geladen ist.
- `custom_components/oekofen/coordinator.py`: `OekofenRuntimeData` (Client, Coordinator, `main_device_id`), Typ `OekofenConfigEntry`. `OekofenCoordinator` holt alle 60 s (Option) die Daten, die Metadaten einmal täglich. `OekofenAuthError` wird zu `ConfigEntryAuthFailed` (Reauth), andere Fehler zu `UpdateFailed` mit `translation_key`.
- `custom_components/oekofen/entity.py`:
  - Geräte: `pe1`, `system` und `weather` liegen auf dem Hauptgerät. `hk`, `pu`, `ww`, `circ` und weitere `pe` werden Untergeräte.
  - **HA ≥ 2026.10:** `ChildDeviceInfo(parent_device_id=...)` statt `via_device`. Das Hauptgerät wird deshalb vorher mit `async_register_main_device` angelegt. Entity-IDs der Untergeräte beginnen mit dem Namen des Hauptgeräts, zum Beispiel `sensor.okofen_pellematic_heating_circuit_1_…`. Im Registry sucht man sie mit `async_get_device_by_identifier` bzw. `async_get_child_device_by_identifier`, `async_get_device` ist deprecated.
  - `OekofenEntityDescription` hat die Felder `kind` (Präfix des Bereichs) und `value_key` (JSON-Key).
  - `async_setup_section_entities` legt Entitäten pro vorhandenem Bereich an und ergänzt neue Bereiche über einen Coordinator-Listener (dynamic-devices).
- `custom_components/oekofen/sensor.py`:
  - `SENSORS` mit `kind_of_value`: `number`, `enum_phase` (Kesselphase über `const.BURNER_PHASES`) oder `text` (Statustext, `|` wird zu `, `).
  - `zero_is_none` für die Raumtemperatur ohne Fühler. Prozentwerte außerhalb von 0 bis 100 ergeben `None`.
- `custom_components/oekofen/binary_sensor.py`: Brenner (aus `L_state` in `BURNING_STATES`, nicht aus `L_br`) und Pumpen.
- `custom_components/oekofen/config_flow.py`: Schritte `user`, `reauth_confirm` und `reconfigure` (alle mit Verbindungstest `_async_test_connection`) sowie die Option Abfrageintervall (`OptionsFlowWithReload`). Doppelte Einrichtung wird über `_async_abort_entries_match` auf Host und Port erkannt, weil der Kessel keine Seriennummer liefert. Schemas mit `probatio`.
- `custom_components/oekofen/const.py`: Domain, Standardport 4321, Intervalle (Standard 60 s, 30 bis 3600 s), `METADATA_REFRESH`, `BURNING_STATES`, `BURNER_PHASES`.
- `custom_components/oekofen/icons.json`: Icons pro `translation_key`.
- `custom_components/oekofen/api/`: Protokoll-Client. **Keine HA-Imports**, damit das Paket später als PyPI-Bibliothek herausgelöst werden kann.
  - `client.py`: `OekofenClient`, das einzige Modul mit Netzwerkzugriff (Egress). Metadaten über `META_PATH = "all??"`, weil yarl das `?` von `all?` entfernt. Daten über `all`. Sperre plus 3 s Abstand, eine Wiederholung bei 401. Exceptions mit `from None`, damit die URL mit dem Passwort nie im Traceback steht.
  - `decode.py`: Dekodierung, JSON-Reparatur, `parse_meta`, `build_data` (Faktoren, Sentinels, V3-Strings), `parse_faults`. `DROPPED_SECTIONS` und `DROPPED_KEYS` regeln den Datenschutz.
  - `models.py`: `OekofenData` (`get`, `field_meta`, `numbered_sections`), `FieldMeta`, `OekofenFault`.
  - `exceptions.py`: `OekofenConnectionError`, `OekofenBusyError`, `OekofenAuthError` (Hilfeseite statt JSON), `OekofenParseError`.
- `tools/`: lokale Skripte. Die Zugangsdaten kommen aus dem Config Entry der Testinstanz (`_conn.py`), Ausgaben enthalten nie Werte.
  - `capture.py`: Rohdaten nach `local/raw/`.
  - `inspect_structure.py`: Keys und Typen.
  - `anonymize.py`: erzeugt `tests/fixtures/`.
  - `live_check.py`: Praxistest mit dem echten Client, im tools-Container.
- `custom_components/oekofen/quality_scale.yaml`: Stand der Integration Quality Scale. Bei jedem Meilenstein aktualisieren.
- `custom_components/oekofen/translations/`: `en.json` und `de.json`. Custom Integrations nutzen kein `strings.json`. Jeder Text steht in beiden Dateien.
- `tests/`: pytest, Fixtures in `tests/fixtures/` (nur erfundene oder anonymisierte Daten, Host immer `192.0.2.x`). `tests/api/` simuliert den Kessel mit `AiohttpClientMocker` und `FakeBoiler`. aioresponses passt nicht zur aiohttp-Version von HA. `test_fixtures_privacy.py` bewacht die Fixtures. `conftest.py` legt die `snapshot`-Fixture fest auf `HomeAssistantSnapshotExtension` (`tests/snapshots/`), sonst entscheidet die Ladereihenfolge der Plugins. Für Snapshots aller Entitäten die Fixture `entity_registry_enabled_by_default` nutzen.
- `devenv/compose.yaml`: Dienst `ha` (Testinstanz) und `tools` (uv, Python 3.14, venv im Docker-Volume).
- `.github/workflows/`: `validate.yaml` (hassfest, HACS-Action), `tests.yaml` (Ruff, mypy, pytest).
- `local/`: echte Kesselantworten und lokale Skripte, steht in `.gitignore`.

## Arbeitsregeln (verbindlich)

1. Nach jeder abgeschlossenen Änderung die Tests laufen lassen (Testbefehl oben), dann `VERSION`, `pyproject.toml` (`version`), `manifest.json` (`version`) und `CHANGELOG.md` anpassen. Die drei Versionsangaben sind immer gleich.
2. Jede Änderung wird sofort committet und gepusht (`origin`, Branch `main`). Version, Changelog-Eintrag und Änderung gehören in denselben Commit. Die Commit-Nachricht beginnt mit der Version, zum Beispiel `v0.5.0: Kurzbeschreibung`. Kein Stand bleibt uncommitted oder ungepusht liegen.
3. Versionen: `MAJOR.MINOR.PATCH`. MAJOR nur auf ausdrücklichen Wunsch des Nutzers. MINOR bei jeder neuen Funktion, PATCH bei jeder Fehlerbehebung. Reine Dokumentation und Refactoring ändern die Version nicht.
4. Changelog im Format Keep a Changelog: `## [x.y.z] - JJJJ-MM-TT`, neueste Version oben, Gruppen „Hinzugefügt“, „Geändert“, „Behoben“. Keine Datumsangaben erfinden.
5. Keine Secrets in Code, Doku, Beispielen, Logs oder Changelog. Das JSON-Passwort steht im URL-Pfad. Es wird in jeder Logmeldung, Exception und Diagnose maskiert, und ein Test prüft das.
6. Data Privacy ist oberste Prämisse:
   - Die Integration spricht nur mit dem Kessel im LAN. Ein neuer Datenfluss nach außen bedeutet: anhalten und den Nutzer fragen.
   - Weil das Repo öffentlich ist, kommen keine echte IP, kein Ort, keine Seriennummer und keine echten Kesselantworten hinein.
   - `weather.L_location` wird beim Parsen verworfen.
   - Echte Rohdaten liest Claude nicht selbst ein. Lokale Skripte werten sie aus, Claude sieht nur Kennzahlen und Struktur.
   - Die `.env` des Pellet-Monitors (`C:\APPs\oekofen`) wird nicht gelesen.
7. **Kein Schreiben auf den Kessel.** Der Client hat keine Schreibfunktion. Schreiben kommt erst nach einer eigenen Planrunde (Risiko Fehler 1020 und Werksreset, siehe `PLAN.md`).
8. Der Kessel verträgt höchstens eine Anfrage alle 2,5 s, und dieses Limit teilen sich alle Clients (auch der Pellet-Monitor, 60 s). Anfragen serialisieren, Intervall nie unter 30 s. In Tests nie den echten Kessel ansprechen.
9. HA-Konventionen: `runtime_data`, `has_entity_name` plus `translation_key`, `EntityDescription`-Listen, `DeviceInfo` als Dataclass, `step_id` in jedem Formular, `PARALLEL_UPDATES` in jeder Plattform, Exceptions mit `translation_key`. Vorbilder im Core: peblar, elgato, homewizard.
10. Neue Funktionen bekommen einen Test. Coverage mindestens 95 %, `config_flow.py` 100 %. Entitäten über syrupy-Snapshots.
11. Diese `CLAUDE.md` aktuell halten, sobald sich Aufbau, Befehle oder Regeln ändern. Nach größeren Änderungen den Nutzer fragen, ob README und `PLAN.md` angepasst werden sollen.
12. Bei jeder Änderung am Ablauf `devenv/compose.yaml`, `.vscode/tasks.json`, README (Abschnitt Entwicklung) und `.github/workflows/` im selben Commit nachziehen.

## Tiefencheck

Fällig vor jedem Meilenstein (Fragen 2 und 4), vor jedem Release (alle vier) und auf Zuruf „Tiefencheck“. Leitsatz: tiefer, nicht umfangreicher.

1. Profi-Extras: Was würde ein erfahrener Entwickler hier tun, worum der Nutzer nicht gebeten hat? Höchstens fünf, jedes mit geschätztem Aufwand. Der Nutzer wählt aus, der Rest kommt in `PLAN.md` unter „Später“.
2. Rohdaten: Mit welchen echten, unverarbeiteten Ausgangsdaten beginnen, zum Beispiel echte `all`- und `all?`-Antworten? Sie bleiben in `local/`. Vertrauliche Rohdaten liest Claude nicht selbst, lokale Skripte werten sie aus. Für Tests werden daraus anonymisierte Daten abgeleitet.
3. Methoden und Werkzeuge: konkrete Bibliotheken, Verfahren und Testwerkzeuge, jeweils mit Begründung.
4. Unabhängige Prüfung: Welcher Nachweis, der nicht von Claude oder dem Nutzer abhängt, belegt das Ergebnis? Zum Beispiel CI (hassfest, HACS-Action, pytest), der Abgleich mit dem Pellet-Monitor oder Kennzahlen aus dem Echtbetrieb. Eigene Code-Durchsicht zählt nicht.

Ein Meilenstein gilt erst als fertig, wenn sein Abnahmekriterium in `PLAN.md` erfüllt ist.

## Weitere Regeln

- Nichts veröffentlichen, versenden oder löschen ohne Bestätigung. Das gilt auch für GitHub-Releases.
- Die HA-Testinstanz bindet den Port nur an 127.0.0.1.
