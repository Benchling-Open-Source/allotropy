from pathlib import Path
import re

import pytest

from allotropy.exceptions import AllotropeConversionError
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.biorad_bioplex_manager.biorad_bioplex_manager_reader import (
    BioradBioplexReader,
)

TESTDATA = f"{Path(__file__).parent}/testdata"


@pytest.mark.short
def test_validate_xml_structure_missing_tags() -> None:
    test_filepath = (
        f"{TESTDATA}/exclude/bio-rad_bio-plex_manager_missing_children_error.xml"
    )
    msg = "Missing expected tags in xml: ['NativeDocumentLocation', 'Wells']"
    with pytest.raises(AllotropeConversionError, match=re.escape(msg)):
        with open(test_filepath) as f:
            BioradBioplexReader(NamedFileContents(f, test_filepath))
