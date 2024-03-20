import json
import os
from pathlib import Path
import re
import subprocess  # noqa: S404, RUF100
from typing import Optional

from autoflake import fix_file  # type: ignore[import-untyped]
from datamodel_code_generator import (
    DataModelType,
    generate,
    InputFileType,
    PythonVersion,
)

from allotropy.allotrope.schema_parser.backup_manager import (
    backup,
    is_file_changed,
    restore_backup,
)
from allotropy.allotrope.schema_parser.model_class_editor import modify_file
from allotropy.allotrope.schemas import get_schema

SCHEMA_DIR_PATH = "src/allotropy/allotrope/schemas"
MODEL_DIR_PATH = "src/allotropy/allotrope/models"


def lint_file(model_path: str) -> None:
    # The first run of ruff changes typing annotations and causes unused imports. We catch failure
    # due to unused imports.
    try:
        subprocess.check_call(
            f"ruff {model_path} --fix",
            shell=True,  # noqa: S602
            stdout=subprocess.DEVNULL,
        )
    except subprocess.CalledProcessError:
        pass
    # The call to autoflake.fix_file removes unused imports.
    fix_file(
        model_path,
        {
            "in_place": True,
            "remove_unused_variables": True,
            "write_to_stdout": False,
            "ignore_init_module_imports": False,
            "expand_star_imports": False,
            "remove_all_unused_imports": True,
            "remove_duplicate_keys": True,
            "remove_rhs_for_unused_variables": False,
            "ignore_pass_statements": False,
            "ignore_pass_after_docstring": False,
            "check": False,
            "check_diff": False,
        },
    )
    # The second call to ruff checks for additional rules.
    subprocess.check_call(
        f"ruff {model_path} --fix", shell=True, stdout=subprocess.DEVNULL  # noqa: S602
    )
    subprocess.check_call(
        f"black {model_path}", shell=True, stderr=subprocess.DEVNULL  # noqa: S602
    )


def _get_schema_and_model_paths(
    root_dir: Path, rel_schema_path: Path
) -> tuple[Path, Path]:
    schema_path = Path(root_dir, SCHEMA_DIR_PATH, rel_schema_path)
    model_file = re.sub(
        "/|-", "_", f"{rel_schema_path.parent}_{rel_schema_path.stem}.py"
    ).lower()
    model_path = Path(root_dir, MODEL_DIR_PATH, model_file)
    return schema_path, model_path


def _generate_schema(
    model_path: Path, schema_path: Path, rel_schema_path: Path
) -> None:
    # get_schema adds extra defs from shared definitions to the schema.
    schema = get_schema(str(rel_schema_path))
    with open(schema_path, "w") as f:
        json.dump(schema, f)

    # Generate models
    generate(
        input_=schema_path,
        output=model_path,
        output_model_type=DataModelType.DataclassesDataclass,
        input_file_type=InputFileType.JsonSchema,
        # Specify base_class as empty when using dataclass
        base_class="",
        target_python_version=PythonVersion.PY_39,
        use_union_operator=False,
    )
    # Import classes from shared files, remove unused classes, format.
    modify_file(str(model_path), str(schema_path))
    lint_file(str(model_path))


def generate_schemas(
    root_dir: Path,
    *,
    dry_run: Optional[bool] = False,
    schema_regex: Optional[str] = None,
) -> list[str]:
    """Generate schemas from JSON schema files.

    :root_dir: The root directory of the project.
    :dry_run: If true, does not save changes to any models, but still returns the list of models that would change.
    :schema_regex: If set, filters schemas to generate using regex.
    :return: A list of model files that were changed.
    """

    os.chdir(os.path.join(root_dir, SCHEMA_DIR_PATH))
    schema_paths = list(Path(".").rglob("*.json"))
    os.chdir(os.path.join(root_dir))
    models_changed = []
    for rel_schema_path in schema_paths:
        if rel_schema_path.parts[0] == "shared":
            continue
        if schema_regex and not re.match(schema_regex, str(rel_schema_path)):
            continue

        print(f"Generating models for schema: {rel_schema_path}...")  # noqa: T201
        schema_path, model_path = _get_schema_and_model_paths(root_dir, rel_schema_path)

        with backup(model_path, restore=dry_run), backup(schema_path, restore=True):
            _generate_schema(model_path, schema_path, rel_schema_path)

            if is_file_changed(model_path):
                models_changed.append(Path(model_path).stem)
            else:
                restore_backup(model_path)

    return models_changed
