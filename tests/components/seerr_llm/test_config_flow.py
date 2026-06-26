"""Tests for Seerr LLM Tools config flow."""
from __future__ import annotations

from typing import Any
from unittest.mock import patch

import aiohttp
import pytest
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import (
    AiohttpClientMocker,
)

from custom_components.seerr_llm.const import (
    CONF_TMDB_API_KEY,
    DOMAIN,
    TMDB_BASE_URL,
)

from .conftest import VALID_CONFIG, _mock_seerr_auth, _mock_tmdb_popular


@pytest.mark.parametrize(
    "input_data",
    [
        VALID_CONFIG,
    ],
)
async def test_user_flow_success(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    enable_custom_integrations: None,
    input_data: dict[str, Any],
) -> None:
    """Test successful user config flow."""
    _mock_tmdb_popular(aioclient_mock)
    _mock_seerr_auth(aioclient_mock)

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input=input_data,
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Seerr LLM Tools"
    assert result["data"] == input_data


async def test_user_flow_invalid_tmdb_key(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    enable_custom_integrations: None,
) -> None:
    """Test user flow with invalid TMDB API key (401)."""
    aioclient_mock.get(
        f"{TMDB_BASE_URL}/movie/popular",
        status=401,
    )

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
    )

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input=VALID_CONFIG,
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_tmdb_key"}


async def test_user_flow_tmdb_unavailable(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    enable_custom_integrations: None,
) -> None:
    """Test user flow when TMDB API is unavailable (500)."""
    aioclient_mock.get(
        f"{TMDB_BASE_URL}/movie/popular",
        status=500,
    )

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
    )

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input=VALID_CONFIG,
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "tmdb_unavailable"}


async def test_user_flow_invalid_seerr_key(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    enable_custom_integrations: None,
) -> None:
    """Test user flow with invalid Seerr API key (401)."""
    _mock_tmdb_popular(aioclient_mock)
    aioclient_mock.get(
        "http://localhost:5055/api/v1/auth/me",
        status=401,
    )

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
    )

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input=VALID_CONFIG,
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_seerr_key"}


async def test_user_flow_seerr_unavailable(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    enable_custom_integrations: None,
) -> None:
    """Test user flow when Seerr is unavailable (500)."""
    _mock_tmdb_popular(aioclient_mock)
    aioclient_mock.get(
        "http://localhost:5055/api/v1/auth/me",
        status=500,
    )

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
    )

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input=VALID_CONFIG,
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "seerr_unavailable"}


async def test_user_flow_cannot_connect(
    hass: HomeAssistant,
    enable_custom_integrations: None,
) -> None:
    """Test user flow when connection fails unexpectedly."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
    )

    with patch(
        "homeassistant.helpers.aiohttp_client.async_get_clientsession",
        side_effect=aiohttp.ClientError,
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input=VALID_CONFIG,
        )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}


async def test_user_flow_already_configured(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    enable_custom_integrations: None,
) -> None:
    """Test user flow aborts when integration is already configured."""
    _mock_tmdb_popular(aioclient_mock)
    _mock_seerr_auth(aioclient_mock)

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Seerr LLM Tools",
        data=VALID_CONFIG,
        unique_id=DOMAIN,
        entry_id="existing_entry",
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
        data=VALID_CONFIG,
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "single_instance_allowed"


async def test_reconfigure_flow_success(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    enable_custom_integrations: None,
) -> None:
    """Test successful reconfigure flow."""
    _mock_tmdb_popular(aioclient_mock)
    _mock_seerr_auth(aioclient_mock)

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Seerr LLM Tools",
        data=VALID_CONFIG,
        unique_id=DOMAIN,
        entry_id="test_entry",
    )
    entry.add_to_hass(hass)

    new_config = {
        **VALID_CONFIG,
        CONF_TMDB_API_KEY: "new-tmdb-key",
    }

    result = await entry.start_reconfigure_flow(hass)

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reconfigure"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input=new_config,
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    assert entry.data[CONF_TMDB_API_KEY] == "new-tmdb-key"


async def test_reconfigure_flow_invalid_tmdb_key(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    enable_custom_integrations: None,
) -> None:
    """Test reconfigure flow with invalid TMDB API key."""
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

    result = await entry.start_reconfigure_flow(hass)

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={**VALID_CONFIG, CONF_TMDB_API_KEY: "bad-tmdb-key"},
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_tmdb_key"}


async def test_reconfigure_flow_cannot_connect(
    hass: HomeAssistant,
    enable_custom_integrations: None,
) -> None:
    """Test reconfigure flow when connection fails."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Seerr LLM Tools",
        data=VALID_CONFIG,
        unique_id=DOMAIN,
        entry_id="test_entry",
    )
    entry.add_to_hass(hass)

    result = await entry.start_reconfigure_flow(hass)

    with patch(
        "homeassistant.helpers.aiohttp_client.async_get_clientsession",
        side_effect=aiohttp.ClientError,
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input=VALID_CONFIG,
        )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}
