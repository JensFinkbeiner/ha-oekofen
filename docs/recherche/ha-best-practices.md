# Home Assistant Custom Integration: Best Practices (Stand 22.11.2026)

Ziel: lokale Polling-Integration für eine ÖkoFEN-Pelletheizung (HTTP/JSON im LAN, lesen und einige Werte schreiben), verteilt über HACS bzw. den neuen Marketplace, mit der Option auf Core.

Stand der Recherche: HA Core **2026.11.2** (aktuell stabil), 2026.12 im Beta-Zyklus.

## 0. Wichtige Änderungen 2026 (vorab)

| Thema | Was gilt jetzt | Quelle |
|---|---|---|
| Doku-Umzug | `developers.home-assistant.io` leitet per 301 auf **contributors.home-assistant.io** um (Core unter `/core/...`, Marketplace unter `/marketplace/...`). | https://contributors.home-assistant.io/core/quality-scale/ |
| **HACS wird Marketplace** | Ab HA **2026.11** steckt HACS als „Marketplace“ in HA (Einstellungen). Eine separate HACS-Installation ist nicht mehr möglich. Katalog bleibt `hacs/default`, `hacs.json` bleibt gleich. Die Erstinstallation einer Config-Flow-Integration braucht keinen Neustart mehr, Updates schon. | https://www.home-assistant.io/blog/2026/11/04/release-202611/ , https://hacs.xyz/docs/marketplace/ , https://contributors.home-assistant.io/marketplace/ |
| Python | Mindestversion ist **3.14** (`homeassistant` 2026.11.2 auf PyPI: `requires_python >=3.14.2`). | https://raw.githubusercontent.com/home-assistant/core/dev/AGENTS.md , https://pypi.org/project/homeassistant/ |
| Test-Paket | Es gibt jetzt das **offizielle `pytest-homeassistant`** (aus dem Core-Repo, Version = HA-Version, z. B. 2026.11.2). `pytest-homeassistant-custom-component` ist laut README **deprecated**. Nicht beide gleichzeitig installieren. | https://pypi.org/project/pytest-homeassistant/ , https://github.com/MatthewFlamm/pytest-homeassistant-custom-component |
| Validierung | Ab 2026.9 läuft die Schema-Validierung mit **probatio** (API-kompatibler Ersatz für voluptuous). `import voluptuous as vol` funktioniert in Custom Integrations weiter (Alias). | https://contributors.home-assistant.io/blog/2026/09/30/probatio-validation-engine/ |
| `DeviceInfo` | Seit 2026.11 eine **Dataclass** statt TypedDict. Zugriff im Dict-Stil ist deprecated. Nicht gesetzte Felder lesen sich als `UNDEFINED`. | https://contributors.home-assistant.io/blog/2026/10/13/device-info-class/ , https://contributors.home-assistant.io/blog/2026/11/19/device-info-mapping/ |
| Rückgabe der Setup-Funktionen | `async_setup_entry`, `async_unload_entry` und `async_migrate_entry` geben in Core `None` zurück, Fehler werden per `ConfigEntry*`-Exception gemeldet. Custom Integrations dürfen weiter `bool` zurückgeben, empfohlen ist aber das neue Muster. | https://contributors.home-assistant.io/blog/2026/10/23/config-entry-methods-return-none/ |
| `step_id` | `async_show_form` und verwandte Methoden brauchen eine explizite `step_id`. Ohne sie bricht der Flow ab **2027.5** ab. | https://contributors.home-assistant.io/blog/2026/10/23/flow-results-require-step-id/ |
| `UpdateFailedUnreachable` | Neu ab **2026.12**: Unterklasse von `UpdateFailed`, die den ersten Ausfall nur auf INFO-Level loggt. | https://contributors.home-assistant.io/blog/2026/11/13/update-failed-unreachable/ |
| Kategorien | Neuer `categories`-Key im Manifest (1 bis 3 Einträge, z. B. `climate.thermostats_heating`). Für Custom Integrations optional, die HACS-Action warnt aber, wenn er fehlt. | https://contributors.home-assistant.io/blog/2026/10/20/integration-categories/ |
| Brand-Bilder | Seit 2026.3 können Custom Integrations einen Ordner `brand/` (icon.png, logo.png, dark_*, @2x) im Integrationsordner mitliefern. Ein PR ins brands-Repo ist dafür nicht mehr nötig. | https://contributors.home-assistant.io/blog/2026/02/24/brands-proxy-api/ |
| Climate/Water Heater | Nur noch die `native_*`-Temperatureigenschaften plus `native_temperature_unit`. Die alten Namen funktionieren ab **2027.11** nicht mehr. | https://contributors.home-assistant.io/blog/2026/10/08/climate-native-temperature/ , https://contributors.home-assistant.io/blog/2026/10/08/water-heater-native-temperature/ |
| Repairs | Issues lassen sich an einen Config Entry binden (`config_entry_id`) und mit `ir.async_refresh_issues` gesammelt aktualisieren (2026.11). | https://contributors.home-assistant.io/blog/2026/10/28/issue-registry-refresh/ |
| pre-commit | Core nutzt jetzt **prek** (in Rust geschrieben, gleiche `.pre-commit-config.yaml`). | https://contributors.home-assistant.io/blog/2026/01/13/replace-pre-commit-with-prek/ |

---

## 1. Integration Quality Scale

Übersicht: https://contributors.home-assistant.io/core/quality-scale/
Alle Regeln: https://contributors.home-assistant.io/core/quality-scale/rules/
Jede Regel hat eine eigene Seite: `https://contributors.home-assistant.io/core/quality-scale/<rule-id>/`

Die Stufe steht im Manifest unter `quality_scale`. Neue Core-Integrationen müssen mindestens Bronze erreichen. Jede Stufe setzt alle darunterliegenden voraus.

### Bronze (20 Regeln)
| Regel | Bedeutung konkret |
|---|---|
| action-setup | Eigene Actions (Services) in `async_setup` registrieren, nicht pro Config Entry. |
| appropriate-polling | Ein sinnvolles `update_interval` wählen, für eine Heizung z. B. 30 bis 60 s statt 1 s. |
| brands | Logo und Icon bereitstellen (Core: brands-Repo, Custom: Ordner `brand/`). |
| common-modules | Den Coordinator in `coordinator.py` und die Basis-Entity in `entity.py` ablegen. |
| config-flow | Einrichtung über die UI (`config_flow: true`), kein YAML. |
| config-flow-test-coverage | Den Config Flow zu 100 % testen, auch die Fehlerpfade und die Erholung nach Fehlern. |
| dependency-transparency | Abhängigkeiten sind Open Source (OSI-Lizenz), liegen auf PyPI und werden aus öffentlicher CI mit getaggten Releases gebaut. |
| docs-actions | Die Actions in der Doku beschreiben. |
| docs-conditions | Integrationseigene Conditions dokumentieren (sonst exempt). |
| docs-high-level-description | Die Doku sagt, was das Gerät ist und wozu die Integration dient. |
| docs-installation-instructions | Eine Schritt-für-Schritt-Einrichtung mit Voraussetzungen (z. B. „JSON-Schnittstelle am Kessel aktivieren“). |
| docs-removal-instructions | Beschreiben, wie man die Integration entfernt. |
| docs-triggers | Integrationseigene Trigger dokumentieren (sonst exempt). |
| entity-event-setup | Event-Abos in `async_added_to_hass` anlegen und beim Entfernen wieder lösen. |
| entity-unique-id | Jede Entity bekommt eine stabile `unique_id`. |
| has-entity-name | `_attr_has_entity_name = True` setzen. Der Name ist relativ zum Gerät. |
| runtime-data | Laufzeitobjekte in `entry.runtime_data` statt in `hass.data` ablegen. |
| test-before-configure | Die Verbindung im Config Flow testen, bevor der Entry angelegt wird. |
| test-before-setup | Die Verbindung beim Setup prüfen und die passende Exception werfen (`ConfigEntryNotReady`, `ConfigEntryAuthFailed`, `ConfigEntryError`). |
| unique-config-entry | Dasselbe Gerät kann nicht zweimal eingerichtet werden (`async_set_unique_id` + `_abort_if_unique_id_configured`). |

### Silber (10 Regeln)
| Regel | Bedeutung konkret |
|---|---|
| action-exceptions | Fehlgeschlagene Actions werfen `ServiceValidationError` (Eingabefehler) oder `HomeAssistantError` (Gerät/Kommunikation). |
| config-entry-unloading | `async_unload_entry` gibt alles sauber frei, sodass ein Reload ohne Neustart möglich ist. |
| docs-configuration-parameters | Jede Option aus dem Options Flow dokumentieren. |
| docs-installation-parameters | Jedes Feld aus dem Setup-Formular dokumentieren. |
| entity-unavailable | Ist das Gerät nicht erreichbar, werden die Entities `unavailable` (der Coordinator macht das automatisch). |
| integration-owner | Mindestens ein Codeowner im Manifest. |
| log-when-unavailable | Den Verbindungsverlust einmal loggen und die Wiederkehr einmal loggen, nicht bei jedem Poll (der Coordinator erledigt das, ab 2026.12 `UpdateFailedUnreachable`). |
| parallel-updates | In jeder Plattformdatei `PARALLEL_UPDATES` explizit setzen (0 für reine Lese-Plattformen mit Coordinator, 1 für schreibende). |
| reauthentication-flow | Neue Zugangsdaten eingeben können, ohne die Integration zu entfernen. Exempt, wenn es keine Authentifizierung gibt. |
| test-coverage | Mehr als 95 % Testabdeckung pro Modul. |

### Gold (21 Regeln)
| Regel | Bedeutung konkret |
|---|---|
| devices | Entities einem Gerät mit vollständiger `DeviceInfo` zuordnen (Hersteller, Modell, Seriennummer, sw/hw-Version). |
| diagnostics | Diagnosedaten zum Download anbieten, sensible Daten mit `async_redact_data` schwärzen. |
| discovery | Geräte automatisch finden (zeroconf/dhcp/ssdp …). Exempt, wenn das Gerät nicht auffindbar ist. |
| discovery-update-info | Neue IP-Adressen aus der Discovery in den bestehenden Entry übernehmen. |
| docs-data-update | Erklären, wie und wie oft Daten abgefragt werden. |
| docs-examples | Automatisierungsbeispiele oder Blueprints anbieten. |
| docs-known-limitations | Bekannte Einschränkungen auflisten. |
| docs-supported-devices | Unterstützte und nicht unterstützte Geräte und Firmware auflisten. |
| docs-supported-functions | Entities und Funktionen beschreiben. |
| docs-troubleshooting | Hilfe zur Selbsthilfe bei typischen Problemen. |
| docs-use-cases | Zeigen, was man mit der Integration anfangen kann. |
| dynamic-devices | Geräte, die nach dem Setup dazukommen (z. B. weitere Heizkreise), ohne Reload hinzufügen. |
| entity-category | `EntityCategory.CONFIG` für Einstellungen und `EntityCategory.DIAGNOSTIC` für Diagnosewerte setzen. |
| entity-device-class | Überall eine Device Class setzen, wo eine passt. |
| entity-disabled-by-default | Selten gebrauchte Entities mit `_attr_entity_registry_enabled_default = False` ausliefern. |
| entity-translations | Entity-Namen über `translation_key` aus den Übersetzungen beziehen. |
| exception-translations | Exceptions für Nutzer mit `translation_domain` und `translation_key` übersetzbar machen. |
| icon-translations | Icons in `icons.json` definieren statt `_attr_icon` zu setzen (auch zustandsabhängig). |
| reconfiguration-flow | `async_step_reconfigure` anbieten, um z. B. Host oder Port ohne Neuanlage zu ändern. |
| repair-issues | Repair Issues für Probleme anlegen, die der Nutzer selbst beheben kann. |
| stale-devices | Verschwundene Geräte entfernen oder per `async_remove_config_entry_device` löschbar machen. |

### Platin (3 Regeln)
| Regel | Bedeutung konkret |
|---|---|
| async-dependency | Die Bibliothek ist asyncio-basiert. |
| inject-websession | Die Bibliothek nimmt HAs Session entgegen (`async_get_clientsession(hass)` für aiohttp oder `get_async_client(hass)` für httpx). |
| strict-typing | Vollständig typisiert, `mypy --strict` läuft durch, die Bibliothek liefert `py.typed` mit. Core: Eintrag in `.strict-typing`. |

### Format von `quality_scale.yaml`
Die Datei liegt im Integrationsordner. Jede Regel hat den Status `done`, `todo` oder `exempt`, und `exempt` braucht einen `comment`. Hassfest prüft, dass jede Regel der angegebenen Stufe `done` oder `exempt` ist. Für einige `done`-Regeln laufen Zusatzchecks.

```yaml
rules:
  # Bronze
  action-setup:
    status: exempt
    comment: Integration registriert keine eigenen Actions.
  appropriate-polling: done
  config-flow: done
  # ...
  # Silver
  reauthentication-flow: todo
  # Gold
  discovery:
    status: exempt
    comment: Der Kessel kündigt sich nicht per mDNS/SSDP/DHCP an.
  # Platinum
  strict-typing: done
```
Vorlagen aus dem Core: https://github.com/home-assistant/core/blob/dev/homeassistant/components/peblar/quality_scale.yaml und https://github.com/home-assistant/core/blob/dev/homeassistant/components/airgradient/quality_scale.yaml

---

## 2. Projektstruktur

Dateistruktur: https://contributors.home-assistant.io/core/integrations/file-structure/
Marketplace-Anforderungen: https://contributors.home-assistant.io/marketplace/guides/integrations/

```
repo-root/
├── hacs.json
├── README.md
├── LICENSE
├── pyproject.toml                # ruff, mypy, pytest-Konfiguration
├── .pre-commit-config.yaml       # mit prek oder pre-commit nutzbar
├── .github/workflows/{validate.yaml,hassfest.yaml,tests.yaml}
├── .devcontainer/
├── custom_components/oekofen/    # genau EIN Unterordner
│   ├── __init__.py               # async_setup_entry / async_unload_entry
│   ├── manifest.json
│   ├── const.py                  # DOMAIN, Defaults
│   ├── config_flow.py            # user, reauth, reconfigure, (zeroconf/dhcp), Options Flow
│   ├── coordinator.py            # DataUpdateCoordinator
│   ├── entity.py                 # Basis-Entity (DeviceInfo, has_entity_name)
│   ├── sensor.py, binary_sensor.py, number.py, select.py, switch.py, water_heater.py, climate.py
│   ├── diagnostics.py
│   ├── repairs.py                # nur bei Repair-Flows nötig
│   ├── icons.json
│   ├── services.yaml             # nur bei eigenen Actions
│   ├── strings.json              # optional für Custom Integrations, siehe unten
│   ├── translations/en.json, translations/de.json
│   ├── quality_scale.yaml        # optional für Custom Integrations, als Fahrplan zu empfehlen
│   └── brand/icon.png, logo.png (+ dark_*, @2x)
└── tests/
    ├── conftest.py, fixtures/*.json, snapshots/*.ambr
    └── test_config_flow.py, test_init.py, test_sensor.py, test_diagnostics.py ...
```

### manifest.json
```json
{
  "domain": "oekofen",
  "name": "ÖkoFEN Pellematic",
  "codeowners": ["@githubuser"],
  "config_flow": true,
  "documentation": "https://github.com/<user>/ha-oekofen",
  "issue_tracker": "https://github.com/<user>/ha-oekofen/issues",
  "integration_type": "device",
  "iot_class": "local_polling",
  "categories": ["climate.thermostats_heating"],
  "loggers": ["pyoekofen"],
  "requirements": ["pyoekofen==0.1.0"],
  "version": "0.1.0"
}
```
- **Pflicht für Marketplace/HACS:** `domain`, `name`, `codeowners`, `documentation`, `issue_tracker`, `version`. Fehlt `version`, verweigert der Marketplace die Installation, und die Version sollte zum Release-Tag passen. Quelle: https://hacs.xyz/docs/publish/integration , https://contributors.home-assistant.io/marketplace/guides/integrations/
- **Core:** ohne `version`, dafür mit `quality_scale` und exakt gepinnten Requirements (`==`).
- `integration_type`: **`device`**, wenn ein Config Entry für einen Kessel steht. `hub` passt, wenn ein Gateway mehrere Geräte bedient. Bei ÖkoFEN ist `device` naheliegend; Heizkreise, Warmwasser und Puffer lassen sich als (Child-)Geräte unter dem Kessel abbilden (Child Devices gibt es ab 2026.11: https://contributors.home-assistant.io/blog/2026/10/22/child-devices/).
- `iot_class`: `local_polling`.
- `loggers`: Logger-Namen der Bibliothek, damit Debug-Logging aus der UI greift.
- `requirements`: nur Pakete, die HA nicht selbst mitbringt. aiohttp ist schon dabei.
- Der Domain-Name darf nicht mit einer Core-Domain kollidieren (`oekofen` ist im Core frei, geprüft am 22.11.2026).

### hacs.json
Referenz: https://contributors.home-assistant.io/marketplace/reference/hacs-json/ , https://hacs.xyz/docs/publish/start
```json
{
  "name": "ÖkoFEN Pellematic",
  "homeassistant": "2026.11.0",
  "country": ["DE", "AT"]
}
```
Optional sind `zip_release` + `filename`, `hide_default_branch`, `persistent_directory` und `content_in_root`. Releases sollten echte GitHub-Releases sein, ein Tag allein genügt nicht.

**Achtung ZIP-Releases:** Ein Forenthread meldet für 2026.11 einen Fehler „missing the hacs.json“ bei ZIP-Assets ohne `hacs.json` auf oberster Ebene. Ohne ZIP-Release (Installation aus dem Quellcode) ist man auf der sicheren Seite. https://community.home-assistant.io/t/is-marketplace-update-is-missing-the-hacs-json-file-required-for-installation/1034550

Weitere Repo-Anforderungen: öffentliches Repo, Description, Topics, README, aktivierte Issues.

### Übersetzungen: strings.json, translations/en.json, translations/de.json
- **Core:** Quelle ist `strings.json` (Englisch). `translations/en.json` wird generiert, die anderen Sprachen kommen über Lokalise.
- **Custom/Marketplace:** „Custom integrations do not use `strings.json`“. Man liefert fertige Dateien in `translations/`, mindestens eine vollständige `en.json`, dazu selbst gepflegt `de.json`. Praxis-Tipp: `strings.json` trotzdem als Quelle pflegen und per Skript nach `translations/en.json` kopieren. Dann ist ein späterer Core-PR trivial.
- Sektionen: `config` (step/error/abort), `options`, `entity.<platform>.<translation_key>.name` und `.state` (für Enum- und Select-Zustände), `exceptions`, `issues`, `services`. Gemeinsame Texte per Referenz wie `[%key:common::config_flow::error::cannot_connect%]`; Abort-Gründe werden seit 2026.9 zentral übersetzt (https://contributors.home-assistant.io/blog/2026/09/28/central-config-flow-abort-reasons/).

### icons.json
```json
{ "entity": { "sensor": { "pellet_stock": { "default": "mdi:grain" } },
              "select": { "heating_mode": { "default": "mdi:radiator", "state": { "off": "mdi:radiator-off" } } } } }
```

### Entity-Grundmuster (entity.py)
```python
class OekofenEntity(CoordinatorEntity[OekofenCoordinator]):
    _attr_has_entity_name = True

    def __init__(
        self, coordinator: OekofenCoordinator, description: EntityDescription
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        serial = coordinator.data.serial
        self._attr_unique_id = f"{serial}_{description.key}"
        self._attr_device_info = DeviceInfo(  # Dataclass seit 2026.11
            identifiers={(DOMAIN, serial)},
            manufacturer="ÖkoFEN",
            model=coordinator.data.model,
            serial_number=serial,
            sw_version=coordinator.data.firmware,
            configuration_url=f"http://{coordinator.config_entry.data[CONF_HOST]}",
        )
```
- Namen über `translation_key` in der EntityDescription, dazu `_attr_name = None` nur für die Hauptentity (sie heißt dann wie das Gerät).
- `unique_id`: stabil, aus Seriennummer bzw. MAC plus Key ableiten, **nie** aus der IP. Fehlt eine Seriennummer, `entry.entry_id` als Fallback nehmen.
- `EntityCategory.DIAGNOSTIC` für Firmware, Fehlercodes und Laufzeiten; `EntityCategory.CONFIG` für Number-, Select- und Switch-Einstellungen, die nicht zum Hauptbetrieb gehören.
- `async_entity_id_changed` und `async_prepare_to_add_to_hass` sind neue Lifecycle-Hooks, nur bei Bedarf (https://contributors.home-assistant.io/blog/2026/10/12/new-entity-lifecycle-hooks/).

### runtime_data und typisierter ConfigEntry
https://contributors.home-assistant.io/core/quality-scale/runtime-data/
```python
type OekofenConfigEntry = ConfigEntry[OekofenCoordinator]


async def async_setup_entry(hass: HomeAssistant, entry: OekofenConfigEntry) -> None:
    client = OekofenClient(
        entry.data[CONF_HOST],
        entry.data[CONF_PORT],
        entry.data[CONF_PASSWORD],
        session=async_get_clientsession(hass),
    )
    coordinator = OekofenCoordinator(hass, entry, client)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)


async def async_unload_entry(hass: HomeAssistant, entry: OekofenConfigEntry) -> None:
    await hass.config_entries.async_unload_platforms_or_raise(entry, PLATFORMS)
```
Eigene `ConfigEntryNotReady`-, `ConfigEntryAuthFailed`- und `ConfigEntryError`-Exceptions mit `translation_key` werfen statt `False` zurückzugeben.

### DataUpdateCoordinator
https://contributors.home-assistant.io/core/integrations/fetching-data/
```python
class OekofenCoordinator(DataUpdateCoordinator[OekofenData]):
    config_entry: OekofenConfigEntry

    def __init__(self, hass, entry, client) -> None:
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=timedelta(seconds=30),
            always_update=False,
        )
        self.client = client

    async def _async_setup(self) -> None:  # einmalig beim ersten Refresh
        self.device = await self.client.get_device_info()

    async def _async_update_data(self) -> OekofenData:
        try:
            return await self.client.get_data()
        except OekofenAuthError as err:
            raise ConfigEntryAuthFailed(
                translation_domain=DOMAIN, translation_key="invalid_auth"
            ) from err
        except OekofenConnectionError as err:
            raise UpdateFailed(
                translation_domain=DOMAIN, translation_key="cannot_connect"
            ) from err
            # ab 2026.12: UpdateFailedUnreachable
```
- `config_entry=` immer übergeben (Pflicht im Core).
- `always_update=False` nur, wenn die Daten mit `==` vergleichbar sind (z. B. eine Dataclass). Dann gibt es keine unnötigen State-Writes.
- `UpdateFailed(retry_after=...)` hilft, wenn der Kessel ein Abfragelimit hat.
- Nach einem Schreibbefehl `await coordinator.async_request_refresh()` aufrufen (debounced).
- `PARALLEL_UPDATES = 0` für sensor und binary_sensor, `1` für number, select, switch, water_heater und climate, damit Schreibbefehle seriell laufen.

### Config Flow: user, reauth, reconfigure, Discovery, Options
- **user:** Host, Port, Passwort abfragen, verbinden, `await self.async_set_unique_id(serial)`, `self._abort_if_unique_id_configured()`, `async_create_entry`. Fehler-Keys: `cannot_connect`, `invalid_auth`, `unknown`.
- **reauth** (https://contributors.home-assistant.io/core/quality-scale/reauthentication-flow/): `async_step_reauth` leitet an `async_step_reauth_confirm` weiter, danach folgen `self._get_reauth_entry()`, `_abort_if_unique_id_mismatch(reason="wrong_device")` und `async_update_reload_and_abort(entry, data_updates=...)`. Der ÖkoFEN-JSON-Zugang ist meines Wissens passwortgeschützt (noch zu verifizieren), damit ist reauth relevant.
- **reconfigure** (https://contributors.home-assistant.io/core/quality-scale/reconfiguration-flow/): `async_step_reconfigure` mit `_get_reconfigure_entry()`, `_abort_if_unique_id_mismatch` und `async_update_reload_and_abort`. Das Formular mit `add_suggested_values_to_schema` vorbelegen.
- **Discovery** (https://contributors.home-assistant.io/core/quality-scale/discovery/): Den Manifest-Key (`zeroconf`, `dhcp` mit `macaddress`/`hostname`, `ssdp`) setzen und `async_step_dhcp`/`async_step_zeroconf` implementieren. Bei DHCP über einen MAC-OUI-Treffer bei bekannter unique_id die IP aktualisieren (`_abort_if_unique_id_configured(updates={CONF_HOST: ip})`, Regel discovery-update-info). Kündigt sich der Kessel nicht an, die Regel als `exempt` mit Begründung führen.
- **Options Flow** (https://contributors.home-assistant.io/core/integrations/options-flow/): von `OptionsFlowWithReload` erben (Reload automatisch, nicht mit einem Update-Listener kombinieren), `self.config_entry` erst in den Steps nutzen. Sinnvoll z. B. für das Polling-Intervall. Für Core gilt allerdings: das Intervall soll nicht konfigurierbar sein (Regel appropriate-polling). Daher Options sparsam einsetzen.
- In jedem `async_show_form` eine **`step_id`** angeben (Pflicht ab 2027.5).
- Formularfelder, die von anderen Feldern abhängen, sind neu möglich (https://contributors.home-assistant.io/blog/2026/10/21/form-fields-visible/).

### diagnostics.py
```python
TO_REDACT = {CONF_PASSWORD, "serial", "mac"}


async def async_get_config_entry_diagnostics(
    hass, entry: OekofenConfigEntry
) -> dict[str, Any]:
    return {
        "entry": async_redact_data(entry.as_dict(), TO_REDACT),
        "data": async_redact_data(asdict(entry.runtime_data.data), TO_REDACT),
    }
```
Das Ergebnis per Syrupy-Snapshot testen.

### Repairs
Repairs nur einsetzen, wenn der Nutzer etwas selbst beheben kann, z. B. „JSON-Schnittstelle deaktiviert“ oder „Firmware zu alt“: `ir.async_create_issue(hass, DOMAIN, f"{entry.entry_id}_json_disabled", config_entry_id=entry.entry_id, is_fixable=False, severity=..., translation_key=...)`. Eine `repairs.py` braucht es nur für behebbare Issues mit Flow.

---

## 3. Bibliothek auf PyPI oder Code im Integrationsordner?

| | Core | HACS/Marketplace |
|---|---|---|
| Protokollcode | **Muss** in einer externen PyPI-Bibliothek liegen. Laut Development Checklist muss jede Kommunikation mit Geräten in einer externen Python-Bibliothek gekapselt sein, und das Code-Review verlangt API-spezifischen Code in einer Drittbibliothek. | Code im Integrationsordner (z. B. `api.py`) ist erlaubt und üblich. |
| Abhängigkeiten | OSI-Lizenz, PyPI, Build aus öffentlicher CI, getaggte Releases, Pin mit `==` (Regel dependency-transparency). | Beliebige PyPI-Pakete in `requirements`; keine Pakete aufnehmen, die HA schon mitbringt. |
| Platin | Async (asyncio), Session-Injection, `py.typed`. | Nicht gefordert. |

Quellen: https://developers.home-assistant.io/docs/development_checklist , https://developers.home-assistant.io/docs/creating_component_code_review , https://developers.home-assistant.io/docs/api_lib_index , https://contributors.home-assistant.io/core/quality-scale/dependency-transparency/ , https://contributors.home-assistant.io/core/quality-scale/inject-websession/

**Empfehlung:** Die Bibliothek von Anfang an getrennt halten (z. B. `pyoekofen`: eigenes Repo, `src/`-Layout, `py.typed`, async mit aiohttp, `session: aiohttp.ClientSession | None = None` im Konstruktor, typisierte Dataclasses statt roher Dicts, eigene Exception-Hierarchie `OekofenError` → `OekofenConnectionError` und `OekofenAuthError`, Publish über GitHub Actions mit PyPI Trusted Publishing). Die Integration enthält dann nur HA-Logik, ein späterer Core-PR braucht keinen Umbau, und Tests mocken die Client-Klasse statt HTTP.
Für den Anfang kann man die Bibliothek auch als lokales Paket im Repo entwickeln und erst vor dem ersten Release auf PyPI veröffentlichen.

---

## 4. Tooling

| Werkzeug | Empfehlung | Quelle |
|---|---|---|
| Python | **3.14** (HA 2026.11 setzt `>=3.14.2` voraus). | https://pypi.org/project/homeassistant/ |
| Paketmanager | `uv` (Core nutzt es, das Blueprint auch). | https://github.com/jpawlowski/hacs.integration_blueprint |
| Tests | **`pytest-homeassistant`** (offiziell, Version = HA-Version, Fixtures `hass`, `MockConfigEntry` aus `pytest_homeassistant.common`; Custom Integrations sind im `hass`-Fixture standardmäßig aktiviert). Die alte Variante `pytest-homeassistant-custom-component` (Fixture `enable_custom_integrations`) ist deprecated. | https://pypi.org/project/pytest-homeassistant/ |
| pytest-Konfiguration | `asyncio_mode = "auto"`, `asyncio_default_fixture_loop_scope = "function"`, `addopts = "-p no:respx"`, `testpaths = ["tests"]`. | ebd. |
| Snapshots | **syrupy** `.ambr` für Entity-States, Diagnostics und Device-Registry; `pytest --snapshot-update`. Typisch: `await snapshot_platform(hass, entity_registry, snapshot, entry.entry_id)` (Helper aus den Core-Tests, in `pytest_homeassistant.components.common` bzw. `pytest_homeassistant.common` nachsehen). | https://contributors.home-assistant.io/core/development/testing/ |
| Coverage | `pytest-cov`, Config Flow 100 %, sonst über 95 %. | https://contributors.home-assistant.io/core/quality-scale/test-coverage/ |
| Lint/Format | **Ruff** (lint + format); die `pyproject.toml` vom Core als Vorlage nehmen. | https://github.com/home-assistant/core/blob/dev/pyproject.toml |
| Typen | **mypy** mit `strict = true`, mypy-Konfiguration an Core anlehnen. Das Blueprint nutzt alternativ Pyright. Die Bibliothek braucht `py.typed`. | https://contributors.home-assistant.io/core/quality-scale/strict-typing/ |
| Git-Hooks | `.pre-commit-config.yaml` (ruff, ruff-format, mypy, codespell, yamllint, prettier), ausgeführt mit **prek** oder pre-commit. | https://contributors.home-assistant.io/blog/2026/01/13/replace-pre-commit-with-prek/ |
| CI | (1) `hacs/action` mit `category: integration`, (2) `home-assistant/actions/hassfest@master`, (3) Tests, Ruff und mypy mit Python 3.14; beide Validierungen sind Pflicht für den Katalog. Actions pinnen und Dependabot nutzen. | https://contributors.home-assistant.io/marketplace/reference/validation/ |
| Releases | GitHub Releases mit Tag gleich `manifest.version`, z. B. per Release Please; gegen die HA-Beta testen. | https://contributors.home-assistant.io/marketplace/guides/releases/ |

### CI-Workflows (Minimal)
```yaml
# .github/workflows/validate.yaml
name: Validate
on: { push: {}, pull_request: {}, schedule: [{cron: "0 0 * * *"}], workflow_dispatch: {} }
permissions: {}
jobs:
  hacs:
    runs-on: ubuntu-latest
    steps:
      - uses: hacs/action@main
        with: { category: integration }
  hassfest:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: home-assistant/actions/hassfest@master
```

### Entwicklungsumgebung unter Windows (Docker/Rancher Desktop)
- **Devcontainer** (VS Code „Dev Containers“): das Blueprint https://github.com/jpawlowski/hacs.integration_blueprint als Vorlage nehmen (Python 3.14, uv, Ruff, prek, HA 2026.11+). Unter Windows **„Clone Repository in Named Container Volume“** wählen, damit die Dateien im WSL2-Dateisystem liegen; Bind-Mounts von `C:\` sind deutlich langsamer. Benötigt laut README mindestens 8 GB RAM.
- **Rancher Desktop:** Container-Engine auf **dockerd (moby)** stellen, nicht containerd/nerdctl. Nur dann funktionieren Dev Containers und `docker compose` wie mit Docker Desktop (WSL2-Backend).
- **Lokale HA-Testinstanz** (ergänzend zu pytest):
  ```yaml
  # docker-compose.yml
  services:
    homeassistant:
      image: ghcr.io/home-assistant/home-assistant:2026.11
      volumes:
        - ./config:/config
        - ./custom_components/oekofen:/config/custom_components/oekofen
      ports: ["8123:8123"]
  ```
  In `config/configuration.yaml` `logger: default: info, logs: custom_components.oekofen: debug` setzen. Für die Arbeit ohne echten Kessel lohnt ein kleiner Mock-Server (z. B. aiohttp oder FastAPI im Container), der aufgezeichnete JSON-Antworten des Kessels ausliefert. Diese Fixtures dienen dann auch als Testdaten.
- Alternativ `hass -c config` direkt im Devcontainer starten; das Blueprint enthält dafür ein Skript.

---

## 5. Plattformen für eine Pelletheizung

Entity-Doku: https://contributors.home-assistant.io/core/entities/sensor/ , https://contributors.home-assistant.io/core/entities/water-heater/ , https://contributors.home-assistant.io/core/entities/climate/

| Plattform | Einsatz bei ÖkoFEN | Hinweise |
|---|---|---|
| **sensor** | Kessel-, Vorlauf-, Rücklauf-, Außen-, Puffer- und Warmwassertemperatur (`temperature`, `measurement`, °C); Leistung bzw. Modulation (`power` in kW oder `%` ohne Device Class); Brennerstarts und Laufzeit (`duration`, `total_increasing`); Pelletverbrauch (`weight`, kg, `total_increasing`); Pelletvorrat/Lager (`weight`, `measurement`); Betriebszustand und Fehlercode (`enum` mit `options` und übersetzten States, `DIAGNOSTIC`). | `native_unit_of_measurement` mit HA-Konstanten (`UnitOfTemperature.CELSIUS`, `UnitOfMass.KILOGRAMS`, `UnitOfEnergy.KILO_WATT_HOUR`); `suggested_display_precision` setzen. Enum-Sensoren bekommen keine Unit und keine State Class. |
| **binary_sensor** | Brenner an/aus (`running`), Pumpen (`running`), Störung (`problem`), Saugzug, Ascheaustragung, Reinigung. | Wenig genutzte Sensoren disabled by default ausliefern. |
| **number** | Sollwerte: Warmwasser-Soll, Heizkurve/Steilheit, Raum-Soll Komfort/Absenk, Heizgrenze. | `NumberDeviceClass.TEMPERATURE`, `native_min_value`/`native_max_value`/`native_step`, `mode=NumberMode.BOX` oder `SLIDER`; Einstellparameter mit `EntityCategory.CONFIG`. |
| **select** | Betriebsart je Heizkreis bzw. Warmwasser (Aus/Auto/Tag/Nacht/Party/Urlaub), Kesselmodus. | Optionen übersetzen (`entity.select.<key>.state.*`); passt besser als `climate`, wenn die Modi gerätespezifisch sind. |
| **switch** | Echte Ein/Aus-Funktionen, z. B. „Warmwasser einmal laden“ oder Kessel aus. | Einmalaktionen sind besser ein **button**. |
| **water_heater** | Warmwasserspeicher: aktuelle Temperatur, Soll, Modi (`STATE_ECO`, `STATE_PERFORMANCE`, `STATE_OFF` oder eigene). | Für Geräte, die **Wasser** erhitzen. `native_temperature_unit` ist Pflicht, `WaterHeaterEntityFeature.TARGET_TEMPERATURE | OPERATION_MODE`. Gute UI- und Sprachassistent-Integration. |
| **climate** | Heizkreis mit **Raumfühler** und Raum-Solltemperatur: `HVACMode.HEAT/AUTO/OFF`, `HVACAction.HEATING/IDLE/PREHEATING`, Presets `comfort/eco/away`. | Nur sinnvoll, wenn der Heizkreis eine Raumtemperatur regelt. Ein reiner Vorlauf-Heizkreis nach Außentemperatur ist kein echtes Thermostat; dafür passen `select` (Modus) und `number` (Kurve) besser. Für Core gilt: keine doppelte Steuerung, also nicht dieselbe Größe gleichzeitig als climate- und als number-Entity. |
| **button** (optional) | „Warmwasser jetzt laden“, „Störung quittieren“. | |
| **update** (optional) | Nur, wenn sich die Firmware-Version mit verfügbaren Updates vergleichen lässt. | |

### Energy-Dashboard-Tauglichkeit
- Das Energy-Dashboard akzeptiert nur Sensoren mit `state_class` `total` oder `total_increasing` und passender Device Class bzw. Einheit: Strom als `energy` (Wh/kWh), Gas als `energy` (kWh) oder `gas` (m³), Wasser als `water`/`volume`. Quellen: https://www.home-assistant.io/integrations/sensor , https://community.home-assistant.io/t/wth-does-the-energy-dashboard-only-allow-m-gas-for-conventional-heating/470573
- **Pellets in kg (`weight`) kann man nicht direkt eintragen.** Das ist keine Doku-Aussage, sondern meine Ableitung aus den zulässigen Kategorien. Lösungsoptionen:
  1. Liefert der Kessel Wärmemenge oder Energie (kWh), diese als `energy` + `total_increasing` anbieten. Sie lässt sich dann z. B. als „Gas“ (kWh) oder als Einzelgerät verbuchen.
  2. Optional einen berechneten Sensor „Pellet-Energie“ anbieten (kg × Heizwert ≈ 4,8 bis 5,0 kWh/kg), Heizwert über den Options Flow einstellbar. Für Core ist ein solcher abgeleiteter Wert eher kritisch (Core bevorzugt Rohwerte); für HACS ist er in Ordnung, sauber dokumentiert.
  3. Den Strombedarf des Kessels (falls gemeldet) als `power` (W) mit `measurement` ausweisen und als „Einzelgerät“ nutzen.
- Langzeitstatistiken entstehen automatisch für jeden Sensor mit `state_class`. Daher `measurement` für Temperaturen und Leistung setzen, `total_increasing` für Zähler wie Verbrauch, Starts und Betriebsstunden (dabei eine nicht monotone Firmware beachten).

---

## 6. Referenz-Integrationen im Core

Alle Angaben geprüft im `dev`-Branch am 22.11.2026. Laut Core-AGENTS.md sind Gold- und Platin-Integrationen die empfohlenen Vorbilder.

| Integration | Stufe | Warum als Vorbild | Link |
|---|---|---|---|
| **Peblar** (Wallbox) | Platin, `local_polling`, `device`, Kategorie energy | Sehr sauberes lokales HTTP-Polling mit sensor, binary_sensor, number, select, switch, button und update; diagnostics, reauth, reconfigure, Snapshot-Tests; Lib `peblar` (Frenck-Stil). Am nächsten am eigenen Vorhaben. | https://github.com/home-assistant/core/tree/dev/homeassistant/components/peblar |
| **AirGradient** | Platin, `local_polling`, `device` | Kompakt, zeroconf-Discovery inklusive discovery-update-info, number, select, switch und update; gutes `quality_scale.yaml` mit exempt-Begründungen. | https://github.com/home-assistant/core/tree/dev/homeassistant/components/airgradient |
| **HomeWizard** | Platin, `local_polling` | Energiezähler: vorbildliche `device_class`/`state_class` für das Energy-Dashboard, Discovery, reauth (lokaler Token), mehrere API-Versionen. | https://github.com/home-assistant/core/tree/dev/homeassistant/components/homewizard |
| **Elgato** | Platin, `local_polling` | Klassisches Lehrbeispiel (Frenck) für Coordinator, Entity-Basisklasse, Tests und Lib-Design (`elgato`, async, Session-Injection). | https://github.com/home-assistant/core/tree/dev/homeassistant/components/elgato |
| *BSB-LAN* (fachlich) | Silber, `local_polling` | Heizungsregler mit **climate + water_heater + number + sensor**. Als fachliches Vorbild für das Heizungs-Mapping nützlich, technisch aber unter Gold. | https://github.com/home-assistant/core/tree/dev/homeassistant/components/bsblan |

Weitere Heizungsintegrationen zum Vergleich: `palazzetti` (Pelletofen, Silber), `ecoforest` (Pelletofen), `stiebel_eltron` (Silber), `nibe_heatpump`.

---

## Kurzfazit für das ÖkoFEN-Projekt
1. Repo-Layout nach dem Blueprint (Python 3.14, uv, Ruff, mypy strict, prek, `pytest-homeassistant`, syrupy).
2. Getrennte async-Bibliothek `pyoekofen` (aiohttp, Session-Injection, `py.typed`) von Anfang an.
3. `integration_type: device`, `iot_class: local_polling`, `categories: ["climate.thermostats_heating"]`, `version` im Manifest, `brand/` im Integrationsordner.
4. Bronze und Silber vollständig umsetzen und `quality_scale.yaml` als Checkliste pflegen; Gold-Regeln (devices, diagnostics, translations, icons, reconfigure, entity categories) direkt mitbauen.
5. Plattformen: sensor, binary_sensor, number, select, water_heater (Warmwasser), climate nur für Heizkreise mit Raumfühler.
6. Neue APIs nutzen: `DeviceInfo` als Dataclass, `step_id` in jedem Formular, `ConfigEntry*`-Exceptions mit Übersetzung, `UpdateFailedUnreachable` ab 2026.12 (für 2026.11-Kompatibilität mit Fallback importieren).
