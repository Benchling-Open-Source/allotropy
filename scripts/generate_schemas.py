#!/usr/bin/env python3
import click

from allotropy.schema_gen.generate import (
    _discover_cached_technique_urls,
    generate_models,
)
from allotropy.schema_gen.technique_resolver import (
    is_shorthand,
    resolve_shorthand_to_urls,
)


@click.command()
@click.argument("schema_urls", nargs=-1, required=False)
@click.option(
    "--all",
    "regenerate_all",
    is_flag=True,
    help="Regenerate all cached technique schemas.",
)
def _generate_schemas(
    schema_urls: tuple[str, ...], *, regenerate_all: bool = False
) -> None:
    """Generate Python models from one or more Allotrope schema URLs.

    Each argument can be a full purl URL or a shorthand like "plate-reader 2026/03".
    Use --all to regenerate every cached technique schema.

    \b
    Examples:
      plate-reader 2026/03
      pcr WD/2025/06
      http://purl.allotrope.org/json-schemas/adm/pcr/REC/2024/09/qpcr.schema
    """
    urls: list[str]
    if regenerate_all:
        urls = _discover_cached_technique_urls()
        click.echo(f"Discovered {len(urls)} cached technique schema(s)")
    elif schema_urls:
        urls = []
        for arg in schema_urls:
            if is_shorthand(arg):
                resolved = resolve_shorthand_to_urls(arg)
                click.echo(f"Resolved '{arg}' to {len(resolved)} schema(s):")
                for u in resolved:
                    click.echo(f"  {u}")
                urls.extend(resolved)
            else:
                urls.append(arg)
    else:
        msg = "Provide schema URLs/shorthands or use --all."
        raise click.UsageError(msg)
    generate_models(urls)


if __name__ == "__main__":
    _generate_schemas()
