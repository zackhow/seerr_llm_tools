"""Constants for Seerr LLM integration."""
from __future__ import annotations

from dataclasses import dataclass

DOMAIN = "seerr_llm"

CONF_TMDB_API_KEY = "tmdb_api_key"
CONF_SEERR_URL = "seerr_url"
CONF_SEERR_API_KEY = "seerr_api_key"

TMDB_BASE_URL = "https://api.themoviedb.org/3"


@dataclass(frozen=True, kw_only=True)
class SeerrLlmConfigEntryData:
    """Runtime data for Seerr LLM config entry."""

    tmdb_api_key: str
    seerr_url: str
    seerr_api_key: str
