# Changelog

Format nach [Keep a Changelog](https://keepachangelog.com/de/1.1.0/). Versionsschema `MAJOR.MINOR.PATCH`:
MAJOR wird nur auf ausdrücklichen Wunsch erhöht, MINOR bei neuen Funktionen, PATCH bei Fehlerbehebungen.
Reine Dokumentation und Refactoring ändern die Version nicht.

## [0.2.0] - 2026-11-22

### Hinzugefügt
- Protokoll-Client `api/` (ohne HA-Abhängigkeit, async mit aiohttp, mypy strict, `py.typed`):
  - Lesen von `all` und der Metadaten-Antwort mit Faktoren, Einheiten, Min/Max und Enum-Texten.
  - Dekodierung UTF-8/Latin-1, Reparatur von kaputtem JSON, Werte von Firmware 3.x als Strings, Sentinel-Werte ergeben „kein Sensor“.
  - Störungseinträge aus dem Bereich `error`.
  - Höchstens eine Anfrage gleichzeitig, mindestens 3 s Abstand, eine Wiederholung bei „busy“ (401).
  - Fehlermeldungen enthalten nie Passwort oder URL. Standort und Wettervorhersage werden verworfen.
- Lokale Werkzeuge in `tools/`: Rohdaten erfassen, Struktur ohne Werte anzeigen, Fixtures anonymisieren, Praxistest gegen den Kessel.
- Anonymisierte Test-Fixtures aus echten Antworten und ein Test, der private Texte und IP-Adressen in Fixtures verhindert.

### Geändert
- Die Metadaten werden über `all??` abgefragt: aiohttp/yarl entfernt bei `all?` das leere `?`, der Kessel bekäme sonst nur `all`. Am Kessel geprüft: `all??` liefert dieselbe Antwort wie `all?`.

### Geprüft
- 22.11.2026, Praxistest `tools/live_check.py` gegen den eigenen Kessel: 7 Bereiche, 108 Werte, 105 Feldbeschreibungen, keine Parse-Fehler. Tests: 35 bestanden, 100 % Branch-Coverage.

## [0.1.0] - 2026-11-22

### Hinzugefügt
- Projektstart: Plan (`PLAN.md`), Recherche zur ÖkoFEN-JSON-Schnittstelle und zu den HA-Standards (`docs/recherche/`).
- Grundgerüst der Integration `oekofen`: Manifest, Einrichtung über die Oberfläche (Host, Port, JSON-Passwort, noch ohne Verbindungstest), Übersetzungen Deutsch und Englisch, `quality_scale.yaml` als Checkliste.
- Tests mit `pytest-homeassistant-custom-component`, Ruff und mypy strict, alles im Container.
- GitHub Actions: hassfest, HACS-Prüfung, Tests.
- HA-Testinstanz auf Rancher Desktop (`devenv/compose.yaml`) und VS-Code-Tasks.
