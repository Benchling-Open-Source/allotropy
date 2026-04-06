"""Tests for locale-aware number parsing."""

import pytest

from allotropy.exceptions import AllotropeConversionError
from allotropy.parsers.utils.locale_number_parser import (
    get_number_format,
    parse_number_with_locale,
)


class TestGetNumberFormat:
    def test_en_us_format(self) -> None:
        fmt = get_number_format("en_US")
        assert fmt.group_delimiter == ","
        assert fmt.decimal_delimiter == "."

    def test_de_de_format(self) -> None:
        fmt = get_number_format("de_DE")
        assert fmt.group_delimiter == "."
        assert fmt.decimal_delimiter == ","

    def test_fr_fr_format(self) -> None:
        fmt = get_number_format("fr_FR")
        assert fmt.decimal_delimiter == ","
        # French uses narrow no-break space for grouping
        assert fmt.group_delimiter == "\u202f"

    def test_invalid_locale_falls_back_to_default(self) -> None:
        fmt = get_number_format("invalid_LOCALE")
        # Should fall back to en_US
        assert fmt.group_delimiter == ","
        assert fmt.decimal_delimiter == "."


class TestParseNumberWithLocale:
    # US English tests
    def test_parse_us_simple_integer(self) -> None:
        assert parse_number_with_locale("123", "en_US") == "123"

    def test_parse_us_simple_decimal(self) -> None:
        assert parse_number_with_locale("123.45", "en_US") == "123.45"

    def test_parse_us_with_thousands(self) -> None:
        assert parse_number_with_locale("1,234.56", "en_US") == "1234.56"

    def test_parse_us_millions(self) -> None:
        assert parse_number_with_locale("1,234,567.89", "en_US") == "1234567.89"

    # German tests
    def test_parse_de_simple_integer(self) -> None:
        assert parse_number_with_locale("123", "de_DE") == "123"

    def test_parse_de_simple_decimal(self) -> None:
        assert parse_number_with_locale("123,45", "de_DE") == "123.45"

    def test_parse_de_with_thousands(self) -> None:
        assert parse_number_with_locale("1.234,56", "de_DE") == "1234.56"

    def test_parse_de_millions(self) -> None:
        assert parse_number_with_locale("1.234.567,89", "de_DE") == "1234567.89"

    # French tests
    def test_parse_fr_simple_integer(self) -> None:
        assert parse_number_with_locale("123", "fr_FR") == "123"

    def test_parse_fr_simple_decimal(self) -> None:
        assert parse_number_with_locale("123,45", "fr_FR") == "123.45"

    # Scientific notation
    def test_parse_us_scientific_notation(self) -> None:
        result = parse_number_with_locale("1.23e5", "en_US")
        assert float(result) == pytest.approx(123000.0)

    def test_parse_de_scientific_notation(self) -> None:
        result = parse_number_with_locale("1,23e5", "de_DE")
        assert float(result) == pytest.approx(123000.0)

    def test_parse_scientific_with_negative_exponent(self) -> None:
        result = parse_number_with_locale("1.23e-5", "en_US")
        assert float(result) == pytest.approx(0.0000123)

    # Special values
    def test_parse_nan(self) -> None:
        assert parse_number_with_locale("nan", "en_US") == "nan"
        assert parse_number_with_locale("NaN", "en_US") == "nan"

    def test_parse_infinity(self) -> None:
        assert parse_number_with_locale("inf", "en_US") == "inf"
        assert parse_number_with_locale("Infinity", "en_US") == "inf"

    # Negative numbers
    def test_parse_negative_us(self) -> None:
        assert parse_number_with_locale("-123.45", "en_US") == "-123.45"

    def test_parse_negative_de(self) -> None:
        assert parse_number_with_locale("-123,45", "de_DE") == "-123.45"

    # Edge cases
    def test_parse_leading_zeros(self) -> None:
        assert parse_number_with_locale("00123.45", "en_US") == "123.45"

    def test_parse_trailing_zeros(self) -> None:
        assert parse_number_with_locale("123.4500", "en_US") == "123.45"

    def test_parse_decimal_only(self) -> None:
        assert parse_number_with_locale(".5", "en_US") == "0.5"

    def test_parse_integer_ending_in_decimal(self) -> None:
        # Some locales allow trailing decimal separator
        result = parse_number_with_locale("123.", "en_US")
        assert result in ("123", "123.0")

    # Error cases
    def test_parse_empty_string_raises(self) -> None:
        with pytest.raises(AllotropeConversionError, match="empty string"):
            parse_number_with_locale("", "en_US")

    def test_parse_invalid_format_raises(self) -> None:
        with pytest.raises(AllotropeConversionError):
            parse_number_with_locale("abc", "en_US")

    def test_parse_wrong_locale_format_raises(self) -> None:
        # German number with US locale should fail
        with pytest.raises(AllotropeConversionError):
            parse_number_with_locale("1.234,56", "en_US")

    # Alternative group delimiters
    def test_parse_fr_with_regular_space(self) -> None:
        # French often uses space instead of narrow no-break space
        result = parse_number_with_locale("1 234,56", "fr_FR")
        assert result == "1234.56"
