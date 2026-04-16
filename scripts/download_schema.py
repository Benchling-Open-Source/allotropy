#!/usr/bin/env python3
import click

from allotropy.schema_gen.fetcher import SchemaFetcher


@click.command()
@click.argument("schema_url")
def _download_schema(schema_url: str) -> None:
    print(f"Downloading schema at {schema_url}...")
    fetcher = SchemaFetcher()
    schemas = fetcher.fetch_with_dependencies(schema_url)
    print(f"Downloaded {len(schemas)} schema(s) to cache")


if __name__ == "__main__":
    _download_schema()
