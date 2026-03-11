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

    # chardet 7.x has different behavior for Windows-1252 detection
    # For very low confidence detections, try Windows-1252 as a fallback
    # This handles cases like single byte \x96 (en dash) which chardet 7.x
    # may misdetect as iso-8859-16 or other encodings
    if confidence < 0.3:
        # For very low confidence, try multiple encodings
        encodings = [DEFAULT_ENCODING, "windows-1252"]
        if detected_encoding and detected_encoding not in encodings:
            encodings.append(detected_encoding)
        return encodings
    elif confidence < 0.7:
        # For medium confidence, try UTF-8 first, then the detected encoding
        return [DEFAULT_ENCODING, detected_encoding]
    else:
        # High confidence, use the detected encoding
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
            if decoded and decoded[0] == '\ufeff':
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
