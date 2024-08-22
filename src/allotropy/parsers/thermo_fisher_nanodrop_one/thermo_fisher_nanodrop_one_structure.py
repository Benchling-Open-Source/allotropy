import pandas as pd

from allotropy.allotrope.schema_mappers.adm.spectrophotometry.benchling._2023._12.spectrophotometry import (
    Data,
    Metadata,
)


def create_data(_: dict[str, pd.DataFrame], file_name: str) -> Data:
    return Data(
        metadata=Metadata(
            device_identifier="N/A",
            device_type="",
            model_number="NanoDrop One",
            brand_name="NanoDrop",
            product_manufacturer="ThermoFisher Scientific",
            file_name=file_name,
            software_name="NanoDrop One software",
        ),
        measurement_groups=[],
    )
