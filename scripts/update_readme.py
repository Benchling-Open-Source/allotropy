#!/usr/bin/env python3

from pathlib import Path

import click

from allotropy.parser_factory import Vendor
from allotropy.parsers.release_state import ReleaseState


@click.command()
def update_readme() -> None:
    """Update parser list in README."""
    release_state_to_parser: dict[ReleaseState, set[str]] = {
        release_state: set() for release_state in ReleaseState
    }
    for vendor in Vendor:
        if "example" in str(vendor).lower():
            continue
        release_state_to_parser[vendor.release_state].add(vendor.display_name)

    readme_file = Path(Path(__file__).parent.parent, "README.md")
    with open(readme_file) as f:
        contents = f.readlines()

    with open(readme_file, "w") as f:
        in_block = False
        newline_count = 0
        for line in contents:
            if line.startswith("### Recommended"):
                in_block = True
                continue
            if in_block:
                if line == "\n":
                    newline_count += 1
                if newline_count == 3:  # noqa: PLR2004
                    for release_state in [
                        ReleaseState.RECOMMENDED,
                        ReleaseState.CANDIDATE_RELEASE,
                        ReleaseState.WORKING_DRAFT,
                    ]:
                        f.write(
                            f'### {release_state.value.replace("_", " ").title()}\n'
                        )
                        for display_name in sorted(
                            release_state_to_parser.get(release_state, [])
                        ):
                            f.write(f"  - {display_name}\n")
                        f.write("\n")
                    in_block = False
                continue
            f.write(line)


if __name__ == "__main__":
    update_readme()
