from __future__ import annotations

import datetime
from itertools import chain
from pathlib import Path

from dateutil import parser

from allotropy.allotrope.models.shared.definitions.definitions import (
    FieldComponentDatatype,
)
from allotropy.allotrope.models.shared.definitions.units import UNITLESS
from allotropy.allotrope.schema_mappers.adm.plate_reader.rec._2025._03.plate_reader import (
    ErrorDocument,
    Measurement,
    MeasurementGroup,
    MeasurementType,
    Metadata,
)
from allotropy.allotrope.schema_mappers.data_cube import DataCube, DataCubeComponent
from allotropy.exceptions import AllotropeConversionError
from allotropy.parsers.constants import (
    DEFAULT_EPOCH_TIMESTAMP,
    NEGATIVE_ZERO,
    NOT_APPLICABLE,
)
from allotropy.parsers.moldev_softmax_pro.constants import DEVICE_TYPE
from allotropy.parsers.moldev_softmax_pro.softmax_pro_structure import (
    DataElement,
    GroupBlock,
    GroupSampleData,
    PlateBlock,
    SpectrumRawPlateData,
    StructureData,
)
from allotropy.parsers.utils.calculated_data_documents.definition import (
    CalculatedDocument,
    DataSource,
    Referenceable,
)
from allotropy.parsers.utils.uuids import random_uuid_str


def create_metadata(file_path: str) -> Metadata:
    return Metadata(
        asm_file_identifier=NOT_APPLICABLE,
        device_identifier=NOT_APPLICABLE,
        model_number=NOT_APPLICABLE,
        data_system_instance_id=NOT_APPLICABLE,
        software_name="SoftMax Pro",
        file_name=Path(file_path).name,
        unc_path=file_path,
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
        measures=[
            [
                value if value is not None else NEGATIVE_ZERO
                for value in data_element.kinetic_measures
            ]
        ],
    )


def _get_spectrum_data_cube(
    plate_block: PlateBlock, data_elements: list[DataElement]
) -> DataCube | None:
    wavelengths = [data_element.wavelength for data_element in data_elements]
    values = [data_element.value for data_element in data_elements]
    if all(value is None for value in values):
        # Ignore the wells completely from the ASM if all values are None
        return None

    return DataCube(
        label=f"{plate_block.header.concept}-spectrum",
        structure_dimensions=[
            DataCubeComponent(
                type_=FieldComponentDatatype.double, concept="wavelength", unit="nm"
            )
        ],
        structure_measures=[
            DataCubeComponent(
                type_=FieldComponentDatatype.double,
                concept=plate_block.header.concept,
                unit=plate_block.header.unit,
            )
        ],
        dimensions=[wavelengths],
        measures=[[value if value is not None else NEGATIVE_ZERO for value in values]],
    )


def _create_spectrum_measurement(
    plate_block: PlateBlock, data_elements: list[DataElement]
) -> Measurement | None:
    measurement_type = plate_block.measurement_type
    first_data_element = data_elements[0]
    spectrum_data_cube = _get_spectrum_data_cube(plate_block, data_elements)
    if not spectrum_data_cube:
        return None

    # Collect error documents and update error_feature to include wavelength with unit
    error_documents = []
    for data_element in data_elements:
        for error_doc in data_element.error_document:
            if error_doc.error_feature == plate_block.header.read_mode:
                updated_error_doc = ErrorDocument(
                    error=error_doc.error, error_feature=f"{data_element.wavelength}nm"
                )
                error_documents.append(updated_error_doc)
            else:
                # Keep original error_feature for non-spectrum data cube errors
                error_documents.append(error_doc)

    return Measurement(
        type_=measurement_type,
        identifier=first_data_element.uuid,
        spectrum_data_cube=spectrum_data_cube,
        compartment_temperature=first_data_element.temperature or None,
        location_identifier=first_data_element.position,
        well_plate_identifier=plate_block.header.name,
        sample_identifier=first_data_element.sample_identifier,
        sample_custom_info={"group_identifier": first_data_element.group_id},
        device_type=DEVICE_TYPE,
        detection_type=plate_block.header.read_mode,
        scan_position_setting=plate_block.header.scan_position,
        excitation_wavelength_setting=(
            plate_block.header.excitation_wavelengths[0]
            if plate_block.header.excitation_wavelengths
            else None
        ),
        wavelength_filter_cutoff_setting=(
            plate_block.header.cutoff_filters[0]
            if plate_block.header.cutoff_filters
            else None
        ),
        number_of_averages=plate_block.header.reads_per_well,
        detector_gain_setting=plate_block.header.pmt_gain,
        total_measurement_time_setting=plate_block.header.read_time,
        read_interval_setting=plate_block.header.read_interval,
        number_of_scans_setting=plate_block.header.kinetic_points,
        error_document=error_documents,
        measurement_custom_info=first_data_element.custom_info,
    )


def _create_measurements(plate_block: PlateBlock, position: str) -> list[Measurement]:

    measurement_type = plate_block.measurement_type
    data_elements = list(plate_block.iter_data_elements(position))

    # Handle spectrum measurements - create single measurement with spectrum_data_cube
    if measurement_type in (
        MeasurementType.ULTRAVIOLET_ABSORBANCE_CUBE_SPECTRUM,
        MeasurementType.EMISSION_FLUORESCENCE_CUBE_SPECTRUM,
        MeasurementType.EXCITATION_FLUORESCENCE_CUBE_SPECTRUM,
        MeasurementType.EMISSION_LUMINESCENCE_CUBE_SPECTRUM,
        MeasurementType.EXCITATION_LUMINESCENCE_CUBE_SPECTRUM,
    ):
        measurement = _create_spectrum_measurement(plate_block, data_elements)
        if not measurement:
            return []
        return [measurement]

    return [
        Measurement(
            type_=measurement_type,
            identifier=data_element.uuid,
            absorbance=(
                (
                    data_element.value
                    if data_element.value is not None
                    else NEGATIVE_ZERO
                )
                if measurement_type == MeasurementType.ULTRAVIOLET_ABSORBANCE
                else None
            ),
            fluorescence=(
                (
                    data_element.value
                    if data_element.value is not None
                    else NEGATIVE_ZERO
                )
                if measurement_type == MeasurementType.FLUORESCENCE
                else None
            ),
            luminescence=(
                (
                    data_element.value
                    if data_element.value is not None
                    else NEGATIVE_ZERO
                )
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
            sample_custom_info={"group_identifier": data_element.group_id},
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
            # Error documents
            error_document=data_element.error_document,
            # custom information
            measurement_custom_info=data_element.custom_info,
        )
        for idx, data_element in enumerate(data_elements)
    ]


def _create_measurement_group(
    plate_block: PlateBlock, position: str, date_last_saved: str | None
) -> MeasurementGroup | None:

    if not (measurements := _create_measurements(plate_block, position)):
        return None

    maximum_wavelength_signal = None
    if isinstance(plate_block.block_data.raw_data, SpectrumRawPlateData):
        maximum_wavelength_signal = (
            plate_block.block_data.raw_data.maximum_wavelength_signal[position]
        )

    measurement_time = DEFAULT_EPOCH_TIMESTAMP
    if date_last_saved:
        delta = datetime.timedelta(seconds=plate_block.header.read_time or 0)
        measurement_time = (parser.parse(date_last_saved) + delta).isoformat()

    return MeasurementGroup(
        measurements=measurements,
        plate_well_count=plate_block.header.num_wells,
        measurement_time=measurement_time,
        maximum_wavelength_signal=maximum_wavelength_signal,
    )


def create_measurement_groups(data: StructureData) -> list[MeasurementGroup]:
    measurement_groups = [
        measurement_group
        for plate_block in data.block_list.plate_blocks.values()
        for position in plate_block.iter_wells()
        if (
            measurement_group := _create_measurement_group(
                plate_block, position, data.date_last_saved
            )
        )
    ]
    if not measurement_groups:
        msg = "Invalid data - the file contains invalid or missing measurement data. Unable to construct ASM."
        raise AllotropeConversionError(msg)

    return measurement_groups


def create_calculated_data(data: StructureData) -> list[CalculatedDocument]:
    return _get_reduced_calc_docs(data) + _get_group_calc_docs(data)


def _get_calc_docs_data_sources(
    plate_block: PlateBlock, position: str
) -> list[DataSource]:
    return [
        DataSource(
            reference=Referenceable(data_source.uuid),
            feature=plate_block.header.read_mode,
        )
        for data_source in plate_block.iter_data_elements(position)
    ]


def _build_calc_doc(
    name: str,
    value: float,
    data_sources: list[DataSource],
    description: str | None = None,
) -> CalculatedDocument:
    return CalculatedDocument(
        uuid=random_uuid_str(),
        name=name,
        value=value,
        unit=UNITLESS,
        data_sources=data_sources,
        description=description,
    )


def _get_reduced_calc_docs(data: StructureData) -> list[CalculatedDocument]:
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


def _get_group_simple_calc_docs(
    data: StructureData,
    group_block: GroupBlock,
    group_sample_data: GroupSampleData,
) -> list[CalculatedDocument]:
    calculated_documents = []
    for group_data_element in group_sample_data.data_elements:
        if group_data_element.plate is None:
            # if the group data element does not have a plate assigned, there is no way at
            # the moment to get the data sources for the calculated data element.
            continue
        data_sources = list(
            chain.from_iterable(
                _get_calc_docs_data_sources(
                    data.block_list.plate_blocks[group_data_element.plate],
                    position,
                )
                for position in group_data_element.positions
            )
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


def _get_group_calc_docs(data: StructureData) -> list[CalculatedDocument]:
    calculated_documents = []
    for group_block in data.block_list.group_blocks:
        for group_sample_data in group_block.group_data.sample_data:
            calculated_documents += _get_group_simple_calc_docs(
                data, group_block, group_sample_data
            )
        calculated_documents += _get_group_summaries_calc_docs(data, group_block)
    return calculated_documents


def _get_group_summaries_calc_docs(
    data: StructureData, group_block: GroupBlock
) -> list[CalculatedDocument]:
    if not group_block.group_summaries_data:
        return []
    # The data sources for the summary elements are all the wells present in the group
    plates_and_positions = {
        # use a dictionary instead of a set to keep the order of the calculated data documents
        (plate, position): 1
        for group_sample_data in group_block.group_data.sample_data
        for group_data_element in group_sample_data.data_elements
        for position in group_data_element.positions
        if (plate := group_data_element.plate) is not None
    }
    data_sources = list(
        chain.from_iterable(
            _get_calc_docs_data_sources(data.block_list.plate_blocks[plate], position)
            for plate, position in plates_and_positions
        )
    )
    calculated_documents = []
    for summary_element in group_block.group_summaries_data:
        calculated_documents.append(
            _build_calc_doc(
                name=summary_element.name,
                value=summary_element.value,
                data_sources=data_sources,
                description=summary_element.description,
            )
        )
    return calculated_documents
