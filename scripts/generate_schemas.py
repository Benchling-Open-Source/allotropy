#!/usr/bin/env python3
import click

from allotropy.schema_gen.generate import (
    _discover_cached_technique_urls,
    generate_models,
)


@click.command()
@click.argument("schema_urls", nargs=-1, required=False)
@click.option("--all", "regenerate_all", is_flag=True, help="Regenerate all cached technique schemas.")
def _generate_schemas(schema_urls: tuple[str, ...], *, regenerate_all: bool = False) -> None:
    """Generate Python models from one or more Allotrope schema URLs.

    Use --all to regenerate every cached technique schema.
    """
    if regenerate_all:
        urls = _discover_cached_technique_urls()
        click.echo(f"Discovered {len(urls)} cached technique schema(s)")
    elif schema_urls:
        urls = list(schema_urls)
    else:
        msg = "Provide schema URLs or use --all."
        raise click.UsageError(msg)
    generate_models(urls)


if __name__ == "__main__":
    _generate_schemas()
