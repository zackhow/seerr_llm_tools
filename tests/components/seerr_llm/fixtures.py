"""Shared fixtures for Seerr LLM Tools integration tests."""
from __future__ import annotations

from typing import Any

import pytest
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.seerr_llm.const import (
    CONF_SEERR_API_KEY,
    CONF_SEERR_URL,
    CONF_TMDB_API_KEY,
    DOMAIN,
    SeerrLlmConfigEntryData,
)

VALID_CONFIG: dict[str, Any] = {
    CONF_TMDB_API_KEY: "test-tmdb-key",
    CONF_SEERR_URL: "http://localhost:5055",
    CONF_SEERR_API_KEY: "test-seerr-key",
}

VALID_CONFIG_FLOW_INPUT: dict[str, Any] = {
    CONF_SEERR_URL: "http://localhost:5055",
    CONF_SEERR_API_KEY: "test-seerr-key",
}


@pytest.fixture
def mock_config_entry(hass: HomeAssistant) -> MockConfigEntry:
    """Create a mocked config entry with runtime data."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Seerr LLM Tools",
        data=VALID_CONFIG,
        unique_id=DOMAIN,
        entry_id="mock_entry_id",
    )
    entry.add_to_hass(hass)
    entry.runtime_data = SeerrLlmConfigEntryData(
        tmdb_api_key=VALID_CONFIG[CONF_TMDB_API_KEY],
        seerr_url=VALID_CONFIG[CONF_SEERR_URL],
        seerr_api_key=VALID_CONFIG[CONF_SEERR_API_KEY],
    )
    return entry
