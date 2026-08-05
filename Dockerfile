# syntax=docker/dockerfile:1.7
# Multi-stage build for the dataprem-mcp HTTP transport. Desktop users keep
# running `uvx dataprem-mcp` (stdio) — this image is for server-side clients
# (e.g. dataprem-chat) that need a long-running MCP process over HTTP.

FROM python:3.12-slim AS builder

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /build

# Install build dependency separately so layer cache survives source edits.
COPY pyproject.toml README.md /build/
COPY src /build/src

RUN pip install --upgrade pip build && \
    pip install --prefix=/install .


FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/usr/local/bin:${PATH}"

# Run as unprivileged user — no need to read/write anything outside /tmp.
RUN groupadd --system --gid 1000 mcp && \
    useradd  --system --uid 1000 --gid mcp --create-home --home-dir /home/mcp mcp

COPY --from=builder /install /usr/local

USER mcp
WORKDIR /home/mcp

EXPOSE 8080

# Default to streamable-http on 0.0.0.0:8080 — the image only makes sense for
# server-side consumers; desktop users would use `uvx dataprem-mcp` directly.
ENTRYPOINT ["python", "-m", "dataprem_mcp"]
CMD ["--transport", "streamable-http", "--host", "0.0.0.0", "--port", "8080"]
