from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class Data:
    @staticmethod
    def create(_: dict[str, pd.DataFrame]) -> Data:
        return Data()
