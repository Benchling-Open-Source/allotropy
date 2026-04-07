import pytest

from allotropy.exceptions import AllotropeConversionError
from allotropy.parsers.utils.locale_context import set_locale_context
from allotropy.parsers.utils.timestamp_parser import (
    _should_use_day_first,
    TimestampParser,
)


class TestShouldUseDayFirst:
    """Test the _should_use_day_first helper function."""

    def test_iso_8601_year_first_returns_false(self) -> None:
        # ISO 8601 formats are always YYYY-MM-DD (month before day)
        assert _should_use_day_first("2023-01-15", "de_DE") is False
        assert _should_use_day_first("2023/01/15", "de_DE") is False
        assert _should_use_day_first("2023.01.15", "de_DE") is False
        assert _should_use_day_first("2023-12-31", "en_GB") is False

    def test_american_locale_returns_false(self) -> None:
        # en_US uses MM/DD/YYYY format
        assert _should_use_day_first("01/15/2023", "en_US") is False
        assert _should_use_day_first("12/31/2023", "en_US") is False

    def test_european_locales_return_true(self) -> None:
        # European locales use DD/MM/YYYY format
        assert _should_use_day_first("15/01/2023", "en_GB") is True
        assert _should_use_day_first("15.01.2023", "de_DE") is True
        assert _should_use_day_first("15/01/2023", "fr_FR") is True
        assert _should_use_day_first("15/01/2023", "es_ES") is True
        assert _should_use_day_first("15/01/2023", "it_IT") is True

    def test_asian_locales_return_false(self) -> None:
        # Asian locales typically use year-first (YMD) which is month-before-day
        assert _should_use_day_first("15/01/2023", "ja_JP") is False
        assert _should_use_day_first("15/01/2023", "zh_CN") is False
        assert _should_use_day_first("15/01/2023", "ko_KR") is False

    def test_none_locale_returns_false(self) -> None:
        # No locale defaults to False (American/month-first)
        assert _should_use_day_first("01/15/2023", None) is False
        assert _should_use_day_first("15/01/2023", None) is False

    def test_invalid_locale_returns_false(self) -> None:
        # Invalid locales default to False
        assert _should_use_day_first("01/15/2023", "invalid_LOCALE") is False


class TestTimestampParser:
    """Test the TimestampParser class with locale support."""

    def test_parse_iso_8601_no_locale(self) -> None:
        parser = TimestampParser()
        result = parser.parse("2023-01-15T10:30:00Z")
        assert result == "2023-01-15T10:30:00+00:00"

    def test_parse_iso_8601_ignores_locale(self) -> None:
        # ISO 8601 format should ignore locale and always parse as YYYY-MM-DD
        parser = TimestampParser()

        with set_locale_context("en_US"):
            result_us = parser.parse("2023-01-15")
        with set_locale_context("de_DE"):
            result_de = parser.parse("2023-01-15")

        assert "2023-01-15" in result_us
        assert "2023-01-15" in result_de

    def test_parse_ambiguous_date_american_locale(self) -> None:
        parser = TimestampParser()
        # 01/02/2023 in American format = January 2nd
        with set_locale_context("en_US"):
            result = parser.parse("01/02/2023")
        assert "2023-01-02" in result

    def test_parse_ambiguous_date_european_locale(self) -> None:
        parser = TimestampParser()
        # 01/02/2023 in European format = February 1st
        with set_locale_context("de_DE"):
            result = parser.parse("01/02/2023")
        assert "2023-02-01" in result

    def test_parse_unambiguous_date_same_result(self) -> None:
        parser = TimestampParser()

        # 31/01/2023 is unambiguous (only valid as January 31st)
        with set_locale_context("en_US"):
            result_us = parser.parse("31/01/2023")
        with set_locale_context("de_DE"):
            result_de = parser.parse("31/01/2023")

        assert "2023-01-31" in result_us
        assert "2023-01-31" in result_de

    def test_parse_with_timezone(self) -> None:
        parser = TimestampParser()
        with set_locale_context("de_DE"):
            result = parser.parse("15/01/2023 10:30:00 PST")
        assert "2023-01-15" in result
        assert "-08:00" in result  # PST is UTC-8

    def test_parse_applies_default_timezone(self) -> None:
        from datetime import timedelta, timezone

        custom_tz = timezone(timedelta(hours=5))
        parser = TimestampParser(default_timezone=custom_tz)

        # Date without timezone should get default timezone
        with set_locale_context("de_DE"):
            result = parser.parse("15/01/2023 10:30:00")
        assert "2023-01-15" in result
        assert "+05:00" in result

    def test_parse_no_locale_defaults_to_american(self) -> None:
        parser = TimestampParser()
        # Without locale context, should use American format (MM/DD/YYYY)
        result = parser.parse("01/02/2023")
        assert "2023-01-02" in result  # January 2nd, not February 1st

    def test_parse_various_european_locales(self) -> None:
        # Test multiple European locales to ensure they all use day-first
        locales = ["en_GB", "fr_FR", "es_ES", "it_IT", "pt_PT", "nl_NL"]
        parser = TimestampParser()

        for locale in locales:
            with set_locale_context(locale):
                result = parser.parse("15/01/2023")
            assert "2023-01-15" in result, f"Failed for locale {locale}"

    def test_parse_fuzzy_matching(self) -> None:
        parser = TimestampParser()
        # dateutil.parser with fuzzy=True can extract dates from text
        with set_locale_context("de_DE"):
            result = parser.parse("Date of measurement: 15/01/2023 at noon")
        assert "2023-01-15" in result

    def test_parse_invalid_date_raises_error(self) -> None:
        parser = TimestampParser()
        with pytest.raises(
            AllotropeConversionError, match="Could not parse time 'not a date'"
        ):
            parser.parse("not a date")

    def test_real_world_examples(self) -> None:
        """Test real-world date formats from various instruments."""
        parser = TimestampParser()
        test_cases = [
            # (input, locale, expected_date)
            ("2023-12-25 14:30:00", "en_US", "2023-12-25"),  # ISO format
            ("12/25/2023", "en_US", "2023-12-25"),  # American Christmas
            ("25/12/2023", "en_GB", "2023-12-25"),  # British Christmas
            ("25.12.2023", "de_DE", "2023-12-25"),  # German Christmas
            ("2023/12/25", "ja_JP", "2023-12-25"),  # Japanese ISO-like
            ("01-FEB-2023", "en_US", "2023-02-01"),  # Named month (unambiguous)
        ]

        for date_str, locale, expected in test_cases:
            with set_locale_context(locale):
                result = parser.parse(date_str)
            assert (
                expected in result
            ), f"Failed: {date_str} with {locale} -> {result} (expected {expected})"
