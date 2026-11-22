# ÖkoFEN Pellematic für Home Assistant

Custom Integration für Home Assistant, die ÖkoFEN-Pelletkessel (Pellematic mit Touch-Bedienung) über die **lokale JSON-Schnittstelle** ausliest. Nur lesend, ohne Cloud. Die Daten verlassen das eigene Netz nicht.

> Status: **0.2.0, im Aufbau.** Der Protokoll-Client steht und ist am echten Kessel getestet. Die Integration lässt sich einrichten, liefert aber noch keine Entitäten. Fahrplan siehe [PLAN.md](PLAN.md).
> Privates Projekt ohne Support. Kein offizielles Produkt von ÖkoFEN.

## Geplanter Umfang (1.0.0)

- **Geräte:** Kessel mit Heizkreisen, Puffer, Warmwasser und Zirkulation als Untergeräten.
- **Sensoren:** Temperaturen, Modulation, Zustände sowie Pumpen und Brenner als Binärsensoren.
- **Störungen:** Störungsmeldung mit Fehlertext und Reparatur-Hinweis in HA.
- **Brenner-Statistik:** Starts und Laufzeit heute, letzter Lauf, Kurzläufe.
- **Energie:** geschätzte Wärmeenergie und Pelletverbrauch fürs Energie-Dashboard.

## Voraussetzungen

- Home Assistant 2026.11 oder neuer.
- ÖkoFEN-Kessel mit Touch-Bedienung und aktivierter JSON-Schnittstelle:
  1. Am Touch: Allgemeine Einstellungen → Netzwerkeinstellungen, nach unten scrollen. Eventuell vorher über das Schloss-Symbol den erweiterten Modus öffnen.
  2. JSON-Modus auf **Ein** stellen, nicht auf „Ein kompatibel“.
  3. Port (meist `4321`) und JSON-Passwort notieren. Das JSON-Passwort ist nicht das Passwort des Webportals.

## Installation

1. In Home Assistant: Einstellungen → Marketplace → ⋮ → Benutzerdefinierte Repositories → `https://github.com/JensFinkbeiner/ha-oekofen`, Kategorie „Integration“.
2. „ÖkoFEN Pellematic“ installieren und Home Assistant neu starten.
3. Einstellungen → Geräte & Dienste → Integration hinzufügen → „ÖkoFEN Pellematic“.
4. Host, Port und JSON-Passwort eintragen.

### Einrichtungsfelder

| Feld | Bedeutung |
|---|---|
| Host | IP-Adresse oder Hostname des Kessels |
| JSON-Port | Port der JSON-Schnittstelle, Standard `4321` |
| JSON-Passwort | Passwort der JSON-Schnittstelle |

## Entfernen

Einstellungen → Geräte & Dienste → ÖkoFEN Pellematic → ⋮ → Löschen. Danach im Marketplace deinstallieren und Home Assistant neu starten.

## Wichtig zum Abfragetakt

Der Kessel nimmt höchstens alle 2,5 Sekunden eine Anfrage an, und dieses Limit teilen sich alle Programme, die ihn abfragen. Die Integration fragt deshalb standardmäßig nur alle 60 Sekunden ab, nie öfter als alle 30 Sekunden.

## Entwicklung

Voraussetzungen: Git, VS Code und Rancher Desktop mit der Container-Engine „dockerd (moby)“. Rancher Desktop braucht unter Windows WSL 2. Python muss nicht lokal installiert sein.

| Aufgabe | VS-Code-Task (Terminal → Task ausführen) | Befehl |
|---|---|---|
| Tests | Tests ausführen | `docker compose -f devenv/compose.yaml run --rm tools uv run pytest` |
| Lint und Typen | Lint und Typprüfung | `docker compose -f devenv/compose.yaml run --rm tools sh -c "uv run ruff check . && uv run mypy"` |
| HA-Testinstanz | HA-Testinstanz: Starten | `docker compose -f devenv/compose.yaml up -d ha` → http://127.0.0.1:8123 |

Die Testinstanz bindet `custom_components/oekofen` schreibgeschützt ein. Nach einer Codeänderung genügt „HA-Testinstanz: Neu starten“. Ihre Konfiguration liegt in `devenv/config/` und wird nicht eingecheckt.

Echte Kesselantworten gehören nur nach `local/`. Dieser Ordner wird nie eingecheckt.

Lokale Werkzeuge in `tools/`: Sie lesen die Zugangsdaten aus der eingerichteten Integration der Testinstanz und geben nie Werte aus.

| Skript | Zweck |
|---|---|
| `python -I tools/capture.py` | Rohdaten des Kessels nach `local/raw/` holen |
| `python -I tools/inspect_structure.py` | Bereiche, Keys und Typen der Rohdaten anzeigen |
| `python -I tools/anonymize.py` | Test-Fixtures aus den Rohdaten erzeugen |
| `docker compose -f devenv/compose.yaml run --rm tools uv run python tools/live_check.py` | Praxistest mit dem echten Client |

## Lizenz

MIT, siehe [LICENSE](LICENSE).
