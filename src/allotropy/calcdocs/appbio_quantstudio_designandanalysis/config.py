from __future__ import annotations

from dataclasses import dataclass

from allotropy.calcdocs.config import CalculatedDataConfig


@dataclass(frozen=True)
class CalculatedDataConfigWithOptional(CalculatedDataConfig):
    optional: bool = False
