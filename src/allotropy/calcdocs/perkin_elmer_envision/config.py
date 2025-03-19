from dataclasses import dataclass

from allotropy.calcdocs.config import CalculatedDataConfig
from allotropy.calcdocs.view import Keys


@dataclass(frozen=True)
class EnvisionCalculatedDataConfig(CalculatedDataConfig):
    plate_number: str = ""

    def get_cache_key(self, keys: Keys) -> str:
        return f"{self.name} {self.value} {keys} {self.plate_number}"
