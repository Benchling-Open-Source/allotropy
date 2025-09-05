from __future__ import annotations

from collections.abc import Callable
import functools
import gc
import os
from typing import Any


def suppress_unused_keys_warning(func: Callable[..., Any]) -> Callable[..., Any]:
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
