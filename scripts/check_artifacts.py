"""Refuse to publish an artifact that carries more than the package.

Reading the build configuration is not enough: what matters is what ends up
inside the archive, so this opens the built files and looks.

Usage: python scripts/check_artifacts.py [dist]
"""

from __future__ import annotations

import re
import sys
import tarfile
import zipfile
from pathlib import Path

# Paths that must never leave the repository, matched against the member path
# with the top-level directory of the archive stripped.
FORBIDDEN_PATHS = (
    ".idea/",
    ".github/",
    ".env",
    "compose.yaml",
    "Dockerfile",
)

# Tracker keys belong in the tracker, not in a file PyPI renders as the
# project page. Standards are written the same way, hence the exceptions.
FORBIDDEN_CONTENT = re.compile(r"\b([A-Z]{2,5})-\d+\b")
CONTENT_EXCEPTIONS = frozenset(
    {"ISO", "RFC", "UTF", "SHA", "AES", "TLS", "HTTP", "IPV", "ECLI", "PEP"}
)

TEXT_SUFFIXES = {".py", ".md", ".toml", ".txt", ".cfg", ".yaml", ".yml", ""}


def members_of(archive: Path) -> list[tuple[str, bytes]]:
    """(path relative to the archive root, contents) for every regular file."""
    if archive.suffix == ".whl":
        with zipfile.ZipFile(archive) as zf:
            return [(i.filename, zf.read(i)) for i in zf.infolist() if not i.is_dir()]

    with tarfile.open(archive) as tf:
        out = []
        for member in tf.getmembers():
            if not member.isfile():
                continue
            # Strip the `name-version/` prefix the sdist wraps everything in.
            relative = member.name.split("/", 1)[1] if "/" in member.name else member.name
            handle = tf.extractfile(member)
            out.append((relative, handle.read() if handle else b""))
        return out


def check(archive: Path) -> list[str]:
    problems = []

    for path, content in members_of(archive):
        for forbidden in FORBIDDEN_PATHS:
            if path == forbidden or path.startswith(forbidden):
                problems.append(f"{archive.name}: ships {path}")
                break

        if Path(path).suffix not in TEXT_SUFFIXES:
            continue

        text = content.decode("utf-8", errors="ignore")
        found = {
            match.group(0)
            for match in FORBIDDEN_CONTENT.finditer(text)
            if match.group(1) not in CONTENT_EXCEPTIONS
        }
        if found:
            problems.append(f"{archive.name}: {path} mentions {', '.join(sorted(found))}")

    return problems


def main(argv: list[str]) -> int:
    dist = Path(argv[0]) if argv else Path("dist")
    archives = sorted(dist.glob("*.tar.gz")) + sorted(dist.glob("*.whl"))

    if not archives:
        print(f"check: no artifact in {dist}/ — run `uv build` first", file=sys.stderr)
        return 1

    problems = [problem for archive in archives for problem in check(archive)]

    for problem in problems:
        print(f"check: {problem}", file=sys.stderr)

    if problems:
        return 1

    print(f"check: {len(archives)} artifacts carry only the package")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
