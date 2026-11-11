from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path

from allotropy.allotrope.path_util import SCHEMA_DIR_PATH
from allotropy.allotrope.schemas import validate_asm_schema
from allotropy.exceptions import AllotropeValidationError


def test_custom_schemas_have_changenotes() -> None:
    for file in Path(SCHEMA_DIR_PATH).glob("**/*.json"):
        if "shared" in str(file):
            continue
        if "BENCHLING" in str(file):
            assert Path(file.parent, "CHANGE_NOTES.md").exists()


def test_validate_asm_schema_is_thread_safe() -> None:
    # validate_asm_schema caches one validator per schema. jsonschema's
    # RefResolver keeps a mutable scope stack, so a validator shared across
    # threads resolved $refs against another thread's scope and rejected valid
    # documents with "Unresolvable JSON pointer".
    asm = json.loads(
        Path(
            "tests/parsers/moldev_softmax_pro/testdata/"
            "MD_SMP_absorbance_endpoint_example01.json"
        ).read_text()
    )
    validate_asm_schema(asm)

    def validate(_: int) -> str | None:
        try:
            validate_asm_schema(asm)
        except AllotropeValidationError as e:
            return str(e)
        return None

    with ThreadPoolExecutor(max_workers=4) as executor:
        errors = [error for error in executor.map(validate, range(32)) if error]

    assert not errors, f"{len(errors)} of 32 concurrent validations failed: {errors[0]}"
