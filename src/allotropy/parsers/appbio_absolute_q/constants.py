from collections.abc import Sequence
from enum import Enum

from attr import dataclass

PLATE_WELL_COUNT = 16
DEVICE_TYPE = "dPCR"
PRODUCT_MANUFACTURER = "ThermoFisher Scientific"
BRAND_NAME = "QuantStudio Absolute Q Digital PCR System"
SOFTWARE_NAME = "QuantStudio Absolute Q Digital PCR Software"
CONCENTRATION_COLUMNS = ("Conc. cp/uL", "Copies per microliter", "Conc.")

POSSIBLE_DYE_SETTING_LENGTHS = [3]


def get_dye_settings(columns: list[str]) -> list[str]:
    return [
        col
        for col in columns
        if len(col) in POSSIBLE_DYE_SETTING_LENGTHS and col == col.upper()
    ]


class AggregationType(str, Enum):
    INDIVIDUAL = "INDIVIDUAL"
    AVERAGE = "AVERAGE"
    POOLED = "POOLED"


class CalculatedDataSource(str, Enum):
    MEASUREMENT = "MEASUREMENT"
    CALCULATED_DATA = "CALCULATED_DATA"


AGGREGATION_LOOKUP = {
    "Average": AggregationType.AVERAGE,
    "Pooled": AggregationType.POOLED,
}


@dataclass(frozen=True)
class CalculatedDataReference:
    column: str | Sequence[str]
    name: str
    source: CalculatedDataSource
    source_feature: str
    unit: str

    @property
    def source_features(self) -> list[str]:
        return self.source_feature.split(",")

    @property
    def column_key(self) -> str:
        return self.column if isinstance(self.column, str) else ",".join(self.column)


CALCULATED_DATA_REFERENCE: dict[AggregationType, list[CalculatedDataReference]] = {
    AggregationType.AVERAGE: [
        CalculatedDataReference(
            column="Total",
            name="Average Total",
            source=CalculatedDataSource.MEASUREMENT,
            source_feature="total partition count",
            unit="#",
        ),
        CalculatedDataReference(
            column=CONCENTRATION_COLUMNS,
            name="Average Concentration",
            source=CalculatedDataSource.MEASUREMENT,
            source_feature="number concentration",
            unit="#/μL",
        ),
        CalculatedDataReference(
            column="SD",
            name="SD Concentration",
            source=CalculatedDataSource.MEASUREMENT,
            source_feature="number concentration",
            unit="#/μL",
        ),
        CalculatedDataReference(
            column="Positives",
            name="Average Positives",
            source=CalculatedDataSource.MEASUREMENT,
            source_feature="positive partition count",
            unit="#",
        ),
        CalculatedDataReference(
            column="CV%",
            name="CV",
            source=CalculatedDataSource.CALCULATED_DATA,
            source_feature="Average Concentration,SD Concentration",
            unit="%",
        ),
        CalculatedDataReference(
            column="95%DeltaLCI",
            name="Average 95%DeltaLCI",
            source=CalculatedDataSource.MEASUREMENT,
            source_feature="95%DeltaLCI",
            unit="(unitless)",
        ),
        CalculatedDataReference(
            column="95%DeltaUCI",
            name="Average 95%DeltaUCI",
            source=CalculatedDataSource.MEASUREMENT,
            source_feature="95%DeltaUCI",
            unit="(unitless)",
        ),
    ],
    AggregationType.POOLED: [
        CalculatedDataReference(
            column="Total",
            name="Pooled Total",
            source=CalculatedDataSource.MEASUREMENT,
            source_feature="total partition count",
            unit="#",
        ),
        CalculatedDataReference(
            column="Conc. cp/uL",
            name="Pooled Concentration",
            source=CalculatedDataSource.MEASUREMENT,
            source_feature="number concentration",
            unit="#/μL",
        ),
        CalculatedDataReference(
            column="Positives",
            name="Pooled Positives",
            source=CalculatedDataSource.MEASUREMENT,
            source_feature="positive partition count",
            unit="#",
        ),
    ],
    AggregationType.INDIVIDUAL: [
        CalculatedDataReference(
            column="95%DeltaLCI",
            name="95%DeltaLCI",
            source=CalculatedDataSource.MEASUREMENT,
            source_feature="total partition count,positive partition count",
            unit="(unitless)",
        ),
        CalculatedDataReference(
            column="95%DeltaUCI",
            name="95%DeltaUCI",
            source=CalculatedDataSource.MEASUREMENT,
            source_feature="total partition count,positive partition count",
            unit="(unitless)",
        ),
        CalculatedDataReference(
            column="Precision %",
            name="Precision %",
            source=CalculatedDataSource.MEASUREMENT,
            source_feature="total partition count,positive partition count",
            unit="(unitless)",
        ),
        CalculatedDataReference(
            column="Lambda (cp/Rxn)",
            name="Lambda (cp/Rxn)",
            source=CalculatedDataSource.MEASUREMENT,
            source_feature="total partition count,positive partition count",
            unit="(unitless)",
        ),
        CalculatedDataReference(
            column="Lambda_95%DeltaLCI",
            name="Lambda_95%DeltaLCI",
            source=CalculatedDataSource.MEASUREMENT,
            source_feature="total partition count,positive partition count",
            unit="(unitless)",
        ),
        CalculatedDataReference(
            column="Lambda_95%DeltaUCI",
            name="Lambda_95%DeltaUCI",
            source=CalculatedDataSource.MEASUREMENT,
            source_feature="total partition count,positive partition count",
            unit="(unitless)",
        ),
        CalculatedDataReference(
            column="Lambda_95%DeltaLCI",
            name="Lambda_95%DeltaLCI",
            source=CalculatedDataSource.MEASUREMENT,
            source_feature="total partition count,positive partition count",
            unit="(unitless)",
        ),
        CalculatedDataReference(
            column="Lambda_95%DeltaUCI",
            name="Lambda_95%DeltaUCI",
            source=CalculatedDataSource.MEASUREMENT,
            source_feature="total partition count,positive partition count",
            unit="(unitless)",
        ),
        CalculatedDataReference(
            column="MeanQC",
            name="MeanQC",
            source=CalculatedDataSource.MEASUREMENT,
            source_feature="QC Channel",
            unit="(unitless)",
        ),
        CalculatedDataReference(
            column="CV_QC",
            name="CV_QC",
            source=CalculatedDataSource.MEASUREMENT,
            source_feature="QC Channel",
            unit="(unitless)",
        ),
    ],
}
