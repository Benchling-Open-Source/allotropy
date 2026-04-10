"""Main orchestrator: fetch schemas, generate modular Python models.

Usage:
    python -m allotropy.schema_gen.generate <schema_url>

Example:
    python -m allotropy.schema_gen.generate \
        "https://gitlab.com/allotrope-public/asm/-/blob/main/json-schemas/adm/spectrophotometry/REC/2024/06/spectrophotometry.schema.json"
"""

from __future__ import annotations

from pathlib import Path
import sys

from allotropy.schema_gen.codegen import SchemaCodeGenerator
from allotropy.schema_gen.fetcher import build_dependency_order, SchemaFetcher
from allotropy.schema_gen.naming import (
    DEFAULT_MODEL_OUTPUT_DIR,
    DEFAULT_SCHEMA_CACHE_DIR,
    schema_url_to_model_file,
)


def generate_models(
    schema_url: str,
    *,
    output_dir: Path = DEFAULT_MODEL_OUTPUT_DIR,
    cache_dir: Path = DEFAULT_SCHEMA_CACHE_DIR,
    models_package: str = "allotropy.allotrope.models_v2",
) -> list[Path]:
    """Generate modular Python models from an Allotrope schema URL.

    Args:
        schema_url: URL to an ADM schema (GitLab blob/raw or Allotrope URL).
        output_dir: Where to write generated Python files.
        cache_dir: Where to cache downloaded schema JSON files.
        models_package: Python package path for the models root.

    Returns:
        List of generated Python file paths.
    """
    # Phase 1: Fetch schemas
    print(f"Fetching schemas from: {schema_url}")  # noqa: T201
    fetcher = SchemaFetcher(cache_dir=cache_dir)
    schemas = fetcher.fetch_with_dependencies(schema_url)
    print(f"  Found {len(schemas)} schema(s)")  # noqa: T201

    # Phase 2: Determine generation order
    order = build_dependency_order(schemas)
    print("Generation order:")  # noqa: T201
    for i, url in enumerate(order):
        print(f"  {i + 1}. {url}")  # noqa: T201

    # Phase 3: Generate code
    print("\nGenerating Python modules...")  # noqa: T201
    generator = SchemaCodeGenerator(schemas, order, models_package=models_package)
    modules = generator.generate_all()

    # Phase 4: Write output files
    generated_files: list[Path] = []
    for url, module_code in modules.items():
        output_path = schema_url_to_model_file(url, output_dir)
        _write_module(output_path, module_code.render(models_package))
        generated_files.append(output_path)
        print(f"  Generated: {output_path}")  # noqa: T201

    print(f"\nDone! Generated {len(generated_files)} module(s)")  # noqa: T201
    return generated_files


def _write_module(path: Path, source: str) -> None:
    """Write a Python module file, creating directories and __init__.py files."""
    # Create all parent directories with __init__.py
    _ensure_package_dirs(path.parent)
    path.write_text(source, encoding="utf-8")


def _ensure_package_dirs(directory: Path) -> None:
    """Create directory and all parents, adding __init__.py to each."""
    directory.mkdir(parents=True, exist_ok=True)

    # Walk up from the directory to the models_v2 root, creating __init__.py files
    current = directory
    while current != current.parent:
        init_file = current / "__init__.py"
        if not init_file.exists():
            init_file.touch()
        # Stop at the models_v2 directory (or whatever the output root is)
        if current.name == "models_v2":
            break
        current = current.parent


def main() -> None:
    """CLI entry point."""
    if len(sys.argv) < 2:
        print(
            "Usage: python -m allotropy.schema_gen.generate <schema_url>"
        )  # noqa: T201
        print()  # noqa: T201
        print("Example:")  # noqa: T201
        print(  # noqa: T201
            '  python -m allotropy.schema_gen.generate "https://gitlab.com/allotrope-public/asm/-/blob/main/json-schemas/adm/spectrophotometry/REC/2024/06/spectrophotometry.schema.json"'
        )
        sys.exit(1)

    schema_url = sys.argv[1]
    output_dir = Path(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_MODEL_OUTPUT_DIR
    generate_models(schema_url, output_dir=output_dir)


if __name__ == "__main__":
    main()
