#!/usr/bin/env python3
from collections import defaultdict
from datetime import datetime
import os
from pathlib import Path
import subprocess

import click
from dateutil import tz
import semantic_version  # type: ignore

from allotropy.__about__ import __version__
from allotropy.allotrope.schema_parser.path_util import ALLOTROPY_DIR, ROOT_DIR

SECTION_TO_PREFIX = {
    "feat": "Added",
    "fix": "Fixed",
    "refactor": "Changed",
    "deprecate": "Deprecated",
    "remove": "Removed",
    "security": "Security",
}


def _get_changes() -> dict[str, list[str]]:
    p = subprocess.run(
        ["git", "log", "--oneline"], capture_output=True, text=True, check=True
    )
    changes = defaultdict(list)
    for line in p.stdout.split("\n"):
        parts = line.split(" ")
        if len(parts) < 3 or not parts[1].endswith(":"):
            continue
        prefix = parts[1].strip(":").lower()
        if prefix == "release":
            break
        if prefix not in SECTION_TO_PREFIX:
            continue
        changes[prefix].append(" ".join(parts[2:]))
    return dict(changes)


def _get_new_section() -> str:
    changes = _get_changes()
    body = ""
    for prefix, section in SECTION_TO_PREFIX.items():
        if prefix not in changes:
            continue
        body += f"\n### {section}\n\n"
        for change in changes[prefix]:
            body += f"- {change}\n"

    return body


def _update_changelog(version: str) -> str:
    changelog_file = Path(ROOT_DIR, "CHANGELOG.md")
    with open(changelog_file) as f:
        contents = f.readlines()

    body = ""
    with open(changelog_file, "w") as f:
        for line in contents:
            if line.startswith("## ") and not body:
                body = _get_new_section()
                f.write(
                    f"## [{version}] - {datetime.now(tz.gettz('EST')).strftime('%Y-%m-%d')}\n"
                )
                f.write(body)
                f.write("\n")
            f.write(line)

    return body


def _write_version_file(version: str) -> None:
    with open(Path(ALLOTROPY_DIR, "__about__.py"), "w") as f:
        f.write(f'__version__ = "{version}"\n')


def _make_pr(version: str, body: str) -> None:
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
    subprocess.run(["git", "push", "-u", "origin", f"release-v{version}"], check=True)

    print("Tagging branch...")
    subprocess.run(
        ["git", "tag", "-a", f"v{version}", "-m", f"'allotropy v{version}'"], check=True
    )
    subprocess.run(["git", "push", "origin", "tag", f"v{version}"], check=True)

    filename = ".temp_pr_description.txt"
    with open(filename, "w") as f:
        f.write(body)

    try:
        print("Creating PR...")
        subprocess.run(
            [
                "gh",
                "pr",
                "create",
                "--title",
                f"release: Update allotropy version to {version}",
                "--body-file",
                filename,
            ],
            check=True,
        )
        print("Creating release...")
        subprocess.run(
            [
                "gh",
                "release",
                "create",
                f"v{version}",
                "-F",
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
    # Check if gh is installed, if not, print hint and exit.
    if not skip_pr:
        try:
            subprocess.run(
                ["gh", "--help"],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except FileNotFoundError:
            print(
                "gh not installed - cannot create PR and release automatically. Try: 'brew install gh'"
            )
            return

    """Update allotropy version."""
    if version:
        semver = semantic_version.Version(version)
    if not version:
        semver = semantic_version.Version(__version__)
        semver.patch += 1

    version = str(semver)

    # Checkout a new branch
    print("Checking out a clean branch from main...")
    subprocess.run(["git", "checkout", "main"], check=True)
    subprocess.run(["git", "pull"], check=True)
    subprocess.run(["git", "checkout", "-b", f"release-v{version}"], check=True)

    print("Updating version file and CHANGELOG...")
    _write_version_file(version)
    body = _update_changelog(version)

    if not skip_pr:
        _make_pr(version, body)


if __name__ == "__main__":
    _update_version()
