from dataclasses import dataclass
from enum import Enum

import pandas as pd

from allotropy.allotrope.models.shared.definitions.units import UNITLESS
from allotropy.allotrope.schema_mappers.adm.plate_reader.rec._2024._06.plate_reader import (
    CalculatedDataItem,
    DataSource,
    Measurement,
)
from allotropy.exceptions import AllotropeConversionError
from allotropy.parsers.utils.pandas import SeriesData
from allotropy.parsers.utils.uuids import random_uuid_str


class AggregatingProperty(Enum):
    ASSAY_IDENTIFIER = "assay identifier"
    SAMPLE_IDENTIFIER = "sample_identifier"
    WELL_PLATE_IDENTIFIER = "well_plate_identifier"
    LOCATION_IDENTIFIER = "location_identifier"
    WELL_PLATE_ID = "well_plate_identifier"
    LOCATION_ID = "location_identifier"


class CalculatedDataColumns(Enum):
    ADJUSTED_SIGNAL = "Adjusted Signal"
    MEAN = "Mean"
    ADJ_SIG_MEAN = "Adj. Sig. Mean"
    FIT_STATISTIC_RSQUARED = "Fit Statistic: RSquared"
    CV = "CV"
    PERCENT_RECOVERY = "% Recovery"
    PERCENT_RECOVERY_MEAN = "% Recovery Mean"
    CALC_CONCENTRATION = "Calc. Concentration"
    CALC_CONC_MEAN = "Calc. Conc. Mean"


@dataclass
class CalculatedDataMapping:
    msd_column: CalculatedDataColumns
    is_data_source_id_measurement: bool  # if True then data source id is measurement id, else calculated data id
    data_source_feature: str
    aggregating_property: list[str]


calculated_data_mappings = [
    CalculatedDataMapping(
        msd_column=CalculatedDataColumns.ADJUSTED_SIGNAL,
        is_data_source_id_measurement=True,
        data_source_feature="luminescence",
        aggregating_property=[
            AggregatingProperty.ASSAY_IDENTIFIER.value,
            AggregatingProperty.SAMPLE_IDENTIFIER.value,
        ],
    ),
    CalculatedDataMapping(
        msd_column=CalculatedDataColumns.MEAN,
        is_data_source_id_measurement=True,
        data_source_feature="luminescence",
        aggregating_property=[AggregatingProperty.ASSAY_IDENTIFIER.value],
    ),
    CalculatedDataMapping(
        msd_column=CalculatedDataColumns.ADJ_SIG_MEAN,
        is_data_source_id_measurement=False,
        data_source_feature=CalculatedDataColumns.MEAN.value,
        aggregating_property=[AggregatingProperty.ASSAY_IDENTIFIER.value],
    ),
    CalculatedDataMapping(
        msd_column=CalculatedDataColumns.FIT_STATISTIC_RSQUARED,
        is_data_source_id_measurement=True,
        data_source_feature="luminescence",
        aggregating_property=[AggregatingProperty.ASSAY_IDENTIFIER.value],
    ),
    CalculatedDataMapping(
        msd_column=CalculatedDataColumns.CV,
        is_data_source_id_measurement=True,
        data_source_feature="luminescence",
        aggregating_property=[AggregatingProperty.ASSAY_IDENTIFIER.value],
    ),
    CalculatedDataMapping(
        msd_column=CalculatedDataColumns.PERCENT_RECOVERY,
        is_data_source_id_measurement=True,
        data_source_feature="luminescence",
        aggregating_property=[
            AggregatingProperty.SAMPLE_IDENTIFIER.value,
            AggregatingProperty.WELL_PLATE_IDENTIFIER.value,
            AggregatingProperty.LOCATION_IDENTIFIER.value,
        ],
    ),
    CalculatedDataMapping(
        msd_column=CalculatedDataColumns.PERCENT_RECOVERY_MEAN,
        is_data_source_id_measurement=False,
        data_source_feature=CalculatedDataColumns.PERCENT_RECOVERY.value,
        aggregating_property=[AggregatingProperty.ASSAY_IDENTIFIER.value],
    ),
    CalculatedDataMapping(
        msd_column=CalculatedDataColumns.CALC_CONCENTRATION,
        is_data_source_id_measurement=True,
        data_source_feature="luminescence",
        aggregating_property=[
            AggregatingProperty.SAMPLE_IDENTIFIER.value,
            AggregatingProperty.WELL_PLATE_IDENTIFIER.value,
            AggregatingProperty.LOCATION_IDENTIFIER.value,
        ],
    ),
    CalculatedDataMapping(
        msd_column=CalculatedDataColumns.CALC_CONC_MEAN,
        is_data_source_id_measurement=False,
        data_source_feature=CalculatedDataColumns.CALC_CONCENTRATION.value,
        aggregating_property=[AggregatingProperty.ASSAY_IDENTIFIER.value],
    ),
]


def _format_r_squared_name(name: str) -> str:
    return name.split(":")[-1].strip()


def _get_measurement_by_location_identifier(
    measurements: list[Measurement], location_identifier: str
) -> Measurement:
    for measurement in measurements:
        if measurement.location_identifier == location_identifier:
            return measurement
    msg = f"No measurement found for location identifier: {location_identifier}"
    raise AllotropeConversionError(msg)


def _get_measurement_aggregate_properties(
    measurement: Measurement, aggregating_property: list[str]
) -> list[str]:
    aggregating_property = aggregating_property.copy()
    agg_properties: list[str] = []
    if (
        AggregatingProperty.ASSAY_IDENTIFIER.value in aggregating_property
        and measurement.measurement_custom_info
    ):
        assay_id = measurement.measurement_custom_info.get(
            AggregatingProperty.ASSAY_IDENTIFIER.value
        )
        if assay_id:
            agg_properties.append(assay_id)
        del aggregating_property[
            aggregating_property.index(AggregatingProperty.ASSAY_IDENTIFIER.value)
        ]

    agg_properties.extend([getattr(measurement, prop) for prop in aggregating_property])
    return agg_properties


def _get_data_sources(
    measurements: list[Measurement],
    calculated_data_mapping: CalculatedDataMapping,
    row: SeriesData,
    calculated_data: list[CalculatedDataItem],
) -> list[DataSource]:
    location_identifier = row[str, "Well"] + "_" + row[str, "Spot"]
    current_measurement = _get_measurement_by_location_identifier(
        measurements, location_identifier
    )
    agg_properties = _get_measurement_aggregate_properties(
        current_measurement, calculated_data_mapping.aggregating_property
    )
    # get measurements with the same aggregate properties as the current one
    measurements_with_agg_properties = [
        measurement
        for measurement in measurements
        if _get_measurement_aggregate_properties(
            measurement, calculated_data_mapping.aggregating_property
        )
        == agg_properties
    ]
    if not calculated_data_mapping.is_data_source_id_measurement:
        feature = calculated_data_mapping.data_source_feature
        if feature == CalculatedDataColumns.FIT_STATISTIC_RSQUARED.value:
            feature = _format_r_squared_name(feature)
        calc_data_by_feature = list(
            filter(lambda item: item.name == feature, calculated_data)
        )
        measurements_with_agg_properties_ids = [
            measurement.identifier for measurement in measurements_with_agg_properties
        ]
        calc_data_by_feature = list(
            filter(
                lambda calc: all(
                    source.identifier in measurements_with_agg_properties_ids
                    for source in calc.data_sources
                ),
                calc_data_by_feature,
            )
        )
        return [
            DataSource(
                identifier=calc_data.identifier,
                feature=calculated_data_mapping.data_source_feature,
            )
            for calc_data in calc_data_by_feature
        ]

    return [
        DataSource(
            identifier=measurement.identifier,
            feature=calculated_data_mapping.data_source_feature,
        )
        for measurement in measurements_with_agg_properties
    ]


def _is_calc_data_created(
    calculated_data: list[CalculatedDataItem],
    data_sources: list[DataSource],
    calc_data_name: str,
) -> bool:
    for calc_data in calculated_data:
        if calc_data.name == calc_data_name and set(calc_data.data_sources) == set(
            data_sources
        ):
            return True
    return False


def create_calculated_data_groups(
    data: pd.DataFrame, measurements: list[Measurement]
) -> list[CalculatedDataItem]:
    data = data.iloc[1:].reset_index(drop=True)
    data.columns = pd.Index(data.iloc[0])
    data = data[1:].reset_index(drop=True)
    calculated_data: list[CalculatedDataItem] = []
    for _row_index, row in data.iterrows():
        row_series = SeriesData(row)
        for calc_data_item in calculated_data_mappings:
            value = row_series.get(float, calc_data_item.msd_column.value)
            data_sources = _get_data_sources(
                measurements, calc_data_item, row_series, calculated_data
            )
            name = calc_data_item.msd_column.value
            # handle special case for Fit Statistic: RSquared
            if name == CalculatedDataColumns.FIT_STATISTIC_RSQUARED.value:
                name = _format_r_squared_name(name)
            if (
                not value
                or not data_sources
                or _is_calc_data_created(calculated_data, data_sources, name)
            ):
                continue

            calculated_data.append(
                CalculatedDataItem(
                    identifier=random_uuid_str(),
                    data_sources=data_sources,
                    unit=UNITLESS,
                    name=name,
                    value=value,
                )
            )

    # merge calculated data that has its source as other calculated data values
    not_data_source_measurement_id_mappings = [
        calc_data_mapping
        for calc_data_mapping in calculated_data_mappings
        if not calc_data_mapping.is_data_source_id_measurement
    ]
    for calc_data_mapping in not_data_source_measurement_id_mappings:
        calc_data: list[CalculatedDataItem] = [
            calc_data_item
            for calc_data_item in calculated_data
            if calc_data_item.name == calc_data_mapping.msd_column.value
        ]
        if not calc_data:
            continue
        data_sources_identifiers = [
            source.identifier for calc in calc_data for source in calc.data_sources
        ]
        if len(data_sources_identifiers) != len(set(data_sources_identifiers)):
            ordered_sources = list(set(data_sources_identifiers))
            ordered_sources.sort()
            value = calc_data[0].value
            new_calc_data_item = CalculatedDataItem(
                identifier=random_uuid_str(),
                data_sources=[
                    DataSource(
                        identifier=identifier,
                        feature=calc_data_mapping.data_source_feature,
                    )
                    for identifier in ordered_sources
                ],
                unit=UNITLESS,
                name=calc_data_mapping.msd_column.value,
                value=value,
            )
            for item in calc_data:
                calculated_data.remove(item)
            calculated_data.append(new_calc_data_item)
    return calculated_data
