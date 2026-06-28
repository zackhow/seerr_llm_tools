"""Custom exceptions for Seerr LLM integration."""


class SeerrLlmError(Exception):
    """Base exception for Seerr LLM integration."""


class TmdbApiError(SeerrLlmError):
    """Exception raised when TMDB API request fails."""

    def __init__(self, status: int, message: str) -> None:
        super().__init__(f"TMDB API error {status}: {message}")
        self.status = status
        self.message = message


class NoResultsError(SeerrLlmError):
    """Exception raised when no results are found."""

    def __init__(self, query: str) -> None:
        super().__init__(f"No results found for '{query}'")
        self.query = query
