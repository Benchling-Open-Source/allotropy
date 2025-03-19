import chardet

from allotropy.constants import CHARDET_ENCODING, DEFAULT_ENCODING
from allotropy.exceptions import AllotropeConversionError, AllotropeParsingError


def determine_encoding(bytes_content: bytes, encoding: str | None) -> list[str]:
    if not encoding:
        return [DEFAULT_ENCODING]
    if encoding != CHARDET_ENCODING:
        return [encoding]

    if not bytes_content:
        msg = "Unable to detect encoding for empty bytes string, file may be empty."
        raise AllotropeConversionError(msg)

    detect_result = chardet.detect(bytes_content)
    if not detect_result["encoding"]:
        msg = f"Unable to detect text encoding for file with content: {bytes_content!r}"
        raise AllotropeParsingError(msg)
    # chardet can report the wrong encoding when there are strange characters in the contents (e.g. emojis)
    # To address this, we take the following approach - if the confidence of the detection is < 50%, report
    # DEFAULT_ENCODING first, and the detected encoding second. If we return multiple encodings, the caller
    # should try all.
    if detect_result["confidence"] < 0.7:
        return [DEFAULT_ENCODING, detect_result["encoding"]]
    return [detect_result["encoding"]]


def decode(bytes_content: bytes, encoding: str | None) -> str:
    possible_encodings = determine_encoding(bytes_content, encoding)
    for encoding in possible_encodings:
        try:
            return bytes_content.decode(encoding)
        except UnicodeDecodeError as e:
            if encoding != possible_encodings[-1]:
                continue
            msg = f"Unable to decode bytes with encoding '{encoding}' with error: {e}, bytes: {bytes_content!r}"
            raise AllotropeParsingError(msg) from e
        except LookupError as e:
            msg = f"Invalid encoding: '{encoding}'."
            raise AllotropeConversionError(msg) from e
