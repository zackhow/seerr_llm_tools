"""Shared fixtures for Seerr LLM Tools integration tests."""
from __future__ import annotations

from typing import Any

import pytest
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
    SeerrLlmConfigEntryData,
)

VALID_CONFIG: dict[str, Any] = {
    CONF_TMDB_API_KEY: "test-tmdb-key",
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


def _mock_tmdb_popular(aioclient_mock: AiohttpClientMocker) -> None:
    """Mock successful TMDB popular movies response."""
    aioclient_mock.get(
        f"{TMDB_BASE_URL}/movie/popular",
        json={
            "page": 1,
            "results": [
                {
                    "id": 12345,
                    "title": "Test Movie",
                    "release_date": "2024-01-01",
                    "vote_average": 8.5,
                    "overview": "A test movie overview.",
                },
            ],
        },
    )


def _mock_tmdb_search_movie(aioclient_mock: AiohttpClientMocker) -> None:
    """Mock successful TMDB movie search response."""
    aioclient_mock.get(
        f"{TMDB_BASE_URL}/search/movie",
        json={
            "page": 1,
            "results": [
                {
                    "id": 12345,
                    "title": "Test Movie",
                    "release_date": "2024-01-01",
                    "vote_average": 8.5,
                    "overview": "A great movie.",
                },
            ],
        },
    )


def _mock_tmdb_search_tv(aioclient_mock: AiohttpClientMocker) -> None:
    """Mock successful TMDB TV search response."""
    aioclient_mock.get(
        f"{TMDB_BASE_URL}/search/tv",
        json={
            "page": 1,
            "results": [
                {
                    "id": 67890,
                    "name": "Test TV Show",
                    "first_air_date": "2023-06-15",
                    "vote_average": 9.0,
                    "overview": "A great show.",
                },
            ],
        },
    )


def _mock_tmdb_movie_details(aioclient_mock: AiohttpClientMocker) -> None:
    """Mock successful TMDB movie details response."""
    aioclient_mock.get(
        f"{TMDB_BASE_URL}/movie/12345",
        json={
            "id": 12345,
            "title": "Test Movie",
            "release_date": "2024-01-01",
            "vote_average": 8.5,
            "overview": "A test movie overview.",
        },
    )


def _mock_tmdb_movie_with_cast(aioclient_mock: AiohttpClientMocker) -> None:
    """Mock TMDB movie details with cast info."""
    aioclient_mock.get(
        f"{TMDB_BASE_URL}/movie/12345",
        json={
            "id": 12345,
            "title": "Test Movie",
            "release_date": "2024-01-01",
            "vote_average": 8.5,
            "overview": "A test movie overview.",
            "credits": {
                "cast": [
                    {"id": 1, "name": "Actor One", "character": "Character 1"},
                    {"id": 2, "name": "Actor Two", "character": "Character 2"},
                    {"id": 3, "name": "Actor Three", "character": "Character 3"},
                ],
            },
        },
    )


def _mock_seerr_auth(aioclient_mock: AiohttpClientMocker) -> None:
    """Mock successful Seerr auth check response."""
    aioclient_mock.get(
        "http://localhost:5055/api/v1/auth/me",
        json={"id": 1, "email": "test@example.com", "name": "Test User"},
    )


def _mock_seerr_request(aioclient_mock: AiohttpClientMocker) -> None:
    """Mock successful Seerr movie request response."""
    aioclient_mock.post(
        "http://localhost:5055/api/v1/request",
        json={"id": 999, "status": "requested"},
        status=201,
    )
