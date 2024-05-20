# mypy: disallow_any_generics = False

from collections.abc import Callable
from typing import Any


def cache(fun: Callable) -> Callable:
    cache: dict[str, Any] = {}

    def inner(*args: Any) -> Any:
        key = "".join([str(arg) for arg in args])
        if key in cache:
            return cache[key]
        result = fun(*args)
        cache[key] = result
        return result

    return inner
