"""Tests for Seerr LLM Tools integration setup and unload."""
from __future__ import annotations

from unittest.mock import patch

import aiohttp
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import (
    AiohttpClientMocker,
)

from custom_components.seerr_llm.const import (
    CONF_SEERR_API_KEY,
    CONF_SEERR_URL,
    CONF_TMDB_API_KEY,
    DOMAIN,
    TMDB_BASE_URL,
)

from .conftest import VALID_CONFIG, _mock_tmdb_popular


async def test_setup_unload_entry(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    enable_custom_integrations: None,
) -> None:
    """Test successful setup and unload of config entry."""
    _mock_tmdb_popular(aioclient_mock)

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Seerr LLM Tools",
        data=VALID_CONFIG,
        unique_id=DOMAIN,
        entry_id="test_entry",
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert result is True
    assert entry.state is ConfigEntryState.LOADED

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.NOT_LOADED


async def test_setup_entry_tmdb_auth_failure(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    enable_custom_integrations: None,
) -> None:
    """Test setup fails when TMDB API key is invalid (401)."""
    aioclient_mock.get(
        f"{TMDB_BASE_URL}/movie/popular",
        status=401,
    )

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Seerr LLM Tools",
        data=VALID_CONFIG,
        unique_id=DOMAIN,
        entry_id="test_entry",
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert result is False
    assert entry.state is ConfigEntryState.SETUP_RETRY


async def test_setup_entry_tmdb_connection_error(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    enable_custom_integrations: None,
) -> None:
    """Test setup fails when TMDB API is unreachable."""
    aioclient_mock.get(
        f"{TMDB_BASE_URL}/movie/popular",
        exc=aiohttp.ClientError,
    )

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Seerr LLM Tools",
        data=VALID_CONFIG,
        unique_id=DOMAIN,
        entry_id="test_entry",
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert result is False
    assert entry.state is ConfigEntryState.SETUP_RETRY


async def test_setup_entry_registers_llm_api(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    enable_custom_integrations: None,
) -> None:
    """Test that setup registers the LLM API."""
    _mock_tmdb_popular(aioclient_mock)

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Seerr LLM Tools",
        data=VALID_CONFIG,
        unique_id=DOMAIN,
        entry_id="test_entry",
    )
    entry.add_to_hass(hass)

    from homeassistant.helpers import llm as hass_llm

    with patch.object(hass_llm, "async_register_api") as mock_register:
        mock_register.return_value = lambda: None
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    mock_register.assert_called_once()
    assert entry.state is ConfigEntryState.LOADED


async def test_setup_entry_runtime_data_set(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    enable_custom_integrations: None,
) -> None:
    """Test that setup sets runtime data on the config entry."""
    _mock_tmdb_popular(aioclient_mock)

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Seerr LLM Tools",
        data=VALID_CONFIG,
        unique_id=DOMAIN,
        entry_id="test_entry",
    )
    entry.add_to_hass(hass)

    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.LOADED
    assert entry.runtime_data.tmdb_api_key == VALID_CONFIG[CONF_TMDB_API_KEY]
    assert entry.runtime_data.seerr_url == VALID_CONFIG[CONF_SEERR_URL]
    assert entry.runtime_data.seerr_api_key == VALID_CONFIG[CONF_SEERR_API_KEY]
