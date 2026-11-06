from pathlib import Path

from allotropy.parser_factory import get_table_contents, Vendor


def test_vendor_display_name() -> None:
    # All vendors implement display_name
    for vendor in Vendor:
        assert vendor.display_name

    # All display names unique
    assert len(Vendor) == len({vendor.display_name for vendor in Vendor})


def test_get_parser() -> None:
    for vendor in Vendor:
        assert vendor.get_parser()


def test_supported_schemas() -> None:
    assert Vendor.AGILENT_GEN5.manifests == [
        "http://purl.allotrope.org/manifests/plate-reader/REC/2025/03/plate-reader.manifest"
    ]
    assert Vendor.AGILENT_GEN5.asm_versions == ["REC/2025/03"]
    assert Vendor.AGILENT_GEN5.technique == "Plate Reader"
    assert Vendor.APPBIO_ABSOLUTE_Q.technique == "dPCR"


def test_table_contents() -> None:
    table_path = Path(__file__).parent.parent.joinpath(
        "SUPPORTED_INSTRUMENT_SOFTWARE.adoc"
    )
    with open(table_path) as f:
        assert (
            get_table_contents() == f.read()
        ), "Supported instruments table out-of-date. Hint: run 'hatch run scripts:update-instrument-table'"
