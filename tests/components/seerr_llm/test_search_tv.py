"""Tests for SearchTvShow LLM tool."""
from __future__ import annotations

from unittest.mock import patch

from homeassistant.core import HomeAssistant
from homeassistant.helpers import llm as hass_llm
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import (
    AiohttpClientMocker,
)

from custom_components.seerr_llm.const import TMDB_BASE_URL
from custom_components.seerr_llm.tools.tv import SearchTvShow

from .conftest import (
    mock_tmdb_search_tv,
    mock_tmdb_tv_details_all,
)


async def test_search_tv_show_tool_success(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Test SearchTvShow tool returns multiple TV show results."""
    mock_tmdb_search_tv(aioclient_mock)
    mock_tmdb_tv_details_all(aioclient_mock)

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
