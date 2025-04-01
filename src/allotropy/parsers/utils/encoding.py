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
    # chardet can report the wrong encoding when there are strange characters in the contents (e.g. emojis)
    # To address this, we take the following approach - if the confidence of the detection is < 70%, report
    # DEFAULT_ENCODING first, and the detected encoding second. If we return multiple encodings, the caller
    # should try all.
    if detect_result["confidence"] < 0.7:
        return [DEFAULT_ENCODING, detect_result["encoding"]]
    return [detect_result["encoding"]]


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
            return actual_contents.decode(encoding)
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
