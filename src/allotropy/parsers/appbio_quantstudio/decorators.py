from typing import Any, Callable


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
