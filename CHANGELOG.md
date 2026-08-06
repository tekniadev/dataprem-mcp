# Changelog

Notable changes to `dataprem-mcp`. Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) · semver.

## [0.5.0] — 2026-08-06

### Changed

- **The tool descriptions come from a catalogue, not from the docstrings.** Their single source is `config/tools.json` in the DataPrem API, because capabilities are defined by whatever implements them. A copy ships inside the package, and the server prefers `GET /v1/tools` when the API answers — so a description can be improved without publishing a release.
- **What the API may change, and what it may not.** Only the wording of tools this package implements. It cannot announce a new one: a tool with no handler in the installed wheel would be picked by the model and then fail.
- **The fallback is silent and deliberate.** `tools/list` runs when a client connects, before anything is asked. An API blip at that moment would otherwise register zero tools and leave the integration looking broken until the client restarts; with the bundled copy the tools are there and a real outage surfaces on the call, where it is legible.
- Tool names, signatures and schemas are unchanged. `tools/list` returns byte for byte what 0.4.0 returned.

## [0.4.0] — 2026-08-05

### Changed

- **Every tool now requires an API key.** `dataprem_borme_search`, `dataprem_cendoj_search` and `dataprem_tenders_search` call the API like `dataprem_catastro_lookup` does; until each connector ships, the API answers `not_implemented` and no tool returns data of its own.
- **Requires the MCP Python SDK 2.x** (`mcp>=2.0.0,<3`). The server now imports `MCPServer` from `mcp.server.mcpserver`, and `host` / `port` are passed to `run()`. Installs pinned to SDK 1.x should stay on 0.3.2.
- Tool names and signatures are unchanged. The three planned tools return an error instead of a payload, so a caller that relied on their demonstration data has to handle `ok: false`.
- The distribution contains the package, its tests, the README, the changelog and the licence, and nothing else.
- `LICENSE` ships with the distribution.

### Added

- `scripts/smoke_stdio.py`: starts the installed console script over stdio with the SDK client and lists the tools, so the published artifact is exercised the way a client uses it.
- `scripts/check_artifacts.py`: verifies the built distribution before it is published.
- CI on Python 3.11–3.13, plus a weekly job that runs the same smoke against the newest SDK release.

## [0.3.2] — 2026-05-07

### Fixed

- README: the `DATAPREM_API_URL` example pointed at a machine-specific host. Replaced with `http://localhost:8000`, which is useful to anyone running a local DataPrem API.

### Changed

- `README.md` and the `[project].description` of `pyproject.toml` are now in English. Contact email is `info@dataprem.com`.

## [0.3.1] — 2026-05-05

### Changed

- PyPI metadata: `authors`, `project.urls` (Homepage, Repository, Issues, Changelog), `keywords`, full `classifiers` (Development Status, Intended Audience, Python 3.11–3.13, Topic). Pure metadata bump; no runtime changes.

## [0.3.0] — 2026-05-04

### Added

- HTTP transport (`streamable-http`) so the chat backend (and any other server-side MCP client) can reach the server over an internal Docker network at `http://dataprem_mcp:8080/mcp`. Stdio transport via `uvx dataprem-mcp` is preserved for desktop clients (Claude Desktop, Cursor).
- Dockerfile + healthcheck endpoint for container deploys.

## [0.2.0] — 2026-05-04

### Changed

- `dataprem_catastro_lookup` no longer returns demo data: tool calls hit the real Catastro SOAP API via the DataPrem backend.

## [0.1.0] — Initial release

- Base MCP server scaffold with stub tools for Catastro, BORME, CENDOJ and Licitaciones; stdio transport.
