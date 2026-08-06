"""The catalogue: what the model reads, and where it is allowed to come from.

Two things are pinned here. That the API can reword a tool but not invent one,
because a tool with no handler in the installed wheel gets picked by the model
and then fails. And that the schema bundled for other consumers matches what
this server actually accepts, since the SDK derives schemas from the Python
signatures and nothing else keeps the two in step.
"""

from __future__ import annotations

import json
from unittest.mock import patch

import httpx
import pytest

from dataprem_mcp import catalogue, server

IMPLEMENTED = server.IMPLEMENTED


def _api_payload(tools: list[dict[str, str]]) -> dict[str, object]:
    return {"version": 1, "tools": tools}


def _response(payload: object, status: int = 200) -> httpx.Response:
    """A response with its request attached: raise_for_status needs one."""
    return httpx.Response(
        status,
        json=payload,
        request=httpx.Request("GET", "https://api.dataprem.com/v1/tools"),
    )


def test_the_bundled_copy_answers_when_no_api_key_is_set(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DATAPREM_API_KEY", raising=False)

    descriptions = catalogue.descriptions(IMPLEMENTED)

    assert set(descriptions) == IMPLEMENTED
    assert descriptions["dataprem_catastro_lookup"].startswith("Consulta datos catastrales")


def test_the_api_can_reword_a_tool(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATAPREM_API_KEY", "dpa_test")
    payload = _api_payload([{"name": "dataprem_borme_search", "description": "Descripcion nueva"}])

    with patch.object(catalogue.httpx, "get", return_value=_response(payload)):
        descriptions = catalogue.descriptions(IMPLEMENTED)

    assert descriptions["dataprem_borme_search"] == "Descripcion nueva"
    # The ones it did not mention keep what shipped, rather than disappearing.
    assert descriptions["dataprem_catastro_lookup"].startswith("Consulta datos catastrales")


def test_the_api_cannot_announce_a_tool_this_package_does_not_implement(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DATAPREM_API_KEY", "dpa_test")
    payload = _api_payload([{"name": "dataprem_inventada", "description": "No existe aqui"}])

    with patch.object(catalogue.httpx, "get", return_value=_response(payload)):
        descriptions = catalogue.descriptions(IMPLEMENTED)

    assert "dataprem_inventada" not in descriptions
    assert set(descriptions) == IMPLEMENTED


@pytest.mark.parametrize(
    "failure",
    [
        httpx.ConnectError("connection refused"),
        httpx.ReadTimeout("too slow"),
        httpx.HTTPStatusError(
            "401",
            request=httpx.Request("GET", "https://api.dataprem.com/v1/tools"),
            response=httpx.Response(401),
        ),
    ],
)
def test_an_unreachable_api_falls_back_instead_of_leaving_the_client_toolless(
    monkeypatch: pytest.MonkeyPatch, failure: Exception
) -> None:
    monkeypatch.setenv("DATAPREM_API_KEY", "dpa_test")

    with patch.object(catalogue.httpx, "get", side_effect=failure):
        descriptions = catalogue.descriptions(IMPLEMENTED)

    assert set(descriptions) == IMPLEMENTED


def test_a_malformed_api_response_falls_back(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATAPREM_API_KEY", "dpa_test")

    with patch.object(catalogue.httpx, "get", return_value=_response({"nope": 1})):
        descriptions = catalogue.descriptions(IMPLEMENTED)

    assert set(descriptions) == IMPLEMENTED


def test_an_empty_description_from_the_api_does_not_blank_a_tool(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DATAPREM_API_KEY", "dpa_test")
    payload = _api_payload([{"name": "dataprem_cendoj_search", "description": ""}])

    with patch.object(catalogue.httpx, "get", return_value=_response(payload)):
        descriptions = catalogue.descriptions(IMPLEMENTED)

    assert descriptions["dataprem_cendoj_search"].startswith("Busca resoluciones judiciales")


def test_the_bundled_catalogue_covers_every_implemented_tool() -> None:
    names = {tool["name"] for tool in catalogue.bundled_tools()}

    assert names == IMPLEMENTED


def test_the_bundled_schemas_match_what_this_server_accepts() -> None:
    """The chat reads the schema from the catalogue; the SDK builds its own from
    the signatures. If they drift, the chat sends arguments this server rejects.
    """
    from mcp.server.mcpserver.tools import Tool

    for entry in catalogue.bundled_tools():
        fn = getattr(server, entry["name"])
        generated = Tool.from_function(fn, name=entry["name"]).parameters

        assert generated == entry["inputSchema"], (
            f"{entry['name']}: the catalogue schema and the one the SDK derives "
            f"from the signature have drifted:\n"
            f"catalogue: {json.dumps(entry['inputSchema'], sort_keys=True)}\n"
            f"signature: {json.dumps(generated, sort_keys=True)}"
        )
