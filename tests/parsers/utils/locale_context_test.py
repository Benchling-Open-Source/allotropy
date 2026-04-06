"""Tests for locale context management."""

import pytest

from allotropy.parsers.utils.locale_context import (
    get_current_locale,
    set_locale_context,
)
from allotropy.parsers.utils.values import try_float


class TestLocaleContext:
    def test_default_locale_is_none(self) -> None:
        assert get_current_locale() is None

    def test_set_locale_context(self) -> None:
        assert get_current_locale() is None

        with set_locale_context("de_DE"):
            assert get_current_locale() == "de_DE"

        assert get_current_locale() is None

    def test_nested_contexts(self) -> None:
        with set_locale_context("en_US"):
            assert get_current_locale() == "en_US"

            with set_locale_context("de_DE"):
                assert get_current_locale() == "de_DE"

            assert get_current_locale() == "en_US"

        assert get_current_locale() is None

    def test_context_exception_handling(self) -> None:
        """Ensure locale is reset even if exception occurs."""
        assert get_current_locale() is None

        try:
            with set_locale_context("de_DE"):
                assert get_current_locale() == "de_DE"
                msg = "test error"
                raise ValueError(msg)
        except ValueError:
            pass

        # Locale should be reset despite exception
        assert get_current_locale() is None


class TestTryFloatWithLocale:
    def test_try_float_with_us_locale(self) -> None:
        with set_locale_context("en_US"):
            result = try_float("1,234.56", "test")
            assert result == pytest.approx(1234.56)

    def test_try_float_with_de_locale(self) -> None:
        with set_locale_context("de_DE"):
            result = try_float("1.234,56", "test")
            assert result == pytest.approx(1234.56)

    def test_try_float_without_locale_uses_default(self) -> None:
        # Without locale, comma is treated as decimal separator
        result = try_float("1,5", "test")
        assert result == pytest.approx(1.5)

    def test_try_float_fallback_on_parse_error(self) -> None:
        # If locale parsing fails, should fall back to default
        with set_locale_context("en_US"):
            # This is invalid for en_US but valid for default (comma as decimal)
            result = try_float("1,5", "test")
            # Should fall back to default parsing (comma as decimal)
            assert result == pytest.approx(1.5)
