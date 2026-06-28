"""LLM tools for searching TV shows."""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

import voluptuous as vol
from homeassistant.helpers import aiohttp_client, llm

from custom_components.seerr_llm.api_client import get_tv_show_details, tmdb_search
from custom_components.seerr_llm.const import DOMAIN, SeerrLlmConfigEntryData
from custom_components.seerr_llm.exceptions import NoResultsError, TmdbApiError

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.util.json import JsonObjectType


def _get_runtime_data(hass: HomeAssistant) -> SeerrLlmConfigEntryData:
    """Get runtime data from the config entry."""
    entries = hass.config_entries.async_entries(DOMAIN)
    entry = entries[0]
    return entry.runtime_data  # type: ignore[no-any-return]


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
            results = await tmdb_search(
                session, config.tmdb_api_key, "search/tv", query, limit=5,
            )
        except NoResultsError as err:
            return {"error": str(err)}
        except TmdbApiError as err:
            return {"error": str(err)}

        search_results: list[dict[str, Any]] = []
        for result in results:
            first_air_date = result.get("first_air_date", "")
            year = first_air_date[:4] if first_air_date else "Unknown"

            cast, season_count = await get_tv_show_details(
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
