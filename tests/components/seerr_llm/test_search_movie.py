"""Tests for SearchMovie LLM tool."""
from __future__ import annotations

from unittest.mock import patch

from homeassistant.core import HomeAssistant
from homeassistant.helpers import llm as hass_llm
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import (
    AiohttpClientMocker,
)

from custom_components.seerr_llm.const import TMDB_BASE_URL
from custom_components.seerr_llm.tools.movie import SearchMovie

from .conftest import (
    mock_tmdb_movies_with_cast_all,
    mock_tmdb_search_movie,
)


async def test_search_movie_tool_success(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test SearchMovie tool returns multiple movie results."""
    mock_tmdb_search_movie(aioclient_mock)
    mock_tmdb_movies_with_cast_all(aioclient_mock)

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
