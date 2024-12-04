from io import StringIO

import pytest

from allotropy.exceptions import AllotropeConversionError
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.appbio_quantstudio.appbio_quantstudio_reader import (
    AppBioQuantStudioReader,
)


def test_header_builder_no_header_then_raise() -> None:
    with pytest.raises(
        AllotropeConversionError,
        match="Cannot parse data from empty header.",
    ):
        AppBioQuantStudioReader.create(
            NamedFileContents(contents=StringIO(""), original_file_path="tmp.txt")
        )
