import re
from xml.etree import ElementTree

import pytest

from allotropy.exceptions import AllotropeConversionError
from allotropy.parsers.biorad_bioplex_manager.biorad_bioplex_manager_structure import (
    validate_xml_structure,
)


@pytest.mark.short
def test_validate_xml_structure_missing_tags() -> None:
    test_filepath = "tests/parsers/biorad_bioplex_manager/testdata/bio-rad_bio-plex_manager_missing_children_error.xml"
    tree = ElementTree.parse(test_filepath)  # noqa: S314
    root = tree.getroot()
    msg = "Missing expected tags in xml: ['NativeDocumentLocation', 'Wells']"
    with pytest.raises(AllotropeConversionError, match=re.escape(msg)):
        validate_xml_structure(root)
