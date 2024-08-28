from allotropy.allotrope.models.adm.pcr.benchling._2023._09.qpcr import (
    ExperimentType,
)
from allotropy.allotrope.models.shared.definitions.definitions import (
    FieldComponentDatatype,
)
from allotropy.allotrope.models.shared.definitions.units import UNITLESS
from allotropy.allotrope.schema_mappers.adm.pcr.BENCHLING._2023._09.qpcr import (
    CalculatedData,
    CalculatedDataItem,
    DataCube,
    DataCubeComponent,
    DataSource,
    Measurement,
    MeasurementGroup,
    Metadata,
    ProcessedData,
)
from allotropy.exceptions import AllotropeConversionError
from allotropy.parsers.appbio_quantstudio.appbio_quantstudio_data_creator import (
    _create_multicomponent_data_cubes,
    _create_processed_data_cubes,
)
from allotropy.parsers.appbio_quantstudio.appbio_quantstudio_structure import (
    AmplificationData,
)
from allotropy.parsers.appbio_quantstudio_designandanalysis import constants
from allotropy.parsers.appbio_quantstudio_designandanalysis.appbio_quantstudio_designandanalysis_reader import (
    DesignQuantstudioReader,
)
from allotropy.parsers.appbio_quantstudio_designandanalysis.structure.generic.creator import (
    Creator,
)
from allotropy.parsers.appbio_quantstudio_designandanalysis.structure.generic.structure import (
    Data,
    Header,
    MeltCurveData,
    Result,
    Well,
    WellItem,
)
from allotropy.parsers.appbio_quantstudio_designandanalysis.structure.genotyping.creator import (
    GenotypingCreator,
)
from allotropy.parsers.appbio_quantstudio_designandanalysis.structure.melt_curve.creator import (
    MeltCurveCreator,
)
from allotropy.parsers.appbio_quantstudio_designandanalysis.structure.presence_absence.creator import (
    PresenceAbsenceCreator,
)
from allotropy.parsers.appbio_quantstudio_designandanalysis.structure.primary_analysis.creator import (
    PrimaryAnalysisCreator,
)
from allotropy.parsers.appbio_quantstudio_designandanalysis.structure.relative_standard_curve.creator import (
    RelativeStandardCurveCreator,
)
from allotropy.parsers.appbio_quantstudio_designandanalysis.structure.standard_curve.creator import (
    StandardCurveCreator,
)


def create_metadata(
    header: Header, file_name: str, experiment_type: ExperimentType
) -> Metadata:
    return Metadata(
        file_name=file_name,
        product_manufacturer=constants.PRODUCT_MANUFACTURER,
        device_identifier=header.device_identifier,
        model_number=header.model_number,
        device_serial_number=header.device_serial_number,
        data_system_instance_identifier=constants.DATA_SYSTEM_INSTANCE_IDENTIFIER,
        unc_path="",  # unknown
        software_name=header.software_name,
        software_version=header.software_version,
        container_type=constants.CONTAINER_TYPE,
        device_type=constants.DEVICE_TYPE,
        experiment_type=experiment_type,
        measurement_method_identifier=header.measurement_method_identifier,
    )


def _create_processed_data(
    result: Result, amplification_data: AmplificationData | None
) -> ProcessedData:
    return ProcessedData(
        automatic_cycle_threshold_enabled_setting=result.automatic_cycle_threshold_enabled_setting,
        cycle_threshold_value_setting=result.cycle_threshold_value_setting,
        automatic_baseline_determination_enabled_setting=result.automatic_baseline_determination_enabled_setting,
        baseline_determination_start_cycle_setting=result.baseline_determination_start_cycle_setting,
        baseline_determination_end_cycle_setting=result.baseline_determination_end_cycle_setting,
        genotyping_determination_method_setting=result.genotyping_determination_method_setting,
        genotyping_determination_result=result.genotyping_determination_result,
        cycle_threshold_result=result.cycle_threshold_result,
        normalized_reporter_result=result.normalized_reporter_result,
        baseline_corrected_reporter_result=result.baseline_corrected_reporter_result,
        data_cubes=_create_processed_data_cubes(amplification_data)
        if amplification_data
        else None,
    )


def _create_melt_curve_data_cube(melt_curve_raw_data: MeltCurveData) -> DataCube:
    return DataCube(
        label="melting curve",
        structure_dimensions=[
            DataCubeComponent(FieldComponentDatatype.double, "temperature", "degC")
        ],
        structure_measures=[
            DataCubeComponent(FieldComponentDatatype.double, "fluorescence", "RFU"),
            DataCubeComponent(FieldComponentDatatype.double, "derivative", UNITLESS),
        ],
        dimensions=[melt_curve_raw_data.temperature],
        measures=[
            melt_curve_raw_data.fluorescence,
            melt_curve_raw_data.derivative,
        ],
    )


def _create_measurement(well: Well, well_item: WellItem, header: Header) -> Measurement:
    data_cubes: list[DataCube] = []
    if well.multicomponent_data:
        data_cubes.extend(
            _create_multicomponent_data_cubes(
                well.multicomponent_data,
                well_item.reporter_dye_setting,
                header.passive_reference_dye_setting,
            )
        )
    if well_item.melt_curve_data:
        data_cubes.append(_create_melt_curve_data_cube(well_item.melt_curve_data))

    return Measurement(
        identifier=well_item.uuid,
        timestamp=header.measurement_time,
        target_identifier=well_item.target_dna_description,
        sample_identifier=well_item.sample_identifier,
        sample_role_type=well_item.sample_role_type,
        well_location_identifier=well_item.well_location_identifier,
        well_plate_identifier=header.barcode,
        total_cycle_number_setting=well_item.amplification_data.total_cycle_number_setting
        if well_item.amplification_data
        else None,
        pcr_detection_chemistry=header.pcr_detection_chemistry,
        reporter_dye_setting=well_item.reporter_dye_setting,
        quencher_dye_setting=well_item.quencher_dye_setting,
        passive_reference_dye_setting=header.passive_reference_dye_setting,
        processed_data=_create_processed_data(
            well_item.result, well_item.amplification_data
        ),
        data_cubes=data_cubes,
    )


def create_measurement_groups(
    wells: list[Well], header: Header
) -> list[MeasurementGroup]:
    return [
        MeasurementGroup(
            analyst=header.analyst,
            experimental_data_identifier=header.experimental_data_identifier,
            plate_well_count=header.plate_well_count,
            measurements=[
                _create_measurement(well, well_item, header)
                for well_item in well.items.values()
            ],
        )
        for well in wells
    ]


def create_calculated_data(data: Data) -> CalculatedData:
    return CalculatedData(
        reference_dna_description=data.reference_target,
        reference_sample_description=data.reference_sample,
        items=[
            CalculatedDataItem(
                identifier=calc_doc.uuid,
                name=calc_doc.name,
                value=calc_doc.value,
                unit=UNITLESS,
                data_sources=[
                    DataSource(
                        identifier=data_source.reference.uuid,
                        feature=data_source.feature,
                    )
                    for data_source in calc_doc.data_sources
                ],
            )
            for calc_doc in data.calculated_documents
        ],
    )


def create_data(reader: DesignQuantstudioReader) -> Data:
    possible_creators: list[type[Creator]] = [
        StandardCurveCreator,
        RelativeStandardCurveCreator,
        GenotypingCreator,
        MeltCurveCreator,
        PresenceAbsenceCreator,
        PrimaryAnalysisCreator,
    ]
    matching_creator = [
        creator for creator in possible_creators if creator.check_type(reader)
    ]

    if len(matching_creator) == 1:
        return matching_creator[0].create(reader)

    msg = "Unable to infer experiment type from sheets in the input"
    raise AllotropeConversionError(msg)
