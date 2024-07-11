#!/usr/bin/env python3
import click

from allotropy.parser_factory import update_readme


@click.command()
def _update_readme() -> None:
    """Update parser list in README."""
    update_readme()


if __name__ == "__main__":
    _update_readme()
