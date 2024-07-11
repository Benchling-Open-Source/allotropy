#!/usr/bin/env python3
from pathlib import Path
import re
import shutil

import click

ALLOTROPY_DIR = Path(Path(__file__).parent.parent, "src/allotropy")
TEMPLATE_DIR = Path(Path(__file__).parent, "parser_templates")


def snake_to_upper_camel(word: str, delimiter: str = "_") -> str:
    prefix = ""
    if word.startswith(delimiter):
        prefix = "_"
        word = word[1:]

    return prefix + "".join(
        x[0].upper() + x[1:] for x in re.split(delimiter, word) if x
    )


def write_template_files(output_dir: Path, template_replacements: dict[str, str], template_files: dict[str, str]) -> None:
    for template_file, output_file in template_files.items():
        with open(Path(TEMPLATE_DIR, template_file)) as f:
            template = f.read()

        with open(Path(output_dir, output_file), "w") as f:
            for pattern, value in template_replacements.items():
                template = template.replace(f"${pattern}$", value)

            f.write(template)


def add_to_parser_factory(enum_name: str, class_name: str):
    parser_factory_file = Path(ALLOTROPY_DIR, "parser_factory.py")
    with open(parser_factory_file) as f:
        contents = f.readlines()

    with open(parser_factory_file, "w") as f:
        do_insert = False
        new_line = f"    Vendor.{enum_name}: {class_name}Parser,\n"
        for line in contents:
            if line.startswith("_VENDOR_TO_PARSER"):
                do_insert = True
            elif do_insert and new_line < line:
                f.write(new_line)
                do_insert = False
            f.write(line)


def create_parser(name: str, display_name: str | None = None):
    name = name.replace(" ", "_").replace("-", "_").lower()
    enum_name = name.upper()
    display_name = display_name or name.replace("_", " ").title()
    class_name = f"{snake_to_upper_camel(name)}Parser"

    schema_path = "pcr.benchling._2023._09.qpcr"
    manifest = "http://purl.allotrope.org/manifests/pcr/BENCHLING/2023/09/qpcr.manifest"

    parser_dir = Path(ALLOTROPY_DIR, "parsers", name)
    tests_dir = Path(ALLOTROPY_DIR.parent.parent, "tests/parsers", name)
    #if parser_dir.exists():
    #    raise ValueError(f"Parser {name} already exists!")
    # parser_dir.mkdir()
    # test_dir.mkdir()
    # Path(tests_dir, "testdata").mkdir()
    parser_dir.mkdir(exist_ok=True)
    Path(parser_dir, "__init__.py").touch()
    tests_dir.mkdir(exist_ok=True)
    Path(tests_dir, "__init__.py").touch()
    Path(tests_dir, "testdata").mkdir(exist_ok=True)

    template_replacements = {
        "PARSER_NAME": name,
        "CLASS_NAME": class_name,
        "DISPLAY_NAME": display_name,
        "ENUM_NAME": enum_name,
        "SCHEMA_PATH": schema_path,
        "MANIFEST": manifest,
    }

    write_template_files(parser_dir, template_replacements, {
        "parser_template": f"{name}_parser.py",
        "structure_template": f"{name}_structure.py",
        "constants_template": "constants.py"
    })
    write_template_files(tests_dir, template_replacements, {
        "test_template": "to_allotrope_test.py",
    })

    add_to_parser_factory(enum_name, class_name)
    # add_to_readme(display_name)



@click.command()
@click.argument("name")
@click.option("--display_name", help="Regex to determine which schemas to generate.")
def _create_parser(name: str, display_name: str | None = None) -> None:
    if "parser" in name.lower():
        raise AssertionError("Cannot include 'parser' in name")
    create_parser(name, display_name)


if __name__ == "__main__":
    _create_parser()
