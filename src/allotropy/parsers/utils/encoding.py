from typing import IO

import chardet

from allotropy.constants import CHARDET_ENCODING, DEFAULT_ENCODING
from allotropy.exceptions import AllotropeConversionError, AllotropeParsingError


def _get_contents(contents: bytes | IO[bytes] | IO[str]) -> str | bytes:
    if isinstance(contents, bytes):
        return contents
    actual_contents = contents.read()
    contents.seek(0)
    return actual_contents


def determine_encoding(
    contents: bytes | IO[bytes] | IO[str], encoding: str | None
) -> list[str | None]:
    if not encoding:
        return [DEFAULT_ENCODING]
    if encoding != CHARDET_ENCODING:
        return [encoding]

    actual_contents = _get_contents(contents)
    if isinstance(actual_contents, str):
        return [None]
    if not actual_contents:
        msg = "Unable to detect encoding for empty bytes string, file may be empty."
        raise AllotropeConversionError(msg)

    detect_result = chardet.detect(actual_contents)
    if not detect_result["encoding"]:
        msg = (
            f"Unable to detect text encoding for file with content: {actual_contents!r}"
        )
        raise AllotropeParsingError(msg)

    detected_encoding = detect_result["encoding"]
    confidence = detect_result["confidence"]

    # chardet can misdetect UTF-8 multi-byte sequences as ISO-8859-1 or similar
    # Latin-1 encodings, especially in older versions (5.x). Always try UTF-8
    # first when Latin-1 family encodings are detected to avoid mojibake.
    latin1_encodings = {
        "ISO-8859-1",
        "ISO-8859-2",
        "ISO-8859-3",
        "ISO-8859-4",
        "ISO-8859-5",
        "ISO-8859-6",
        "ISO-8859-7",
        "ISO-8859-8",
        "ISO-8859-9",
        "ISO-8859-10",
        "ISO-8859-13",
        "ISO-8859-14",
        "ISO-8859-15",
        "ISO-8859-16",
        "cp1250",
        "cp1251",
        "cp1252",
        "cp1253",
        "cp1254",
        "cp1255",
        "cp1256",
        "cp1257",
        "cp1258",
        "windows-1250",
        "windows-1251",
        "windows-1252",
        "windows-1253",
        "windows-1254",
        "windows-1255",
        "windows-1256",
        "windows-1257",
        "windows-1258",
    }

    # Normalize encoding name for comparison
    normalized_encoding = detected_encoding.upper() if detected_encoding else ""

    if confidence < 0.3:
        # Very low confidence, try multiple encodings
        encodings: list[str | None] = [DEFAULT_ENCODING, "windows-1252"]
        if detected_encoding and detected_encoding not in encodings:
            encodings.append(detected_encoding)
        return encodings
    elif normalized_encoding in latin1_encodings or confidence < 0.7:
        # For Latin-1 family or medium confidence, try UTF-8 first
        # This handles chardet 5.x incorrectly detecting UTF-8 as ISO-8859-1
        if detected_encoding != DEFAULT_ENCODING:
            return [DEFAULT_ENCODING, detected_encoding]
        return [DEFAULT_ENCODING]
    else:
        # High confidence non-Latin encoding, use as detected
        return [detected_encoding]


def decode(contents: IO[bytes] | IO[str], encoding: str | None) -> str:
    actual_contents = _get_contents(contents)
    if isinstance(actual_contents, str):
        return actual_contents
    possible_encodings = determine_encoding(actual_contents, encoding)

    for encoding in possible_encodings:
        # NOTE: this should not be possible, we only return None if contents is str, which should have returned already.
        if encoding is None:
            msg = f"Could not determine encoding of contents: {actual_contents!r}"
            raise AssertionError(msg)
        try:
            decoded = actual_contents.decode(encoding)
            # Strip BOM (Byte Order Mark) if present
            # UTF-16 and UTF-8 files may include BOM character U+FEFF
            # which should be removed from the content
            if decoded and decoded[0] == "\ufeff":
                decoded = decoded[1:]
            return decoded
        except UnicodeDecodeError as e:
            if encoding != possible_encodings[-1]:
                continue
            msg = f"Unable to decode bytes with encoding '{encoding}' with error: {e}, bytes: {actual_contents!r}"
            raise AllotropeParsingError(msg) from e
        except LookupError as e:
            msg = f"Invalid encoding: '{encoding}'."
            raise AllotropeConversionError(msg) from e
    msg = f"Unable to decode contents with possible encodings: {possible_encodings}. Contents: {actual_contents!r}"
    raise AllotropeConversionError(msg)
