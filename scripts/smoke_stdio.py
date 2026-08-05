"""Start the installed package the way a desktop client does and list its tools.

A test suite exercises the source tree; this exercises the artifact. It spawns
the console script over stdio and talks to it with the real SDK client, which
is the path Claude Desktop and Cursor take.

Usage: python scripts/smoke_stdio.py [expected-tool-count]
"""

from __future__ import annotations

import asyncio
import shutil
import sys
from pathlib import Path

from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

DEFAULT_EXPECTED_TOOLS = 4
CONSOLE_SCRIPT = "dataprem-mcp"


def console_script_path() -> str:
    """The installed entry point, which is what a client actually spawns.

    Falls back to the interpreter's own bin directory so the smoke also runs
    from a virtualenv that has not been activated.
    """
    found = shutil.which(CONSOLE_SCRIPT)
    if found:
        return found

    sibling = Path(sys.executable).parent / CONSOLE_SCRIPT
    if sibling.exists():
        return str(sibling)

    raise FileNotFoundError(f"{CONSOLE_SCRIPT} is not installed in this environment")


async def list_tool_names() -> list[str]:
    params = StdioServerParameters(command=console_script_path(), args=[])
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.list_tools()
            return [tool.name for tool in result.tools]


def main(argv: list[str]) -> int:
    expected = int(argv[0]) if argv else DEFAULT_EXPECTED_TOOLS

    try:
        names = asyncio.run(list_tool_names())
    except Exception as error:  # noqa: BLE001 — any failure here is a failed smoke
        print(f"smoke: the server did not start over stdio: {error}", file=sys.stderr)
        return 1

    print(f"smoke: initialize OK, {len(names)} tools: {', '.join(sorted(names))}")

    if len(names) != expected:
        print(f"smoke: expected {expected} tools", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
