from typing import Any

import pandas as pd

from allotropy.json_to_csv.json_to_csv import json_to_csv
from allotropy.json_to_csv.mapper_config import MapperConfig


def map_json(
    data: dict[str, Any], mapper_config: dict[str, Any]
) -> dict[str, pd.DataFrame | dict[str, Any]]:
    return json_to_csv(data, MapperConfig.create(mapper_config))
