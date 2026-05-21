from __future__ import annotations

import os
import pathlib

import pytest


def _load_dotenv(path):
    p = pathlib.Path(path)
    if not p.is_file():
        return
    for raw in p.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        key, _, val = line.partition('=')
        key = key.strip()
        val = val.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = val


# Load project .env so LLM integration tests pick up API keys
_load_dotenv(pathlib.Path(__file__).parents[3] / '.env')


def pytest_configure(config):
    config.addinivalue_line('markers', 'asyncio: mark test as async')
