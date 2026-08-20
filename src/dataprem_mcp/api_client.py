"""HTTP client for the DataPrem REST API.

Thin wrapper around httpx that:
* reads `DATAPREM_API_URL` and `DATAPREM_API_KEY` from environment
* encodes the bearer token in every call
* normalises HTTP errors to a small set of dict shapes that the MCP tools
  can hand straight back to the LLM (no exceptions across the MCP boundary).
"""

from __future__ import annotations

import os
from typing import Any

import httpx

DEFAULT_BASE_URL = "https://api.dataprem.com"
DEFAULT_TIMEOUT = 20.0


class DatapremApiClient:
    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        timeout: float = DEFAULT_TIMEOUT,
    ) -> None:
        resolved_url = base_url or os.getenv("DATAPREM_API_URL") or DEFAULT_BASE_URL
        self.base_url = resolved_url.rstrip("/")
        self.api_key = api_key or os.getenv("DATAPREM_API_KEY") or ""
        self.timeout = timeout

    def get_catastro_property(
        self,
        refcat: str | None = None,
        address: str | None = None,
        city: str | None = None,
        province: str | None = None,
    ) -> dict[str, Any]:
        """Look up a Spanish cadastral property by reference or by address.

        Returns one of:
        * `{"ok": True, "data": {...}}` on a successful match
        * `{"ok": False, "error": "...", "message": "..."}` otherwise
        """
        params: dict[str, str] = {}
        if refcat:
            params["refcat"] = refcat
        elif address and city:
            params["address"] = address
            params["city"] = city
            if province:
                params["province"] = province
        else:
            return {
                "ok": False,
                "error": "invalid_request",
                "message": (
                    "Either 'refcat' or both 'address' and 'city' are required."
                ),
            }

        return self._get_json("/v1/es/catastro/property", params=params)

    def search_borme(
        self,
        company_name: str,
        date_from: str | None = None,
        date_to: str | None = None,
        act_type: str | None = None,
        limit: int | None = None,
    ) -> dict[str, Any]:
        """Search company filings in the Spanish commercial registry."""
        params: dict[str, Any] = {"company_name": company_name}
        if date_from:
            params["date_from"] = date_from
        if date_to:
            params["date_to"] = date_to
        if act_type:
            params["act_type"] = act_type
        if limit:
            params["limit"] = limit

        return self._get_json("/v1/es/borme/search", params=params)

    def search_subsidies(
        self,
        query: str | None = None,
        beneficiary: str | None = None,
        body: str | None = None,
        level: str | None = None,
        min_amount: str | None = None,
        max_amount: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        limit: int | None = None,
    ) -> dict[str, Any]:
        """Search Spanish public subsidies and who received them."""
        params: dict[str, Any] = {}
        for name, value in (
            ("query", query),
            ("beneficiary", beneficiary),
            ("body", body),
            ("level", level),
            ("min_amount", min_amount),
            ("max_amount", max_amount),
            ("date_from", date_from),
            ("date_to", date_to),
            ("limit", limit),
        ):
            # Not `if value`: a limit of 0 is a value the caller chose, and the
            # API is the one that says what it does with it.
            if value is not None and value != "":
                params[name] = value

        return self._get_json("/v1/es/subsidies/search", params=params)

    def search_tenders(
        self,
        query: str | None = None,
        location: str | None = None,
        status: str | None = None,
        buyer: str | None = None,
        company: str | None = None,
        cpv: str | None = None,
        min_amount: str | None = None,
        max_amount: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        limit: int | None = None,
    ) -> dict[str, Any]:
        """Search Spanish public tenders and awarded contracts.

        `query`, `location` and `status` are the three the published versions of
        this package already send, and they keep their meaning.
        """
        params: dict[str, Any] = {}
        for name, value in (
            ("query", query),
            ("location", location),
            ("status", status),
            ("buyer", buyer),
            ("company", company),
            ("cpv", cpv),
            ("min_amount", min_amount),
            ("max_amount", max_amount),
            ("date_from", date_from),
            ("date_to", date_to),
            ("limit", limit),
        ):
            # Not `if value`: zero is falsy in Python, and `max_amount=0` is a
            # filter the API accepts and answers.
            if value is not None and value != "":
                params[name] = value

        return self._get_json("/v1/es/tenders/search", params=params)

    # ─── internal ───────────────────────────────────────────────────────────

    def _get_json(self, path: str, params: dict[str, str]) -> dict[str, Any]:
        if not self.api_key:
            return {
                "ok": False,
                "error": "missing_api_key",
                "message": (
                    "Set the DATAPREM_API_KEY environment variable in the MCP "
                    "client config (Authorization: Bearer dpa_...)."
                ),
            }

        url = f"{self.base_url}{path}"
        headers = {"Authorization": f"Bearer {self.api_key}"}

        try:
            response = httpx.get(
                url, params=params, headers=headers, timeout=self.timeout
            )
        except httpx.RequestError as exc:
            return {
                "ok": False,
                "error": "upstream_unreachable",
                "message": f"Could not reach DataPrem API at {self.base_url}: {exc}",
            }

        return self._handle_response(response)

    @staticmethod
    def _handle_response(response: httpx.Response) -> dict[str, Any]:
        status = response.status_code

        if status == 200:
            try:
                payload = response.json()
            except ValueError:
                return {
                    "ok": False,
                    "error": "bad_response",
                    "message": "DataPrem API returned non-JSON 200.",
                }
            answer: dict[str, Any] = {"ok": True, "data": payload.get("data", payload)}

            # Without meta the model never learns there are more results, nor
            # which years hold them, so narrowing stays guesswork.
            if isinstance(payload, dict) and isinstance(payload.get("meta"), dict):
                answer["meta"] = payload["meta"]

            return answer

        if status == 401:
            return {
                "ok": False,
                "error": "unauthorized",
                "message": (
                    "API key invalid or revoked. Request a new one at "
                    "https://dataprem.com and update DATAPREM_API_KEY."
                ),
            }

        if status == 400:
            # The API answers a bad value with the list of good ones. Losing it
            # here leaves the model to guess the same wrong word again.
            body = _safe_body(response)
            answer: dict[str, Any] = {
                "ok": False,
                "error": body.get("error", "invalid_request"),
                "message": _safe_message(response, default="The request was rejected as invalid."),
            }

            for key in ("field", "statuses", "act_types"):
                if key in body:
                    answer[key] = body[key]

            return answer

        if status == 404:
            return {
                "ok": False,
                "error": "not_found",
                "message": _safe_message(response, default="No match for the given input."),
            }

        if status == 422:
            return {
                "ok": False,
                "error": "validation_error",
                "message": _safe_message(response, default="The source rejected the input as invalid."),
            }

        if status == 429:
            return {
                "ok": False,
                "error": "rate_limited",
                "message": (
                    "Rate limit reached for your DataPrem plan. Wait or upgrade tier."
                ),
            }

        # Before the 5xx branch: a planned source is not a temporary failure,
        # and telling an agent to retry would be wrong.
        if status == 501:
            return {
                "ok": False,
                "error": "not_implemented",
                "message": _safe_message(
                    response, default="This source is not available yet."
                ),
                "source": _safe_body(response).get("source"),
            }

        if status >= 500:
            return {
                "ok": False,
                "error": "upstream_error",
                "message": f"DataPrem API returned HTTP {status}: temporary upstream issue.",
            }

        return {
            "ok": False,
            "error": "unexpected_status",
            "message": f"DataPrem API returned HTTP {status}.",
        }


def _safe_message(response: httpx.Response, *, default: str) -> str:
    body = _safe_body(response)
    message = body.get("message")

    return message if isinstance(message, str) else default


def _safe_body(response: httpx.Response) -> dict[str, Any]:
    try:
        body = response.json()
    except ValueError:
        return {}

    return body if isinstance(body, dict) else {}
