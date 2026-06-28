"""Mock Seerr API responses for testing."""
from __future__ import annotations

from pytest_homeassistant_custom_component.test_util.aiohttp import (
    AiohttpClientMocker,
)


def mock_seerr_auth(aioclient_mock: AiohttpClientMocker) -> None:
    """Mock successful Seerr auth check response."""
    aioclient_mock.get(
        "http://localhost:5055/api/v1/auth/me",
        json={"id": 1, "email": "test@example.com", "name": "Test User"},
    )


def mock_seerr_request(aioclient_mock: AiohttpClientMocker) -> None:
    """Mock successful Seerr movie request response."""
    aioclient_mock.post(
        "http://localhost:5055/api/v1/request",
        json={"id": 999, "status": "requested"},
        status=201,
    )


def mock_seerr_tv_request(aioclient_mock: AiohttpClientMocker) -> None:
    """Mock successful Seerr TV show request response."""
    aioclient_mock.post(
        "http://localhost:5055/api/v1/request",
        json={"id": 1000, "status": "requested"},
        status=201,
    )


def mock_seerr_movie_available(aioclient_mock: AiohttpClientMocker) -> None:
    """Mock Seerr movie details with media already available."""
    aioclient_mock.get(
        "http://localhost:5055/api/v1/movie/12345",
        json={
            "id": 1,
            "tmdbId": 12345,
            "title": "Test Movie",
            "mediaInfo": {
                "id": 1,
                "tmdbId": 12345,
                "status": 5,
                "requests": [],
            },
        },
    )


def mock_seerr_movie_requested(aioclient_mock: AiohttpClientMocker) -> None:
    """Mock Seerr movie details with pending request."""
    aioclient_mock.get(
        "http://localhost:5055/api/v1/movie/12345",
        json={
            "id": 1,
            "tmdbId": 12345,
            "title": "Test Movie",
            "mediaInfo": {
                "id": 1,
                "tmdbId": 12345,
                "status": 2,
                "requests": [
                    {"id": 1, "status": 1, "media": {"tmdbId": 12345}},
                ],
            },
        },
    )


def mock_seerr_movie_declined(aioclient_mock: AiohttpClientMocker) -> None:
    """Mock Seerr movie details with only declined request."""
    aioclient_mock.get(
        "http://localhost:5055/api/v1/movie/12345",
        json={
            "id": 1,
            "tmdbId": 12345,
            "title": "Test Movie",
            "mediaInfo": {
                "id": 1,
                "tmdbId": 12345,
                "status": 1,
                "requests": [
                    {"id": 1, "status": 3, "media": {"tmdbId": 12345}},
                ],
            },
        },
    )


def mock_seerr_movie_not_found(aioclient_mock: AiohttpClientMocker) -> None:
    """Mock Seerr movie not found (404)."""
    aioclient_mock.get(
        "http://localhost:5055/api/v1/movie/12345",
        status=404,
    )


def mock_seerr_tv_available(aioclient_mock: AiohttpClientMocker) -> None:
    """Mock Seerr TV show details with media already available."""
    aioclient_mock.get(
        "http://localhost:5055/api/v1/tv/67890",
        json={
            "id": 1,
            "tmdbId": 67890,
            "name": "Test TV Show",
            "mediaInfo": {
                "id": 1,
                "tmdbId": 67890,
                "status": 5,
                "requests": [],
            },
        },
    )


def mock_seerr_tv_requested(aioclient_mock: AiohttpClientMocker) -> None:
    """Mock Seerr TV show details with pending request."""
    aioclient_mock.get(
        "http://localhost:5055/api/v1/tv/67890",
        json={
            "id": 1,
            "tmdbId": 67890,
            "name": "Test TV Show",
            "mediaInfo": {
                "id": 1,
                "tmdbId": 67890,
                "status": 2,
                "requests": [
                    {"id": 1, "status": 1, "media": {"tmdbId": 67890}},
                ],
            },
        },
    )


def mock_seerr_tv_declined(aioclient_mock: AiohttpClientMocker) -> None:
    """Mock Seerr TV show details with only declined request."""
    aioclient_mock.get(
        "http://localhost:5055/api/v1/tv/67890",
        json={
            "id": 1,
            "tmdbId": 67890,
            "name": "Test TV Show",
            "mediaInfo": {
                "id": 1,
                "tmdbId": 67890,
                "status": 1,
                "requests": [
                    {"id": 1, "status": 3, "media": {"tmdbId": 67890}},
                ],
            },
        },
    )


def mock_seerr_tv_not_found(aioclient_mock: AiohttpClientMocker) -> None:
    """Mock Seerr TV show not found (404)."""
    aioclient_mock.get(
        "http://localhost:5055/api/v1/tv/67890",
        status=404,
    )
