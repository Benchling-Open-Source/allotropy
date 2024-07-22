from allotropy.allotrope.models.adm.pcr.benchling._2023._09.qpcr import ContainerType
from allotropy.allotrope.models.shared.definitions.custom import TQuantityValueNumber
from allotropy.allotrope.models.shared.definitions.definitions import (
    FieldComponentDatatype,
)
from allotropy.allotrope.models.shared.definitions.units import UNITLESS
from allotropy.allotrope.schema_mappers.adm.pcr.BENCHLING._2023._09.qpcr import (
    Data as MapperData,
    DataCube,
    DataCubeComponent,
    Measurement,
    MeasurementGroup,
    Metadata,
)
from allotropy.parsers.appbio_quantstudio.appbio_quantstudio_calculated_documents import (
    iter_calculated_data_documents,
)
from allotropy.parsers.appbio_quantstudio.appbio_quantstudio_structure import (
    AmplificationData,
    Data,
    Header,
    MeltCurveRawData,
    MulticomponentData,
    RawData,
    Result,
    Well,
    WellItem,
    WellList,
)
from allotropy.parsers.constants import NOT_APPLICABLE
from allotropy.parsers.lines_reader import LinesReader
from allotropy.parsers.utils.values import try_int_or_nan


def _create_measurement(well_item: WellItem, header: Header, well: Well):
    data_cubes = [
        DataCube(
            label="normalized reporter",
            structure_dimensions=[DataCubeComponent(FieldComponentDatatype.integer, "cycle count", "#")],
            structure_measures=[DataCubeComponent(FieldComponentDatatype.integer, "normalized report result", UNITLESS)],
            dimensions=[well_item.amplification_data.cycle],
            measures=[well_item.amplification_data.rn],
        ),
        DataCube(
            label="baseline corrected reporter",
            structure_dimensions=[DataCubeComponent(FieldComponentDatatype.integer, "cycle count", "#")],
            structure_measures=[DataCubeComponent(FieldComponentDatatype.double, "baseline corrected reporter result", UNITLESS)],
            dimensions=[well_item.amplification_data.cycle],
            measures=[well_item.amplification_data.delta_rn],
        )
    ]
    if well.multicomponent_data:
        if well_item.reporter_dye_setting is not None:
            data_cubes.append(
                DataCube(
                    label="reporter dye",
                    structure_dimensions=[DataCubeComponent(FieldComponentDatatype.integer, "cycle count", "#")],
                    structure_measures=[DataCubeComponent(FieldComponentDatatype.double, "reporter dye fluorescence", "RFU")],
                    dimensions=[well_item.amplification_data.cycle],
                    measures=[well.multicomponent_data.get_column(well_item.reporter_dye_setting)],
                ),
            )
        if header.passive_reference_dye_setting is not None:
            data_cubes.append(
                DataCube(
                    label="passive reference dye",
                    structure_dimensions=[DataCubeComponent(FieldComponentDatatype.integer, "cycle count", "#")],
                    structure_measures=[DataCubeComponent(FieldComponentDatatype.double, "passive reference dye fluorescence", "RFU")],
                    dimensions=[well_item.amplification_data.cycle],
                    measures=[well.multicomponent_data.get_column(header.passive_reference_dye_setting)],
                ),
            )

        if well.melt_curve_raw_data:
            data_cubes.append(
                DataCube(
                    label="melting curve",
                    structure_dimensions=[DataCubeComponent(FieldComponentDatatype.double, "temperature", "degrees C")],
                    structure_measures=[
                        DataCubeComponent(FieldComponentDatatype.double, "reporter dye fluorescence", "RFU")
                    ],
                    dimensions=[well_item.amplification_data.cycle],
                    measures=[well.multicomponent_data.get_column(header.passive_reference_dye_setting)],
                ),
            )

    Measurement(
        identifier=well_item.identifier,
        timestamp=header.measurement_time,
        target_identifier=well_item.target_dna_description,
        sample_identifier=well_item.sample_identifier,
        sample_role_type=well_item.sample_role_type,
        well_location_identifier=well_item.well_location_identifier,
        well_plate_identifier=header.barcode,
        total_cycle_number_setting=well_item.amplification_data.total_cycle_number_setting,
        pcr_detection_chemistry=header.pcr_detection_chemistry,
        reporter_dye_setting=well_item.reporter_dye_setting,
        quencher_dye_setting=well_item.quencher_dye_setting,
        passive_reference_dye_setting=header.passive_reference_dye_setting,
        automatic_cycle_threshold_enabled_setting=well_item.result.automatic_baseline_determination_enabled_setting,
        cycle_threshold_value_setting=well_item.result.cycle_threshold_value_setting,
        automatic_baseline_determination_enabled_setting=well_item.result.automatic_baseline_determination_enabled_setting,
        genotyping_determination_result=well_item.result.genotyping_determination_method_setting,
        cycle_threshold_result=well_item.result.cycle_threshold_result,
        normalized_reporter_result=well_item.result.normalized_reporter_result,
        baseline_corrected_reporter_result=well_item.result.baseline_corrected_reporter_result,
        data_cubes=[


            DataCube(
                label="baseline corrected reporter",
                structure_dimensions=[DataCubeComponent(FieldComponentDatatype.integer, "cycle count", "#")],
                structure_measures=[DataCubeComponent(FieldComponentDatatype.double, "baseline corrected reporter result", UNITLESS)],
                dimensions=[well_item.amplification_data.cycle],
                measures=[well_item.amplification_data.delta_rn],
            ),
            DataCube(
                label="baseline corrected reporter",
                structure_dimensions=[DataCubeComponent(FieldComponentDatatype.integer, "cycle count", "#")],
                structure_measures=[DataCubeComponent(FieldComponentDatatype.double, "baseline corrected reporter result", UNITLESS)],
                dimensions=[well_item.amplification_data.cycle],
                measures=[well_item.amplification_data.delta_rn],
            ),
        ]
    )

def create_data(reader: LinesReader, file_name: str) -> Data:
    header = Header.create(reader)
    wells = WellList.create(reader, header.experiment_type)
    # Skip raw data section
    RawData.create(reader)

    amp_data = AmplificationData.get_data(reader)
    multi_data = MulticomponentData.get_data(reader)
    results_data, results_metadata = Result.get_data(reader)
    melt_data = MeltCurveRawData.get_data(reader)
    for well in wells:
        if multi_data is not None:
            well.multicomponent_data = MulticomponentData.create(
                multi_data,
                well,
            )

        if melt_data is not None:
            well.melt_curve_raw_data = MeltCurveRawData.create(
                melt_data,
                well,
            )

        for well_item in well.items.values():
            well_item.amplification_data = AmplificationData.create(
                amp_data,
                well_item,
            )

            well_item.result = Result.create(
                results_data,
                well_item,
                header.experiment_type,
            )

    endogenous_control = results_metadata.get(str, "Endogenous Control", NOT_APPLICABLE)
    reference_sample = results_metadata.get(str, "Reference Sample", NOT_APPLICABLE)

    metadata = Metadata(
        device_identifier=header.device_identifier,
        device_type="qPRC",
        device_serial_number=header.device_serial_number,
        model_number=header.model_number,
        software_name="Thermo QuantStudio",
        software_version="1.0",
        data_system_instance_identifier="localhost",
        file_name=file_name,
        unc_path="",  # unknown
        measurement_method_identifier=header.measurement_method_identifier
    )

    measurement_groups = [
        MeasurementGroup(
            analyst=header.analyst,
            experimental_data_identifier=header.experimental_data_identifier,
            experiment_type=header.experiment_type,
            container_type=ContainerType.qPCR_reaction_block,
            plate_well_count=TQuantityValueNumber(
                value=try_int_or_nan(header.plate_well_count)
            ),
            measurements=[
                _create_measurement(well_item, header, well)
                for well_item in well.items.values()
            ]
        )
        for well in wells
    ]

    calculated_data_documents = iter_calculated_data_documents(
        wells,
        header.experiment_type,
        reference_sample,
        endogenous_control,
    )

    return MapperData(
        metadata=metadata,
        measurement_groups=measurement_groups,
        calculated_data_documents=calculated_data_documents
    )
