#!/usr/bin/env python3
from datetime import datetime
import os
from pathlib import Path
import subprocess

import click
from pytz import timezone
import semantic_version  # type: ignore

from allotropy.__about__ import __version__
from allotropy.allotrope.schema_parser.path_util import ALLOTROPY_DIR, ROOT_DIR


def _update_changelog(version: str) -> str:
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

    return body


def _write_version_file(version: str) -> None:
    with open(Path(ALLOTROPY_DIR, "__about__.py"), "w") as f:
        f.write(f'__version__ = "{version}"\n')


def _make_pr(version: str, body: str) -> None:
    try:
        subprocess.run(
            ["gh", "--help"],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except FileNotFoundError:
        print(
            "gh not installed - cannot create PR automatically. Try: 'brew install gh'"
        )
        return

    print("Making commit...")
    subprocess.run(
        [
            "git",
            "commit",
            "-am",
            f"Update allotropy version to {version}",
        ],
        check=True,
    )
    print("Pushing commit...")
    subprocess.run(["git", "push"], check=True)

    print("Creating PR...")
    filename = ".temp_pr_description.txt"
    with open(filename, "w") as f:
        f.write(body)

    try:
        subprocess.run(
            [
                "gh",
                "pr",
                "create",
                "--title",
                f"chore: Update allotropy version to {version}",
                "--body-file",
                filename,
            ],
            check=True,
        )
    finally:
        os.remove(filename)


@click.command()
@click.option(
    "--version", "-v", help="Version to update to, defaults to next patch version"
)
@click.option(
    "--skip_pr", is_flag=True, default=False, help="Whether to make PR in script"
)
def _update_version(
    version: str | None = None, skip_pr: bool = False  # noqa: FBT001, FBT002
) -> None:
    """Update allotropy version."""
    if version:
        semver = semantic_version.Version(version)
    if not version:
        semver = semantic_version.Version(__version__)
        semver.patch += 1

    version = str(semver)

    print("Updating version file and CHANGELOG...")
    _write_version_file(version)
    body = _update_changelog(version)
    if not skip_pr:
        _make_pr(version, body)


if __name__ == "__main__":
    _update_version()
