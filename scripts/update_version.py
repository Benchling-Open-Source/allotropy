#!/usr/bin/env python3
from datetime import datetime
from pathlib import Path

import click
from pytz import timezone
import semantic_version  # type: ignore

from allotropy.__about__ import __version__
from allotropy.allotrope.schema_parser.path_util import ALLOTROPY_DIR, ROOT_DIR


def _update_changelog(version: str) -> None:
    changelog_file = Path(ROOT_DIR, "CHANGELOG.md")
    with open(changelog_file) as f:
        contents = f.readlines()

    body = ""
    with open(changelog_file, "w") as f:
        editing = None
        current_contents: list[str] = []
        for line in contents:
            if line.startswith("## "):
                if editing:
                    # Add last section to body and write body
                    if "".join(current_contents[1:]).strip():
                        body += "".join(
                            f"- {c.strip()}\n"
                            if not (c.startswith("-") or c.startswith("\n"))
                            else c
                            for c in current_contents
                            if c != "\n"
                        )
                    f.write(body)

                    # Write start of new section
                    f.write("\n")

                    editing = False
                elif editing is None:
                    # Start writing current changelog entry, skipping empty sections.
                    f.write(
                        """## [Unreleased]\n\n### Added\n\n### Fixed\n\n### Changed\n\n### Deprecated\n\n### Removed\n\n### Security\n\n"""
                    )
                    f.write(
                        f"## [{version}] - {datetime.now(timezone('EST')).strftime('%Y-%m-%d')}\n"
                    )
                    editing = True
                    continue

            if editing:
                if line.startswith("### "):
                    if "".join(current_contents[1:]).strip():
                        body += "".join(
                            f"- {c.strip()}\n"
                            if not (c.startswith("-") or c.startswith("\n"))
                            else c
                            for c in current_contents
                            if c != "\n"
                        )
                    current_contents = [f"\n{line}\n"]
                else:
                    current_contents.append(line)
                continue

            f.write(line)

    print(body)


def _write_version_file(version: str) -> None:
    with open(Path(ALLOTROPY_DIR, "__about__.py"), "w") as f:
        f.write(f'__version__ = "{version}"')


@click.command()
@click.option(
    "--version", "-v", help="Version to update to, defaults to next patch version"
)
def _update_version(version: str | None = None) -> None:
    """Update allotropy version."""
    if version:
        semver = semantic_version.Version(version)
    if not version:
        semver = semantic_version.Version(__version__)
        semver.patch += 1

    version = str(semver)

    _write_version_file(version)
    _update_changelog(version)


if __name__ == "__main__":
    _update_version()
