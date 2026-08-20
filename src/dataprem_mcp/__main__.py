"""Entry point: ``python -m dataprem_mcp`` or ``dataprem-mcp`` (script).

Two transports are supported:

* ``stdio`` (default) — used by desktop MCP clients (Claude Desktop, Cursor)
  that spawn the server as a subprocess and talk JSON-RPC over stdin/stdout.
* ``streamable-http`` — for server-side consumers (e.g. a multi-request web
  app) that need to talk to a long-running MCP process over HTTP. Listens on
  ``--host`` / ``--port`` (default ``127.0.0.1:8080``).
"""

from __future__ import annotations

import argparse
import sys

from dataprem_mcp.server import mcp

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8080
SUPPORTED_TRANSPORTS = ("stdio", "streamable-http")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="dataprem-mcp",
        description="DataPrem MCP server (Catastro, BORME, public tenders, subsidies).",
    )
    parser.add_argument(
        "--transport",
        choices=SUPPORTED_TRANSPORTS,
        default="stdio",
        help=(
            "MCP transport. 'stdio' for desktop clients that spawn the server "
            "as a subprocess (default); 'streamable-http' for server-side "
            "consumers that talk JSON-RPC over HTTP."
        ),
    )
    parser.add_argument(
        "--host",
        default=DEFAULT_HOST,
        help=f"Bind address for streamable-http (default {DEFAULT_HOST}).",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=DEFAULT_PORT,
        help=f"TCP port for streamable-http (default {DEFAULT_PORT}).",
    )
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)

    if args.transport == "stdio":
        mcp.run(transport="stdio")
        return

    if args.transport == "streamable-http":
        mcp.run(transport="streamable-http", host=args.host, port=args.port)
        return

    # argparse already restricts choices; this guard catches future drift.
    print(f"Unsupported transport: {args.transport}", file=sys.stderr)
    sys.exit(2)


if __name__ == "__main__":
    main()
