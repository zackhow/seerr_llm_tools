"""LLM tools for requesting media via Seerr."""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

import aiohttp
import voluptuous as vol
from homeassistant.helpers import aiohttp_client, llm

from custom_components.seerr_llm.api_client import check_seerr_media, get_movie_title, get_tv_show_title
from custom_components.seerr_llm.const import DOMAIN, SeerrLlmConfigEntryData
from custom_components.seerr_llm.exceptions import TmdbApiError

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.util.json import JsonObjectType


def _get_runtime_data(hass: HomeAssistant) -> SeerrLlmConfigEntryData:
    """Get runtime data from the config entry."""
    entries = hass.config_entries.async_entries(DOMAIN)
    entry = entries[0]
    return entry.runtime_data  # type: ignore[no-any-return]


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

        seerr_title, existing_status = await check_seerr_media(
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
                movie_data = await get_movie_title(session, config.tmdb_api_key, tmdb_id)
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

        seerr_title, existing_status = await check_seerr_media(
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
                tv_data = await get_tv_show_title(session, config.tmdb_api_key, tmdb_id)
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
