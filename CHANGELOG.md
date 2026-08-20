# Changelog

Notable changes to `dataprem-mcp`. Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) · semver.

## [0.10.0] — 2026-08-20

### Added

- **`dataprem_subsidies_search`, and it answers with data.** Spanish public subsidies and grants from the Base de Datos Nacional de Subvenciones: who received the money, how much, under which call and from which administration. Filters by `query` over the title of the call, `beneficiary` by name or NIF, `body` — which also finds by region, so «navarra» works —, `level` (ESTADO, AUTONOMICA, LOCAL), `min_amount`, `max_amount`, `date_from`, `date_to` and `limit`.
- **The origin travels with the data.** Its terms of reuse ask for the source to be named wherever it is shown, so every answer carries `meta.source`.

### Removed

- **`dataprem_cendoj_search`.** It was in the catalogue as a planned source, and it is not one: the CENDOJ forbids commercial use and mass download of its database, and reuse needs prior authorisation from the CGPJ. A tool nobody can lawfully implement is not a promise to keep in a catalogue.

## [0.9.0] — 2026-08-18

### Added

- **`dataprem_tenders_search` answers with data.** Spanish public procurement, from the Plataforma de Contratación del Sector Público: what was put out to tender, by whom, for how much, and — where it is settled — who won it and at what price. The three arguments earlier versions send (`query`, `location`, `status`) keep their meaning, and `status` still takes `open`, `closed` and `all` besides the platform's own codes.
- **Eight more filters on that tool, all optional.** `company` answers the question no other source does: what a given firm has been awarded, by name or by NIF. `cpv` takes 2 to 10 digits, so `45` is every construction contract and `45210000` one kind of building. Then `buyer` — the public body that put the contract out —, `min_amount`, `max_amount`, `date_from`, `date_to` and `limit`.

### Fixed

- **`meta` reaches the model.** The client kept `data` and dropped everything else, so `meta.has_more` and `meta.years` — announced in 0.7.0 — never left the API. A model could not say there were more results, nor which years held them, and narrowing was guesswork.
- **A rejected value comes back with the valid ones.** The API answers an unknown status or act type with the list of good ones; the client turned that into a bare `HTTP 400`, leaving the model to guess the same wrong word again.

## [0.8.0] — 2026-08-14

### Added

- **`limit` in `dataprem_borme_search`.** The API had it — 25 by default, capped at 100 — but the schema never offered it, so when the answer said there were more and the user asked to see them, repeating the call returned the same 25. Narrowing by date or act type is still the better answer, and the description keeps saying so: a year of a large group is hundreds of filings, not tens.

### Changed

- **`act_type` is matched however it is written.** It used to be compared letter by letter, accents and capitals included, and anything else came back as an empty list — which reads as "this company has no such filings". Now it is compared without case or accents, and an unknown type is refused with the list of valid ones instead of silently finding nothing. The description also stops implying there are sixteen types: it names `Otros conceptos`, which is over a million acts on its own.

## [0.7.0] — 2026-08-13

### Added

- **`act_type` in `dataprem_borme_search`.** Searching a group like Telefónica matches thousands of filings, and the useful question is usually narrower: only the appointments, only the dissolutions. The value is the wording the bulletin itself uses — `Nombramientos`, `Ceses/Dimisiones`, `Constitución`, `Ampliación de capital`… — and the description lists the ones worth asking for.
- The response carries `meta.has_more`, so a model can say there are more without inventing a figure. It is deliberately not a count: counting a common name takes minutes against seventeen years of bulletin, where the search itself takes a fifth of a second.

### Changed

- The BORME is no longer a planned source. It answers with data from 02-01-2009 onwards, most recent first, and the description says so and tells a model to narrow by date or act type rather than ask for a bigger page.

### Compatibility

- Additive. 0.6.0 keeps working against the same API: it does not send `act_type`, and a request without it behaves exactly as before.

## [0.6.0] — 2026-08-07

### Changed

- **The province is required when looking a property up by address.** The Catastro refuses the search without it (`error 11: LA PROVINCIA ES OBLIGATORIA`), and the description of `dataprem_catastro_lookup` said it was optional. A model reading that sent `address` + `city`, got a refusal it could not act on, and told the user the address was wrong — which it was not. The API now turns the request away naming the field, and the description here says the three values are needed.
- Only the wording changed. Tool names, signatures and schemas are what 0.5.0 returned.

### Fixed

- The bundled catalogue no longer describes itself as the source. It is a copy of `config/tools.json` in the DataPrem API, kept as the floor the server falls back to when the API is unreachable; its note used to say "edit here", which is the one thing not to do to a copy. 0.5.0 shipped the old wording, so an installation that could not reach the API handed clients the previous contract.

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
