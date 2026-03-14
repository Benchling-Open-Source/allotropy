"""Optimized schema generation that runs in memory and in parallel."""

from concurrent.futures import as_completed, ProcessPoolExecutor
import json
from pathlib import Path
import re
import tempfile
from typing import Any
import warnings

from autoflake import fix_code  # type: ignore[import-untyped]
import black
from datamodel_code_generator import (
    DataModelType,
    generate,
    InputFileType,
    PythonVersion,
)

from allotropy.allotrope.schema_parser.backup_manager import (
    backup_paths,
    get_original_path,
)
from allotropy.allotrope.schema_parser.model_class_editor import (
    get_shared_schema_info,
    ModelClassEditor,
)
from allotropy.allotrope.schema_parser.path_util import (
    GENERATED_SHARED_PATHS,
    get_manifest_from_schema_path,
    get_model_path_from_schema_path,
    get_rel_schema_path,
    get_schema_path_from_model_path,
    MODEL_DIR_PATH,
    SCHEMA_DIR_PATH,
)
from allotropy.allotrope.schema_parser.schema_cleaner import SchemaCleaner
from allotropy.allotrope.schema_parser.update_units import update_unit_files
from allotropy.allotrope.schemas import get_schema


def format_code_in_memory(code: str) -> str:
    """Format Python code in memory using black and autoflake."""
    # First pass: fix imports using autoflake
    code = fix_code(
        code,
        remove_all_unused_imports=True,
        remove_unused_variables=True,
        remove_duplicate_keys=True,
        ignore_init_module_imports=False,
    )

    # Second pass: format with black
    try:
        code = black.format_str(code, mode=black.Mode())  # type: ignore[attr-defined]
    except Exception:  # noqa: S110
        # If black fails, return the autoflake-cleaned code
        pass

    return code


def generate_model_in_memory(schema: dict[str, Any]) -> str:
    """Generate model code from schema without writing to disk."""
    with warnings.catch_warnings():
        # Suppress expected warnings
        warnings.filterwarnings(
            "ignore",
            category=UserWarning,
            message="Field name `.*` is duplicated on .*",
        )
        warnings.filterwarnings(
            "ignore",
            category=UserWarning,
            message=re.escape(
                "format of 'iri' not understood for 'string' - using default"
            ),
        )

        # Use a temporary file for the schema (datamodel_code_generator requires a file)
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json") as schema_file:
            json.dump(schema, schema_file)
            schema_file.flush()

            # Generate to a temporary output file
            with tempfile.NamedTemporaryFile(mode="w+", suffix=".py") as output_file:
                generate(
                    input_=Path(schema_file.name),
                    output=Path(output_file.name),
                    output_model_type=DataModelType.DataclassesDataclass,
                    input_file_type=InputFileType.JsonSchema,
                    base_class="",
                    target_python_version=PythonVersion.PY_310,
                    use_union_operator=True,
                )

                # Read the generated content
                output_file.seek(0)
                generated_code = output_file.read()

    return generated_code


def process_single_schema(
    schema_path: Path, schema_regex: str | None = None
) -> tuple[str | None, dict[str, str], str | None]:
    """Process a single schema file and return (model_name, units, generated_code)."""
    rel_schema_path = str(get_rel_schema_path(schema_path))

    # Check if should process
    if rel_schema_path.startswith("shared"):
        return None, {}, None
    if schema_regex and not re.match(schema_regex, rel_schema_path):
        return None, {}, None

    print(f"Generating models for schema: {rel_schema_path}...")  # noqa: T201

    # Clean schema and get units
    schema_cleaner = SchemaCleaner()
    schema = schema_cleaner.clean(get_schema(schema_path))
    unit_to_iri = schema_cleaner.get_referenced_units()

    # Generate model code in memory
    generated_code = generate_model_in_memory(schema)

    # Modify the generated code (imports, etc.)
    model_path = Path(MODEL_DIR_PATH, get_model_path_from_schema_path(schema_path))
    schema_path_for_manifest = get_schema_path_from_model_path(
        get_original_path(model_path)
    )

    classes_to_skip, imports_to_add = get_shared_schema_info(schema)
    manifest = get_manifest_from_schema_path(schema_path_for_manifest)
    editor = ModelClassEditor(
        manifest, classes_to_skip, imports_to_add, schema_path_for_manifest.name
    )
    modified_code = editor.modify_file(generated_code)

    # Format the code in memory
    formatted_code = format_code_in_memory(modified_code)

    model_path = Path(MODEL_DIR_PATH, get_model_path_from_schema_path(schema_path))
    return model_path.stem, unit_to_iri, formatted_code


def generate_schemas_optimized(
    *,
    dry_run: bool = False,
    schema_regex: str | None = None,
    max_workers: int | None = None,
) -> list[str]:
    """
    Generate schemas with in-memory processing and parallelization.

    This version:
    - Processes schemas in parallel using multiprocessing
    - Generates and formats code in memory
    - Only writes final results (no temp files)
    - Reduces I/O operations significantly
    :param dry_run: If true, does not save changes to any models
    :param schema_regex: If set, filters schemas to generate using regex
    :param max_workers: Maximum number of parallel workers (default: CPU count)
    :return: List of model files that were changed
    """
    schema_paths = list(Path(SCHEMA_DIR_PATH).rglob("*.json"))

    # Process schemas in parallel
    models_changed = []
    all_units = {}
    generated_models = {}

    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks
        future_to_path = {
            executor.submit(process_single_schema, path, schema_regex): path
            for path in schema_paths
        }

        # Collect results as they complete
        for future in as_completed(future_to_path):
            schema_path = future_to_path[future]
            try:
                model_name, units, code = future.result()
                if model_name:
                    all_units.update(units)
                    model_path = Path(
                        MODEL_DIR_PATH, get_model_path_from_schema_path(schema_path)
                    )
                    generated_models[model_path] = code
            except Exception as e:
                print(f"Error processing {schema_path}: {e}")  # noqa: T201

    # Now write all results (unless dry_run)
    for model_path, code in generated_models.items():
        # Ensure directory exists
        model_path.parent.mkdir(parents=True, exist_ok=True)

        # Check if file changed
        if model_path.exists():
            with open(model_path) as f:
                existing_code = f.read()
            if existing_code == code:
                continue  # No change

        # Write the new code
        if not dry_run and code is not None:
            with open(model_path, "w") as f:
                f.write(code)

        models_changed.append(model_path.stem)

    # Update unit files (this must be done serially)
    if not dry_run:
        with backup_paths(GENERATED_SHARED_PATHS, restore=False) as working_paths:
            update_unit_files(all_units, *working_paths)
            # Format the unit files
            for path in working_paths:
                if path.suffix == ".py" and path.exists():
                    with open(path) as f:
                        content = f.read()
                    formatted = format_code_in_memory(content)
                    with open(path, "w") as f:
                        f.write(formatted)

    return models_changed
