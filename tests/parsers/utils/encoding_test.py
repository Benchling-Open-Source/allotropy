from io import BytesIO

from allotropy.constants import CHARDET_ENCODING
from allotropy.parsers.utils.encoding import decode


def test_decode_utf_8_detected_as_windows_1254() -> None:
    test_bytes = "HeLa (😢)".encode("utf-8")  # noqa: UP012
    assert decode(BytesIO(test_bytes), encoding=CHARDET_ENCODING) == "HeLa (😢)"


def test_decode_actually_windows_1252() -> None:
    test_bytes = b"Special byte \x96"
    assert (
        decode(BytesIO(test_bytes), encoding=CHARDET_ENCODING)
        == "Special byte –"  # noqa: RUF001
    )
