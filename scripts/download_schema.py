#!/usr/bin/env python3
import click

from allotropy.schema_gen.fetcher import SchemaFetcher
from allotropy.schema_gen.technique_resolver import (
    is_shorthand,
    resolve_shorthand_to_urls,
)


@click.command()
@click.argument("schema_input")
def _download_schema(schema_input: str) -> None:
    """Download an Allotrope schema and its dependencies.

    SCHEMA_INPUT can be a full purl URL or a shorthand like "plate-reader 2026/03".

    \b
    Examples:
      plate-reader 2026/03
      pcr WD/2025/06
      http://purl.allotrope.org/json-schemas/adm/pcr/REC/2024/09/qpcr.schema
    """
    if is_shorthand(schema_input):
        urls = resolve_shorthand_to_urls(schema_input)
        click.echo(f"Resolved to {len(urls)} schema(s):")
        for url in urls:
            click.echo(f"  {url}")
    else:
        urls = [schema_input]

    fetcher = SchemaFetcher()
    total = 0
    for url in urls:
        click.echo(f"Downloading schema at {url}...")
        schemas = fetcher.fetch_with_dependencies(url)
        total += len(schemas)
    click.echo(f"Downloaded {total} schema(s) to cache")


if __name__ == "__main__":
    _download_schema()
