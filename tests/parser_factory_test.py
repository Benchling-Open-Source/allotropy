from allotropy.parser_factory import Vendor

NON_READY_PARSERS = {
    # NOTE: example parser will never be marked as ready to use, as it shouldn't be used.
    Vendor.EXAMPLE_WEYLAND_YUTANI
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
