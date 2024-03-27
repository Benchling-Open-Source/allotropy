from __future__ import annotations

from dataclasses import dataclass


@dataclass
class BackgroundInfo:
    experiment_type: str


@dataclass(frozen=True)
class Data:
    version: str
    background_info: BackgroundInfo

    def get_experiment_type(self) -> str:
        return self.background_info.experiment_type
