"""Resolve technique shorthand (e.g. "plate-reader 2026/03") to purl URLs.

Supports fuzzy matching of technique names against the GitLab directory listing
and automatic discovery of all schema files within a technique+version directory.
"""

from __future__ import annotations

import difflib
import json
import re
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

import click

from allotropy.schema_gen.naming import ALLOTROPE_URL_PREFIX

# GitLab API base for the Allotrope public ASM repository
_GITLAB_API_BASE = (
    "https://gitlab.com/api/v4/projects/allotrope-public%2Fasm/repository/tree"
)

_VALID_STATUSES = {"REC", "WD", "BENCHLING"}

# Matches: "plate-reader 2026/03" or "pcr REC/2026/03" or "pcr benchling/2024/11"
_RE_SHORTHAND = re.compile(
    r"^(?P<technique>\S+)"
    r"\s+"
    r"(?:(?P<status>[a-zA-Z]+)/)?"
    r"(?P<year>\d{4})/(?P<month>\d{2})$",
)


def is_shorthand(input_str: str) -> bool:
    """Return True if the input is a technique shorthand, not a full URL."""
    return not input_str.startswith(("http://", "https://"))


def parse_shorthand(input_str: str) -> tuple[str, str, str, str]:
    """Parse shorthand into (technique, status, year, month).

    Status defaults to "REC" if not provided.

    Raises:
        click.UsageError: If the input doesn't match the expected format.
    """
    match = _RE_SHORTHAND.match(input_str.strip())
    if not match:
        msg = (
            f"Invalid shorthand format: '{input_str}'\n"
            "Expected: <technique> [<status>/]<year>/<month>\n"
            "Examples: plate-reader 2026/03, pcr WD/2025/06"
        )
        raise click.UsageError(msg)

    technique = match.group("technique").lower()
    status = (match.group("status") or "REC").upper()
    year = match.group("year")
    month = match.group("month")

    if status not in _VALID_STATUSES:
        msg = f"Invalid status '{status}'. Must be one of: {', '.join(sorted(_VALID_STATUSES))}"
        raise click.UsageError(msg)

    return technique, status, year, month


def _gitlab_tree(path: str) -> list[dict[str, str]]:
    """Fetch a directory listing from the GitLab API."""
    url = f"{_GITLAB_API_BASE}?path={path}&per_page=100&ref=main"
    try:
        with urlopen(url, timeout=30) as response:  # noqa: S310
            data = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        msg = f"GitLab API error (HTTP {exc.code}) listing {path}"
        raise RuntimeError(msg) from exc
    except URLError as exc:
        msg = f"Network error listing {path}: {exc.reason}"
        raise RuntimeError(msg) from exc
    return data  # type: ignore[no-any-return]


def list_gitlab_techniques() -> list[str]:
    """List all technique directory names from the GitLab ASM repository."""
    entries = _gitlab_tree("json-schemas/adm")
    return sorted(entry["name"] for entry in entries if entry.get("type") == "tree")


def resolve_technique_name(input_name: str, techniques: list[str]) -> str:
    """Resolve a technique name with exact, normalized, or fuzzy matching.

    Returns:
        The matched technique name.

    Raises:
        click.Abort: If no match is found or the user declines the suggestion.
    """
    # Exact match
    if input_name in techniques:
        return input_name

    # Normalized match: underscores -> hyphens, lowercase
    normalized = input_name.replace("_", "-").lower()
    if normalized in techniques:
        return normalized

    # Fuzzy match
    matches = difflib.get_close_matches(normalized, techniques, n=5, cutoff=0.6)

    if not matches:
        click.echo(f"Technique '{input_name}' not found. No similar techniques.")
        click.echo(f"Available techniques: {', '.join(techniques)}")
        raise click.Abort()

    if len(matches) == 1:
        if click.confirm(
            f"Technique '{input_name}' not found. Did you mean '{matches[0]}'?"
        ):
            return matches[0]
        raise click.Abort()

    click.echo(f"Technique '{input_name}' not found. Similar techniques:")
    for i, name in enumerate(matches, 1):
        click.echo(f"  {i}. {name}")
    choice: int = click.prompt(
        "Select a technique",
        type=click.IntRange(1, len(matches)),
    )
    return matches[choice - 1]


def list_schemas_in_directory(
    technique: str, status: str, year: str, month: str
) -> list[str]:
    """List schema filenames in a technique+version directory on GitLab.

    Returns only *.schema.json files, excluding *.embed.schema.json.
    """
    path = f"json-schemas/adm/{technique}/{status}/{year}/{month}"
    try:
        entries = _gitlab_tree(path)
    except RuntimeError:
        msg = f"No schemas found at {technique}/{status}/{year}/{month}"
        raise click.UsageError(msg) from None

    return sorted(
        entry["name"]
        for entry in entries
        if entry.get("type") == "blob"
        and entry["name"].endswith(".schema.json")
        and not entry["name"].endswith(".embed.schema.json")
    )


def resolve_shorthand_to_urls(input_str: str) -> list[str]:
    """Resolve a technique shorthand string to a list of purl URLs.

    This is the main entry point. It parses the shorthand, resolves the
    technique name (with fuzzy matching if needed), discovers all schema
    files in the directory, and constructs purl URLs.
    """
    technique, status, year, month = parse_shorthand(input_str)

    click.echo(f"Looking up technique '{technique}' on GitLab...")
    techniques = list_gitlab_techniques()
    technique = resolve_technique_name(technique, techniques)

    schema_files = list_schemas_in_directory(technique, status, year, month)
    if not schema_files:
        msg = f"No schema files found in {technique}/{status}/{year}/{month}"
        raise click.UsageError(msg)

    urls = []
    for filename in schema_files:
        # Remove .json suffix to get the purl-style path (e.g. plate-reader.schema)
        schema_name = filename.removesuffix(".json")
        url = f"{ALLOTROPE_URL_PREFIX}adm/{technique}/{status}/{year}/{month}/{schema_name}"
        urls.append(url)

    return urls
