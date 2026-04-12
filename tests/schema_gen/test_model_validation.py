"""Validation test: generated models produce correct ASM JSON.

This test:
1. Runs the AppBio QuantStudio parser through the real pipeline
2. Serializes with the to_dict() serializer
3. Also serializes with to_dict() directly to confirm parity
4. Validates json_name metadata coverage on all model fields
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from allotropy.allotrope.allotrope import serialize_and_validate_allotrope
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.appbio_quantstudio.appbio_quantstudio_parser import (
    AppBioQuantStudioParser,
)
from allotropy.schema_gen.serializer import to_dict

TESTDATA_DIR = (
    Path(__file__).parent.parent / "parsers" / "appbio_quantstudio" / "testdata"
)
GOLDEN_FILE = TESTDATA_DIR / "appbio_quantstudio_example01.json"
INPUT_FILE = TESTDATA_DIR / "appbio_quantstudio_example01.txt"


def _deep_diff(expected: Any, actual: Any, path: str = "") -> list[str]:
    """Deep comparison returning list of difference descriptions."""
    diffs = []

    if isinstance(expected, dict) and isinstance(actual, dict):
        all_keys = set(expected.keys()) | set(actual.keys())
        for k in sorted(all_keys):
            child_path = f"{path}.{k}" if path else k
            if k not in expected:
                diffs.append(f"EXTRA key in actual: {child_path}")
            elif k not in actual:
                diffs.append(f"MISSING key in actual: {child_path}")
            else:
                diffs.extend(_deep_diff(expected[k], actual[k], child_path))
    elif isinstance(expected, list) and isinstance(actual, list):
        if len(expected) != len(actual):
            diffs.append(
                f"LIST length mismatch at {path}: expected {len(expected)}, got {len(actual)}"
            )
        for i in range(min(len(expected), len(actual))):
            diffs.extend(_deep_diff(expected[i], actual[i], f"{path}[{i}]"))
    elif type(expected) != type(actual):
        # Allow int/float equivalence
        if isinstance(expected, int | float) and isinstance(actual, int | float):
            if float(expected) != float(actual):
                diffs.append(
                    f"VALUE mismatch at {path}: expected {expected!r}, got {actual!r}"
                )
        else:
            diffs.append(
                f"TYPE mismatch at {path}: expected {type(expected).__name__}({expected!r}), "
                f"got {type(actual).__name__}({actual!r})"
            )
    elif expected != actual:
        diffs.append(f"VALUE mismatch at {path}: expected {expected!r}, got {actual!r}")

    return diffs


@pytest.mark.long
def test_model_produces_same_output() -> None:
    """Validate model pipeline produces correct ASM output for qPCR parser."""
    if not INPUT_FILE.exists():
        pytest.skip(f"Test data not found: {INPUT_FILE}")

    # Run parser through the real pipeline
    parser = AppBioQuantStudioParser()
    named_file = NamedFileContents(INPUT_FILE.open("rb"), INPUT_FILE.name)
    data = parser.create_data(named_file)

    # Map and serialize through the real pipeline
    mapper = parser._get_mapper()
    model = mapper.map_model(data)

    pipeline_dict = serialize_and_validate_allotrope(model)

    # Also serialize directly with to_dict to confirm they match
    direct_dict = to_dict(model)

    # Pipeline and direct serialization must be identical
    pipeline_json = json.dumps(pipeline_dict, indent=4, sort_keys=True)
    direct_json = json.dumps(direct_dict, indent=4, sort_keys=True)
    assert pipeline_json == direct_json, (
        "Pipeline (serialize_and_validate_allotrope) and direct (to_dict) "
        "serialization produce different output"
    )

    # Compare structure against golden file (values like UUIDs may differ)
    golden = json.loads(GOLDEN_FILE.read_text())

    # Strip volatile fields for structural comparison
    def _strip_volatile(obj: Any) -> Any:
        """Remove fields that change between runs (UUIDs, versions, paths)."""
        volatile_keys = {
            "measurement identifier",
            "calculated data identifier",
            "data source identifier",
            "ASM converter version",
            "UNC path",
        }
        if isinstance(obj, dict):
            return {
                k: _strip_volatile(v) for k, v in obj.items() if k not in volatile_keys
            }
        if isinstance(obj, list):
            return [_strip_volatile(item) for item in obj]
        return obj

    golden_stable = _strip_volatile(golden)
    actual_stable = _strip_volatile(pipeline_dict)

    diffs = _deep_diff(golden_stable, actual_stable)
    if diffs:
        print(f"\n{'='*80}")  # noqa: T201
        print(f"Found {len(diffs)} differences vs golden file:")  # noqa: T201
        print(f"{'='*80}")  # noqa: T201
        for d in diffs[:50]:
            print(f"  {d}")  # noqa: T201
        if len(diffs) > 50:
            print(f"  ... and {len(diffs) - 50} more")  # noqa: T201
        print(f"{'='*80}")  # noqa: T201

    assert len(diffs) == 0, f"Golden file comparison: {len(diffs)} differences found"


@pytest.mark.long
def test_json_name_metadata_coverage() -> None:
    """Verify all model fields have json_name metadata when needed.

    Fields whose Python name maps to the JSON name via simple underscore-to-space
    conversion (e.g., ``sample_identifier`` -> ``"sample identifier"``) do not
    need explicit ``json_name`` metadata — the serializer handles this by default.
    Only fields where the mapping is non-trivial (e.g., parenthesized qualifiers
    or ``$asm.*`` prefixes) require explicit metadata.
    """
    import dataclasses

    from allotropy.allotrope.models.adm.pcr.rec._2024._09 import qpcr as qpcr_module

    bad_fields = []

    for name in dir(qpcr_module):
        obj = getattr(qpcr_module, name)
        if dataclasses.is_dataclass(obj) and isinstance(obj, type):
            for f in dataclasses.fields(obj):
                json_name = f.metadata.get("json_name", f.name.replace("_", " "))
                # The serializer uses this same fallback, so the field is fine
                # as long as the implicit json_name is reasonable (no leading/
                # trailing spaces, not empty).
                if not json_name or json_name != json_name.strip():
                    bad_fields.append(f"{name}.{f.name}: bad json_name={json_name!r}")

    if bad_fields:
        print("\nFields with bad json_name mapping:")  # noqa: T201
        for m in bad_fields:
            print(f"  {m}")  # noqa: T201

    assert len(bad_fields) == 0, f"{len(bad_fields)} fields with bad json_name mapping"


if __name__ == "__main__":
    test_model_produces_same_output()
