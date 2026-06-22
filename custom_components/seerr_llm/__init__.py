"""Seerr LLM Tools integration for Home Assistant."""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import aiohttp_client
from homeassistant.helpers import llm as hass_llm

from .const import (
    CONF_SEERR_API_KEY,
    CONF_SEERR_URL,
    CONF_TMDB_API_KEY,
    DOMAIN,
    TMDB_BASE_URL,
    SeerrLlmConfigEntryData,
)
from .llm import SeerrLlmAPI

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Seerr LLM Tools from a config entry."""
    import aiohttp  # noqa: PLC0415

    config = SeerrLlmConfigEntryData(
        tmdb_api_key=entry.data[CONF_TMDB_API_KEY],
        seerr_url=entry.data[CONF_SEERR_URL],
        seerr_api_key=entry.data[CONF_SEERR_API_KEY],
    )

    session = aiohttp_client.async_get_clientsession(hass)
    try:
        url = f"{TMDB_BASE_URL}/movie/popular"
        headers = {"Authorization": f"Bearer {config.tmdb_api_key}"}
        async with session.get(
            url, headers=headers, params={"language": "en-US"}, timeout=aiohttp.ClientTimeout(total=10),
        ) as resp:
            if resp.status != 200:
                body = await resp.text()
                raise ConfigEntryNotReady(
                    f"TMDB API authentication failed (status {resp.status}): {body}",
                )
    except aiohttp.ClientError as err:
        raise ConfigEntryNotReady(f"Unable to connect to TMDB API: {err}") from err

    entry.runtime_data = config

    unreg = hass_llm.async_register_api(hass, SeerrLlmAPI(hass, entry))
    entry.async_on_unload(unreg)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    return True
