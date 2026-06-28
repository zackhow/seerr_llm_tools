"""LLM tools for TMDB search and Seerr requests."""
from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.helpers import llm

from .const import DOMAIN
from .tools import RequestMovie, RequestTvShow, SearchMovie, SearchTvShow

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant


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
