"""Smoke tests on the four MCP tools.

They touch the tool callables directly (not the MCP wire protocol) — enough
to catch regressions in signatures and in what each one delegates to.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from dataprem_mcp import server


def test_catastro_tool_delegates_to_api_client() -> None:
    with patch.object(server, "DatapremApiClient") as cls:
        cls.return_value.get_catastro_property.return_value = {"ok": True, "data": {"x": 1}}

        result = server.dataprem_catastro_lookup(refcat="9872023VH5797S0001WX")

        assert result == {"ok": True, "data": {"x": 1}}
        cls.return_value.get_catastro_property.assert_called_once_with(
            refcat="9872023VH5797S0001WX",
            address=None,
            city=None,
            province=None,
        )


@pytest.mark.parametrize(
    "tool_callable,args,client_method,expected_call",
    [
        (
            server.dataprem_borme_search,
            {"company_name": "ACME SL"},
            "search_borme",
            {"company_name": "ACME SL", "date_from": None, "date_to": None, "act_type": None},
        ),
        (
            server.dataprem_cendoj_search,
            {"query": "despido improcedente"},
            "search_cendoj",
            {"query": "despido improcedente", "court": None, "date_from": None},
        ),
        (
            server.dataprem_tenders_search,
            {"query": "limpieza"},
            "search_tenders",
            {"query": "limpieza", "location": None, "status": None},
        ),
    ],
)
def test_every_tool_asks_the_api(tool_callable, args, client_method, expected_call) -> None:
    with patch.object(server, "DatapremApiClient") as cls:
        getattr(cls.return_value, client_method).return_value = {"ok": False}

        tool_callable(**args)

        getattr(cls.return_value, client_method).assert_called_once_with(**expected_call)


@pytest.mark.parametrize(
    "tool_callable,args",
    [
        (server.dataprem_borme_search, {"company_name": "ACME SL"}),
        (server.dataprem_cendoj_search, {"query": "despido"}),
        (server.dataprem_tenders_search, {"query": "limpieza"}),
    ],
)
def test_no_tool_answers_from_data_of_its_own(
    tool_callable, args, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Without a key nothing comes back. These three used to serve invented
    filings from dictionaries written into the server module."""
    monkeypatch.delenv("DATAPREM_API_KEY", raising=False)

    result = tool_callable(**args)

    assert result["ok"] is False
    assert result["error"] == "missing_api_key"
    assert "resultados" not in result
