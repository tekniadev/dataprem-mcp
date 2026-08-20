# DataPrem MCP Server

A [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) server that exposes Spanish public-data sources to AI agents (Claude Desktop, Cursor, ChatGPT, …).

It is a thin client of the [DataPrem REST API](https://api.dataprem.com): each MCP tool maps to an HTTPS call against `api.dataprem.com` using your API key.

Requires the MCP Python SDK 2.x (`mcp>=2.0.0,<3`).

## Tool status (0.4.0)

| Tool | Status | Source |
|------|--------|--------|
| `dataprem_catastro_lookup` | **Live** | Sede Electrónica del Catastro |
| `dataprem_borme_search` | **Live** | Boletín Oficial del Registro Mercantil |
| `dataprem_tenders_search` | **Live** | Plataforma de Contratación del Sector Público |
| `dataprem_subsidies_search` | **Live** | Base de Datos Nacional de Subvenciones |

Every tool answers with real data. The subsidies one carries its attribution in `meta.source`: its terms of reuse ask for the origin to be named wherever the data is shown.

## Getting an API key

Every tool requires a Bearer token from `api.dataprem.com`:

1. Request access by email to `info@dataprem.com`, describing your use case.
2. You will receive a token prefixed `dpa_…` along with the API URL.
3. Configure it in your MCP client (next section).

## Installation

Requires Python 3.11+.

```bash
# Via PyPI (recommended for MCP clients)
uvx dataprem-mcp

# Or local install for development
pip install -e ".[dev]"
```

## Claude Desktop configuration

Edit `claude_desktop_config.json` (Mac: `~/Library/Application Support/Claude/claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "dataprem": {
      "command": "uvx",
      "args": ["dataprem-mcp"],
      "env": {
        "DATAPREM_API_KEY": "dpa_YOUR_TOKEN_HERE",
        "DATAPREM_API_URL": "https://api.dataprem.com"
      }
    }
  }
}
```

Restart Claude Desktop. The four tools should show up as available to the model.

## Server-side HTTP transport

For clients that cannot spawn the server as a subprocess (e.g. a multi-request web app) there is a `streamable-http` transport that runs the server as a long-lived process listening for JSON-RPC over HTTP.

```bash
# Without Docker
python -m dataprem_mcp --transport streamable-http --host 0.0.0.0 --port 8080

# With Docker
docker compose up dataprem_mcp     # local image build; exposed only on the internal network
```

The MCP endpoint is `/mcp` (no trailing slash). The standard handshake (`initialize` → `tools/list` → `tools/call`) works with `Content-Type: application/json` and `Accept: application/json, text/event-stream`. Each conversation receives an `mcp-session-id` that the client must echo back on subsequent requests.

```bash
# Example: initialize handshake
curl -sL -X POST http://127.0.0.1:8080/mcp \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
      "protocolVersion": "2025-03-26",
      "clientInfo": {"name": "smoke", "version": "1"},
      "capabilities": {}
    }
  }' -i
```

By default the compose service does not publish the port to the host: place it on a Docker network shared with your client and reach it as `http://dataprem_mcp:8080/mcp`.

### Alternative configuration (local development)

```json
{
  "mcpServers": {
    "dataprem-dev": {
      "command": "python",
      "args": ["-m", "dataprem_mcp"],
      "cwd": "/path/to/dataprem-mcp",
      "env": {
        "DATAPREM_API_KEY": "dpa_dev_token",
        "DATAPREM_API_URL": "http://localhost:8000"
      }
    }
  }
}
```

## Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATAPREM_API_KEY` | _(empty)_ | Bearer token (`dpa_…`). **Required** for live tools. |
| `DATAPREM_API_URL` | `https://api.dataprem.com` | API base URL. Override to point at a development environment. |

## Tools — reference

### `dataprem_catastro_lookup` ✅ Live

Looks up cadastral data for a property. Two modes are supported:

**By cadastral reference:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `refcat` | string | Cadastral reference (14, 18 or 20 characters) |

**By address:**

| Parameter | Type | Required | Description |
|-----------|------|:--------:|-------------|
| `address` | string | yes | Literal address (street type + name + number) |
| `city` | string | yes | Municipality |
| `province` | string | no | Province |

Returns the normalised cadastral record (class, use, surfaces, year of construction, address with INE codes, breakdown of constructions by floor and use). **Does not expose the owner** for LOPD/GDPR reasons.

### `dataprem_borme_search`

| Parameter | Type | Required |
|-----------|------|:--------:|
| `company_name` | string | yes |
| `date_from` | string YYYY-MM-DD | no |
| `date_to` | string YYYY-MM-DD | no |
| `act_type` | string | no |
| `limit` | integer (default 25, max 100) | no |

### `dataprem_subsidies_search`

Every parameter is optional on its own, but at least one is required.

| Parameter | Type | Required |
|-----------|------|:--------:|
| `query` | string | no |
| `beneficiary` | string (name or NIF) | no |
| `body` | string | no |
| `level` | ESTADO / AUTONOMICA / LOCAL / OTRA | no |
| `min_amount` | string | no |
| `max_amount` | string | no |
| `date_from` | string YYYY-MM-DD | no |
| `date_to` | string YYYY-MM-DD | no |
| `limit` | integer (default 25, max 100) | no |

### `dataprem_tenders_search`

Every parameter is optional on its own, but at least one is required: searching for everything is not a search.

| Parameter | Type | Required |
|-----------|------|:--------:|
| `query` | string, words from the object of the contract | no |
| `buyer` | string, public body that put the contract out | no |
| `company` | string, awarded company by name or NIF | no |
| `cpv` | string, 2 to 10 digits, comma separated | no |
| `location` | string, city or NUTS code (`ES300`) | no |
| `status` | `"open"` \| `"closed"` \| `"all"` \| `PRE,PUB,EV,ADJ,RES,ANUL` | no |
| `min_amount` | string, euros without tax | no |
| `max_amount` | string, euros without tax | no |
| `date_from` | string YYYY-MM-DD | no |
| `date_to` | string YYYY-MM-DD | no |
| `limit` | integer, 25 by default, capped at 100 | no |

`buyer` is who put the contract out; `company` is who won it — the one no other source answers: what a given firm has been awarded. `cpv` widens or narrows by how much of the code you give — `45` is every construction contract, `45210000` one kind of building.

## Response shape

Every tool returns a `dict` marking success or failure with `ok`:

```json
{ "ok": true, "data": { ... cadastral record ... } }

{ "ok": false, "error": "unauthorized", "message": "API key invalid or revoked..." }
```

A search also carries `meta`, which says what the results alone do not: that there are more of them, and which years hold them, so narrowing is not guesswork.

```json
{ "ok": true,
  "meta": { "count": 25, "has_more": true, "years": [2024, 2025, 2026] },
  "data": [ ... ] }
```

A value the API refuses comes back with the ones it accepts, rather than as a bare failure:

```json
{ "ok": false, "error": "invalid_request", "message": "Unknown tender status \"ABIERTA\".",
  "statuses": ["PRE", "PUB", "EV", "ADJ", "RES", "ANUL"] }
```

A search with nothing to narrow by is refused, and the answer says what it takes:

```json
{ "ok": false, "error": "invalid_request",
  "message": "A subsidy search needs something to narrow by: text, a beneficiary, a granting body, a level, an amount or a date.",
  "levels": ["ESTADO", "AUTONOMICA", "LOCAL", "OTRA"] }
```

Error codes:

| `error` | Meaning |
|---------|---------|
| `missing_api_key` | `DATAPREM_API_KEY` is not set in the environment |
| `invalid_request` | Required parameters are missing |
| `unauthorized` | Token revoked or expired |
| `not_found` | The upstream returned no match |
| `validation_error` | The source rejected the input (malformed RC, unknown street, …) |
| `rate_limited` | Monthly quota exhausted |
| `not_implemented` | The source is in the catalogue but its connector has not shipped |
| `upstream_error` | The source or DataPrem temporarily unavailable |
| `upstream_unreachable` | `DATAPREM_API_URL` cannot be reached |

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Start the installed console script over stdio and list its tools,
# the same way a desktop client does. The suite alone cannot catch a
# package that imports fine from the source tree but not once installed.
python scripts/smoke_stdio.py

# Run the server with a local API key
DATAPREM_API_KEY=dpa_xxx DATAPREM_API_URL=http://localhost python -m dataprem_mcp
```

## Releasing

Publishing runs from CI through PyPI trusted publishing, so no token lives on
anyone's machine:

```bash
# bump the version in pyproject.toml and add the CHANGELOG entry, then
git tag 0.3.4
git push origin 0.3.4
```

The release workflow builds, checks the artifact, installs the wheel, starts it
over stdio, refuses to continue if the tag disagrees with the built version,
and only then publishes.

## License

MIT
