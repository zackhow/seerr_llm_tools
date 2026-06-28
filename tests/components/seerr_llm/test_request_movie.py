"""Tests for RequestMovie LLM tool."""
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
from custom_components.seerr_llm.tools.request import RequestMovie

from .conftest import (
    mock_seerr_movie_available,
    mock_seerr_movie_declined,
    mock_seerr_movie_not_found,
    mock_seerr_movie_requested,
    mock_seerr_request,
    mock_tmdb_movie_details,
)


async def test_request_movie_tool_success(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test RequestMovie tool creates a Seerr request."""
    mock_seerr_movie_not_found(aioclient_mock)
    mock_tmdb_movie_details(aioclient_mock)
    mock_seerr_request(aioclient_mock)

    with patch(
        "homeassistant.config_entries.ConfigEntries.async_entries",
        return_value=[mock_config_entry],
    ):
        tool = RequestMovie()
        result = await tool.async_call(
            hass,
            hass_llm.ToolInput(tool_name="RequestMovie", tool_args={"tmdb_id": 12345}),
            hass_llm.LLMContext(platform="conversation", context=None, language="en", assistant=None, device_id=None),
        )

    assert result["status"] == "success"
    assert "Test Movie" in result["message"]
    assert result["tmdb_id"] == 12345


async def test_request_movie_tool_seerr_error(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test RequestMovie tool returns error dict on Seerr API failure."""
    mock_seerr_movie_not_found(aioclient_mock)
    mock_tmdb_movie_details(aioclient_mock)
    aioclient_mock.post(
        "http://localhost:5055/api/v1/request",
        status=409,
    )

    with patch(
        "homeassistant.config_entries.ConfigEntries.async_entries",
        return_value=[mock_config_entry],
    ):
        tool = RequestMovie()
        result = await tool.async_call(
            hass,
            hass_llm.ToolInput(tool_name="RequestMovie", tool_args={"tmdb_id": 12345}),
            hass_llm.LLMContext(platform="conversation", context=None, language="en", assistant=None, device_id=None),
        )

    assert "error" in result
    assert "409" in result["error"]


async def test_request_movie_tool_fallback_title(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test RequestMovie uses fallback title when TMDB lookup fails."""
    aioclient_mock.get(
        "http://localhost:5055/api/v1/movie/99999",
        status=404,
    )
    aioclient_mock.get(
        f"{TMDB_BASE_URL}/movie/99999",
        status=404,
    )
    aioclient_mock.post(
        "http://localhost:5055/api/v1/request",
        json={"id": 999, "status": "requested"},
        status=200,
    )

    with patch(
        "homeassistant.config_entries.ConfigEntries.async_entries",
        return_value=[mock_config_entry],
    ):
        tool = RequestMovie()
        result = await tool.async_call(
            hass,
            hass_llm.ToolInput(tool_name="RequestMovie", tool_args={"tmdb_id": 99999}),
            hass_llm.LLMContext(platform="conversation", context=None, language="en", assistant=None, device_id=None),
        )

    assert result["status"] == "success"
    assert "99999" in result["message"]


async def test_request_movie_tool_connection_error(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test RequestMovie returns error dict on Seerr connection failure."""
    mock_seerr_movie_not_found(aioclient_mock)
    mock_tmdb_movie_details(aioclient_mock)
    aioclient_mock.post(
        "http://localhost:5055/api/v1/request",
        exc=aiohttp.ClientError,
    )

    with patch(
        "homeassistant.config_entries.ConfigEntries.async_entries",
        return_value=[mock_config_entry],
    ):
        tool = RequestMovie()
        result = await tool.async_call(
            hass,
            hass_llm.ToolInput(tool_name="RequestMovie", tool_args={"tmdb_id": 12345}),
            hass_llm.LLMContext(platform="conversation", context=None, language="en", assistant=None, device_id=None),
        )

    assert "error" in result
    assert "Seerr" in result["error"]


async def test_request_movie_already_available(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test RequestMovie returns already_available when media is in library."""
    mock_seerr_movie_available(aioclient_mock)

    with patch(
        "homeassistant.config_entries.ConfigEntries.async_entries",
        return_value=[mock_config_entry],
    ):
        tool = RequestMovie()
        result = await tool.async_call(
            hass,
            hass_llm.ToolInput(tool_name="RequestMovie", tool_args={"tmdb_id": 12345}),
            hass_llm.LLMContext(platform="conversation", context=None, language="en", assistant=None, device_id=None),
        )

    assert result["status"] == "already_available"
    assert "Test Movie" in result["message"]
    assert "already available" in result["message"]
    assert result["tmdb_id"] == 12345


async def test_request_movie_already_requested(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test RequestMovie returns already_requested when pending request exists."""
    mock_seerr_movie_requested(aioclient_mock)

    with patch(
        "homeassistant.config_entries.ConfigEntries.async_entries",
        return_value=[mock_config_entry],
    ):
        tool = RequestMovie()
        result = await tool.async_call(
            hass,
            hass_llm.ToolInput(tool_name="RequestMovie", tool_args={"tmdb_id": 12345}),
            hass_llm.LLMContext(platform="conversation", context=None, language="en", assistant=None, device_id=None),
        )

    assert result["status"] == "already_requested"
    assert "Test Movie" in result["message"]
    assert "already been requested" in result["message"]
    assert result["tmdb_id"] == 12345


async def test_request_movie_declined_allows_rerequest(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test RequestMovie proceeds when only declined requests exist."""
    mock_seerr_movie_declined(aioclient_mock)
    mock_seerr_request(aioclient_mock)

    with patch(
        "homeassistant.config_entries.ConfigEntries.async_entries",
        return_value=[mock_config_entry],
    ):
        tool = RequestMovie()
        result = await tool.async_call(
            hass,
            hass_llm.ToolInput(tool_name="RequestMovie", tool_args={"tmdb_id": 12345}),
            hass_llm.LLMContext(platform="conversation", context=None, language="en", assistant=None, device_id=None),
        )

    assert result["status"] == "success"
    assert "Request created" in result["message"]
    assert result["tmdb_id"] == 12345


async def test_request_movie_seerr_media_not_found(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test RequestMovie falls back to TMDB when Seerr media not found."""
    mock_seerr_movie_not_found(aioclient_mock)
    mock_tmdb_movie_details(aioclient_mock)
    mock_seerr_request(aioclient_mock)

    with patch(
        "homeassistant.config_entries.ConfigEntries.async_entries",
        return_value=[mock_config_entry],
    ):
        tool = RequestMovie()
        result = await tool.async_call(
            hass,
            hass_llm.ToolInput(tool_name="RequestMovie", tool_args={"tmdb_id": 12345}),
            hass_llm.LLMContext(platform="conversation", context=None, language="en", assistant=None, device_id=None),
        )

    assert result["status"] == "success"
    assert "Test Movie" in result["message"]
    assert result["tmdb_id"] == 12345


async def test_request_movie_seerr_connection_error(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test RequestMovie falls back to TMDB on Seerr connection error."""
    aioclient_mock.get(
        "http://localhost:5055/api/v1/movie/12345",
        exc=aiohttp.ClientError,
    )
    mock_tmdb_movie_details(aioclient_mock)
    mock_seerr_request(aioclient_mock)

    with patch(
        "homeassistant.config_entries.ConfigEntries.async_entries",
        return_value=[mock_config_entry],
    ):
        tool = RequestMovie()
        result = await tool.async_call(
            hass,
            hass_llm.ToolInput(tool_name="RequestMovie", tool_args={"tmdb_id": 12345}),
            hass_llm.LLMContext(platform="conversation", context=None, language="en", assistant=None, device_id=None),
        )

    assert result["status"] == "success"
    assert "Test Movie" in result["message"]
    assert result["tmdb_id"] == 12345
