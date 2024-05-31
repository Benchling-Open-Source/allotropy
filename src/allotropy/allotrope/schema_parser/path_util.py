from collections.abc import Mapping
import importlib
import os
from pathlib import Path
import re
from typing import Any

ALLOTROPE_DIR = os.path.join(Path(__file__).parent.parent)
SCHEMA_DIR_PATH = os.path.join(ALLOTROPE_DIR, "schemas")
SHARED_SCHEMAS_PATH = os.path.join(SCHEMA_DIR_PATH, "shared", "definitions")
UNITS_SCHEMAS_PATH = os.path.join(SHARED_SCHEMAS_PATH, "units.json")
CUSTOM_SCHEMAS_PATH = os.path.join(SHARED_SCHEMAS_PATH, "custom.json")
MODEL_DIR_PATH = os.path.join(ALLOTROPE_DIR, "models")
SHARED_MODELS_PATH = os.path.join(MODEL_DIR_PATH, "shared", "definitions")
UNITS_MODELS_PATH = os.path.join(SHARED_MODELS_PATH, "units.py")
CUSTOM_MODELS_PATH = os.path.join(SHARED_MODELS_PATH, "custom.py")
GENERATED_SHARED_PATHS = [
    UNITS_SCHEMAS_PATH,
    UNITS_MODELS_PATH,
    CUSTOM_SCHEMAS_PATH,
    CUSTOM_MODELS_PATH,
]


def get_schema_path_from_manifest(manifest: str) -> str:
    match = re.match(r"http://purl.allotrope.org/manifests/(.*)\.manifest", manifest)
    if not match:
        msg = f"No matching schema in repo for manifest: {manifest}"
        raise ValueError(msg)
    return f"{match.groups()[0]}.json"


def get_model_file_from_rel_schema_path(rel_schema_path: Path) -> str:
    return re.sub(
        "/|-", "_", f"{rel_schema_path.parent}_{rel_schema_path.stem}.py"
    ).lower()


def get_model_class_from_schema(asm: Mapping[str, Any]) -> Any:
    schema_path = get_schema_path_from_manifest(asm["$asm.manifest"])
    model_file = get_model_file_from_rel_schema_path(Path(schema_path))
    import_path = f"allotropy.allotrope.models.{model_file[:-3]}"
    # NOTE: it is safe to assume that every schema module has Model, as we generate this code.
    return importlib.import_module(import_path).Model


def get_schema_and_model_paths(
    root_dir: Path, rel_schema_path: Path
) -> tuple[Path, Path]:
    schema_path = Path(root_dir, SCHEMA_DIR_PATH, rel_schema_path)
    model_file = get_model_file_from_rel_schema_path(rel_schema_path)
    model_path = Path(root_dir, MODEL_DIR_PATH, model_file)
    return schema_path, model_path
