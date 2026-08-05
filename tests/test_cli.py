"""Tests for the dataprem-mcp CLI parser."""

from __future__ import annotations

import pytest

from dataprem_mcp.__main__ import (
    DEFAULT_HOST,
    DEFAULT_PORT,
    SUPPORTED_TRANSPORTS,
    build_parser,
)


def test_default_transport_is_stdio() -> None:
    args = build_parser().parse_args([])
    assert args.transport == "stdio"
    assert args.host == DEFAULT_HOST
    assert args.port == DEFAULT_PORT


def test_explicit_stdio_transport() -> None:
    args = build_parser().parse_args(["--transport", "stdio"])
    assert args.transport == "stdio"


def test_streamable_http_with_defaults() -> None:
    args = build_parser().parse_args(["--transport", "streamable-http"])
    assert args.transport == "streamable-http"
    assert args.host == DEFAULT_HOST
    assert args.port == DEFAULT_PORT


def test_streamable_http_custom_host_and_port() -> None:
    args = build_parser().parse_args(
        ["--transport", "streamable-http", "--host", "0.0.0.0", "--port", "9090"]
    )
    assert args.host == "0.0.0.0"
    assert args.port == 9090


def test_port_must_be_integer() -> None:
    with pytest.raises(SystemExit):
        build_parser().parse_args(["--port", "not-a-number"])


def test_unknown_transport_rejected() -> None:
    with pytest.raises(SystemExit):
        build_parser().parse_args(["--transport", "websocket"])


def test_supported_transports_contract() -> None:
    """Locks the public set of transports — adding one must be a deliberate edit."""
    assert SUPPORTED_TRANSPORTS == ("stdio", "streamable-http")


def test_main_dispatches_stdio(monkeypatch: pytest.MonkeyPatch) -> None:
    from dataprem_mcp import __main__ as cli

    calls: list[dict[str, object]] = []

    def fake_run(transport: str, **kwargs: object) -> None:
        calls.append({"transport": transport, **kwargs})

    monkeypatch.setattr(cli.mcp, "run", fake_run)
    cli.main([])

    assert calls == [{"transport": "stdio"}]


def test_main_dispatches_streamable_http_with_bind_address(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Host and port travel as run() arguments, which is where the SDK reads them."""
    from dataprem_mcp import __main__ as cli

    calls: list[dict[str, object]] = []

    def fake_run(transport: str, **kwargs: object) -> None:
        calls.append({"transport": transport, **kwargs})

    monkeypatch.setattr(cli.mcp, "run", fake_run)
    cli.main(["--transport", "streamable-http", "--host", "0.0.0.0", "--port", "8080"])

    assert calls == [
        {"transport": "streamable-http", "host": "0.0.0.0", "port": 8080}
    ]
