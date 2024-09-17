from pathlib import Path

from allotropy.parser_factory import Vendor
from allotropy.parsers.release_state import ReleaseState


def test_vendor_display_name() -> None:
    # All vendors implement display_name
    for vendor in Vendor:
        assert vendor.display_name

    # All display names unique
    assert len(Vendor) == len({vendor.display_name for vendor in Vendor})


def test_get_parser() -> None:
    for vendor in Vendor:
        assert vendor.get_parser()


def test_vendors_in_readme() -> None:
    readme_path = Path(__file__).parent.parent.joinpath("README.md")
    parsers: dict[ReleaseState, set[str]] = {
        ReleaseState.RECOMMENDED: set(),
        ReleaseState.CANDIDATE_RELEASE: set(),
        ReleaseState.WORKING_DRAFT: set(),
    }
    # We don't include example parser in README
    parsers[ReleaseState.WORKING_DRAFT].add(Vendor.EXAMPLE_WEYLAND_YUTANI.display_name)
    section = None
    with open(readme_path) as f:
        for line in f:
            if line.startswith("### Recommended"):
                section = ReleaseState.RECOMMENDED
            elif line.startswith("### Candidate Release"):
                section = ReleaseState.CANDIDATE_RELEASE
            elif line.startswith("### Working Draft"):
                section = ReleaseState.WORKING_DRAFT
            elif section and line.strip().startswith("-"):
                parsers[section].add(line.strip()[2:])
            else:
                section = None

    # Assert all vendors are in README
    for vendor in Vendor:
        assert (
            vendor.display_name in parsers[vendor.release_state]
        ), f"Missing vendor in README: '{vendor.display_name}'. Hint: run 'hatch run scripts:update-readme'"

    # Assert not extra parsers in README
    assert (
        set.union(*parsers.values()) - {vendor.display_name for vendor in Vendor}
        == set()
    ), f"Extra vendor in README: '{vendor.display_name}'. Hint: run 'hatch run scripts:update-readme'"
