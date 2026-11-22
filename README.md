# ÖkoFEN Pellematic für Home Assistant

Custom Integration für Home Assistant, die ÖkoFEN-Pelletkessel (Pellematic mit Touch-Bedienung) über die **lokale JSON-Schnittstelle** ausliest. Nur lesend, ohne Cloud. Die Daten verlassen das eigene Netz nicht.

> Status: **0.4.0, im Aufbau.** Einrichtung, Geräte, Sensoren, Störungsmeldung und Diagnose funktionieren. Brenner-Statistik und Energie folgen. Fahrplan siehe [PLAN.md](PLAN.md).
> Privates Projekt ohne Support. Kein offizielles Produkt von ÖkoFEN.

## Geplanter Umfang (1.0.0)

- **Geräte:** Kessel mit Heizkreisen, Puffer, Warmwasser und Zirkulation als Untergeräten.
- **Sensoren:** Temperaturen, Modulation, Zustände sowie Pumpen und Brenner als Binärsensoren.
- **Störungen:** Störungsmeldung mit Fehlertext und Reparatur-Hinweis in HA.
- **Brenner-Statistik:** Starts und Laufzeit heute, letzter Lauf, Kurzläufe.
- **Energie:** geschätzte Wärmeenergie und Pelletverbrauch fürs Energie-Dashboard.

## Voraussetzungen

- Home Assistant 2026.11 oder neuer.
- ÖkoFEN-Kessel mit Touch-Bedienung und aktivierter JSON-Schnittstelle. Getestet nur mit einer Pellematic Compact und Touch V4.00b. Andere Firmware-Stände sollten funktionieren, sind aber ungeprüft.
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

Die Verbindung wird beim Einrichten geprüft. Ändert sich später das JSON-Passwort, fragt Home Assistant von selbst nach dem neuen. Host und Port lassen sich über ⋮ → „Neu konfigurieren“ ändern.

### Optionen

| Option | Bedeutung |
|---|---|
| Abfrageintervall | Sekunden zwischen zwei Abfragen, Standard 60, erlaubt 30 bis 3600 |

## Geräte und Entitäten

Der Regler erscheint als Gerät „ÖkoFEN Pellematic“, Modell laut Kessel, zum Beispiel COMPACT. Heizkreise, Puffer, Warmwasser und Zirkulation erscheinen als Untergeräte. Die Integration legt nur an, was der Kessel meldet. Kommt später ein Bereich dazu, zum Beispiel ein zweiter Heizkreis, erscheint er ohne Neustart. Ein Untergerät, das der Kessel nicht mehr meldet, kann man in HA löschen.

| Gerät | Entitäten (Standard aktiv) | Zusätzlich, standardmäßig deaktiviert |
|---|---|---|
| Regler und Kessel | Außentemperatur, Kesseltemperatur, Kessel-Soll, Feuerraumtemperatur, Modulation, Brennerphase, Status, Brenner (an/aus), Störung (an/aus), Störungsmeldung. Diagnose: Brennerstarts, Brennerstunden, mittlere Laufzeit | Temperatur und Bewölkung vom Wetterdienst, Feuerraum-Soll, externer Kesselfühler, Saugzuggebläse, Verbrennungsluft, Kesselpumpe |
| Heizkreis | Vorlauf, Vorlauf-Soll, Status, Pumpe | Raumtemperatur und Raum-Soll (nur mit Raumfühler sinnvoll) |
| Puffer | Temperatur oben, Temperatur Mitte, Pufferpumpe (%), Status | Solltemperaturen oben und Mitte |
| Warmwasser | Warmwassertemperatur, Warmwasser-Soll, Status, Pumpe | Warmwassertemperatur unten |
| Zirkulation | Rücklauftemperatur, Pumpe | Freigabetemperatur |

- „Brenner“ und „Brennerphase“ kommen aus der Kesselphase. Der Kessel-Wert `L_br` zeigt den Brenner bei der Pellematic Compact nicht zuverlässig an.
- „Status“ zeigt den Statustext des Kessels in der Sprache, die am Touch eingestellt ist.

## Störungen

Meldet der Kessel eine Störung, passiert dreierlei:
- „Störung“ geht auf an.
- „Störungsmeldung“ zeigt Text und Code. Das Attribut `faults` enthält alle Meldungen mit Datum.
- Unter Einstellungen → Reparaturen erscheint ein Hinweis. Er verschwindet, sobald der Kessel die Störung nicht mehr meldet.

Beispiel-Automation für eine Push-Nachricht aufs Handy:

```yaml
alias: Pelletheizung Störung melden
triggers:
  - trigger: state
    entity_id: binary_sensor.okofen_pellematic_storung
    to: "on"
    for: "00:02:00"
actions:
  - action: notify.mobile_app_mein_handy
    data:
      title: Pelletheizung
      message: "Störung: {{ states('sensor.okofen_pellematic_storungsmeldung') }}"
mode: single
```

Die Entity-IDs hängen von der Sprache ab, in der die Integration eingerichtet wurde, auf Englisch zum Beispiel `binary_sensor.okofen_pellematic_fault`.

## Datenabfrage

Eine Anfrage pro Intervall (`all`). Einheiten, Faktoren und Klartexte (`all??`) holt die Integration beim Start und danach einmal täglich. Ist der Kessel nicht erreichbar, werden die Entitäten „nicht verfügbar“, und sie kommen von selbst zurück, sobald er wieder antwortet.

## Bekannte Einschränkungen

- Nur lesend: keine Betriebsarten, Sollwerte oder Warmwasser-Einmalladung.
- Pelletvorrat und -verbrauch misst der Kessel nicht. `L_storage_*` ist ein fester Einstellwert und wird deshalb nicht angeboten.
- Kein HTTPS: Das JSON-Passwort steht im Klartext in der Anfrage im LAN (Vorgabe von ÖkoFEN).
- Der Kessel wird nicht automatisch gefunden. Host und Port gibst du selbst ein.

## Unterstützte Geräte

- Getestet: Pellematic Compact (PES 212) mit Touch V4.00b.
- Sollte funktionieren: ÖkoFEN-Kessel mit Touch-Bedienung ab Firmware V3.10d. Andere Bereiche (Solar, Wärmepumpe, mehrere Kessel) liefern Grundsensoren und sind ungeprüft.
- Nicht unterstützt: Kessel ohne Touch bzw. ohne JSON-Schnittstelle, das Cloud-Portal my.oekofen.info.

## Fehlersuche

| Problem | Ursache und Lösung |
|---|---|
| „Der Kessel ist nicht erreichbar“ | IP oder Port falsch, oder die JSON-Schnittstelle ist aus. Am Touch prüfen: JSON-Modus „Ein“, Port. Läuft ein `curl http://<IP>:<Port>/<Passwort>/all` im LAN? |
| „Der Kessel hat keine Daten geliefert“ | Falsches JSON-Passwort. Der Kessel liefert dann seine Hilfeseite. |
| „Kessel ausgelastet“ | Ein anderes Programm fragt den Kessel gerade ab. Ein paar Sekunden warten. Den Abstand der anderen Programme nicht unter 30 s setzen. |
| Entitäten zeitweise „nicht verfügbar“ | Kessel neu gestartet oder WLAN-Aussetzer. Die Integration fragt dann seltener ab (bis 10 min) und erholt sich von selbst. |
| Werte fehlen oder sind unplausibel | Diagnose herunterladen (Gerät → ⋮ → Diagnose herunterladen). Zugangsdaten und Namen sind darin geschwärzt. |

Für ausführliche Logs in `configuration.yaml` eintragen:

```yaml
logger:
  logs:
    custom_components.oekofen: debug
```

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
