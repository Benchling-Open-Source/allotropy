from collections.abc import Iterable
from pathlib import Path

from allotropy.allotrope.models.shared.definitions.definitions import (
    FieldComponentDatatype,
)
from allotropy.allotrope.models.shared.definitions.units import UNITLESS
from allotropy.allotrope.schema_mappers.adm.pcr.BENCHLING._2023._09.qpcr import (
    CalculatedData,
    CalculatedDataItem,
    DataSource,
    Measurement,
    MeasurementGroup,
    Metadata,
    ProcessedData,
)
from allotropy.allotrope.schema_mappers.data_cube import DataCube, DataCubeComponent
from allotropy.parsers.agilent_gen5_image.constants import POSSIBLE_WELL_COUNTS
from allotropy.parsers.appbio_quantstudio import constants
from allotropy.parsers.appbio_quantstudio.appbio_quantstudio_structure import (
    AmplificationData,
    Header,
    MeltCurveRawData,
    MulticomponentData,
    Result,
    ResultMetadata,
    Well,
    WellItem,
)
from allotropy.parsers.utils.calculated_data_documents.definition import (
    CalculatedDocument,
)
from allotropy.parsers.utils.values import try_int_or_nan


def _create_processed_data_cubes(
    amplification_data: AmplificationData | None,
) -> tuple[DataCube | None, DataCube | None]:
    if not amplification_data:
        return None, None
    cycle_count = DataCubeComponent(FieldComponentDatatype.integer, "cycle count", "#")
    return (
        DataCube(
            label="normalized reporter",
            structure_dimensions=[cycle_count],
            structure_measures=[
                DataCubeComponent(
                    FieldComponentDatatype.double,
                    "normalized report result",
                    UNITLESS,
                )
            ],
            dimensions=[amplification_data.cycle],
            measures=[amplification_data.rn],
        ),
        DataCube(
            label="baseline corrected reporter",
            structure_dimensions=[cycle_count],
            structure_measures=[
                DataCubeComponent(
                    FieldComponentDatatype.double,
                    "baseline corrected reporter result",
                    UNITLESS,
                )
            ],
            dimensions=[amplification_data.cycle],
            measures=[amplification_data.delta_rn],
        ),
    )


def _create_processed_data(
    amplification_data: AmplificationData | None, result: Result
) -> ProcessedData:
    (
        normalized_reporter_data_cube,
        baseline_corrected_reporter_data_cube,
    ) = _create_processed_data_cubes(amplification_data)
    return ProcessedData(
        automatic_cycle_threshold_enabled_setting=result.automatic_cycle_threshold_enabled_setting,
        cycle_threshold_value_setting=result.cycle_threshold_value_setting,
        automatic_baseline_determination_enabled_setting=result.automatic_baseline,
        baseline_determination_start_cycle_setting=result.baseline_start,
        baseline_determination_end_cycle_setting=result.baseline_end,
        genotyping_determination_method_setting=result.genotyping_determination_method_setting,
        genotyping_determination_result=result.genotyping_determination_result,
        cycle_threshold_result=result.cycle_threshold_result,
        normalized_reporter_result=result.normalized_reporter_result,
        baseline_corrected_reporter_result=result.baseline_corrected_reporter_result,
        normalized_reporter_data_cube=normalized_reporter_data_cube,
        baseline_corrected_reporter_data_cube=baseline_corrected_reporter_data_cube,
        custom_info=result.extra_data,
    )


def _create_multicomponent_data_cubes(
    multicomponent_data: MulticomponentData | None,
    reporter_dye_setting: str | None,
    passive_reference_dye_setting: str | None,
) -> tuple[DataCube | None, DataCube | None]:
    if not multicomponent_data:
        return None, None

    cycle_count = DataCubeComponent(FieldComponentDatatype.integer, "cycle count", "#")
    reporter_dye_data_cube = None
    if reporter_dye_setting is not None:
        reporter_dye_data_cube = DataCube(
            label="reporter dye",
            structure_dimensions=[cycle_count],
            structure_measures=[
                DataCubeComponent(
                    FieldComponentDatatype.double,
                    "reporter dye fluorescence",
                    "RFU",
                )
            ],
            dimensions=[multicomponent_data.cycle],
            measures=[multicomponent_data.get_column(reporter_dye_setting)],
        )
    passive_reference_dye_data_cube = None
    if passive_reference_dye_setting is not None:
        passive_reference_dye_data_cube = DataCube(
            label="passive reference dye",
            structure_dimensions=[cycle_count],
            structure_measures=[
                DataCubeComponent(
                    FieldComponentDatatype.double,
                    "passive reference dye fluorescence",
                    "RFU",
                )
            ],
            dimensions=[multicomponent_data.cycle],
            measures=[multicomponent_data.get_column(passive_reference_dye_setting)],
        )
    return reporter_dye_data_cube, passive_reference_dye_data_cube


def _create_melt_curve_data_cube(
    melt_curve_raw_data: MeltCurveRawData | None,
) -> DataCube | None:
    if not melt_curve_raw_data:
        return None
    return DataCube(
        label="melting curve",
        structure_dimensions=[
            DataCubeComponent(FieldComponentDatatype.double, "temperature", "degrees C")
        ],
        structure_measures=[
            DataCubeComponent(
                FieldComponentDatatype.double,
                "reporter dye fluorescence",
                UNITLESS,
            ),
            DataCubeComponent(FieldComponentDatatype.double, "slope", UNITLESS),
        ],
        dimensions=[melt_curve_raw_data.reading],
        measures=[
            melt_curve_raw_data.fluorescence,
            melt_curve_raw_data.derivative,
        ],
    )


def _create_measurement(
    well_item: WellItem,
    header: Header,
    multicomponent_data: MulticomponentData | None,
    melt_curve_raw_data: MeltCurveRawData | None,
    amplification_data: AmplificationData | None,
    result: Result | None,
) -> Measurement | None:
    if not result:
        return None
    # TODO: temp workaround for cal doc result
    well_item._result = result

    (
        reporter_dye_data_cube,
        passive_reference_dye_data_cube,
    ) = _create_multicomponent_data_cubes(
        multicomponent_data,
        well_item.reporter_dye_setting,
        header.passive_reference_dye_setting,
    )
    return Measurement(
        identifier=well_item.uuid,
        timestamp=header.measurement_time,
        target_identifier=well_item.target_dna_description,
        sample_identifier=well_item.sample_identifier,
        group_identifier=well_item.group_identifier,
        sample_role_type=well_item.sample_role_type,
        well_location_identifier=well_item.well_location_identifier,
        well_plate_identifier=header.barcode,
        total_cycle_number_setting=amplification_data.total_cycle_number_setting
        if amplification_data
        else None,
        pcr_detection_chemistry=header.pcr_detection_chemistry,
        reporter_dye_setting=well_item.reporter_dye_setting,
        quencher_dye_setting=well_item.quencher_dye_setting,
        passive_reference_dye_setting=header.passive_reference_dye_setting,
        processed_data=_create_processed_data(amplification_data, result),
        sample_custom_info=well_item.extra_data,
        reporter_dye_data_cube=reporter_dye_data_cube,
        passive_reference_dye_data_cube=passive_reference_dye_data_cube,
        melting_curve_data_cube=_create_melt_curve_data_cube(melt_curve_raw_data),
    )


def create_metadata(header: Header, file_path: str) -> Metadata:
    return Metadata(
        device_identifier=header.device_identifier,
        device_type=constants.DEVICE_TYPE,
        device_serial_number=header.device_serial_number,
        model_number=header.model_number,
        software_name=constants.SOFTWARE_NAME,
        software_version=constants.SOFTWARE_VERSION,
        data_system_instance_identifier=constants.DATA_SYSTEM_INSTANCE_IDENTIFIER,
        file_name=Path(file_path).name,
        unc_path=file_path,
        measurement_method_identifier=header.measurement_method_identifier,
        experiment_type=header.experiment_type,
        container_type=constants.CONTAINER_TYPE,
    )


def create_calculated_data(
    calculated_data_documents: Iterable[CalculatedDocument],
    results_metadata: ResultMetadata,
) -> CalculatedData:
    return CalculatedData(
        reference_sample_description=results_metadata.reference_sample_description,
        reference_dna_description=results_metadata.reference_dna_description,
        items=[
            CalculatedDataItem(
                identifier=cal_doc.uuid,
                name=cal_doc.name,
                value=cal_doc.value,
                unit=UNITLESS,
                data_sources=[
                    DataSource(
                        identifier=data_source.reference.uuid,
                        feature=data_source.feature,
                    )
                    for data_source in cal_doc.data_sources
                ],
            )
            for cal_doc in calculated_data_documents
        ],
    )


def get_well_item_results(
    well_item: WellItem,
    results_data: dict[int, dict[str, Result]],
) -> Result | None:
    return results_data.get(well_item.identifier, {}).get(
        well_item.target_dna_description.replace(" ", "")
    )


def get_well_item_amp_data(
    well_item: WellItem, amp_data: dict[int, dict[str, AmplificationData]]
) -> AmplificationData | None:
    return amp_data.get(well_item.identifier, {}).get(well_item.target_dna_description)


def _create_measurement_group(
    header: Header,
    well: Well,
    amp_data: dict[int, dict[str, AmplificationData]],
    multi_data: dict[int, MulticomponentData],
    results_data: dict[int, dict[str, Result]],
    melt_data: dict[int, MeltCurveRawData],
    plate_well_count: int | None,
) -> MeasurementGroup | None:
    measurements = [
        _create_measurement(
            well_item,
            header,
            multi_data.get(well.identifier),
            melt_data.get(well.identifier),
            get_well_item_amp_data(well_item, amp_data),
            get_well_item_results(well_item, results_data),
        )
        for well_item in well.items
        if get_well_item_results(well_item, results_data)
    ]
    group = MeasurementGroup(
        analyst=header.analyst,
        experimental_data_identifier=header.experimental_data_identifier,
        plate_well_count=try_int_or_nan(plate_well_count),
        measurements=[m for m in measurements if m is not None],
    )
    return group if group.measurements else None


def _get_plate_well_count(header: Header, wells: list[Well]) -> int | None:
    if header.plate_well_count is not None:
        return header.plate_well_count

    # Get well numbers via Well ID (1, 2, 3, ...) and well location (A1, B1, ...)
    well_ids = [well_item.identifier for well in wells for well_item in well.items]
    well_location = [
        well_item.position
        for well in wells
        for well_item in well.items
        if well_item.position
    ]
    largest_column = sorted([str(loc[0]) for loc in well_location])[-1]
    largest_row = sorted(int(loc[1:]) for loc in well_location)[-1]
    well_number_by_position = (ord(largest_column.upper()) - ord("A") + 1) * largest_row
    largest_well_number = max(sorted(well_ids)[-1], well_number_by_position)

    # Round up to the first possible well count GTE the count e.g:
    # - If we have well id 94 but none greater than 96, it's a 96-well plate
    for possible_count in POSSIBLE_WELL_COUNTS:
        if largest_well_number > possible_count:
            continue
        return possible_count

    return None


def create_measurement_groups(
    header: Header,
    wells: list[Well],
    amp_data: dict[int, dict[str, AmplificationData]],
    multi_data: dict[int, MulticomponentData],
    results_data: dict[int, dict[str, Result]],
    melt_data: dict[int, MeltCurveRawData],
) -> list[MeasurementGroup]:

    plate_well_count = _get_plate_well_count(header, wells)
    groups = [
        _create_measurement_group(
            header,
            well,
            amp_data,
            multi_data,
            results_data,
            melt_data,
            plate_well_count,
        )
        for well in wells
    ]
    return [group for group in groups if group]
