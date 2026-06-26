# Seerr LLM Tools

Home Assistant custom integration that exposes TMDB search and Seerr request tools for LLM voice pipelines.

## Features

- Search for movies and TV shows via TMDB
- Request media through Seerr
- Powered by Home Assistant's LLM integration

## Installation

1. Copy `custom_components/seerr_llm` to your Home Assistant `custom_components` directory
2. Restart Home Assistant
3. Add integration via UI: Settings > Devices & Services > Add Integration > "SeerrLLM Tools"

## Testing

### Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install homeassistant pytest pytest-homeassistant-custom-component aioresponses
```

### Run Tests

```bash
source .venv/bin/activate
python -m pytest tests/ -v
```

### Run Lint

```bash
source .venv/bin/activate
ruff check custom_components/ tests/
```

## License

MIT
