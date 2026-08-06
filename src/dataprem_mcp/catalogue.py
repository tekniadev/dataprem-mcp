"""The tool catalogue: what the model reads to choose a tool and how to call it.

Its single source is `config/tools.json` in dataprem-api, because capabilities
are defined by whatever implements them. This module gets it from two places,
in this order:

1. `GET /v1/tools` on the API, so a description can be improved without
   publishing to PyPI. The catalogue is prompt engineering, and prompt
   engineering wants iteration faster than a release cycle.
2. The copy bundled in this package, when the API is unreachable, slow or
   unauthenticated.

The fallback is not an afterthought. `tools/list` happens when a desktop client
connects, before the user asks anything: an API blip at that moment would
register zero tools and leave the integration looking broken until the client
restarts. With the bundled copy the client sees its tools, and a real outage
shows up on the call, where it is legible and retryable.

**What the API may change, and what it may not.** Only descriptions of tools
this package implements. It cannot add one: announcing a tool whose handler is
not in the installed wheel means the model picks it and hits a server that
cannot answer.

Schemas are not read from here. The MCP SDK derives them from the Python
signatures and offers no supported way to supply one, so the signatures remain
their source; a test pins the catalogue's copy against what the SDK generates
so the two cannot drift.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

import httpx

BUNDLED_CATALOGUE = Path(__file__).with_name("tools.json")

# Short on purpose: this runs while a desktop client waits for tools/list, and
# a slow API must not look like a hung server.
FETCH_TIMEOUT_SECONDS = 3.0

logger = logging.getLogger(__name__)


def _load_bundled() -> dict[str, Any]:
    with BUNDLED_CATALOGUE.open(encoding="utf-8") as handle:
        return json.load(handle)


def _fetch_from_api() -> dict[str, Any] | None:
    base_url = (os.getenv("DATAPREM_API_URL") or "https://api.dataprem.com").rstrip("/")
    api_key = os.getenv("DATAPREM_API_KEY") or ""
    if not api_key:
        return None

    try:
        response = httpx.get(
            f"{base_url}/v1/tools",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=FETCH_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        payload = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        logger.info("Tool catalogue not fetched from the API, using the bundled copy: %s", exc)
        return None

    if not isinstance(payload, dict) or not isinstance(payload.get("tools"), list):
        logger.info("Tool catalogue from the API has no tools[], using the bundled copy")
        return None

    return payload


def descriptions(implemented: set[str]) -> dict[str, str]:
    """Description per tool, for the tools this package can actually run.

    Anything the API announces that is not in `implemented` is dropped, and the
    bundled copy fills any gap the API leaves.
    """
    bundled = _load_bundled()
    merged: dict[str, str] = {
        tool["name"]: tool["description"]
        for tool in bundled["tools"]
        if tool["name"] in implemented
    }

    remote = _fetch_from_api()
    if remote is None:
        return merged

    for tool in remote["tools"]:
        name = tool.get("name")
        description = tool.get("description")
        if not isinstance(name, str) or not isinstance(description, str) or description == "":
            continue
        if name not in implemented:
            logger.info("Tool %r announced by the API is not implemented here, ignoring it", name)
            continue
        merged[name] = description

    return merged


def bundled_tools() -> list[dict[str, Any]]:
    """The bundled catalogue, for tests and for anyone auditing what shipped."""
    return list(_load_bundled()["tools"])
