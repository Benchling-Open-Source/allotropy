from enum import Enum

from attr import dataclass


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
    None: AggregationType.INDIVIDUAL,
}


@dataclass(frozen=True)
class CalculatedDataItem:
    column: str
    name: str
    source: CalculatedDataSource
    source_feature: str
    unit: str


CALCULATED_DATA_REFERENCE: dict[AggregationType, list[CalculatedDataItem]] = {
    AggregationType.AVERAGE: [
        CalculatedDataItem(
            column="Total",
            name="Average Total",
            source=CalculatedDataSource.MEASUREMENT,
            source_feature="total partition count",
            unit="#",
        ),
        CalculatedDataItem(
            column="Conc. cp/uL",
            name="Average Concentration",
            source=CalculatedDataSource.MEASUREMENT,
            source_feature="number concentration",
            unit="#/μL",
        ),
        CalculatedDataItem(
            column="SD",
            name="SD Concentration",
            source=CalculatedDataSource.MEASUREMENT,
            source_feature="number concentration",
            unit="#/μL",
        ),
        CalculatedDataItem(
            column="CV%",
            name="CV",
            source=CalculatedDataSource.CALCULATED_DATA,
            source_feature="Average Concentration,SD Concentration",
            unit="%",
        ),
        CalculatedDataItem(
            column="Positives",
            name="Average Positives",
            source=CalculatedDataSource.MEASUREMENT,
            source_feature="positive partition count",
            unit="#",
        ),
    ],
    AggregationType.POOLED: [
        CalculatedDataItem(
            column="Total",
            name="Pooled Total",
            source=CalculatedDataSource.MEASUREMENT,
            source_feature="total partition count",
            unit="#",
        ),
        CalculatedDataItem(
            column="Conc. cp/uL",
            name="Pooled Concentration",
            source=CalculatedDataSource.MEASUREMENT,
            source_feature="number concentration",
            unit="#/μL",
        ),
        CalculatedDataItem(
            column="Positives",
            name="Pooled Positives",
            source=CalculatedDataSource.MEASUREMENT,
            source_feature="positive partition count",
            unit="#",
        ),
    ],
}
