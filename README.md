# Seerr LLM Tools

Home Assistant custom integration that exposes TMDB search and Seerr request tools for HA assist pipelines.

## Features

- Search for movies and TV shows via TMDB
- Request media through Seerr(movie only for atm)

## Installation
### Install via HACS (recommended)
Click to install seerr_llm_tools via HACS:  
[![image](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=zackhow&repository=seerr_llm_tools&category=integration)

### Manual Installation
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
