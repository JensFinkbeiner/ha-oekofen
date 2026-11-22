---
name: release
description: Abschluss jeder Änderung an der ÖkoFEN-Integration für Home Assistant. Tests und Lint laufen lassen, Version an drei Stellen und CHANGELOG.md anpassen, committen und pushen, bei Releases die unabhängige Prüfung ausführen und nach dem GitHub-Release fragen. Nutzen nach jeder abgeschlossenen Änderung am Code.
---

# Release einer Änderung

Nach jeder abgeschlossenen Änderung, in dieser Reihenfolge (Regeln aus `CLAUDE.md`):

1. Tests und Lint im Container:
   - `docker compose -f devenv/compose.yaml run --rm tools uv run pytest`
   - `docker compose -f devenv/compose.yaml run --rm tools sh -c "uv run ruff check . && uv run ruff format --check . && uv run mypy"`
   - Hat sich das Lockfile geändert, `uv lock` im selben Container ausführen und `uv.lock` mit committen.
2. Version: PATCH bei einer Fehlerbehebung, MINOR bei einer neuen Funktion, MAJOR nur auf ausdrücklichen Wunsch. Reine Doku-, Refactoring- und Werkzeug-Änderungen bekommen keine neue Version. Die Version steht an drei Stellen und ist überall gleich: `VERSION`, `pyproject.toml`, `custom_components/oekofen/manifest.json`.
3. `CHANGELOG.md`: neuer Abschnitt `## [x.y.z] - JJJJ-MM-TT` oberhalb des letzten, mit „Hinzugefügt“, „Geändert“, „Behoben“.
4. Mitpflegen, wenn betroffen:
   - `translations/en.json` und `de.json`: jeder Text in beiden Sprachen.
   - `quality_scale.yaml`: Regeln, die jetzt erfüllt sind, auf `done` setzen.
   - README: bei neuen Entitäten, Optionen oder geänderter Einrichtung.
   - `PLAN.md`: Meilenstein abhaken. Bei einem neuen Datenfluss nach außen erst nach Genehmigung des Nutzers abschließen.
   - Snapshots (`tests/snapshots/`): nur bewusst aktualisieren (`--snapshot-update`) und die Änderung prüfen.
5. Datenschutz-Check vor dem Commit: `git diff --cached` enthält keine echte IP (nur `192.0.2.x`), keinen Ort, kein Passwort und nichts aus `local/`.
6. Commit und Push: Die Nachricht beginnt mit der Version (`v1.2.3: Kurzbeschreibung`), danach `git push`.
7. **Release** (neue MINOR- oder MAJOR-Version, die auf die echte HA soll):
   - Vorher die unabhängige Prüfung aus dem Tiefencheck (Frage 4) des aktuellen Meilensteins in `PLAN.md` ausführen. Dazu gehören CI grün (hassfest, HACS, Tests) und die Abnahme des Meilensteins.
   - Ergebnis mit Datum im CHANGELOG-Eintrag festhalten. Schlägt sie fehl: nicht veröffentlichen.
   - Den Nutzer fragen, ob ein GitHub-Release `vX.Y.Z` angelegt werden soll. Erst nach Zustimmung taggen und veröffentlichen.
   - Kleine PATCH-Änderungen brauchen nur die normalen Tests.

Nie einchecken: `local/`, `devenv/config/`, Passwörter, echte Kesselantworten, echte IP-Adressen.
