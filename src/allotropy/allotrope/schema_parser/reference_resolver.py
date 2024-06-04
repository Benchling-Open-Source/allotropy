from pathlib import Path
from typing import Any
import urllib.request

from allotropy.allotrope.schema_parser.path_util import (
    get_full_schema_path,
    get_schema_path_from_reference,
)


def _get_schema_from_reference(reference: str) -> str:
    return reference.split("#/$defs")[0]


def _get_references(schema: dict[str, Any]) -> set[str]:
    """Get all references ($ref:) from the given schema."""
    references = set()
    for key, value in schema.items():
        if key == "$ref":
            references.add(_get_schema_from_reference(value))
        elif isinstance(value, dict):
            references |= _get_references(value)
        elif isinstance(value, list):
            for v in value:
                references |= _get_references(v)
    return references


def _download_schema(reference: str, schema_path: Path) -> None:
    schema_path = get_full_schema_path(schema_path)
    if not schema_path.parent.exists():
        schema_path.parent.mkdir(parents=True, exist_ok=True)
    if not reference.startswith(("http:", "https:")):
        msg = f"Invald URL {reference}"
        raise ValueError(msg)
    # NOTE: S310 checks that you do not access a URL without checking it is a valid http url.
    # the code above does this, exactly as the documentation recommends, but it is still being
    # flagged, so ignore it.
    urllib.request.urlretrieve(reference, schema_path)  # noqa: S310


def _download_references(references: set[str]) -> set[Path]:
    """Downloads all references to the schemas directory, returning the corresponding paths."""
    schema_paths: set[Path] = set()
    for reference in references:
        if reference.startswith("http"):
            schema_path = get_schema_path_from_reference(reference)
            if not schema_path.exists():
                _download_schema(reference, schema_path)
            schema_paths.add(schema_path)
        else:
            if not Path(reference).exists():
                msg = f"Custom schema at path: '{reference}' does not exist, did you forget to add it?"
                raise AssertionError(msg)
            schema_paths.add(Path(reference))
    return schema_paths


def download_all_references_schemas_for_schema(schema: dict[str, Any]) -> set[Path]:
    references = _get_references(schema)
    return _download_references(references)
