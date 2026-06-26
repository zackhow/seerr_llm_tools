"""Constants for Seerr LLM integration."""
from __future__ import annotations

from dataclasses import dataclass

DOMAIN = "seerr_llm"

CONF_DEF_TMDB_API_KEY="eyJhbGciOiJIUzI1NiJ9.eyJhdWQiOiJiYjc1Nzc2NTc4NmFjMTQ1OWM0YjE4OWNjZGRiNzUyMCIsIm5iZiI6MTc4MTk5ODI3Mi40NTgsInN1YiI6IjZhMzcyMmMwZjkzMGQ1ZWY5NTIzYmVhZiIsInNjb3BlcyI6WyJhcGlfcmVhZCJdLCJ2ZXJzaW9uIjoxfQ.ChQ_p15G7v83jj8RYAMpwt7H0jam-8qzVz02-GJh2ko"
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
