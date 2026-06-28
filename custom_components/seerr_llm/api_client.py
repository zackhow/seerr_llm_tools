"""API client helpers for TMDB and Seerr."""
from __future__ import annotations

import logging
from typing import Any

import aiohttp

from .const import (
    SEERR_MEDIA_STATUS_AVAILABLE,
    SEERR_REQUEST_STATUS_DECLINED,
    TMDB_BASE_URL,
)
from .exceptions import NoResultsError, TmdbApiError

_LOGGER = logging.getLogger(__name__)


async def tmdb_request(
    session: aiohttp.ClientSession,
    tmdb_api_key: str,
    url: str,
    params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Make an authenticated GET request to TMDB API."""
    headers = {
        "Authorization": f"Bearer {tmdb_api_key}",
    }
    async with session.get(
        url, headers=headers, params=params, timeout=aiohttp.ClientTimeout(total=10),
    ) as resp:
        if resp.status != 200:
            body = await resp.text()
            raise TmdbApiError(resp.status, body)
        return await resp.json()


async def tmdb_search(
    session: aiohttp.ClientSession,
    tmdb_api_key: str,
    endpoint: str,
    query: str,
    limit: int = 1,
) -> list[dict[str, Any]]:
    """Search TMDB and return results up to the specified limit."""
    url = f"{TMDB_BASE_URL}/{endpoint}"
    params = {
        "query": query,
        "language": "en-US",
    }
    data = await tmdb_request(session, tmdb_api_key, url, params)

    if not data.get("results"):
        raise NoResultsError(query)

    return data["results"][:limit]


async def get_movie_title(
    session: aiohttp.ClientSession,
    tmdb_api_key: str,
    tmdb_id: int,
) -> dict[str, Any]:
    """Fetch movie details from TMDB by ID."""
    url = f"{TMDB_BASE_URL}/movie/{tmdb_id}"
    params = {
        "language": "en-US",
    }
    return await tmdb_request(session, tmdb_api_key, url, params)


async def get_movie_cast(
    session: aiohttp.ClientSession,
    tmdb_api_key: str,
    tmdb_id: int,
) -> list[str]:
    """Fetch the first two cast members for a movie from TMDB."""
    url = f"{TMDB_BASE_URL}/movie/{tmdb_id}"
    params = {
        "language": "en-US",
        "append_to_response": "credits",
    }
    try:
        data = await tmdb_request(session, tmdb_api_key, url, params)
    except TmdbApiError:
        return []

    cast = data.get("credits", {}).get("cast", [])
    return [member["name"] for member in cast[:2] if "name" in member]


async def get_tv_show_title(
    session: aiohttp.ClientSession,
    tmdb_api_key: str,
    tmdb_id: int,
) -> dict[str, Any]:
    """Fetch TV show details from TMDB by ID."""
    url = f"{TMDB_BASE_URL}/tv/{tmdb_id}"
    params = {
        "language": "en-US",
    }
    return await tmdb_request(session, tmdb_api_key, url, params)


async def get_tv_show_details(
    session: aiohttp.ClientSession,
    tmdb_api_key: str,
    tmdb_id: int,
) -> tuple[list[str], int]:
    """Fetch cast and season count for a TV show from TMDB."""
    url = f"{TMDB_BASE_URL}/tv/{tmdb_id}"
    params = {
        "language": "en-US",
        "append_to_response": "credits",
    }
    try:
        data = await tmdb_request(session, tmdb_api_key, url, params)
    except TmdbApiError:
        return [], 0

    cast = data.get("credits", {}).get("cast", [])
    cast_names = [member["name"] for member in cast[:2] if "name" in member]
    season_count = data.get("number_of_seasons", 0)
    return cast_names, season_count


async def check_seerr_media(
    session: aiohttp.ClientSession,
    seerr_url: str,
    seerr_api_key: str,
    media_type: str,
    tmdb_id: int,
) -> tuple[str | None, str | None]:
    """
    Check if media already exists in Seerr and its request status.

    Returns (title, status) where status is one of:
    - 'already_available' if media is available
    - 'already_requested' if there's a pending/approved request
    - None if it's safe to proceed with a new request
    """
    title: str | None = None

    url = f"{seerr_url}/api/v1/{media_type}/{tmdb_id}"
    headers = {
        "X-Api-Key": seerr_api_key,
        "Accept": "application/json",
    }

    try:
        async with session.get(
            url, headers=headers, timeout=aiohttp.ClientTimeout(total=10),
        ) as resp:
            if resp.status == 404:
                return None, None
            if resp.status != 200:
                return None, None
            data = await resp.json()
    except aiohttp.ClientError:
        return None, None

    title = data.get("title") or data.get("name")
    media_info = data.get("mediaInfo", {})

    if media_info.get("status") == SEERR_MEDIA_STATUS_AVAILABLE:
        return title, "already_available"

    requests = media_info.get("requests", [])
    for req in requests:
        if req.get("status") != SEERR_REQUEST_STATUS_DECLINED:
            return title, "already_requested"

    return title, None
