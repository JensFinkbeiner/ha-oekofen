"""Config flow for ÖkoFEN Pellematic: setup, reauth, reconfigure and options."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from homeassistant.config_entries import (
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlowWithReload,
)
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_PORT, CONF_SCAN_INTERVAL
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)
import probatio

from .api import (
    OekofenAuthError,
    OekofenBusyError,
    OekofenClient,
    OekofenConnectionError,
    OekofenError,
)
from .const import (
    CONF_CALIBRATION,
    CONF_EFFICIENCY,
    CONF_HEATING_VALUE,
    CONF_NOMINAL_KW,
    DEFAULT_CALIBRATION,
    DEFAULT_EFFICIENCY,
    DEFAULT_HEATING_VALUE,
    DEFAULT_NOMINAL_KW,
    DEFAULT_PORT,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_TITLE,
    DOMAIN,
    LOGGER,
    MAX_SCAN_INTERVAL,
    MIN_SCAN_INTERVAL,
)
from .coordinator import OekofenConfigEntry

PASSWORD_SELECTOR = TextSelector(TextSelectorConfig(type=TextSelectorType.PASSWORD))
PORT_SELECTOR = NumberSelector(
    NumberSelectorConfig(min=1, max=65535, mode=NumberSelectorMode.BOX)
)

STEP_USER_SCHEMA = probatio.Schema(
    {
        probatio.Required(CONF_HOST): TextSelector(),
        probatio.Required(CONF_PORT, default=DEFAULT_PORT): PORT_SELECTOR,
        probatio.Required(CONF_PASSWORD): PASSWORD_SELECTOR,
    }
)
STEP_REAUTH_SCHEMA = probatio.Schema(
    {probatio.Required(CONF_PASSWORD): PASSWORD_SELECTOR}
)
STEP_RECONFIGURE_SCHEMA = probatio.Schema(
    {
        probatio.Required(CONF_HOST): TextSelector(),
        probatio.Required(CONF_PORT): PORT_SELECTOR,
    }
)


async def _async_test_connection(
    hass: HomeAssistant, host: str, port: int, password: str
) -> str | None:
    """Read the boiler once. Return an error key, or None on success."""
    client = OekofenClient(host, port, password, async_get_clientsession(hass))
    try:
        data = await client.async_get_data(refresh_metadata=True)
    except OekofenAuthError:
        return "invalid_auth"
    except OekofenBusyError:
        return "busy"
    except OekofenConnectionError:
        return "cannot_connect"
    except OekofenError:
        return "invalid_answer"
    except Exception:
        LOGGER.exception("Unexpected error while testing the connection")
        return "unknown"
    if not data.numbered_sections("pe"):
        return "no_boiler"
    return None


class OekofenConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for ÖkoFEN Pellematic."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: OekofenConfigEntry) -> OekofenOptionsFlow:
        """Return the options flow."""
        return OekofenOptionsFlow()

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Ask for host, port and JSON password."""
        errors: dict[str, str] = {}
        if user_input is not None:
            host = str(user_input[CONF_HOST]).strip()
            port = int(user_input[CONF_PORT])
            # The boiler reports no serial number or MAC, so match on the address.
            self._async_abort_entries_match({CONF_HOST: host, CONF_PORT: port})
            password = user_input[CONF_PASSWORD]
            error = await _async_test_connection(self.hass, host, port, password)
            if error is None:
                return self.async_create_entry(
                    title=DEFAULT_TITLE,
                    data={CONF_HOST: host, CONF_PORT: port, CONF_PASSWORD: password},
                )
            errors["base"] = error
        return self.async_show_form(
            step_id="user",
            # Never send the entered password back to the browser.
            data_schema=self.add_suggested_values_to_schema(
                STEP_USER_SCHEMA,
                {k: v for k, v in (user_input or {}).items() if k != CONF_PASSWORD},
            ),
            errors=errors,
        )

    async def async_step_reauth(
        self, entry_data: Mapping[str, Any]
    ) -> ConfigFlowResult:
        """Start reauthentication after the boiler rejected the password."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Ask for the new JSON password."""
        entry = self._get_reauth_entry()
        errors: dict[str, str] = {}
        if user_input is not None:
            error = await _async_test_connection(
                self.hass,
                entry.data[CONF_HOST],
                entry.data[CONF_PORT],
                user_input[CONF_PASSWORD],
            )
            if error is None:
                return self.async_update_reload_and_abort(
                    entry, data_updates={CONF_PASSWORD: user_input[CONF_PASSWORD]}
                )
            errors["base"] = error
        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=STEP_REAUTH_SCHEMA,
            errors=errors,
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Change host or port of an existing entry."""
        entry = self._get_reconfigure_entry()
        errors: dict[str, str] = {}
        if user_input is not None:
            host = str(user_input[CONF_HOST]).strip()
            port = int(user_input[CONF_PORT])
            self._async_abort_entries_match({CONF_HOST: host, CONF_PORT: port})
            error = await _async_test_connection(
                self.hass, host, port, entry.data[CONF_PASSWORD]
            )
            if error is None:
                return self.async_update_reload_and_abort(
                    entry, data_updates={CONF_HOST: host, CONF_PORT: port}
                )
            errors["base"] = error
        return self.async_show_form(
            step_id="reconfigure",
            data_schema=self.add_suggested_values_to_schema(
                STEP_RECONFIGURE_SCHEMA, user_input or entry.data
            ),
            errors=errors,
        )


class OekofenOptionsFlow(OptionsFlowWithReload):
    """Options: polling interval."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Show the options."""
        if user_input is not None:
            return self.async_create_entry(
                data={
                    CONF_SCAN_INTERVAL: int(user_input[CONF_SCAN_INTERVAL]),
                    CONF_NOMINAL_KW: float(user_input[CONF_NOMINAL_KW]),
                    CONF_EFFICIENCY: float(user_input[CONF_EFFICIENCY]),
                    CONF_HEATING_VALUE: float(user_input[CONF_HEATING_VALUE]),
                    CONF_CALIBRATION: float(user_input[CONF_CALIBRATION]),
                }
            )
        options = self.config_entry.options
        fields = (
            (
                CONF_SCAN_INTERVAL,
                DEFAULT_SCAN_INTERVAL,
                MIN_SCAN_INTERVAL,
                MAX_SCAN_INTERVAL,
                1,
                "s",
            ),
            (CONF_NOMINAL_KW, DEFAULT_NOMINAL_KW, 2, 100, 0.1, "kW"),
            (CONF_EFFICIENCY, DEFAULT_EFFICIENCY, 50, 100, 0.1, "%"),
            (CONF_HEATING_VALUE, DEFAULT_HEATING_VALUE, 3.5, 5.5, 0.01, "kWh/kg"),
            (CONF_CALIBRATION, DEFAULT_CALIBRATION, 0.5, 2.0, 0.01, ""),
        )
        schema = probatio.Schema(
            {
                probatio.Required(
                    key, default=options.get(key, default)
                ): NumberSelector(
                    NumberSelectorConfig(
                        min=low,
                        max=high,
                        step=step,
                        mode=NumberSelectorMode.BOX,
                        **({"unit_of_measurement": unit} if unit else {}),
                    )
                )
                for key, default, low, high, step, unit in fields
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
