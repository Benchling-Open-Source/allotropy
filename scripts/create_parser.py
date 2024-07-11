#!/usr/bin/env python3
from pathlib import Path

import click

from allotropy.allotrope.schema_parser.path_util import (
    get_import_path_from_path,
    get_manifest_from_schema_path,
    get_model_file_from_schema_path,
    SCHEMA_DIR_PATH,
)
from allotropy.allotrope.schema_parser.schema_model import snake_to_upper_camel

ALLOTROPY_DIR = Path(Path(__file__).parent.parent, "src/allotropy")
TEMPLATE_DIR = Path(Path(__file__).parent, "templates")


def write_template_files(
    output_dir: Path,
    template_replacements: dict[str, str],
    template_files: dict[str, str],
) -> None:
    for template_file, output_file in template_files.items():
        with open(Path(TEMPLATE_DIR, template_file)) as f:
            template = f.read()

        with open(Path(output_dir, output_file), "w") as f:
            for pattern, value in template_replacements.items():
                template = template.replace(f"${pattern}$", value)

            f.write(template)


def add_to_parser_factory(parser_name: str, enum_name: str, class_name: str) -> None:
    parser_factory_file = Path(ALLOTROPY_DIR, "parser_factory.py")
    with open(parser_factory_file) as f:
        contents = f.readlines()

    line_and_condition = {
        f'    {enum_name} = "{enum_name}"\n': "class Vendor",
        f"    Vendor.{enum_name}: {class_name},\n": "_VENDOR_TO_PARSER",
        f"from allotropy.parsers.{parser_name}.{parser_name}_parser import {class_name}\n": "from allotropy.parsers",
    }
    in_condition: dict[str, bool] = {}

    with open(parser_factory_file, "w") as f:
        for line in contents:
            for new_line, condition in line_and_condition.items():
                if new_line not in in_condition and line.startswith(condition):
                    in_condition[new_line] = True
                elif in_condition.get(new_line) and new_line <= line:
                    if new_line != line:
                        f.write(new_line)
                    in_condition[new_line] = False

            f.write(line)


def create_parser(
    name: str, schema_path: Path, display_name: str | None = None
) -> None:
    name = name.replace(" ", "_").replace("-", "_").lower()
    enum_name = name.upper()
    display_name = display_name or name.replace("_", " ").title()
    class_name = f"{snake_to_upper_camel(name)}Parser"

    model_path = get_model_file_from_schema_path(schema_path)
    import_path = get_import_path_from_path(model_path)
    manifest = get_manifest_from_schema_path(schema_path)

    parser_dir = Path(ALLOTROPY_DIR, "parsers", name)
    tests_dir = Path(ALLOTROPY_DIR.parent.parent, "tests/parsers", name)
    if parser_dir.exists():
        msg = f"Parser {name} already exists!"
        raise ValueError(msg)

    parser_dir.mkdir()
    Path(parser_dir, "__init__.py").touch()
    tests_dir.mkdir()
    Path(tests_dir, "__init__.py").touch()
    Path(tests_dir, "testdata").mkdir()

    template_replacements = {
        "PARSER_NAME": name,
        "CLASS_NAME": class_name,
        "DISPLAY_NAME": display_name,
        "ENUM_NAME": enum_name,
        "IMPORT_PATH": import_path,
        "MANIFEST": manifest,
    }
    write_template_files(
        parser_dir,
        template_replacements,
        {
            "parser_template": f"{name}_parser.py",
            "structure_template": f"{name}_structure.py",
            "constants_template": "constants.py",
        },
    )
    write_template_files(
        tests_dir,
        template_replacements,
        {
            "test_template": "to_allotrope_test.py",
        },
    )
    add_to_parser_factory(name, enum_name, class_name)


@click.command()
@click.argument("name")
@click.argument("schema_regex")
@click.option(
    "--display_name", help="Display name for parser, defaults to title case of NAME"
)
def _create_parser(
    name: str, schema_regex: str, display_name: str | None = None
) -> None:
    """Create parser with name NAME for schema found with SCHEMA_REGEX."""
    if "parser" in name.lower():
        msg = "Cannot include 'parser' in name"
        raise ValueError(msg)

    schema_paths = list(SCHEMA_DIR_PATH.rglob(f"{schema_regex}*.json"))
    if not schema_paths:
        msg = f"Could not find schema with schema regex: '{schema_regex}'"
        raise ValueError(msg)
    if len(schema_paths) > 1:
        msg = f"Found more than one schema with schema regex, please narrow down: {[str(p) for p in schema_paths]}"
        raise ValueError(msg)

    create_parser(name, schema_paths[0], display_name)

    # Import update_readme now to get updated files.
    from allotropy.parser_factory import update_readme

    update_readme()


if __name__ == "__main__":
    _create_parser()
