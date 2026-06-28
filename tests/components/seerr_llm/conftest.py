"""Shared fixtures and mock responses for Seerr LLM Tools tests."""
from .fixtures import VALID_CONFIG, VALID_CONFIG_FLOW_INPUT, mock_config_entry  # noqa: F401
from .mocks.seerr import (  # noqa: F401
    mock_seerr_auth,
    mock_seerr_movie_available,
    mock_seerr_movie_declined,
    mock_seerr_movie_not_found,
    mock_seerr_movie_requested,
    mock_seerr_request,
    mock_seerr_tv_available,
    mock_seerr_tv_declined,
    mock_seerr_tv_not_found,
    mock_seerr_tv_request,
    mock_seerr_tv_requested,
)
from .mocks.tmdb import (  # noqa: F401
    mock_tmdb_movie_details,
    mock_tmdb_movie_with_cast,
    mock_tmdb_movies_with_cast_all,
    mock_tmdb_popular,
    mock_tmdb_search_movie,
    mock_tmdb_search_tv,
    mock_tmdb_tv_details,
    mock_tmdb_tv_details_all,
    mock_tmdb_tv_with_cast,
)
