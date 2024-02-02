#!/usr/bin/env python3
from pathlib import Path

import click

from allotropy.allotrope.schema_parser.generate_schemas import generate_schemas

ROOT_DIR = Path(__file__).parent.parent


@click.command()
@click.option("-r", "--regex", help="Regex to determine which schemas to generate.")
def _generate_schemas(regex: str) -> None:
    generate_schemas(ROOT_DIR, schema_regex=regex)


if __name__ == "__main__":
    _generate_schemas()
