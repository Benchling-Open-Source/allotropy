#!/usr/bin/env python3
import click

from allotropy.allotrope.schema_parser.generate_schemas import generate_schemas


@click.command()
@click.option("-r", "--regex", help="Regex to determine which schemas to generate.")
def _generate_schemas(regex: str | None = None) -> None:
    generate_schemas(schema_regex=regex)


if __name__ == "__main__":
    _generate_schemas()
