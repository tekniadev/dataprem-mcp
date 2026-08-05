"""Tests for DatapremApiClient — covers happy path + every error mapping."""

from __future__ import annotations

import httpx
import pytest
import respx

from dataprem_mcp.api_client import DatapremApiClient


BASE = "http://api.test"


def make_client() -> DatapremApiClient:
    return DatapremApiClient(base_url=BASE, api_key="dpa_test")


def test_missing_api_key_returns_dict_not_raises() -> None:
    client = DatapremApiClient(base_url=BASE, api_key="")
    result = client.get_catastro_property(refcat="X")
    assert result == {
        "ok": False,
        "error": "missing_api_key",
        "message": (
            "Set the DATAPREM_API_KEY environment variable in the MCP "
            "client config (Authorization: Bearer dpa_...)."
        ),
    }


def test_requires_either_refcat_or_address_plus_city() -> None:
    client = make_client()
    result = client.get_catastro_property()
    assert result["ok"] is False
    assert result["error"] == "invalid_request"


@respx.mock
def test_happy_path_by_refcat_returns_data_unwrapped() -> None:
    respx.get(f"{BASE}/v1/es/catastro/property").mock(
        return_value=httpx.Response(
            200,
            json={"data": {"reference_catastral": "9872023VH5797S0001WX", "surface_built_sqm": 308}},
        )
    )

    result = make_client().get_catastro_property(refcat="9872023VH5797S0001WX")

    assert result["ok"] is True
    assert result["data"]["reference_catastral"] == "9872023VH5797S0001WX"
    assert result["data"]["surface_built_sqm"] == 308


@respx.mock
def test_happy_path_by_address() -> None:
    route = respx.get(f"{BASE}/v1/es/catastro/property").mock(
        return_value=httpx.Response(200, json={"data": {"reference_catastral": "X"}})
    )

    make_client().get_catastro_property(
        address="CL MAYOR 5", city="MADRID", province="MADRID"
    )

    assert route.called
    request = route.calls.last.request
    assert request.url.params["address"] == "CL MAYOR 5"
    assert request.url.params["city"] == "MADRID"
    assert request.url.params["province"] == "MADRID"


@respx.mock
def test_authorization_header_is_sent() -> None:
    route = respx.get(f"{BASE}/v1/es/catastro/property").mock(
        return_value=httpx.Response(200, json={"data": {}})
    )

    make_client().get_catastro_property(refcat="X")

    assert route.calls.last.request.headers["authorization"] == "Bearer dpa_test"


@pytest.mark.parametrize(
    "status,error_key",
    [
        (401, "unauthorized"),
        (404, "not_found"),
        (422, "validation_error"),
        (429, "rate_limited"),
        (501, "not_implemented"),
        (500, "upstream_error"),
        (502, "upstream_error"),
        (418, "unexpected_status"),
    ],
)
@respx.mock
def test_http_errors_map_to_dict_codes(status: int, error_key: str) -> None:
    respx.get(f"{BASE}/v1/es/catastro/property").mock(
        return_value=httpx.Response(status, json={"message": "boom"})
    )

    result = make_client().get_catastro_property(refcat="X")

    assert result["ok"] is False
    assert result["error"] == error_key
    assert isinstance(result["message"], str) and result["message"]


@respx.mock
def test_validation_message_uses_upstream_text_when_present() -> None:
    respx.get(f"{BASE}/v1/es/catastro/property").mock(
        return_value=httpx.Response(
            422, json={"message": "Catastro error 4: RC mal formada"}
        )
    )

    result = make_client().get_catastro_property(refcat="bad")

    assert result["error"] == "validation_error"
    assert "Catastro error 4" in result["message"]


@pytest.mark.parametrize(
    "method,kwargs,path",
    [
        ("search_borme", {"company_name": "ACME SL"}, "/v1/es/borme/search"),
        ("search_cendoj", {"query": "despido"}, "/v1/es/cendoj/search"),
        ("search_tenders", {"query": "limpieza"}, "/v1/es/tenders/search"),
    ],
)
@respx.mock
def test_planned_sources_ask_the_api(method: str, kwargs: dict[str, str], path: str) -> None:
    route = respx.get(f"{BASE}{path}").mock(
        return_value=httpx.Response(
            501,
            json={
                "error": "not_implemented",
                "message": "The source is not available yet.",
                "source": "borme",
            },
        )
    )

    result = getattr(make_client(), method)(**kwargs)

    assert route.called
    assert route.calls.last.request.headers["authorization"] == "Bearer dpa_test"
    assert result["ok"] is False
    assert result["error"] == "not_implemented"
    assert result["source"] == "borme"


@respx.mock
def test_a_planned_source_is_not_reported_as_a_temporary_failure() -> None:
    """501 falls before the 5xx branch, which would tell the agent to retry."""
    respx.get(f"{BASE}/v1/es/borme/search").mock(
        return_value=httpx.Response(501, json={"message": "The borme source is not available yet."})
    )

    result = make_client().search_borme(company_name="ACME SL")

    assert result["error"] == "not_implemented"
    assert "temporary" not in result["message"]


@pytest.mark.parametrize(
    "method,kwargs",
    [
        ("search_borme", {"company_name": "ACME SL"}),
        ("search_cendoj", {"query": "despido"}),
        ("search_tenders", {"query": "limpieza"}),
    ],
)
def test_planned_sources_need_a_key_like_every_other_tool(
    method: str, kwargs: dict[str, str]
) -> None:
    client = DatapremApiClient(base_url=BASE, api_key="")

    result = getattr(client, method)(**kwargs)

    assert result["error"] == "missing_api_key"


@respx.mock
def test_network_error_returns_upstream_unreachable() -> None:
    respx.get(f"{BASE}/v1/es/catastro/property").mock(
        side_effect=httpx.ConnectError("dns gone")
    )

    result = make_client().get_catastro_property(refcat="X")

    assert result["error"] == "upstream_unreachable"
    assert "dns gone" in result["message"]


def test_env_var_resolution(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATAPREM_API_URL", "https://from-env.example/")
    monkeypatch.setenv("DATAPREM_API_KEY", "dpa_envtoken")
    client = DatapremApiClient()
    assert client.base_url == "https://from-env.example"
    assert client.api_key == "dpa_envtoken"
