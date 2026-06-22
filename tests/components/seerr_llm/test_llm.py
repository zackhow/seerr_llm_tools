"""Tests for Seerr LLM Tools LLM tools."""
from __future__ import annotations

import asyncio
from unittest.mock import patch

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.helpers import llm as hass_llm
from pytest_homeassistant_custom_component.test_util.aiohttp import (
    AiohttpClientMocker,
)

from custom_components.seerr_llm.const import (
    DOMAIN,
    TMDB_BASE_URL,
)
from custom_components.seerr_llm.exceptions import NoResultsError, TmdbApiError
from custom_components.seerr_llm.llm import (
    RequestMovie,
    SearchMovie,
    SearchTvShow,
    _get_movie_cast,
    _get_movie_title,
    _tmdb_request,
    _tmdb_search,
)

from .conftest import (
    VALID_CONFIG,
    _mock_seerr_request,
    _mock_tmdb_movie_details,
    _mock_tmdb_movie_with_cast,
    _mock_tmdb_popular,
    _mock_tmdb_search_movie,
    _mock_tmdb_search_tv,
)


async def test_tmdb_request_success(
    aioclient_mock: AiohttpClientMocker,
) -> None:
    """Test successful TMDB API request."""
    _mock_tmdb_popular(aioclient_mock)

    loop = asyncio.get_running_loop()
    session = aioclient_mock.create_session(loop)
    result = await _tmdb_request(
        session,
        "test-key",
        f"{TMDB_BASE_URL}/movie/popular",
    )

    assert result["page"] == 1
    assert len(result["results"]) == 1


async def test_tmdb_request_failure(
    aioclient_mock: AiohttpClientMocker,
) -> None:
    """Test TMDB API request failure raises TmdbApiError."""
    aioclient_mock.get(
        f"{TMDB_BASE_URL}/movie/popular",
        status=401,
    )

    loop = asyncio.get_running_loop()
    session = aioclient_mock.create_session(loop)

    with pytest.raises(TmdbApiError) as exc_info:
        await _tmdb_request(
            session,
            "test-key",
            f"{TMDB_BASE_URL}/movie/popular",
        )

    assert exc_info.value.status == 401


async def test_tmdb_search_success(
    aioclient_mock: AiohttpClientMocker,
) -> None:
    """Test successful TMDB search returns top result."""
    aioclient_mock.get(
        f"{TMDB_BASE_URL}/search/movie",
        json={
            "results": [
                {"id": 1, "title": "First Movie"},
                {"id": 2, "title": "Second Movie"},
            ],
        },
    )

    loop = asyncio.get_running_loop()
    session = aioclient_mock.create_session(loop)
    result = await _tmdb_search(
        session,
        "test-key",
        "search/movie",
        "test query",
    )

    assert result["id"] == 1
    assert result["title"] == "First Movie"


async def test_tmdb_search_no_results(
    aioclient_mock: AiohttpClientMocker,
) -> None:
    """Test TMDB search with no results raises NoResultsError."""
    aioclient_mock.get(
        f"{TMDB_BASE_URL}/search/movie",
        json={"results": []},
    )

    loop = asyncio.get_running_loop()
    session = aioclient_mock.create_session(loop)

    with pytest.raises(NoResultsError) as exc_info:
        await _tmdb_search(
            session,
            "test-key",
            "search/movie",
            "nonexistent movie",
        )

    assert exc_info.value.query == "nonexistent movie"


async def test_get_movie_title(
    aioclient_mock: AiohttpClientMocker,
) -> None:
    """Test fetching movie title by TMDB ID."""
    _mock_tmdb_movie_details(aioclient_mock)

    loop = asyncio.get_running_loop()
    session = aioclient_mock.create_session(loop)
    result = await _get_movie_title(
        session,
        "test-key",
        12345,
    )

    assert result["title"] == "Test Movie"


async def test_get_movie_cast(
    aioclient_mock: AiohttpClientMocker,
) -> None:
    """Test fetching movie cast returns first two cast members."""
    aioclient_mock.get(
        f"{TMDB_BASE_URL}/movie/12345",
        json={
            "credits": {
                "cast": [
                    {"id": 1, "name": "Actor One"},
                    {"id": 2, "name": "Actor Two"},
                    {"id": 3, "name": "Actor Three"},
                ],
            },
        },
    )

    loop = asyncio.get_running_loop()
    session = aioclient_mock.create_session(loop)
    result = await _get_movie_cast(
        session,
        "test-key",
        12345,
    )

    assert result == ["Actor One", "Actor Two"]


async def test_get_movie_cast_empty(
    aioclient_mock: AiohttpClientMocker,
) -> None:
    """Test fetching movie cast with no cast data returns empty list."""
    aioclient_mock.get(
        f"{TMDB_BASE_URL}/movie/12345",
        json={"credits": {"cast": []}},
    )

    loop = asyncio.get_running_loop()
    session = aioclient_mock.create_session(loop)
    result = await _get_movie_cast(
        session,
        "test-key",
        12345,
    )

    assert result == []


async def test_get_movie_cast_api_error(
    aioclient_mock: AiohttpClientMocker,
) -> None:
    """Test fetching movie cast returns empty list on API error."""
    aioclient_mock.get(
        f"{TMDB_BASE_URL}/movie/12345",
        status=404,
    )

    loop = asyncio.get_running_loop()
    session = aioclient_mock.create_session(loop)
    result = await _get_movie_cast(
        session,
        "test-key",
        12345,
    )

    assert result == []


async def test_search_movie_tool_success(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    mock_config_entry,
) -> None:
    """Test SearchMovie tool returns movie details."""
    _mock_tmdb_search_movie(aioclient_mock)
    _mock_tmdb_movie_with_cast(aioclient_mock)

    with patch(
        "homeassistant.config_entries.ConfigEntries.async_entries",
        return_value=[mock_config_entry],
    ):
        tool = SearchMovie()
        result = await tool.async_call(
            hass,
            hass_llm.ToolInput(tool_name="SearchMovie", tool_args={"query": "Test Movie"}),
            hass_llm.LLMContext(platform="conversation", context=None, language="en", assistant=None, device_id=None),
        )

    assert result["title"] == "Test Movie"
    assert result["year"] == "2024"
    assert result["overview"] == "A great movie."
    assert result["rating"] == 8.5
    assert result["cast"] == ["Actor One", "Actor Two"]
    assert result["tmdb_id"] == 12345


async def test_search_movie_tool_no_results(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    mock_config_entry,
) -> None:
    """Test SearchMovie tool returns error when no results found."""
    aioclient_mock.get(
        f"{TMDB_BASE_URL}/search/movie",
        json={"results": []},
    )

    with patch(
        "homeassistant.config_entries.ConfigEntries.async_entries",
        return_value=[mock_config_entry],
    ):
        tool = SearchMovie()
        result = await tool.async_call(
            hass,
            hass_llm.ToolInput(tool_name="SearchMovie", tool_args={"query": "nonexistent"}),
            hass_llm.LLMContext(platform="conversation", context=None, language="en", assistant=None, device_id=None),
        )

    assert "error" in result
    assert "nonexistent" in result["error"]


async def test_search_tv_show_tool_success(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    mock_config_entry,
) -> None:
    """Test SearchTvShow tool returns TV show details."""
    _mock_tmdb_search_tv(aioclient_mock)

    with patch(
        "homeassistant.config_entries.ConfigEntries.async_entries",
        return_value=[mock_config_entry],
    ):
        tool = SearchTvShow()
        result = await tool.async_call(
            hass,
            hass_llm.ToolInput(tool_name="SearchTvShow", tool_args={"query": "Test TV Show"}),
            hass_llm.LLMContext(platform="conversation", context=None, language="en", assistant=None, device_id=None),
        )

    assert result["title"] == "Test TV Show"
    assert result["year"] == "2023"
    assert result["overview"] == "A great show."
    assert result["rating"] == 9.0
    assert result["tmdb_id"] == 67890


async def test_search_tv_show_tool_no_results(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    mock_config_entry,
) -> None:
    """Test SearchTvShow tool returns error when no results found."""
    aioclient_mock.get(
        f"{TMDB_BASE_URL}/search/tv",
        json={"results": []},
    )

    with patch(
        "homeassistant.config_entries.ConfigEntries.async_entries",
        return_value=[mock_config_entry],
    ):
        tool = SearchTvShow()
        result = await tool.async_call(
            hass,
            hass_llm.ToolInput(tool_name="SearchTvShow", tool_args={"query": "nonexistent"}),
            hass_llm.LLMContext(platform="conversation", context=None, language="en", assistant=None, device_id=None),
        )

    assert "error" in result
    assert "nonexistent" in result["error"]


async def test_request_movie_tool_success(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    mock_config_entry,
) -> None:
    """Test RequestMovie tool creates a Seerr request."""
    _mock_tmdb_movie_details(aioclient_mock)
    _mock_seerr_request(aioclient_mock)

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
    mock_config_entry,
) -> None:
    """Test RequestMovie tool returns error dict on Seerr API failure."""
    _mock_tmdb_movie_details(aioclient_mock)
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
    mock_config_entry,
) -> None:
    """Test RequestMovie uses fallback title when TMDB lookup fails."""
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


async def test_search_movie_tool_no_release_date(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    mock_config_entry,
) -> None:
    """Test SearchMovie handles missing release date."""
    aioclient_mock.get(
        f"{TMDB_BASE_URL}/search/movie",
        json={
            "results": [
                {
                    "id": 12345,
                    "title": "Upcoming Movie",
                    "release_date": "",
                    "vote_average": 0,
                    "overview": "Coming soon.",
                },
            ],
        },
    )
    aioclient_mock.get(
        f"{TMDB_BASE_URL}/movie/12345",
        json={"credits": {"cast": []}},
    )

    with patch(
        "homeassistant.config_entries.ConfigEntries.async_entries",
        return_value=[mock_config_entry],
    ):
        tool = SearchMovie()
        result = await tool.async_call(
            hass,
            hass_llm.ToolInput(tool_name="SearchMovie", tool_args={"query": "Upcoming Movie"}),
            hass_llm.LLMContext(platform="conversation", context=None, language="en", assistant=None, device_id=None),
        )

    assert result["title"] == "Upcoming Movie"
    assert result["year"] == "Unknown"
    assert result["rating"] == "N/A"
    assert result["cast"] == []


async def test_request_movie_tool_connection_error(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    mock_config_entry,
) -> None:
    """Test RequestMovie returns error dict on Seerr connection failure."""
    import aiohttp

    _mock_tmdb_movie_details(aioclient_mock)
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
