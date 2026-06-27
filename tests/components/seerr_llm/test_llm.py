"""Tests for Seerr LLM Tools LLM tools."""
from __future__ import annotations

import asyncio
from unittest.mock import patch

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.helpers import llm as hass_llm
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import (
    AiohttpClientMocker,
)

from custom_components.seerr_llm.const import (
    TMDB_BASE_URL,
)
from custom_components.seerr_llm.exceptions import NoResultsError, TmdbApiError
from custom_components.seerr_llm.llm import (
    RequestMovie,
    RequestTvShow,
    SearchMovie,
    SearchTvShow,
    _get_movie_cast,
    _get_movie_title,
    _get_tv_show_details,
    _get_tv_show_title,
    _tmdb_request,
    _tmdb_search,
)

from .conftest import (
    _mock_seerr_movie_available,
    _mock_seerr_movie_declined,
    _mock_seerr_movie_not_found,
    _mock_seerr_movie_requested,
    _mock_seerr_request,
    _mock_seerr_tv_available,
    _mock_seerr_tv_declined,
    _mock_seerr_tv_not_found,
    _mock_seerr_tv_request,
    _mock_seerr_tv_requested,
    _mock_tmdb_movie_details,
    _mock_tmdb_movies_with_cast_all,
    _mock_tmdb_popular,
    _mock_tmdb_search_movie,
    _mock_tmdb_search_tv,
    _mock_tmdb_tv_details,
    _mock_tmdb_tv_details_all,
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
    """Test successful TMDB search returns results as list."""
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

    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0]["id"] == 1
    assert result[0]["title"] == "First Movie"


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
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test SearchMovie tool returns multiple movie results."""
    _mock_tmdb_search_movie(aioclient_mock)
    _mock_tmdb_movies_with_cast_all(aioclient_mock)

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

    assert "results" in result
    assert isinstance(result["results"], list)
    assert len(result["results"]) == 3

    first = result["results"][0]
    assert first["title"] == "Test Movie"
    assert first["year"] == "2024"
    assert first["overview"] == "A great movie."
    assert first["rating"] == 8.5
    assert first["cast"] == ["Actor One", "Actor Two"]
    assert first["tmdb_id"] == 12345

    second = result["results"][1]
    assert second["title"] == "Test Movie 2"
    assert second["year"] == "2023"
    assert second["cast"] == ["Actor Three", "Actor Four"]
    assert second["tmdb_id"] == 12346


async def test_search_movie_tool_no_results(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    mock_config_entry: MockConfigEntry,
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
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test SearchTvShow tool returns multiple TV show results."""
    _mock_tmdb_search_tv(aioclient_mock)
    _mock_tmdb_tv_details_all(aioclient_mock)

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

    assert "results" in result
    assert isinstance(result["results"], list)
    assert len(result["results"]) == 3

    first = result["results"][0]
    assert first["title"] == "Test TV Show"
    assert first["year"] == "2023"
    assert first["overview"] == "A great show."
    assert first["rating"] == 9.0
    assert first["cast"] == ["Actor One", "Actor Two"]
    assert first["season_count"] == 3
    assert first["tmdb_id"] == 67890

    second = result["results"][1]
    assert second["title"] == "Test TV Show 2"
    assert second["year"] == "2022"
    assert second["cast"] == ["Actor Three", "Actor Four"]
    assert second["season_count"] == 2
    assert second["tmdb_id"] == 67891


async def test_get_tv_show_title(
    aioclient_mock: AiohttpClientMocker,
) -> None:
    """Test fetching TV show title by TMDB ID."""
    _mock_tmdb_tv_details(aioclient_mock)

    loop = asyncio.get_running_loop()
    session = aioclient_mock.create_session(loop)
    result = await _get_tv_show_title(
        session,
        "test-key",
        67890,
    )

    assert result["name"] == "Test TV Show"


async def test_get_tv_show_details(
    aioclient_mock: AiohttpClientMocker,
) -> None:
    """Test fetching TV show details returns cast and season count."""
    aioclient_mock.get(
        f"{TMDB_BASE_URL}/tv/67890",
        json={
            "number_of_seasons": 5,
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
    result = await _get_tv_show_details(
        session,
        "test-key",
        67890,
    )

    assert result == (["Actor One", "Actor Two"], 5)


async def test_get_tv_show_details_empty(
    aioclient_mock: AiohttpClientMocker,
) -> None:
    """Test fetching TV show details with no cast data returns empty list."""
    aioclient_mock.get(
        f"{TMDB_BASE_URL}/tv/67890",
        json={"credits": {"cast": []}, "number_of_seasons": 2},
    )

    loop = asyncio.get_running_loop()
    session = aioclient_mock.create_session(loop)
    result = await _get_tv_show_details(
        session,
        "test-key",
        67890,
    )

    assert result == ([], 2)


async def test_get_tv_show_details_api_error(
    aioclient_mock: AiohttpClientMocker,
) -> None:
    """Test fetching TV show details returns empty on API error."""
    aioclient_mock.get(
        f"{TMDB_BASE_URL}/tv/67890",
        status=404,
    )

    loop = asyncio.get_running_loop()
    session = aioclient_mock.create_session(loop)
    result = await _get_tv_show_details(
        session,
        "test-key",
        67890,
    )

    assert result == ([], 0)


async def test_search_tv_show_tool_no_results(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    mock_config_entry: MockConfigEntry,
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


async def test_search_tv_show_fewer_than_five_results(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test SearchTvShow handles fewer than 5 results."""
    aioclient_mock.get(
        f"{TMDB_BASE_URL}/search/tv",
        json={
            "page": 1,
            "results": [
                {
                    "id": 67890,
                    "name": "Only Show",
                    "first_air_date": "2023-06-15",
                    "vote_average": 9.0,
                    "overview": "A great show.",
                },
            ],
        },
    )
    aioclient_mock.get(
        f"{TMDB_BASE_URL}/tv/67890",
        json={
            "id": 67890,
            "name": "Only Show",
            "first_air_date": "2023-06-15",
            "vote_average": 9.0,
            "overview": "A test TV show overview.",
            "number_of_seasons": 3,
            "credits": {
                "cast": [
                    {"id": 1, "name": "Actor One", "character": "Character 1"},
                    {"id": 2, "name": "Actor Two", "character": "Character 2"},
                ],
            },
        },
    )

    with patch(
        "homeassistant.config_entries.ConfigEntries.async_entries",
        return_value=[mock_config_entry],
    ):
        tool = SearchTvShow()
        result = await tool.async_call(
            hass,
            hass_llm.ToolInput(tool_name="SearchTvShow", tool_args={"query": "Only Show"}),
            hass_llm.LLMContext(platform="conversation", context=None, language="en", assistant=None, device_id=None),
        )

    assert "results" in result
    assert len(result["results"]) == 1
    assert result["results"][0]["title"] == "Only Show"


async def test_search_tv_show_detail_api_error(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test SearchTvShow handles detail API failure gracefully."""
    aioclient_mock.get(
        f"{TMDB_BASE_URL}/search/tv",
        json={
            "page": 1,
            "results": [
                {
                    "id": 67890,
                    "name": "Good Show",
                    "first_air_date": "2023-06-15",
                    "vote_average": 9.0,
                    "overview": "A great show.",
                },
                {
                    "id": 67891,
                    "name": "Bad Show",
                    "first_air_date": "2022-01-10",
                    "vote_average": 8.5,
                    "overview": "Another show.",
                },
            ],
        },
    )
    aioclient_mock.get(
        f"{TMDB_BASE_URL}/tv/67890",
        json={
            "id": 67890,
            "name": "Good Show",
            "number_of_seasons": 3,
            "credits": {
                "cast": [
                    {"id": 1, "name": "Actor One", "character": "Character 1"},
                ],
            },
        },
    )
    aioclient_mock.get(
        f"{TMDB_BASE_URL}/tv/67891",
        status=404,
    )

    with patch(
        "homeassistant.config_entries.ConfigEntries.async_entries",
        return_value=[mock_config_entry],
    ):
        tool = SearchTvShow()
        result = await tool.async_call(
            hass,
            hass_llm.ToolInput(tool_name="SearchTvShow", tool_args={"query": "Test"}),
            hass_llm.LLMContext(platform="conversation", context=None, language="en", assistant=None, device_id=None),
        )

    assert "results" in result
    assert len(result["results"]) == 2
    assert result["results"][0]["cast"] == ["Actor One"]
    assert result["results"][0]["season_count"] == 3
    assert result["results"][1]["cast"] == []
    assert result["results"][1]["season_count"] == "Unknown"


async def test_request_movie_tool_success(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test RequestMovie tool creates a Seerr request."""
    _mock_seerr_movie_not_found(aioclient_mock)
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
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test RequestMovie tool returns error dict on Seerr API failure."""
    _mock_seerr_movie_not_found(aioclient_mock)
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


async def test_search_movie_tool_no_release_date(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    mock_config_entry: MockConfigEntry,
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

    assert "results" in result
    assert len(result["results"]) == 1
    assert result["results"][0]["title"] == "Upcoming Movie"
    assert result["results"][0]["year"] == "Unknown"
    assert result["results"][0]["rating"] == "N/A"
    assert result["results"][0]["cast"] == []


async def test_search_movie_fewer_than_five_results(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test SearchMovie handles fewer than 5 results."""
    aioclient_mock.get(
        f"{TMDB_BASE_URL}/search/movie",
        json={
            "page": 1,
            "results": [
                {
                    "id": 12345,
                    "title": "Only Movie",
                    "release_date": "2024-06-15",
                    "vote_average": 8.5,
                    "overview": "A great movie.",
                },
            ],
        },
    )
    aioclient_mock.get(
        f"{TMDB_BASE_URL}/movie/12345",
        json={
            "id": 12345,
            "title": "Only Movie",
            "release_date": "2024-06-15",
            "vote_average": 8.5,
            "overview": "A test movie overview.",
            "credits": {
                "cast": [
                    {"id": 1, "name": "Actor One", "character": "Character 1"},
                    {"id": 2, "name": "Actor Two", "character": "Character 2"},
                ],
            },
        },
    )

    with patch(
        "homeassistant.config_entries.ConfigEntries.async_entries",
        return_value=[mock_config_entry],
    ):
        tool = SearchMovie()
        result = await tool.async_call(
            hass,
            hass_llm.ToolInput(tool_name="SearchMovie", tool_args={"query": "Only Movie"}),
            hass_llm.LLMContext(platform="conversation", context=None, language="en", assistant=None, device_id=None),
        )

    assert "results" in result
    assert len(result["results"]) == 1
    assert result["results"][0]["title"] == "Only Movie"


async def test_search_movie_detail_api_error(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test SearchMovie handles detail API failure gracefully."""
    aioclient_mock.get(
        f"{TMDB_BASE_URL}/search/movie",
        json={
            "page": 1,
            "results": [
                {
                    "id": 12345,
                    "title": "Good Movie",
                    "release_date": "2024-01-01",
                    "vote_average": 8.5,
                    "overview": "A great movie.",
                },
                {
                    "id": 12346,
                    "title": "Bad Movie",
                    "release_date": "2023-05-15",
                    "vote_average": 7.0,
                    "overview": "Another movie.",
                },
            ],
        },
    )
    aioclient_mock.get(
        f"{TMDB_BASE_URL}/movie/12345",
        json={
            "id": 12345,
            "title": "Good Movie",
            "credits": {
                "cast": [
                    {"id": 1, "name": "Actor One", "character": "Character 1"},
                ],
            },
        },
    )
    aioclient_mock.get(
        f"{TMDB_BASE_URL}/movie/12346",
        status=404,
    )

    with patch(
        "homeassistant.config_entries.ConfigEntries.async_entries",
        return_value=[mock_config_entry],
    ):
        tool = SearchMovie()
        result = await tool.async_call(
            hass,
            hass_llm.ToolInput(tool_name="SearchMovie", tool_args={"query": "Test"}),
            hass_llm.LLMContext(platform="conversation", context=None, language="en", assistant=None, device_id=None),
        )

    assert "results" in result
    assert len(result["results"]) == 2
    assert result["results"][0]["cast"] == ["Actor One"]
    assert result["results"][1]["cast"] == []

async def test_request_movie_tool_connection_error(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test RequestMovie returns error dict on Seerr connection failure."""
    import aiohttp

    _mock_seerr_movie_not_found(aioclient_mock)
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


async def test_request_tv_show_tool_success(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test RequestTvShow tool creates a Seerr request for all seasons."""
    _mock_seerr_tv_not_found(aioclient_mock)
    _mock_tmdb_tv_details(aioclient_mock)
    _mock_seerr_tv_request(aioclient_mock)

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
    _mock_seerr_tv_not_found(aioclient_mock)
    _mock_tmdb_tv_details(aioclient_mock)
    _mock_seerr_tv_request(aioclient_mock)

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
    _mock_seerr_tv_not_found(aioclient_mock)
    _mock_tmdb_tv_details(aioclient_mock)
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
    import aiohttp

    _mock_seerr_tv_not_found(aioclient_mock)
    _mock_tmdb_tv_details(aioclient_mock)
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


# -- RequestMovie: existing request checks --

async def test_request_movie_already_available(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test RequestMovie returns already_available when media is in library."""
    _mock_seerr_movie_available(aioclient_mock)

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
    _mock_seerr_movie_requested(aioclient_mock)

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
    _mock_seerr_movie_declined(aioclient_mock)
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
    assert "Request created" in result["message"]
    assert result["tmdb_id"] == 12345


async def test_request_movie_seerr_media_not_found(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test RequestMovie falls back to TMDB when Seerr media not found."""
    _mock_seerr_movie_not_found(aioclient_mock)
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


async def test_request_movie_seerr_connection_error(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test RequestMovie falls back to TMDB on Seerr connection error."""
    import aiohttp

    aioclient_mock.get(
        "http://localhost:5055/api/v1/movie/12345",
        exc=aiohttp.ClientError,
    )
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


# -- RequestTvShow: existing request checks --

async def test_request_tv_show_already_available(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test RequestTvShow returns already_available when media is in library."""
    _mock_seerr_tv_available(aioclient_mock)

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
    _mock_seerr_tv_requested(aioclient_mock)

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
    _mock_seerr_tv_declined(aioclient_mock)
    _mock_seerr_tv_request(aioclient_mock)

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
    _mock_seerr_tv_not_found(aioclient_mock)
    _mock_tmdb_tv_details(aioclient_mock)
    _mock_seerr_tv_request(aioclient_mock)

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
    import aiohttp

    aioclient_mock.get(
        "http://localhost:5055/api/v1/tv/67890",
        exc=aiohttp.ClientError,
    )
    _mock_tmdb_tv_details(aioclient_mock)
    _mock_seerr_tv_request(aioclient_mock)

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
