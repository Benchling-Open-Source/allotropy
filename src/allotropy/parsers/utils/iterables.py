from collections.abc import Callable, Iterable
from typing import TypeVar

T = TypeVar("T")
S = TypeVar("S")


def get_first_not_none(func: Callable[[T], S | None], args: Iterable[T]) -> S | None:
    for arg in args:
        ret = func(arg)
        if ret is not None:
            return ret
    return None
