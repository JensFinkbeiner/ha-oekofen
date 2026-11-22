"""Config flow for ÖkoFEN Pellematic.

Milestone 0.1.0: collects host, port and JSON password. The connection test
(test-before-configure), reauth and reconfigure follow in 0.3.0 together with
the protocol client.
"""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_PORT
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)
import probatio

from .const import DEFAULT_PORT, DOMAIN

STEP_USER_SCHEMA = probatio.Schema(
    {
        probatio.Required(CONF_HOST): TextSelector(),
        probatio.Required(CONF_PORT, default=DEFAULT_PORT): NumberSelector(
            NumberSelectorConfig(min=1, max=65535, mode=NumberSelectorMode.BOX)
        ),
        probatio.Required(CONF_PASSWORD): TextSelector(
            TextSelectorConfig(type=TextSelectorType.PASSWORD)
        ),
    }
)


class OekofenConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for ÖkoFEN Pellematic."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        if user_input is not None:
            host: str = user_input[CONF_HOST].strip()
            port = int(user_input[CONF_PORT])
            self._async_abort_entries_match({CONF_HOST: host, CONF_PORT: port})
            return self.async_create_entry(
                title="ÖkoFEN Pellematic",
                data={
                    CONF_HOST: host,
                    CONF_PORT: port,
                    CONF_PASSWORD: user_input[CONF_PASSWORD],
                },
            )

        return self.async_show_form(step_id="user", data_schema=STEP_USER_SCHEMA)
