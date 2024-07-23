from collections.abc import Iterable

from allotropy.allotrope.models.adm.pcr.benchling._2023._09.qpcr import ContainerType
from allotropy.allotrope.models.shared.definitions.definitions import (
    FieldComponentDatatype,
)
from allotropy.allotrope.models.shared.definitions.units import UNITLESS
from allotropy.allotrope.schema_mappers.adm.pcr.BENCHLING._2023._09.qpcr import (
    CalculatedData,
    CalculatedDataItem,
    Data,
    DataCube,
    DataCubeComponent,
    DataSource,
    Measurement,
    MeasurementGroup,
    Metadata,
    ProcessedData,
)
from allotropy.parsers.appbio_quantstudio.appbio_quantstudio_calculated_documents import (
    iter_calculated_data_documents,
)
from allotropy.parsers.appbio_quantstudio.appbio_quantstudio_structure import (
    AmplificationData,
    Header,
    MeltCurveRawData,
    MulticomponentData,
    RawData,
    Result,
    ResultMetadata,
    Well,
    WellItem,
)
from allotropy.parsers.lines_reader import LinesReader
from allotropy.parsers.utils.calculated_data_documents.definition import (
    CalculatedDocument,
)
from allotropy.parsers.utils.values import try_int_or_nan


def _create_processed_data(
    amplification_data: AmplificationData,
    result: Result,
) -> ProcessedData:
    cycle_count = DataCubeComponent(FieldComponentDatatype.integer, "cycle count", "#")
    return ProcessedData(
        automatic_cycle_threshold_enabled_setting=result.automatic_baseline_determination_enabled_setting,
        cycle_threshold_value_setting=result.cycle_threshold_value_setting,
        automatic_baseline_determination_enabled_setting=result.automatic_baseline_determination_enabled_setting,
        genotyping_determination_method_setting=result.genotyping_determination_method_setting,
        genotyping_determination_result=result.genotyping_determination_result,
        cycle_threshold_result=result.cycle_threshold_result,
        normalized_reporter_result=result.normalized_reporter_result,
        baseline_corrected_reporter_result=result.baseline_corrected_reporter_result,
        data_cubes=[
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
        ],
    )


def _create_measurement(
    well_item: WellItem,
    header: Header,
    multicomponent_data: MulticomponentData | None,
    melt_curve_raw_data: MeltCurveRawData | None,
    amplification_data: AmplificationData,
    result: Result,
) -> Measurement:
    # TODO: temp workaround for cal doc result
    well_item._result = result

    cycle_count = DataCubeComponent(FieldComponentDatatype.integer, "cycle count", "#")
    data_cubes = []
    if multicomponent_data:
        if well_item.reporter_dye_setting is not None:
            data_cubes.append(
                DataCube(
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
                    measures=[
                        multicomponent_data.get_column(well_item.reporter_dye_setting)
                    ],
                ),
            )
        if header.passive_reference_dye_setting is not None:
            data_cubes.append(
                DataCube(
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
                    measures=[
                        multicomponent_data.get_column(
                            header.passive_reference_dye_setting
                        )
                    ],
                ),
            )

    if melt_curve_raw_data:
        data_cubes.append(
            DataCube(
                label="melting curve",
                structure_dimensions=[
                    DataCubeComponent(
                        FieldComponentDatatype.double, "temperature", "degrees C"
                    )
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
            ),
        )

    return Measurement(
        identifier=well_item.uuid,
        timestamp=header.measurement_time,
        target_identifier=well_item.target_dna_description,
        sample_identifier=well_item.sample_identifier,
        sample_role_type=well_item.sample_role_type,
        well_location_identifier=well_item.well_location_identifier,
        well_plate_identifier=header.barcode,
        total_cycle_number_setting=amplification_data.total_cycle_number_setting,
        pcr_detection_chemistry=header.pcr_detection_chemistry,
        reporter_dye_setting=well_item.reporter_dye_setting,
        quencher_dye_setting=well_item.quencher_dye_setting,
        passive_reference_dye_setting=header.passive_reference_dye_setting,
        processed_data=_create_processed_data(amplification_data, result),
        data_cubes=data_cubes,
    )


def _create_metadata(header: Header, file_name: str) -> Metadata:
    return Metadata(
        device_identifier=header.device_identifier,
        device_type="qPCR",
        device_serial_number=header.device_serial_number,
        model_number=header.model_number,
        software_name="Thermo QuantStudio",
        software_version="1.0",
        data_system_instance_identifier="localhost",
        file_name=file_name,
        unc_path="",  # unknown
        measurement_method_identifier=header.measurement_method_identifier,
        experiment_type=header.experiment_type,
        container_type=ContainerType.qPCR_reaction_block,
    )


def _create_calculated_data(
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


def _create_data(
    file_name: str,
    header: Header,
    wells: list[Well],
    amp_data: dict[int, dict[str, AmplificationData]],
    multi_data: dict[int, MulticomponentData],
    results_data: dict[int, dict[str, Result]],
    results_metadata: ResultMetadata,
    melt_data: dict[int, MeltCurveRawData],
    calculated_documents: Iterable[CalculatedDocument],
) -> Data:
    measurement_groups = [
        MeasurementGroup(
            analyst=header.analyst,
            experimental_data_identifier=header.experimental_data_identifier,
            plate_well_count=try_int_or_nan(header.plate_well_count),
            measurements=[
                _create_measurement(
                    well_item,
                    header,
                    multi_data.get(well.identifier),
                    melt_data.get(well.identifier),
                    amp_data[well_item.identifier][well_item.target_dna_description],
                    results_data[well_item.identifier][
                        well_item.target_dna_description.replace(" ", "")
                    ],
                )
                for well_item in well.items
            ],
        )
        for well in wells
    ]

    return Data(
        metadata=_create_metadata(header, file_name),
        measurement_groups=measurement_groups,
        calculated_data=_create_calculated_data(calculated_documents, results_metadata),
    )


def create_data(reader: LinesReader, file_name: str) -> Data:
    # Data sections must be read in order from the file.
    header = Header.create(reader)
    wells = Well.create(reader, header.experiment_type)
    # Skip raw data section
    RawData.create(reader)
    amp_data = AmplificationData.create(reader)
    multi_data = MulticomponentData.create(reader)
    results_data, results_metadata = Result.create(reader, header.experiment_type)
    melt_data = MeltCurveRawData.create(reader)

    calculated_data_documents = iter_calculated_data_documents(
        [well_item for well in wells for well_item in well.items],
        header.experiment_type,
        results_metadata.reference_sample_description,
        results_metadata.reference_dna_description,
    )

    return _create_data(
        file_name,
        header,
        wells,
        amp_data,
        multi_data,
        results_data,
        results_metadata,
        melt_data,
        calculated_data_documents,
    )
