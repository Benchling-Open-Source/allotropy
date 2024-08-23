from pathlib import Path
import re
from xml.etree import ElementTree

import pytest

from allotropy.exceptions import AllotropeConversionError
from allotropy.named_file_contents import NamedFileContents
from allotropy.parser_factory import Vendor
from allotropy.parsers.biorad_bioplex_manager.biorad_bioplex_manager_reader import (
    BioradBioplexReader,
)
from tests.to_allotrope_test import ParserTest

VENDOR_TYPE = Vendor.BIORAD_BIOPLEX
TESTDATA = f"{Path(__file__).parent}/testdata"


class TestParser(ParserTest):
    VENDOR = VENDOR_TYPE


@pytest.mark.short
def test_validate_xml_structure_missing_tags() -> None:
    test_filepath = (
        f"{TESTDATA}/exclude/bio-rad_bio-plex_manager_missing_children_error.xml"
    )
    msg = "Missing expected tags in xml: ['NativeDocumentLocation', 'Wells']"
    with pytest.raises(AllotropeConversionError, match=re.escape(msg)):
        with open(test_filepath) as f:
            BioradBioplexReader(NamedFileContents(f.read(), test_filepath))
