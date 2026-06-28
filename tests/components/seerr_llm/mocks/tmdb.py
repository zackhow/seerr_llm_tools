"""Mock TMDB API responses for testing."""
from __future__ import annotations

from pytest_homeassistant_custom_component.test_util.aiohttp import (
    AiohttpClientMocker,
)

from custom_components.seerr_llm.const import TMDB_BASE_URL


def mock_tmdb_popular(aioclient_mock: AiohttpClientMocker) -> None:
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


def mock_tmdb_search_movie(aioclient_mock: AiohttpClientMocker) -> None:
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
                {
                    "id": 12346,
                    "title": "Test Movie 2",
                    "release_date": "2023-05-15",
                    "vote_average": 7.8,
                    "overview": "Another great movie.",
                },
                {
                    "id": 12347,
                    "title": "Test Movie 3",
                    "release_date": "2022-11-20",
                    "vote_average": 6.9,
                    "overview": "A third movie.",
                },
            ],
        },
    )


def mock_tmdb_search_tv(aioclient_mock: AiohttpClientMocker) -> None:
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
                {
                    "id": 67891,
                    "name": "Test TV Show 2",
                    "first_air_date": "2022-01-10",
                    "vote_average": 8.5,
                    "overview": "Another great show.",
                },
                {
                    "id": 67892,
                    "name": "Test TV Show 3",
                    "first_air_date": "2021-03-20",
                    "vote_average": 7.8,
                    "overview": "A third show.",
                },
            ],
        },
    )


def mock_tmdb_tv_details_all(aioclient_mock: AiohttpClientMocker) -> None:
    """Mock TMDB TV show details for all searched shows."""
    aioclient_mock.get(
        f"{TMDB_BASE_URL}/tv/67890",
        json={
            "id": 67890,
            "name": "Test TV Show",
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
    aioclient_mock.get(
        f"{TMDB_BASE_URL}/tv/67891",
        json={
            "id": 67891,
            "name": "Test TV Show 2",
            "first_air_date": "2022-01-10",
            "vote_average": 8.5,
            "overview": "Another test TV show.",
            "number_of_seasons": 2,
            "credits": {
                "cast": [
                    {"id": 3, "name": "Actor Three", "character": "Character 3"},
                    {"id": 4, "name": "Actor Four", "character": "Character 4"},
                ],
            },
        },
    )
    aioclient_mock.get(
        f"{TMDB_BASE_URL}/tv/67892",
        json={
            "id": 67892,
            "name": "Test TV Show 3",
            "first_air_date": "2021-03-20",
            "vote_average": 7.8,
            "overview": "A third test TV show.",
            "number_of_seasons": 1,
            "credits": {
                "cast": [
                    {"id": 5, "name": "Actor Five", "character": "Character 5"},
                    {"id": 6, "name": "Actor Six", "character": "Character 6"},
                ],
            },
        },
    )


def mock_tmdb_movie_details(aioclient_mock: AiohttpClientMocker) -> None:
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


def mock_tmdb_movie_with_cast(aioclient_mock: AiohttpClientMocker) -> None:
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


def mock_tmdb_movies_with_cast_all(aioclient_mock: AiohttpClientMocker) -> None:
    """Mock TMDB movie details with cast info for all searched movies."""
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
                ],
            },
        },
    )
    aioclient_mock.get(
        f"{TMDB_BASE_URL}/movie/12346",
        json={
            "id": 12346,
            "title": "Test Movie 2",
            "release_date": "2023-05-15",
            "vote_average": 7.8,
            "overview": "Another test movie.",
            "credits": {
                "cast": [
                    {"id": 3, "name": "Actor Three", "character": "Character 3"},
                    {"id": 4, "name": "Actor Four", "character": "Character 4"},
                ],
            },
        },
    )
    aioclient_mock.get(
        f"{TMDB_BASE_URL}/movie/12347",
        json={
            "id": 12347,
            "title": "Test Movie 3",
            "release_date": "2022-11-20",
            "vote_average": 6.9,
            "overview": "A third test movie.",
            "credits": {
                "cast": [
                    {"id": 5, "name": "Actor Five", "character": "Character 5"},
                    {"id": 6, "name": "Actor Six", "character": "Character 6"},
                ],
            },
        },
    )


def mock_tmdb_tv_details(aioclient_mock: AiohttpClientMocker) -> None:
    """Mock successful TMDB TV show details response."""
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


def mock_tmdb_tv_with_cast(aioclient_mock: AiohttpClientMocker) -> None:
    """Mock TMDB TV show details with cast info."""
    aioclient_mock.get(
        f"{TMDB_BASE_URL}/tv/67890",
        json={
            "id": 67890,
            "name": "Test TV Show",
            "first_air_date": "2023-06-15",
            "vote_average": 9.0,
            "overview": "A test TV show overview.",
            "number_of_seasons": 3,
            "credits": {
                "cast": [
                    {"id": 1, "name": "Actor One", "character": "Character 1"},
                    {"id": 2, "name": "Actor Two", "character": "Character 2"},
                    {"id": 3, "name": "Actor Three", "character": "Character 3"},
                ],
            },
        },
    )
