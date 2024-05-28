from pathlib import Path

from allotropy.parser_factory import Vendor

NON_READY_PARSERS = {
    # NOTE: example parser will never be marked as ready to use, as it shouldn't be used.
    Vendor.EXAMPLE_WEYLAND_YUTANI,
    # We want to collect more test cases for this parser before marking as ready.
    Vendor.QIACUITY_DPCR,
}


def test_vendor_display_name() -> None:
    # All vendors implement display_name
    for vendor in Vendor:
        assert vendor.display_name

    # All display names unique
    assert len(Vendor) == len({vendor.display_name for vendor in Vendor})


def test_vendor_is_ready_to_use() -> None:
    for vendor in Vendor:
        assert vendor.is_ready_to_use or vendor in NON_READY_PARSERS


def test_get_parser() -> None:
    for vendor in Vendor:
        assert vendor.get_parser()


def test_vendors_in_readme() -> None:
    readme_path = Path(__file__).parent.parent.joinpath("README.md")
    with open(readme_path) as f:
        readme_contents = f.read()

    for vendor in Vendor:
        if vendor.is_ready_to_use:
            assert vendor.display_name in readme_contents
        else:
            assert vendor.display_name not in readme_contents
