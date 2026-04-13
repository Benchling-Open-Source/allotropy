#!/usr/bin/env python3
import click

from allotropy.schema_gen.generate import generate_models


@click.command()
@click.argument("schema_urls", nargs=-1, required=True)
def _generate_schemas(schema_urls: tuple[str, ...]) -> None:
    """Generate Python models from one or more Allotrope schema URLs.

    All schemas sharing the same core version (e.g., REC/2024/09) must be
    passed together so shared modules accumulate types from all schemas.
    """
    generate_models(list(schema_urls))


if __name__ == "__main__":
    _generate_schemas()
