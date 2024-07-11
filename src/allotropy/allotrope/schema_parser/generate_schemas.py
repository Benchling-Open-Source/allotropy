from pathlib import Path
import re
import subprocess
import warnings  # noqa: S404, RUF100

from autoflake import fix_file  # type: ignore[import-untyped]
from datamodel_code_generator import (
    DataModelType,
    generate,
    InputFileType,
    PythonVersion,
)

from allotropy.allotrope.schema_parser.backup_manager import (
    backup,
    is_backup_file,
    is_file_changed,
    restore_backup,
)
from allotropy.allotrope.schema_parser.model_class_editor import modify_file
from allotropy.allotrope.schema_parser.path_util import (
    CUSTOM_MODELS_PATH,
    GENERATED_SHARED_PATHS,
    get_model_file_from_schema_path,
    get_rel_schema_path,
    MODEL_DIR_PATH,
    SCHEMA_DIR_PATH,
    UNITS_MODELS_PATH,
)
from allotropy.allotrope.schema_parser.schema_cleaner import SchemaCleaner
from allotropy.allotrope.schema_parser.update_units import update_unit_files


def lint_file(model_path: Path) -> None:
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
        str(model_path),
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


def _generate_schema(model_path: Path, schema_path: Path) -> None:
    with warnings.catch_warnings():
        # We expect duplicated field names for variations with an anyOf schema.
        warnings.filterwarnings(
            "ignore",
            category=UserWarning,
            message="Field name `.*` is duplicated on .*",
        )
        # Known issue - it is OK to treat iri as a string for our purposes.
        warnings.filterwarnings(
            "ignore",
            category=UserWarning,
            message=re.escape(
                "format of 'iri' not understood for 'string' - using default"
            ),
        )
        # Generate models
        generate(
            input_=schema_path,
            output=model_path,
            output_model_type=DataModelType.DataclassesDataclass,
            input_file_type=InputFileType.JsonSchema,
            # Specify base_class as empty when using dataclass
            base_class="",
            target_python_version=PythonVersion.PY_310,
            use_union_operator=True,
        )
        # Import classes from shared files, remove unused classes, format.
        modify_file(model_path, schema_path)
        lint_file(model_path)


def _should_generate_schema(schema_path: Path, schema_regex: str | None = None) -> bool:
    # Skip files in the shared directory
    rel_schema_path = str(get_rel_schema_path(schema_path))
    if rel_schema_path.startswith("shared"):
        return False
    if is_backup_file(rel_schema_path):
        return False
    if schema_regex:
        return bool(re.match(schema_regex, str(rel_schema_path)))
    return True


def make_model_directories(model_path: Path) -> None:
    if model_path == MODEL_DIR_PATH:
        return

    # Call recursively on parents first. We can't just create all directories
    # with a single call, because we want to create __init__ files too.
    make_model_directories(model_path.parent)
    if model_path.exists():
        return
    model_path.mkdir()
    init_path = Path(model_path, "__init__.py")
    if not init_path.exists():
        init_path.touch()


def generate_schemas(
    *,
    dry_run: bool | None = False,
    schema_regex: str | None = None,
) -> list[str]:
    """Generate schemas from JSON schema files.
    :dry_run: If true, does not save changes to any models, but still returns the list of models that would change.
    :schema_regex: If set, filters schemas to generate using regex.
    :return: A list of model files that were changed.
    """
    unit_to_iri: dict[str, str] = {}
    with backup(GENERATED_SHARED_PATHS, restore=dry_run):
        schema_paths = list(Path(SCHEMA_DIR_PATH).rglob("*.json"))
        models_changed = []
        for schema_path in schema_paths:
            if not _should_generate_schema(schema_path, schema_regex):
                continue

            print(  # noqa: T201
                f"Generating models for schema: {get_rel_schema_path(schema_path)}..."
            )
            model_path = Path(
                MODEL_DIR_PATH, get_model_file_from_schema_path(schema_path)
            )
            make_model_directories(model_path.parent)

            with backup(model_path, restore=dry_run), backup(schema_path, restore=True):
                schema_cleaner = SchemaCleaner()
                schema_cleaner.clean_file(str(schema_path))
                unit_to_iri |= schema_cleaner.get_referenced_units()
                _generate_schema(model_path, schema_path)

                if is_file_changed(model_path):
                    models_changed.append(model_path.stem)
                else:
                    restore_backup(model_path)

        update_unit_files(unit_to_iri)
        for path in [UNITS_MODELS_PATH, CUSTOM_MODELS_PATH]:
            lint_file(path)

    return models_changed
