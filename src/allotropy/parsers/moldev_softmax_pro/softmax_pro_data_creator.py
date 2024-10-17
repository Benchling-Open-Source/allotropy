from __future__ import annotations

from itertools import chain

from allotropy.allotrope.models.shared.definitions.definitions import (
    FieldComponentDatatype,
)
from allotropy.allotrope.models.shared.definitions.units import UNITLESS
from allotropy.allotrope.schema_mappers.adm.plate_reader.rec._2024._06.plate_reader import (
    CalculatedDataItem,
    DataCube,
    DataCubeComponent,
    DataSource,
    Measurement,
    MeasurementGroup,
    MeasurementType,
    Metadata,
)
from allotropy.exceptions import AllotropeConversionError
from allotropy.parsers.constants import NOT_APPLICABLE
from allotropy.parsers.moldev_softmax_pro.constants import DEVICE_TYPE, EPOCH
from allotropy.parsers.moldev_softmax_pro.softmax_pro_structure import (
    DataElement,
    GroupBlock,
    GroupSampleData,
    PlateBlock,
    StructureData,
)
from allotropy.parsers.utils.uuids import random_uuid_str


def create_metadata(file_name: str) -> Metadata:
    return Metadata(
        asm_file_identifier=NOT_APPLICABLE,
        device_identifier=NOT_APPLICABLE,
        model_number=NOT_APPLICABLE,
        data_system_instance_id=NOT_APPLICABLE,
        unc_path=NOT_APPLICABLE,
        software_name="SoftMax Pro",
        file_name=file_name,
    )


def _get_data_cube(
    plate_block: PlateBlock, data_element: DataElement
) -> DataCube | None:

    if plate_block.measurement_type not in (
        MeasurementType.FLUORESCENCE_CUBE_DETECTOR,
        MeasurementType.LUMINESCENCE_CUBE_DETECTOR,
        MeasurementType.ULTRAVIOLET_ABSORBANCE_CUBE_DETECTOR,
    ):
        return None

    return DataCube(
        label=plate_block.measurement_type.value,
        structure_dimensions=[
            DataCubeComponent(
                type_=FieldComponentDatatype.double, concept="elapsed time", unit="s"
            )
        ],
        structure_measures=[
            DataCubeComponent(
                type_=FieldComponentDatatype.double,
                concept=plate_block.header.concept,
                unit=plate_block.header.unit,
            )
        ],
        dimensions=[data_element.elapsed_time],
        measures=[data_element.kinetic_measures],
    )


def _create_measurements(plate_block: PlateBlock, position: str) -> list[Measurement]:

    measurement_type = plate_block.measurement_type

    return [
        Measurement(
            type_=measurement_type,
            identifier=data_element.uuid,
            absorbance=(
                data_element.value
                if measurement_type == MeasurementType.ULTRAVIOLET_ABSORBANCE
                else None
            ),
            fluorescence=(
                data_element.value
                if measurement_type == MeasurementType.FLUORESCENCE
                else None
            ),
            luminescence=(
                data_element.value
                if measurement_type == MeasurementType.LUMINESCENCE
                else None
            ),
            profile_data_cube=_get_data_cube(plate_block, data_element),
            # A temperature of 0 indicates the temperature was not actualy read.
            compartment_temperature=data_element.temperature or None,
            # Sample document
            location_identifier=data_element.position,
            well_plate_identifier=plate_block.header.name,
            sample_identifier=data_element.sample_identifier,
            # Device Control document
            device_type=DEVICE_TYPE,
            detection_type=plate_block.header.read_mode,
            scan_position_setting=plate_block.header.scan_position,
            detector_wavelength_setting=data_element.wavelength,
            excitation_wavelength_setting=(
                plate_block.header.excitation_wavelengths[idx]
                if plate_block.header.excitation_wavelengths
                else None
            ),
            wavelength_filter_cutoff_setting=(
                plate_block.header.cutoff_filters[idx]
                if plate_block.header.cutoff_filters
                else None
            ),
            number_of_averages=plate_block.header.reads_per_well,
            detector_gain_setting=plate_block.header.pmt_gain,
            total_measurement_time_setting=plate_block.header.read_time,
            read_interval_setting=plate_block.header.read_interval,
            number_of_scans_setting=plate_block.header.kinetic_points,
        )
        for idx, data_element in enumerate(plate_block.iter_data_elements(position))
    ]


def _create_measurement_group(
    plate_block: PlateBlock, position: str
) -> MeasurementGroup | None:

    if not (measurements := _create_measurements(plate_block, position)):
        return None

    return MeasurementGroup(
        measurements=measurements,
        plate_well_count=plate_block.header.num_wells,
        measurement_time=EPOCH,
    )


def create_measurement_groups(data: StructureData) -> list[MeasurementGroup]:
    measurement_groups = [
        measurement_group
        for plate_block in data.block_list.plate_blocks.values()
        for position in plate_block.iter_wells()
        if (measurement_group := _create_measurement_group(plate_block, position))
    ]
    if not measurement_groups:
        msg = "Invalid data - the file contains invalid or missing measurement data. Unable to construct ASM."
        raise AllotropeConversionError(msg)

    return measurement_groups


def create_calculated_data(data: StructureData) -> list[CalculatedDataItem]:
    return _get_reduced_calc_docs(data) + _get_group_calc_docs(data)


def _get_calc_docs_data_sources(
    plate_block: PlateBlock, position: str
) -> list[DataSource]:
    return [
        DataSource(
            identifier=data_source.uuid,
            feature=plate_block.header.read_mode,
        )
        for data_source in plate_block.iter_data_elements(position)
    ]


def _build_calc_doc(
    name: str,
    value: float,
    data_sources: list[DataSource],
    description: str | None = None,
) -> CalculatedDataItem:
    return CalculatedDataItem(
        identifier=random_uuid_str(),
        name=name,
        value=value,
        unit=UNITLESS,
        data_sources=data_sources,
        description=description,
    )


def _get_reduced_calc_docs(data: StructureData) -> list[CalculatedDataItem]:
    return [
        _build_calc_doc(
            name="Reduced",
            value=reduced_data_element.value,
            data_sources=_get_calc_docs_data_sources(
                plate_block,
                reduced_data_element.position,
            ),
        )
        for plate_block in data.block_list.plate_blocks.values()
        for reduced_data_element in plate_block.iter_reduced_data()
    ]


def _get_group_agg_calc_docs(
    data: StructureData,
    group_block: GroupBlock,
    group_sample_data: GroupSampleData,
) -> list[CalculatedDataItem]:
    return [
        _build_calc_doc(
            name=aggregated_entry.name,
            value=aggregated_entry.value,
            data_sources=list(
                chain.from_iterable(
                    _get_calc_docs_data_sources(
                        data.block_list.plate_blocks[group_data_element.plate],
                        group_data_element.position,
                    )
                    for group_data_element in group_sample_data.data_elements
                )
            ),
            description=group_block.group_columns.data.get(aggregated_entry.name),
        )
        for aggregated_entry in group_sample_data.aggregated_entries
    ]


def _get_group_simple_calc_docs(
    data: StructureData,
    group_block: GroupBlock,
    group_sample_data: GroupSampleData,
) -> list[CalculatedDataItem]:
    calculated_documents = []
    for group_data_element in group_sample_data.data_elements:
        data_sources = _get_calc_docs_data_sources(
            data.block_list.plate_blocks[group_data_element.plate],
            group_data_element.position,
        )
        for entry in group_data_element.entries:
            calculated_documents.append(
                _build_calc_doc(
                    name=entry.name,
                    value=entry.value,
                    data_sources=data_sources,
                    description=group_block.group_columns.data.get(entry.name),
                )
            )
    return calculated_documents


def _get_group_calc_docs(data: StructureData) -> list[CalculatedDataItem]:
    calculated_documents = []
    for group_block in data.block_list.group_blocks:
        for group_sample_data in group_block.group_data.sample_data:
            calculated_documents += _get_group_agg_calc_docs(
                data, group_block, group_sample_data
            )
            calculated_documents += _get_group_simple_calc_docs(
                data, group_block, group_sample_data
            )
    return calculated_documents
