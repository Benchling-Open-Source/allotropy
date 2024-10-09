#!/usr/bin/env python3
import click

from allotropy.parser_factory import update_supported_instruments


@click.command()
def _update_supported_instruments() -> None:
    """Update parser table in supported instruments."""
    update_supported_instruments()


if __name__ == "__main__":
    _update_supported_instruments()
