# Changelog

Format nach [Keep a Changelog](https://keepachangelog.com/de/1.1.0/). Versionsschema `MAJOR.MINOR.PATCH`:
MAJOR wird nur auf ausdrücklichen Wunsch erhöht, MINOR bei neuen Funktionen, PATCH bei Fehlerbehebungen.
Reine Dokumentation und Refactoring ändern die Version nicht.

## [0.4.0] - 2026-11-22

### Hinzugefügt
- Störungsmeldung:
  - Binärsensor „Störung“ (Problem). Er ist an, wenn der Kessel Störungstexte oder einen Fehlerzähler `system.L_errors` > 0 meldet.
  - Sensor „Störungsmeldung“ mit Text und Code, alle Meldungen im Attribut `faults`.
  - Reparatur-Hinweis in HA, solange die Störung anliegt. Danach verschwindet er von selbst.
- Diagnose-Download. Geschwärzt sind Host, Passwort, Namen der Heizkreise und die Wetterquelle. Der Standort wird gar nicht erst gelesen.
- Robuste Abfrage:
  - Eine einzelne Kollision mit einem anderen Programm (zum Beispiel dem Pellet-Monitor) behält die letzten Werte.
  - Bei einem Dauerausfall verdoppelt sich das Intervall bis höchstens 10 Minuten und springt danach zurück.
- Firmware des Touch als Softwareversion des Geräts, gelesen aus dem Kopf der Hilfeseite (zum Beispiel V4.00b).
- Das Modell des Kessels wird bei jeder täglichen Aktualisierung der Metadaten nachgezogen.

### Geändert
- Meldet der Kessel für einen Wert eine andere Einheit als erwartet (zum Beispiel Sekunden statt Minuten), wird die Entität nicht angelegt, mit einer Warnung im Log.
- Die Zähler (Brennerstarts, Brennerstunden) laufen nie rückwärts. Ein kurzer Rücksprung zählt also nicht als Reset in der Statistik.
- Der Standort der Wetterquelle wird auch aus den Metadaten entfernt.

### Geprüft
- 22.11.2026: 97 Tests bestanden (80 Snapshots, darunter die Diagnose), 100 % Branch-Coverage, mypy strict ohne Befund.
- In der Testinstanz am echten Kessel: 40 Entitäten, Modell COMPACT, Firmware V4.00b, kein Fehler im Log.

## [0.3.0] - 2026-11-22

### Hinzugefügt
- Einrichtung mit Verbindungstest, Reauth bei geändertem JSON-Passwort, „Neu konfigurieren“ für Host und Port, Option Abfrageintervall (30 bis 3600 s).
- Coordinator: eine Anfrage pro Intervall, Metadaten einmal täglich. Fehler werden als übersetzte Meldung gezeigt, ein falsches Passwort startet die Reauth.
- Geräte: Regler als Hauptgerät (Modell aus `pe1.L_type`), Heizkreis, Puffer, Warmwasser und Zirkulation als Untergeräte (`ChildDeviceInfo`). Neue Bereiche kommen ohne Neustart dazu, nicht mehr gemeldete Untergeräte lassen sich löschen.
- 34 Sensoren und 4 Binärsensoren, Namen auf Deutsch und Englisch, Icons über `icons.json`. Selten gebrauchte Werte sind standardmäßig deaktiviert.

### Behoben (aus dem Review vor dem Release)
- Eine leere oder fremde Antwort (zum Beispiel HTML) gilt nicht mehr als falsches Passwort. Nur die echte Hilfeseite des Kessels („Oekofen JSON Interface … usage:“) startet die Reauth. Vorher hätte ein kurzer Aussetzer das Abfragen dauerhaft gestoppt.
- Das Passwort wird in der URL kodiert (`/`, `?`, `#`, `%`, Leerzeichen). IPv6-Adressen werden in eckige Klammern gesetzt.
- Verbindungsfehler tragen die aiohttp-Exception nicht mehr als `__context__` mit. Deren Text enthält die URL und damit das Passwort.
- Fehlen die Metadaten, wird das als Fehler gemeldet, statt die Werte unskaliert zu übernehmen (sonst 10-fach zu hohe Temperaturen).
- Prozentwerte: Sentinel-Werte und Werte außerhalb von 0 bis 100 erscheinen als „unbekannt“.
- Raumtemperatur ohne Raumfühler (0) erscheint als „unbekannt“ statt 0 °C.
- Ein Gerät lässt sich nicht löschen, solange die Integration nicht geladen ist. Vorher kam ein AttributeError.
- Nach einem Fehler im Einrichtungsformular wird das Passwort nicht ins Formular zurückgegeben.
- Eigene Fehlermeldung „Kessel ausgelastet“, wenn ein anderes Programm den Kessel gerade abfragt.

### Geprüft
- 22.11.2026: 83 Tests bestanden (76 Snapshots), 100 % Branch-Coverage, mypy strict ohne Befund.
- In der Testinstanz am echten Kessel wurden 38 Entitäten angelegt (25 aktiv), ohne Fehler im Log.
- Ein Subagent hat den Code gegen die Quality-Scale-Regeln geprüft. Die kritischen und wichtigen Funde sind behoben, der Rest steht in `PLAN.md`.

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
