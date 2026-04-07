"""Context management for locale-aware number parsing.

This module provides utilities to set and manage the current locale context
for number parsing throughout the parsing pipeline.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from allotropy.parsers.utils.values import _current_locale


@contextmanager
def set_locale_context(locale: str | None) -> Iterator[None]:
    """Context manager to set the locale for number parsing.

    Args:
        locale: The locale string (e.g., "en_US", "de_DE", "fr_FR") or None for default

    Example:
        >>> with set_locale_context("de_DE"):
        ...     # All try_float() calls within this context will use German locale
        ...     value = try_float("1.234,56", "value")  # Parses as 1234.56
    """
    token = _current_locale.set(locale)
    try:
        yield
    finally:
        _current_locale.reset(token)


def get_current_locale() -> str | None:
    """Get the currently set locale for number parsing.

    Returns:
        The current locale string or None if not set
    """
    return _current_locale.get()
