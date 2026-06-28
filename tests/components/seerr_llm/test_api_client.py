"""Tests for TMDB and Seerr API client functions."""
from __future__ import annotations

import asyncio

import pytest
from pytest_homeassistant_custom_component.test_util.aiohttp import (
    AiohttpClientMocker,
)

from custom_components.seerr_llm.api_client import (
    get_movie_cast,
    get_movie_title,
    get_tv_show_details,
    get_tv_show_title,
    tmdb_request,
    tmdb_search,
)
from custom_components.seerr_llm.const import TMDB_BASE_URL
from custom_components.seerr_llm.exceptions import NoResultsError, TmdbApiError


async def test_tmdb_request_success(
    aioclient_mock: AiohttpClientMocker,
) -> None:
    """Test successful TMDB API request."""
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

    loop = asyncio.get_running_loop()
    session = aioclient_mock.create_session(loop)
    result = await tmdb_request(
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
        await tmdb_request(
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
    result = await tmdb_search(
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
        await tmdb_search(
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

    loop = asyncio.get_running_loop()
    session = aioclient_mock.create_session(loop)
    result = await get_movie_title(
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
    result = await get_movie_cast(
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
    result = await get_movie_cast(
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
    result = await get_movie_cast(
        session,
        "test-key",
        12345,
    )

    assert result == []


async def test_get_tv_show_title(
    aioclient_mock: AiohttpClientMocker,
) -> None:
    """Test fetching TV show title by TMDB ID."""
    aioclient_mock.get(
        f"{TMDB_BASE_URL}/tv/67890",
        json={
            "id": 67890,
            "name": "Test TV Show",
            "first_air_date": "2023-06-15",
            "vote_average": 9.0,
            "overview": "A test TV show overview.",
            "number_of_seasons": 3,
        },
    )

    loop = asyncio.get_running_loop()
    session = aioclient_mock.create_session(loop)
    result = await get_tv_show_title(
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
    result = await get_tv_show_details(
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
    result = await get_tv_show_details(
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
    result = await get_tv_show_details(
        session,
        "test-key",
        67890,
    )

    assert result == ([], 0)
