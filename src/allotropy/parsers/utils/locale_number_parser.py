"""Locale-aware number parsing utilities.

This module provides locale-aware number parsing based on Babel's CLDR data.
It allows parsing numbers with locale-specific decimal and grouping separators.

Example:
    >>> parse_number_with_locale("1.234,56", "de_DE")
    "1234.56"
    >>> parse_number_with_locale("1,234.56", "en_US")
    "1234.56"
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
import logging
import math
import re

from babel.core import Locale, UnknownLocaleError
from babel.numbers import (
    get_decimal_symbol,
    get_group_symbol,
    NumberFormatError,
    parse_decimal,
)

from allotropy.exceptions import AllotropeConversionError

logger = logging.getLogger(__name__)

# Default locale for number parsing (US English)
DEFAULT_LOCALE = "en_US"


@dataclass(frozen=True)
class NumberFormat:
    """Format used to parse numbers for a locale.

    Attributes:
        group_delimiter: The symbol used as the group separator (ex. "," in 1,234.56)
        decimal_delimiter: The symbol used as the decimal point (ex. "." in 1,234.56)
    """

    group_delimiter: str
    decimal_delimiter: str


# Alternative group delimiters that some locales support
GROUP_DELIMITER_ALTERNATIVES = {
    "\xa0": " ",  # Non-breaking space → regular space
    "\u202f": " ",  # Narrow no-break space → regular space
    "'": "'",  # Different apostrophe encodings
}


class _NumberFormatBuilder:
    """Builder for locale-specific number formats."""

    locale_str: str
    locale: Locale

    def __init__(self, locale: str) -> None:
        """Initialize the builder.

        Args:
            locale: The locale string (e.g., "en_US", "de_DE", "fr_FR")

        Raises:
            AllotropeConversionError: If locale is invalid
        """
        locale = locale.replace("-", "_")
        try:
            self.locale = Locale.parse(locale)
        except UnknownLocaleError:
            # Try with just the language code (e.g., "es" from "es_LA")
            locale = locale[: locale.index("_")] if "_" in locale else locale
            try:
                self.locale = Locale.parse(locale)
            except UnknownLocaleError as e:
                msg = f"Unsupported locale: {locale}"
                raise AllotropeConversionError(msg) from e
        self.locale_str = locale

    def build(self) -> NumberFormat:
        """Build a NumberFormat for this locale."""
        return NumberFormat(
            group_delimiter=get_group_symbol(self.locale_str),
            decimal_delimiter=get_decimal_symbol(self.locale_str),
        )


# Cache for number formats to avoid repeated Babel lookups
_NUMBER_FORMAT_CACHE: dict[str, NumberFormat] = {}


def get_number_format(locale: str = DEFAULT_LOCALE) -> NumberFormat:
    """Get the number format for a locale.

    Args:
        locale: The locale string (e.g., "en_US", "de_DE")

    Returns:
        NumberFormat for the locale
    """
    if locale not in _NUMBER_FORMAT_CACHE:
        try:
            builder = _NumberFormatBuilder(locale)
            _NUMBER_FORMAT_CACHE[locale] = builder.build()
        except AllotropeConversionError:
            logger.warning(
                f"Unsupported locale {locale}, falling back to {DEFAULT_LOCALE}"
            )
            if DEFAULT_LOCALE not in _NUMBER_FORMAT_CACHE:
                _NUMBER_FORMAT_CACHE[DEFAULT_LOCALE] = _NumberFormatBuilder(
                    DEFAULT_LOCALE
                ).build()
            return _NUMBER_FORMAT_CACHE[DEFAULT_LOCALE]
    return _NUMBER_FORMAT_CACHE[locale]


def parse_number_with_locale(number_str: str, locale: str = DEFAULT_LOCALE) -> str:
    """Parse a locale-formatted number string and return a standard format.

    Converts a number with locale-specific separators to a standard format
    (period decimal separator, no group separators).

    Args:
        number_str: The number string to parse (e.g., "1.234,56" in de_DE)
        locale: The locale to use for parsing (e.g., "de_DE")

    Returns:
        The number in standard format (e.g., "1234.56")

    Raises:
        AllotropeConversionError: If the number cannot be parsed
    """
    if not number_str or number_str.strip() == "":
        msg = "Cannot parse empty string as number"
        raise AllotropeConversionError(msg)

    number_str = number_str.strip()

    # Handle special values (NaN, infinity)
    special_value = _is_nan_or_inf(number_str)
    if special_value is not False:
        # Normalize to Python's standard string representation
        return str(special_value).lower()

    try:
        number_format = get_number_format(locale)
        sanitized = _sanitize_number_to_parse(number_str, number_format)

        # Parse with Babel
        if "e" in sanitized.lower():
            # Scientific notation
            result = _parse_scientific_notation(sanitized, locale, number_format)
        else:
            # Standard notation
            result = _parse_standard_notation(sanitized, locale, number_format)

        # Convert Decimal to string, preserving precision
        return str(result)
    except (NumberFormatError, ValueError, AllotropeConversionError) as e:
        msg = f"Cannot parse '{number_str}' as number for locale {locale}: {e}"
        raise AllotropeConversionError(msg) from e


def _sanitize_number_to_parse(number_str: str, number_format: NumberFormat) -> str:
    """Sanitize number string for parsing."""
    # Convert alternative group delimiters
    sanitized = _convert_group_delimiters(number_str, number_format)

    # Remove underscores (Python numeric literal support)
    if "__" in sanitized:
        msg = f"Invalid number format: {number_str}"
        raise AllotropeConversionError(msg)
    sanitized = sanitized.replace("_", "")

    return sanitized.lower()


def _convert_group_delimiters(number_str: str, number_format: NumberFormat) -> str:
    """Convert alternative group delimiters to standard ones."""
    if number_format.group_delimiter in GROUP_DELIMITER_ALTERNATIVES:
        alternative = GROUP_DELIMITER_ALTERNATIVES[number_format.group_delimiter]
        return number_str.replace(alternative, number_format.group_delimiter)
    return number_str


def _is_nan_or_inf(number_str: str) -> bool | float:
    """Check if string represents NaN or infinity.

    Returns:
        False if not NaN/inf, otherwise returns the normalized float value
    """
    try:
        value = float(number_str)
        if math.isnan(value) or math.isinf(value):
            return value
        return False
    except ValueError:
        return False


def _parse_scientific_notation(
    number_str: str, locale: str, number_format: NumberFormat
) -> Decimal:
    """Parse number in scientific notation."""
    before_e, after_e = number_str.split("e", 1)

    # Validate exponent
    if not re.match(r"^[+-]?\d+$", after_e):
        msg = f"Invalid scientific notation: {number_str}"
        raise AllotropeConversionError(msg)

    # Parse mantissa
    parse_decimal(string=before_e, locale=locale, strict=True)

    # Remove group delimiter for Babel (it doesn't support groups in scientific notation)
    sanitized = before_e.replace(number_format.group_delimiter, "") + "e" + after_e
    return parse_decimal(string=sanitized, locale=locale, strict=True)


def _parse_standard_notation(
    number_str: str, locale: str, number_format: NumberFormat
) -> Decimal:
    """Parse number in standard notation."""
    # Extract parts
    maybe_sign, before_decimal, after_decimal = _try_match_number(
        number_str, number_format, locale
    )

    # Remove leading/trailing zeros
    before_decimal = before_decimal.lstrip("0") if before_decimal else ""
    if after_decimal:
        after_decimal = after_decimal.rstrip("0").rstrip(
            number_format.decimal_delimiter
        )

    # Reconstruct number
    number = before_decimal + after_decimal

    # Add leading zero if starts with decimal
    if number and number[0] == number_format.decimal_delimiter:
        number = "0" + number

    # Handle empty string (was all zeros)
    if not number:
        number = "0"

    # Add sign
    if maybe_sign == "-":
        number = "-" + number

    return parse_decimal(string=number, locale=locale, strict=True)


def _try_match_number(
    number_str: str, number_format: NumberFormat, locale: str
) -> tuple[str, str, str]:
    """Match number string and extract parts."""
    # Match optional sign
    sign_group = "([-+]?)"

    # Match digits and group delimiters before decimal
    before_decimal_group = f"([\\d{number_format.group_delimiter}]*)?"

    # Match decimal and digits after
    after_decimal_group = (
        f"([{number_format.decimal_delimiter}{number_format.group_delimiter}\\d]*)?"
    )

    pattern = f"^{sign_group}{before_decimal_group}{after_decimal_group}$"
    match = re.match(pattern, number_str)

    if not match:
        msg = f"Invalid number format for locale {locale}: {number_str}"
        raise AllotropeConversionError(msg)

    return match.group(1), match.group(2) or "", match.group(3) or ""
