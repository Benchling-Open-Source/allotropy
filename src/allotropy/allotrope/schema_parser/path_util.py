from collections.abc import Mapping
import importlib
from pathlib import Path, PurePosixPath, PureWindowsPath
import re
from typing import Any

ALLOTROPE_DIR: Path = Path(__file__).parent.parent
ALLOTROPY_DIR: Path = ALLOTROPE_DIR.parent
ROOT_DIR: Path = ALLOTROPE_DIR.parent.parent.parent
SCHEMA_DIR_PATH: Path = Path(ALLOTROPE_DIR, "schemas")
SHARED_SCHEMAS_PATH: Path = Path(SCHEMA_DIR_PATH, "shared")
SHARED_SCHEMAS_DEFINITIONS_PATH: Path = Path(SHARED_SCHEMAS_PATH, "definitions")
UNITS_SCHEMAS_PATH: Path = Path(SHARED_SCHEMAS_DEFINITIONS_PATH, "units.json")
CUSTOM_SCHEMAS_PATH: Path = Path(SHARED_SCHEMAS_DEFINITIONS_PATH, "custom.json")
MODEL_DIR_PATH: Path = Path(ALLOTROPE_DIR, "models")
SHARED_MODELS_PATH: Path = Path(MODEL_DIR_PATH, "shared")
SHARED_MODELS_DEFINITIONS_PATH: Path = Path(SHARED_MODELS_PATH, "definitions")
UNITS_MODELS_PATH: Path = Path(SHARED_MODELS_DEFINITIONS_PATH, "units.py")
CUSTOM_MODELS_PATH: Path = Path(SHARED_MODELS_DEFINITIONS_PATH, "custom.py")
GENERATED_SHARED_PATHS: list[Path] = [
    UNITS_SCHEMAS_PATH,
    UNITS_MODELS_PATH,
    CUSTOM_SCHEMAS_PATH,
    CUSTOM_MODELS_PATH,
]


def get_rel_schema_path(schema_path: Path) -> Path:
    try:
        return schema_path.relative_to(SCHEMA_DIR_PATH)
    except ValueError as err:
        if not Path(SCHEMA_DIR_PATH, schema_path).exists():
            msg = f"Invalid schema path: {schema_path}"
            raise ValueError(msg) from err
        return schema_path


def get_full_schema_path(schema_path: Path) -> Path:
    if str(schema_path).startswith(str(SCHEMA_DIR_PATH)):
        return schema_path
    return Path(SCHEMA_DIR_PATH, schema_path)


def get_manifest_from_schema_path(schema_path: Path) -> str:
    rel_schema_path = get_rel_schema_path(schema_path)
    if not rel_schema_path.parts[0] == "adm" or not str(rel_schema_path).endswith(
        ".schema.json"
    ):
        msg = f"Invalid schema path: {rel_schema_path}"
        raise ValueError(msg)
    return f"http://purl.allotrope.org/manifests/{str(PurePosixPath(rel_schema_path))[4:-12]}.manifest"


def get_schema_path_from_manifest(manifest: str) -> Path:
    match = re.match(r"http://purl.allotrope.org/manifests/(.*)\.manifest", manifest)
    if not match:
        msg = f"No matching schema in repo for manifest: {manifest}"
        raise ValueError(msg)
    return Path(f"adm/{match.groups()[0]}.schema.json")


def get_schema_path_from_reference(reference: str) -> Path:
    ref_match = re.match(r"http://purl.allotrope.org/json-schemas/(.*)", reference)
    if not ref_match:
        msg = f"Could not parse reference: {reference}"
        raise ValueError(msg)
    return Path(f"{ref_match.groups()[0]}.json")


def get_model_file_from_schema_path(schema_path: Path) -> Path:
    rel_schema_path = PureWindowsPath(get_rel_schema_path(schema_path))
    schema_file = rel_schema_path.name
    model_file = schema_file.replace(".schema.json", ".py").replace("-", "_").lower()
    model_path = Path(
        *[
            re.sub("^([0-9]+)$", r"_\1", part.lower().replace("-", "_"))
            for part in rel_schema_path.parent.parts
        ]
    )
    return Path(model_path, model_file)


def get_import_path_from_path(model_path: Path) -> str:
    # NOTE: PureWindowsPath handles both Windows and linux paths.
    return (
        f"allotropy.allotrope.models.{'.'.join(PureWindowsPath(model_path).parts)[:-3]}"
    )


def get_model_class_from_schema(asm: Mapping[str, Any]) -> Any:
    schema_path = get_schema_path_from_manifest(asm["$asm.manifest"])
    model_file = get_model_file_from_schema_path(Path(schema_path))
    import_path = get_import_path_from_path(model_file)
    # NOTE: it is safe to assume that every schema module has Model, as we generate this code.
    return importlib.import_module(import_path).Model
