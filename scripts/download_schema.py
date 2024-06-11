#!/usr/bin/env python3
import click

from allotropy.allotrope.schema_parser.reference_resolver import download_schema


@click.command()
@click.argument("schema_url")
def _download_schema(schema_url: str) -> None:
    print(f"Downloading schema at {schema_url}...")  # noqa: T201
    schema_path = download_schema(schema_url)
    print(f"Downloaded to {schema_path}")  # noqa: T201


if __name__ == "__main__":
    _download_schema()
