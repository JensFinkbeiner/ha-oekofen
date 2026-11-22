# Changelog

Format nach [Keep a Changelog](https://keepachangelog.com/de/1.1.0/). Versionsschema `MAJOR.MINOR.PATCH`:
MAJOR wird nur auf ausdrücklichen Wunsch erhöht, MINOR bei neuen Funktionen, PATCH bei Fehlerbehebungen.
Reine Dokumentation und Refactoring ändern die Version nicht.

## [0.1.0] - 2026-11-22

### Hinzugefügt
- Projektstart: Plan (`PLAN.md`), Recherche zur ÖkoFEN-JSON-Schnittstelle und zu den HA-Standards (`docs/recherche/`).
- Grundgerüst der Integration `oekofen`: Manifest, Einrichtung über die Oberfläche (Host, Port, JSON-Passwort, noch ohne Verbindungstest), Übersetzungen Deutsch und Englisch, `quality_scale.yaml` als Checkliste.
- Tests mit `pytest-homeassistant-custom-component`, Ruff und mypy strict, alles im Container.
- GitHub Actions: hassfest, HACS-Prüfung, Tests.
- HA-Testinstanz auf Rancher Desktop (`devenv/compose.yaml`) und VS-Code-Tasks.
