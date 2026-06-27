"""LLM tools for TMDB search and Seerr requests."""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

import aiohttp
import voluptuous as vol
from homeassistant.helpers import aiohttp_client, llm

from .const import (
    DOMAIN,
    TMDB_BASE_URL,
    SeerrLlmConfigEntryData,
)
from .exceptions import NoResultsError, TmdbApiError

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant
    from homeassistant.util.json import JsonObjectType

_LOGGER = logging.getLogger(__name__)

_SEERR_MEDIA_STATUS_AVAILABLE = 5
_SEERR_REQUEST_STATUS_DECLINED = 3


async def _check_seerr_media(
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

    if media_info.get("status") == _SEERR_MEDIA_STATUS_AVAILABLE:
        return title, "already_available"

    requests = media_info.get("requests", [])
    for req in requests:
        if req.get("status") != _SEERR_REQUEST_STATUS_DECLINED:
            return title, "already_requested"

    return title, None


async def _tmdb_request(
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


async def _tmdb_search(
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
    data = await _tmdb_request(session, tmdb_api_key, url, params)

    if not data.get("results"):
        raise NoResultsError(query)

    return data["results"][:limit]


async def _get_movie_title(
    session: aiohttp.ClientSession,
    tmdb_api_key: str,
    tmdb_id: int,
) -> dict[str, Any]:
    """Fetch movie details from TMDB by ID."""
    url = f"{TMDB_BASE_URL}/movie/{tmdb_id}"
    params = {
        "language": "en-US",
    }
    return await _tmdb_request(session, tmdb_api_key, url, params)


async def _get_movie_cast(
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
        data = await _tmdb_request(session, tmdb_api_key, url, params)
    except TmdbApiError:
        return []

    cast = data.get("credits", {}).get("cast", [])
    return [member["name"] for member in cast[:2] if "name" in member]


async def _get_tv_show_title(
    session: aiohttp.ClientSession,
    tmdb_api_key: str,
    tmdb_id: int,
) -> dict[str, Any]:
    """Fetch TV show details from TMDB by ID."""
    url = f"{TMDB_BASE_URL}/tv/{tmdb_id}"
    params = {
        "language": "en-US",
    }
    return await _tmdb_request(session, tmdb_api_key, url, params)


async def _get_tv_show_details(
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
        data = await _tmdb_request(session, tmdb_api_key, url, params)
    except TmdbApiError:
        return [], 0

    cast = data.get("credits", {}).get("cast", [])
    cast_names = [member["name"] for member in cast[:2] if "name" in member]
    season_count = data.get("number_of_seasons", 0)
    return cast_names, season_count


def _get_runtime_data(hass: HomeAssistant) -> SeerrLlmConfigEntryData:
    """Get runtime data from the config entry."""
    entries = hass.config_entries.async_entries(DOMAIN)
    entry = entries[0]
    return entry.runtime_data  # type: ignore[no-any-return]


class SearchMovie(llm.Tool):
    """Search for a movie by title."""

    name = "SearchMovie"
    description = "Search for a movie by title and return up to 5 matching results with details including TMDB IDs."
    parameters = vol.Schema({
        vol.Required("query"): str,
    })

    async def async_call(
        self,
        hass: HomeAssistant,
        tool_input: llm.ToolInput,
        llm_context: llm.LLMContext,
    ) -> JsonObjectType:
        config = _get_runtime_data(hass)
        session = aiohttp_client.async_get_clientsession(hass)
        query = tool_input.tool_args["query"]

        try:
            results = await _tmdb_search(
                session, config.tmdb_api_key, "search/movie", query, limit=5,
            )
        except NoResultsError as err:
            return {"error": str(err)}
        except TmdbApiError as err:
            return {"error": str(err)}

        search_results = []
        for result in results:
            release_date = result.get("release_date", "")
            year = release_date[:4] if release_date else "Unknown"

            cast = await _get_movie_cast(
                session, config.tmdb_api_key, result.get("id", 0),
            )

            search_results.append({
                "title": result.get("title", "Unknown"),
                "year": year,
                "overview": result.get("overview", "No overview available."),
                "rating": round(result.get("vote_average", 0), 1) if result.get("vote_average") else "N/A",
                "cast": cast,
                "type": "movie",
                "tmdb_id": result.get("id"),
            })

        return {
            "results": search_results,
        }


class SearchTvShow(llm.Tool):
    """Search for a TV show by title."""

    name = "SearchTvShow"
    description = "Search for a TV show by title and return up to 5 matching results with details including TMDB IDs."
    parameters = vol.Schema({
        vol.Required("query"): str,
    })

    async def async_call(
        self,
        hass: HomeAssistant,
        tool_input: llm.ToolInput,
        llm_context: llm.LLMContext,
    ) -> JsonObjectType:
        config = _get_runtime_data(hass)
        session = aiohttp_client.async_get_clientsession(hass)
        query = tool_input.tool_args["query"]

        try:
            results = await _tmdb_search(
                session, config.tmdb_api_key, "search/tv", query, limit=5,
            )
        except NoResultsError as err:
            return {"error": str(err)}
        except TmdbApiError as err:
            return {"error": str(err)}

        search_results = []
        for result in results:
            first_air_date = result.get("first_air_date", "")
            year = first_air_date[:4] if first_air_date else "Unknown"

            cast, season_count = await _get_tv_show_details(
                session, config.tmdb_api_key, result.get("id", 0),
            )

            search_results.append({
                "title": result.get("name", "Unknown"),
                "year": year,
                "overview": result.get("overview", "No overview available."),
                "rating": round(result.get("vote_average", 0), 1) if result.get("vote_average") else "N/A",
                "cast": cast,
                "season_count": season_count or "Unknown",
                "type": "tvshow",
                "tmdb_id": result.get("id"),
            })

        return {
            "results": search_results,
        }


class RequestMovie(llm.Tool):
    """Request a movie via Seerr using its TMDB ID."""

    name = "RequestMovie"
    description = "Request a movie to be added via Seerr. Requires the TMDB ID of the movie."
    parameters = vol.Schema({
        vol.Required("tmdb_id"): int,
    })

    async def async_call(
        self,
        hass: HomeAssistant,
        tool_input: llm.ToolInput,
        llm_context: llm.LLMContext,
    ) -> JsonObjectType:
        config = _get_runtime_data(hass)
        tmdb_id = tool_input.tool_args["tmdb_id"]
        session = aiohttp_client.async_get_clientsession(hass)

        seerr_title, existing_status = await _check_seerr_media(
            session, config.seerr_url, config.seerr_api_key, "movie", tmdb_id,
        )

        if existing_status == "already_available":
            return {
                "status": "already_available",
                "message": f"'{seerr_title}' is already available.",
                "tmdb_id": tmdb_id,
            }

        if existing_status == "already_requested":
            return {
                "status": "already_requested",
                "message": f"'{seerr_title}' has already been requested.",
                "tmdb_id": tmdb_id,
            }

        title: str | None = seerr_title
        if title is None:
            try:
                movie_data = await _get_movie_title(session, config.tmdb_api_key, tmdb_id)
                title = movie_data.get("title", f"Movie (TMDB ID: {tmdb_id})")
            except TmdbApiError:
                title = f"Movie (TMDB ID: {tmdb_id})"

        url = f"{config.seerr_url}/api/v1/request"
        headers = {
            "X-Api-Key": config.seerr_api_key,
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        payload = {
            "mediaType": "movie",
            "mediaId": tmdb_id,
        }

        try:
            async with session.post(
                url, headers=headers, json=payload, timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                if resp.status in (200, 201):
                    return {
                        "status": "success",
                        "message": f"Request created for '{title}'.",
                        "tmdb_id": tmdb_id,
                    }
                body = await resp.text()
                return {"error": f"Seerr API error {resp.status}: {body}"}
        except aiohttp.ClientError as err:
            return {"error": f"Unable to connect to Seerr: {err}"}


class RequestTvShow(llm.Tool):
    """Request a TV show via Seerr using its TMDB ID."""

    name = "RequestTvShow"
    description = (
        "Request a TV show to be added via Seerr. Requires the TMDB ID of the show. "
        "By default, requests all seasons. Optionally specify a list of season numbers."
    )
    parameters = vol.Schema({
        vol.Required("tmdb_id"): int,
        vol.Optional("seasons"): vol.Any(str, [int]),
    })

    async def async_call(
        self,
        hass: HomeAssistant,
        tool_input: llm.ToolInput,
        llm_context: llm.LLMContext,
    ) -> JsonObjectType:
        config = _get_runtime_data(hass)
        tmdb_id = tool_input.tool_args["tmdb_id"]
        seasons = tool_input.tool_args.get("seasons", "all")
        session = aiohttp_client.async_get_clientsession(hass)

        seerr_title, existing_status = await _check_seerr_media(
            session, config.seerr_url, config.seerr_api_key, "tv", tmdb_id,
        )

        if existing_status == "already_available":
            return {
                "status": "already_available",
                "message": f"'{seerr_title}' is already available.",
                "tmdb_id": tmdb_id,
            }

        if existing_status == "already_requested":
            return {
                "status": "already_requested",
                "message": f"'{seerr_title}' has already been requested.",
                "tmdb_id": tmdb_id,
            }

        title: str | None = seerr_title
        if title is None:
            try:
                tv_data = await _get_tv_show_title(session, config.tmdb_api_key, tmdb_id)
                title = tv_data.get("name", f"TV Show (TMDB ID: {tmdb_id})")
            except TmdbApiError:
                title = f"TV Show (TMDB ID: {tmdb_id})"

        url = f"{config.seerr_url}/api/v1/request"
        headers = {
            "X-Api-Key": config.seerr_api_key,
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        payload: dict[str, Any] = {
            "mediaType": "tv",
            "mediaId": tmdb_id,
            "seasons": seasons,
        }

        try:
            async with session.post(
                url, headers=headers, json=payload, timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                if resp.status in (200, 201):
                    return {
                        "status": "success",
                        "message": f"Request created for '{title}'.",
                        "tmdb_id": tmdb_id,
                    }
                body = await resp.text()
                return {"error": f"Seerr API error {resp.status}: {body}"}
        except aiohttp.ClientError as err:
            return {"error": f"Unable to connect to Seerr: {err}"}


class SeerrLlmAPI(llm.API):
    """LLM API that exposes TMDB search and Seerr request tools."""

    id = DOMAIN
    name = "Seerr LLM Tools"

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(hass=hass, id=f"{DOMAIN}-{entry.entry_id}", name=entry.title)

    async def async_get_api_instance(
        self, llm_context: llm.LLMContext,
    ) -> llm.APIInstance:
        return llm.APIInstance(
            api=self,
            api_prompt=(
                "When a user requests to download a movie, use SearchMovie to look up media details. "
                "When a user requests a TV show, use SearchTvShow to look up details. "
                "SearchMovie returns up to 5 matching results. Present only the first result to the user "
                "before taking further action. "
                "SearchTvShow returns up to 5 matching results. Present only the first result to the user "
                "before taking further action. "
                "Repeat back the release year and the main cast for clarity. "
                "Require confirmation they want to download the media after presenting info. "
                "If they reject the confirmation. Tell the user you need more info to narrow the "
                "request, such as release year or a cast member. "
                "For movies, use RequestMovie with the tmdb_id from the search result. "
                "For TV shows, use RequestTvShow with the tmdb_id. By default, request all seasons "
                "unless the user specifies particular seasons. "
                "RequestMovie and RequestTvShow may return status 'already_available' if the media "
                "is already in the library, or 'already_requested' if it has been requested before. "
                "Handle these gracefully by informing the user of the current status."
            ),
            llm_context=llm_context,
            tools=[
                SearchMovie(),
                SearchTvShow(),
                RequestMovie(),
                RequestTvShow(),
            ],
        )
