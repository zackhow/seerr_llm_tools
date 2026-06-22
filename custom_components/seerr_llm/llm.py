"""LLM tools for TMDB search and Seerr requests."""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

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


def _get_timeout() -> object:
    """Get aiohttp ClientTimeout without top-level import."""
    import aiohttp  # noqa: PLC0415

    return aiohttp.ClientTimeout(total=10)


async def _tmdb_request(
    session,
    tmdb_api_key: str,
    url: str,
    params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Make an authenticated GET request to TMDB API."""
    headers = {
        "Authorization": f"Bearer {tmdb_api_key}",
    }
    async with session.get(
        url, headers=headers, params=params, timeout=_get_timeout(),
    ) as resp:
        if resp.status != 200:
            body = await resp.text()
            raise TmdbApiError(resp.status, body)
        return await resp.json()


async def _tmdb_search(
    session,
    tmdb_api_key: str,
    endpoint: str,
    query: str,
) -> dict[str, Any]:
    """Search TMDB and return the top result."""
    url = f"{TMDB_BASE_URL}/{endpoint}"
    params = {
        "query": query,
        "language": "en-US",
    }
    data = await _tmdb_request(session, tmdb_api_key, url, params)

    if not data.get("results"):
        raise NoResultsError(query)

    return data["results"][0]


async def _get_movie_title(
    session,
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
    session,
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


def _get_runtime_data(hass: HomeAssistant) -> SeerrLlmConfigEntryData:
    """Get runtime data from the config entry."""
    entries = hass.config_entries.async_entries(DOMAIN)
    entry = entries[0]
    return entry.runtime_data  # type: ignore[no-any-return]


class SearchMovie(llm.Tool):
    """Search for a movie by title."""

    name = "SearchMovie"
    description = "Search for a movie by title and return its details including the TMDB ID."
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
            result = await _tmdb_search(
                session, config.tmdb_api_key, "search/movie", query,
            )
        except NoResultsError as err:
            return {"error": str(err)}
        except TmdbApiError as err:
            return {"error": str(err)}

        release_date = result.get("release_date", "")
        year = release_date[:4] if release_date else "Unknown"

        cast = await _get_movie_cast(session, config.tmdb_api_key, result.get("id", 0))

        return {
            "title": result.get("title", "Unknown"),
            "year": year,
            "overview": result.get("overview", "No overview available."),
            "rating": round(result.get("vote_average", 0), 1) if result.get("vote_average") else "N/A",
            "cast": cast,
            "tmdb_id": result.get("id"),
        }


class SearchTvShow(llm.Tool):
    """Search for a TV show by title."""

    name = "SearchTvShow"
    description = "Search for a TV show by title and return its details including the TMDB ID."
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
            result = await _tmdb_search(
                session, config.tmdb_api_key, "search/tv", query,
            )
        except NoResultsError as err:
            return {"error": str(err)}
        except TmdbApiError as err:
            return {"error": str(err)}

        first_air_date = result.get("first_air_date", "")
        year = first_air_date[:4] if first_air_date else "Unknown"

        return {
            "title": result.get("name", "Unknown"),
            "year": year,
            "overview": result.get("overview", "No overview available."),
            "rating": round(result.get("vote_average", 0), 1) if result.get("vote_average") else "N/A",
            "tmdb_id": result.get("id"),
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

        title: str | None = None
        try:
            session = aiohttp_client.async_get_clientsession(hass)
            movie_data = await _get_movie_title(session, config.tmdb_api_key, tmdb_id)
            title = movie_data.get("title", f"Movie (TMDB ID: {tmdb_id})")
        except TmdbApiError:
            title = f"Movie (TMDB ID: {tmdb_id})"

        session = aiohttp_client.async_get_clientsession(hass)
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

        import aiohttp  # noqa: PLC0415

        try:
            async with session.post(
                url, headers=headers, json=payload, timeout=_get_timeout(),
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
                "When a user requests to download a movie, use SearchMovie or SearchTvShow to look up media details."
                "Always present the search results to the user before taking further action. "
                "Repeat back the movie release year and the main cast for clarity. "
                "Require confirmation they want to download a movie after presenting movie info."
                "Use RequestMovie with the tmdb_id from the search result to download the movie."
            ),
            llm_context=llm_context,
            tools=[
                SearchMovie(),
                SearchTvShow(),
                RequestMovie(),
            ],
        )
