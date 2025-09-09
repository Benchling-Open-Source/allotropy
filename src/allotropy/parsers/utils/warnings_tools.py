from __future__ import annotations

from collections.abc import Callable
import functools
import gc
import os
from typing import Any


def suppress_unused_keys_warning(func: Callable[..., Any]) -> Callable[..., Any]:
    """
    Use when a class that warns for unread keys is created for a special one-off use that does not intend to read all keys, e.g.
    to read a single value and return.
    Not appropriate to use in the main use of the class where unread keys should be copied into custom data fields.
    """

    @functools.wraps(func)
    def _wrapper(*args: Any, **kwargs: Any) -> Any:
        previous_warn_unused_keys = os.environ.pop("WARN_UNUSED_KEYS", None)
        try:
            return func(*args, **kwargs)
        finally:
            gc.collect()
            if previous_warn_unused_keys is not None:
                os.environ["WARN_UNUSED_KEYS"] = previous_warn_unused_keys

    return _wrapper
