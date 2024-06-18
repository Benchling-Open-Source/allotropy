from pathlib import Path

from allotropy.parser_factory import Vendor
from allotropy.parsers.release_state import ReleaseState

NON_READY_PARSERS = {
    # NOTE: example parser will never be marked as ready to use, as it shouldn't be used.
    Vendor.EXAMPLE_WEYLAND_YUTANI,
    # We want to collect more test cases for this parser before marking as ready.
    Vendor.QIACUITY_DPCR,
    # We want to collect more test cases for this parser before marking as ready.
    Vendor.MABTECH_APEX,
}


def test_vendor_display_name() -> None:
    # All vendors implement display_name
    for vendor in Vendor:
        assert vendor.display_name

    # All display names unique
    assert len(Vendor) == len({vendor.display_name for vendor in Vendor})


def test_vendor_release_state() -> None:
    for vendor in Vendor:
        assert (
            vendor.release_state == ReleaseState.RECOMMENDED
            or vendor in NON_READY_PARSERS
        )


def test_get_parser() -> None:
    for vendor in Vendor:
        assert vendor.get_parser()


def test_vendors_in_readme() -> None:
    readme_path = Path(__file__).parent.parent.joinpath("README.md")
    with open(readme_path) as f:
        readme_contents = f.read()

    for vendor in Vendor:
        if vendor.release_state == ReleaseState.RECOMMENDED:
            assert f"- {vendor.display_name}" in readme_contents
        elif vendor.release_state == ReleaseState.CANDIDATE_RELEASE:
            assert f"- *{vendor.display_name}" in readme_contents
        else:
            assert vendor.display_name not in readme_contents
