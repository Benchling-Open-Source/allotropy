from allotropy.parser_factory import Vendor


def test_vendor_get_display_name() -> None:
    vendor = Vendor.APPBIO_QUANTSTUDIO
    assert vendor.get_display_name() == "AppBio QuantStudio RT-PCR"
