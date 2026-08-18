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

def test_the_act_type_is_only_sent_when_asked_for(respx_mock: respx.MockRouter) -> None:
    """The MCP already published does not send it, and the API must still answer."""
    route = respx_mock.get(f"{BASE}/v1/es/borme/search").mock(
        return_value=httpx.Response(200, json={"data": []})
    )

    make_client().search_borme(company_name="ACME SL")
    assert "act_type" not in route.calls.last.request.url.params

    make_client().search_borme(company_name="ACME SL", act_type="Nombramientos")
    assert route.calls.last.request.url.params["act_type"] == "Nombramientos"


@respx.mock
def test_borme_limit_travels_to_the_api_only_when_asked_for() -> None:
    """The chat needs a way to say "show me more" — narrowing by date or act
    type is the better answer, but a year of a large group is still hundreds.
    """
    route = respx.get(f"{BASE}/v1/es/borme/search").mock(
        return_value=httpx.Response(200, json={"data": []})
    )
    client = make_client()

    client.search_borme(company_name="REPSOL", limit=100)
    assert route.calls.last.request.url.params["limit"] == "100"

    client.search_borme(company_name="REPSOL")
    assert "limit" not in route.calls.last.request.url.params


@respx.mock
def test_meta_reaches_the_model_instead_of_being_dropped() -> None:
    """Without it the model never learns there are more results, nor which
    years hold them, so narrowing stays guesswork.
    """
    respx.get(f"{BASE}/v1/es/tenders/search").mock(
        return_value=httpx.Response(
            200,
            json={"meta": {"count": 2, "has_more": True, "years": [2024, 2026]}, "data": [1, 2]},
        )
    )

    answer = make_client().search_tenders(query="limpieza")

    assert answer["ok"] is True
    assert answer["data"] == [1, 2]
    assert answer["meta"]["has_more"] is True
    assert answer["meta"]["years"] == [2024, 2026]


@respx.mock
def test_a_payload_without_meta_still_answers() -> None:
    respx.get(f"{BASE}/v1/es/tenders/search").mock(
        return_value=httpx.Response(200, json={"data": []})
    )

    assert "meta" not in make_client().search_tenders(query="limpieza")


@respx.mock
def test_a_rejected_value_comes_back_with_the_valid_ones() -> None:
    """The API answers a bad status with the list of good ones; guessing the
    same wrong word again is what losing it costs.
    """
    respx.get(f"{BASE}/v1/es/tenders/search").mock(
        return_value=httpx.Response(
            400,
            json={
                "error": "invalid_request",
                "message": 'Unknown tender status "ABIERTA".',
                "statuses": ["PRE", "PUB", "EV", "ADJ", "RES", "ANUL"],
            },
        )
    )

    answer = make_client().search_tenders(query="obras", status="ABIERTA")

    assert answer["ok"] is False
    assert answer["error"] == "invalid_request"
    assert "ABIERTA" in answer["message"]
    assert answer["statuses"] == ["PRE", "PUB", "EV", "ADJ", "RES", "ANUL"]


@respx.mock
def test_a_missing_parameter_says_which_one() -> None:
    respx.get(f"{BASE}/v1/es/borme/search").mock(
        return_value=httpx.Response(
            400,
            json={"error": "missing_parameter", "field": "company_name", "message": "Required."},
        )
    )

    answer = make_client().search_borme(company_name="")

    assert answer["error"] == "missing_parameter"
    assert answer["field"] == "company_name"


@respx.mock
def test_the_three_tender_filters_already_published_keep_working() -> None:
    """A version of this package installed before today sends only these, and
    the API has to keep answering it.
    """
    route = respx.get(f"{BASE}/v1/es/tenders/search").mock(
        return_value=httpx.Response(200, json={"data": []})
    )

    make_client().search_tenders(query="limpieza", location="ES300", status="open")

    params = route.calls.last.request.url.params
    assert params["query"] == "limpieza"
    assert params["location"] == "ES300"
    assert params["status"] == "open"
    assert "cpv" not in params


@respx.mock
def test_the_new_tender_filters_travel_only_when_asked_for() -> None:
    route = respx.get(f"{BASE}/v1/es/tenders/search").mock(
        return_value=httpx.Response(200, json={"data": []})
    )
    client = make_client()

    client.search_tenders(
        winner="B15720436",
        cpv="45,72",
        organisation="ayuntamiento de valencia",
        min_amount="50000",
        max_amount="500000",
        date_from="2024-01-01",
        date_to="2026-08-18",
        limit=100,
    )

    params = route.calls.last.request.url.params
    assert params["winner"] == "B15720436"
    assert params["cpv"] == "45,72"
    assert params["organisation"] == "ayuntamiento de valencia"
    assert params["min_amount"] == "50000"
    assert params["max_amount"] == "500000"
    assert params["date_from"] == "2024-01-01"
    assert params["limit"] == "100"
    assert "query" not in params

    client.search_tenders(query="obras")
    assert set(route.calls.last.request.url.params) == {"query"}


@respx.mock
def test_a_zero_is_a_filter_and_not_an_absence() -> None:
    """Zero is falsy in Python; the API takes max_amount=0 and answers it."""
    route = respx.get(f"{BASE}/v1/es/tenders/search").mock(
        return_value=httpx.Response(200, json={"data": []})
    )

    make_client().search_tenders(query="obras", max_amount="0", min_amount="0", limit=0)

    params = route.calls.last.request.url.params
    assert params["max_amount"] == "0"
    assert params["min_amount"] == "0"
    assert params["limit"] == "0"


@respx.mock
def test_an_empty_string_is_not_sent() -> None:
    route = respx.get(f"{BASE}/v1/es/tenders/search").mock(
        return_value=httpx.Response(200, json={"data": []})
    )

    make_client().search_tenders(query="obras", winner="", cpv="")

    assert set(route.calls.last.request.url.params) == {"query"}
