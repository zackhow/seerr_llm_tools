"""Tests for RequestTvShow LLM tool."""
from __future__ import annotations

from unittest.mock import patch

import aiohttp
from homeassistant.core import HomeAssistant
from homeassistant.helpers import llm as hass_llm
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import (
    AiohttpClientMocker,
)

from custom_components.seerr_llm.const import TMDB_BASE_URL
from custom_components.seerr_llm.tools.request import RequestTvShow

from .conftest import (
    mock_seerr_tv_available,
    mock_seerr_tv_declined,
    mock_seerr_tv_not_found,
    mock_seerr_tv_request,
    mock_seerr_tv_requested,
    mock_tmdb_tv_details,
)


async def test_request_tv_show_tool_success(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test RequestTvShow tool creates a Seerr request for all seasons."""
    mock_seerr_tv_not_found(aioclient_mock)
    mock_tmdb_tv_details(aioclient_mock)
    mock_seerr_tv_request(aioclient_mock)

    with patch(
        "homeassistant.config_entries.ConfigEntries.async_entries",
        return_value=[mock_config_entry],
    ):
        tool = RequestTvShow()
        result = await tool.async_call(
            hass,
            hass_llm.ToolInput(tool_name="RequestTvShow", tool_args={"tmdb_id": 67890}),
            hass_llm.LLMContext(platform="conversation", context=None, language="en", assistant=None, device_id=None),
        )

    assert result["status"] == "success"
    assert "Test TV Show" in result["message"]
    assert result["tmdb_id"] == 67890


async def test_request_tv_show_tool_specific_seasons(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test RequestTvShow tool creates a Seerr request for specific seasons."""
    mock_seerr_tv_not_found(aioclient_mock)
    mock_tmdb_tv_details(aioclient_mock)
    mock_seerr_tv_request(aioclient_mock)

    with patch(
        "homeassistant.config_entries.ConfigEntries.async_entries",
        return_value=[mock_config_entry],
    ):
        tool = RequestTvShow()
        result = await tool.async_call(
            hass,
            hass_llm.ToolInput(
                tool_name="RequestTvShow",
                tool_args={"tmdb_id": 67890, "seasons": [1, 2]},
            ),
            hass_llm.LLMContext(platform="conversation", context=None, language="en", assistant=None, device_id=None),
        )

    assert result["status"] == "success"
    assert "Test TV Show" in result["message"]
    assert result["tmdb_id"] == 67890


async def test_request_tv_show_tool_seerr_error(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test RequestTvShow tool returns error dict on Seerr API failure."""
    mock_seerr_tv_not_found(aioclient_mock)
    mock_tmdb_tv_details(aioclient_mock)
    aioclient_mock.post(
        "http://localhost:5055/api/v1/request",
        status=409,
    )

    with patch(
        "homeassistant.config_entries.ConfigEntries.async_entries",
        return_value=[mock_config_entry],
    ):
        tool = RequestTvShow()
        result = await tool.async_call(
            hass,
            hass_llm.ToolInput(tool_name="RequestTvShow", tool_args={"tmdb_id": 67890}),
            hass_llm.LLMContext(platform="conversation", context=None, language="en", assistant=None, device_id=None),
        )

    assert "error" in result
    assert "409" in result["error"]


async def test_request_tv_show_tool_fallback_title(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test RequestTvShow uses fallback title when TMDB lookup fails."""
    aioclient_mock.get(
        "http://localhost:5055/api/v1/tv/99999",
        status=404,
    )
    aioclient_mock.get(
        f"{TMDB_BASE_URL}/tv/99999",
        status=404,
    )
    aioclient_mock.post(
        "http://localhost:5055/api/v1/request",
        json={"id": 1001, "status": "requested"},
        status=200,
    )

    with patch(
        "homeassistant.config_entries.ConfigEntries.async_entries",
        return_value=[mock_config_entry],
    ):
        tool = RequestTvShow()
        result = await tool.async_call(
            hass,
            hass_llm.ToolInput(tool_name="RequestTvShow", tool_args={"tmdb_id": 99999}),
            hass_llm.LLMContext(platform="conversation", context=None, language="en", assistant=None, device_id=None),
        )

    assert result["status"] == "success"
    assert "99999" in result["message"]


async def test_request_tv_show_tool_connection_error(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test RequestTvShow returns error dict on Seerr connection failure."""
    mock_seerr_tv_not_found(aioclient_mock)
    mock_tmdb_tv_details(aioclient_mock)
    aioclient_mock.post(
        "http://localhost:5055/api/v1/request",
        exc=aiohttp.ClientError,
    )

    with patch(
        "homeassistant.config_entries.ConfigEntries.async_entries",
        return_value=[mock_config_entry],
    ):
        tool = RequestTvShow()
        result = await tool.async_call(
            hass,
            hass_llm.ToolInput(tool_name="RequestTvShow", tool_args={"tmdb_id": 67890}),
            hass_llm.LLMContext(platform="conversation", context=None, language="en", assistant=None, device_id=None),
        )

    assert "error" in result
    assert "Seerr" in result["error"]


async def test_request_tv_show_already_available(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test RequestTvShow returns already_available when media is in library."""
    mock_seerr_tv_available(aioclient_mock)

    with patch(
        "homeassistant.config_entries.ConfigEntries.async_entries",
        return_value=[mock_config_entry],
    ):
        tool = RequestTvShow()
        result = await tool.async_call(
            hass,
            hass_llm.ToolInput(tool_name="RequestTvShow", tool_args={"tmdb_id": 67890}),
            hass_llm.LLMContext(platform="conversation", context=None, language="en", assistant=None, device_id=None),
        )

    assert result["status"] == "already_available"
    assert "Test TV Show" in result["message"]
    assert "already available" in result["message"]
    assert result["tmdb_id"] == 67890


async def test_request_tv_show_already_requested(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test RequestTvShow returns already_requested when pending request exists."""
    mock_seerr_tv_requested(aioclient_mock)

    with patch(
        "homeassistant.config_entries.ConfigEntries.async_entries",
        return_value=[mock_config_entry],
    ):
        tool = RequestTvShow()
        result = await tool.async_call(
            hass,
            hass_llm.ToolInput(tool_name="RequestTvShow", tool_args={"tmdb_id": 67890}),
            hass_llm.LLMContext(platform="conversation", context=None, language="en", assistant=None, device_id=None),
        )

    assert result["status"] == "already_requested"
    assert "Test TV Show" in result["message"]
    assert "already been requested" in result["message"]
    assert result["tmdb_id"] == 67890


async def test_request_tv_show_declined_allows_rerequest(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test RequestTvShow proceeds when only declined requests exist."""
    mock_seerr_tv_declined(aioclient_mock)
    mock_seerr_tv_request(aioclient_mock)

    with patch(
        "homeassistant.config_entries.ConfigEntries.async_entries",
        return_value=[mock_config_entry],
    ):
        tool = RequestTvShow()
        result = await tool.async_call(
            hass,
            hass_llm.ToolInput(tool_name="RequestTvShow", tool_args={"tmdb_id": 67890}),
            hass_llm.LLMContext(platform="conversation", context=None, language="en", assistant=None, device_id=None),
        )

    assert result["status"] == "success"
    assert "Request created" in result["message"]
    assert result["tmdb_id"] == 67890


async def test_request_tv_show_seerr_media_not_found(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test RequestTvShow falls back to TMDB when Seerr media not found."""
    mock_seerr_tv_not_found(aioclient_mock)
    mock_tmdb_tv_details(aioclient_mock)
    mock_seerr_tv_request(aioclient_mock)

    with patch(
        "homeassistant.config_entries.ConfigEntries.async_entries",
        return_value=[mock_config_entry],
    ):
        tool = RequestTvShow()
        result = await tool.async_call(
            hass,
            hass_llm.ToolInput(tool_name="RequestTvShow", tool_args={"tmdb_id": 67890}),
            hass_llm.LLMContext(platform="conversation", context=None, language="en", assistant=None, device_id=None),
        )

    assert result["status"] == "success"
    assert "Test TV Show" in result["message"]
    assert result["tmdb_id"] == 67890


async def test_request_tv_show_seerr_connection_error(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test RequestTvShow falls back to TMDB on Seerr connection error."""
    aioclient_mock.get(
        "http://localhost:5055/api/v1/tv/67890",
        exc=aiohttp.ClientError,
    )
    mock_tmdb_tv_details(aioclient_mock)
    mock_seerr_tv_request(aioclient_mock)

    with patch(
        "homeassistant.config_entries.ConfigEntries.async_entries",
        return_value=[mock_config_entry],
    ):
        tool = RequestTvShow()
        result = await tool.async_call(
            hass,
            hass_llm.ToolInput(tool_name="RequestTvShow", tool_args={"tmdb_id": 67890}),
            hass_llm.LLMContext(platform="conversation", context=None, language="en", assistant=None, device_id=None),
        )

    assert result["status"] == "success"
    assert "Test TV Show" in result["message"]
    assert result["tmdb_id"] == 67890
