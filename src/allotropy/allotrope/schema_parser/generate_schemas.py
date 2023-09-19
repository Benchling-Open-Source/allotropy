import json
import os
from pathlib import Path
import re
import subprocess  # noqa: S404, RUF100

from autoflake import fix_file  # type: ignore[import]
from datamodel_code_generator import (
    DataModelType,
    generate,
    InputFileType,
    PythonVersion,
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


def files_equal(path1: str, path2: str) -> bool:
    with open(path1) as file1, open(path2) as file2:
        for line1, line2 in zip(file1, file2):
            if line1 != line2 and not line1.startswith("#   timestamp:"):
                return False
    return True


def generate_schemas(root_dir: Path) -> int:
    """Generate schemas from JSON schema files.

    :root_dir: The root directory of the project.
    :return: The number of schemas generated.
    """

    os.chdir(os.path.join(root_dir, SCHEMA_DIR_PATH))
    schema_paths = list(Path(".").rglob("*.json"))
    os.chdir(os.path.join(root_dir))
    number_generated = 0
    for rel_schema_path in schema_paths:
        if str(rel_schema_path).startswith("shared"):
            continue
        print(f"Generating models for schema: {rel_schema_path}...")  # noqa: T201
        schema_name = rel_schema_path.stem
        schema_path = os.path.join(root_dir, SCHEMA_DIR_PATH, rel_schema_path)
        output_file = re.sub(
            "/|-", "_", f"{rel_schema_path.parent}_{schema_name}.py"
        ).lower()
        model_path = os.path.join(root_dir, MODEL_DIR_PATH, output_file)
        model_backup_path = f"{model_path}.bak"
        schema_backup_path = f"{schema_path}.bak"

        # Backup model to do diff after generation
        if os.path.exists(model_path):
            os.rename(model_path, model_backup_path)

        # Backup schema and override with extra defs
        schema = get_schema(str(rel_schema_path))
        os.rename(schema_path, schema_backup_path)
        with open(schema_path, "w") as f:
            json.dump(schema, f)

        # Generate models
        generate(
            input_=Path(schema_path),
            output=Path(model_path),
            output_model_type=DataModelType.DataclassesDataclass,
            input_file_type=InputFileType.JsonSchema,
            # Specify base_class as empty when using dataclass
            base_class="",
            target_python_version=PythonVersion.PY_39,
            use_union_operator=False,
        )
        # Import classes from shared files, remove unused classes, format.
        modify_file(model_path, schema_path)
        lint_file(model_path)

        # Restore backups
        if os.path.exists(model_backup_path):
            if files_equal(model_path, model_backup_path):
                os.rename(model_backup_path, model_path)
            else:
                os.remove(model_backup_path)
        os.rename(schema_backup_path, schema_path)

        number_generated += 1

    return number_generated
