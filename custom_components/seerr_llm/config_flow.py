"""Config flow for Seerr LLM Tools integration."""
from __future__ import annotations

from typing import Any

import aiohttp
import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_BASE
from homeassistant.helpers import aiohttp_client

from .const import (
    CONF_DEF_TMDB_API_KEY,
    CONF_SEERR_API_KEY,
    CONF_SEERR_URL,
    CONF_TMDB_API_KEY,
    DOMAIN,
)

STEP_USER_DATA_SCHEMA: vol.Schema = vol.Schema(
    {
        vol.Required(
            CONF_SEERR_URL,
            description={"suggested_value": "http://localhost:5055"},
        ): str,
        vol.Required(
            CONF_SEERR_API_KEY,
            description={"suggested_value": ""},
        ): str,
    },
)


async def _validate_seerr_connection(
    session: aiohttp.ClientSession,
    seerr_url: str,
    seerr_api_key: str,
) -> None:
    """Validate Seerr connection by making a test request."""
    url = f"{seerr_url}/api/v1/auth/me"
    headers = {"X-Api-Key": seerr_api_key}
    async with session.get(
        url, headers=headers, timeout=aiohttp.ClientTimeout(total=10),
    ) as resp:
        if resp.status == 401:
            raise ValueError("invalid_seerr_key")
        if resp.status != 200:
            raise ValueError("seerr_unavailable")


def _validate_and_handle_input(
    user_input: dict[str, Any],
) -> tuple[dict[str, str], bool]:
    """Validate input and return (errors, is_valid)."""
    errors: dict[str, str] = {}

    if user_input is not None and (not user_input.get(CONF_SEERR_URL) or not user_input.get(CONF_SEERR_API_KEY)):
        errors[CONF_BASE] = "invalid_input"

    return errors, len(errors) == 0


async def _async_validate_connection(
    hass: object,
    user_input: dict[str, Any],
) -> dict[str, str]:
    """Validate Seerr connection and return errors dict."""
    errors: dict[str, str] = {}

    try:
        session = aiohttp_client.async_get_clientsession(hass)
        await _validate_seerr_connection(
            session, user_input[CONF_SEERR_URL], user_input[CONF_SEERR_API_KEY],
        )
    except ValueError as err:
        errors[CONF_BASE] = str(err)
    except Exception:  # noqa: BLE001
        errors[CONF_BASE] = "cannot_connect"

    return errors


class SeerrLlmConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Seerr LLM Tools."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            errors = await _async_validate_connection(self.hass, user_input)

            if not errors:
                await self.async_set_unique_id(DOMAIN)
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title="Seerr LLM Tools",
                    data={
                        CONF_TMDB_API_KEY: CONF_DEF_TMDB_API_KEY,
                        **user_input,
                    },
                )

        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(
                STEP_USER_DATA_SCHEMA, user_input,
            ),
            errors=errors,
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        entry = self._get_reconfigure_entry()

        if user_input is not None:
            errors = await _async_validate_connection(self.hass, user_input)

            if not errors:
                return self.async_update_reload_and_abort(
                    entry,
                    data_updates={
                        CONF_TMDB_API_KEY: CONF_DEF_TMDB_API_KEY,
                        **user_input,
                    },
                )

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=self.add_suggested_values_to_schema(
                STEP_USER_DATA_SCHEMA, entry.data,
            ),
            errors=errors,
        )
