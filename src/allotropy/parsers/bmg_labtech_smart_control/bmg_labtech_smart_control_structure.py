import logging
from pathlib import Path

from allotropy.allotrope.models.shared.components.plate_reader import SampleRoleType
from allotropy.allotrope.models.shared.definitions.custom import (
    TQuantityValueSecondTime,
    TQuantityValueUnitless,
)
from allotropy.allotrope.schema_mappers.adm.plate_reader.rec._2024._06.plate_reader import (
    CalculatedDataItem,
    DataSource,
    Measurement,
    MeasurementGroup,
    MeasurementType,
    Metadata,
    ScanPositionSettingPlateReader,
)
from allotropy.parsers.bmg_labtech_smart_control.bmg_labtech_smart_control_reader import (
    BmgLabtechSmartControlReader,
)
from allotropy.parsers.bmg_labtech_smart_control.constants import (
    DEVICE_TYPE,
    PRODUCT_MANUFACTURER,
    SAMPLE_ROLE_TYPE_MAPPING,
    SOFTWARE_NAME,
    TARGET_TEMPERATURE,
)
from allotropy.parsers.constants import NOT_APPLICABLE
from allotropy.parsers.utils.pandas import SeriesData
from allotropy.parsers.utils.uuids import random_uuid_str
from allotropy.parsers.utils.values import quantity_or_none, try_float


def create_metadata(file_path: str) -> Metadata:
    path = Path(file_path)
    return Metadata(
        asm_file_identifier=path.with_suffix(".json").name,
        device_identifier=NOT_APPLICABLE,
        product_manufacturer=PRODUCT_MANUFACTURER,
        model_number=NOT_APPLICABLE,
        data_system_instance_id=NOT_APPLICABLE,
        file_name=path.name,
        unc_path=file_path,
        software_name=SOFTWARE_NAME,
    )


def map_measurement_group(row: SeriesData, headers: SeriesData) -> MeasurementGroup:
    fluorescence = row[
        float,
        f"Raw Data ({headers[str, 'Excitation']}/{headers[str, 'Emission']})",
    ]
    sample_identifier = row[str, "Content"]
    filter_position_map = {
        "Bottom": ScanPositionSettingPlateReader.bottom_scan_position__plate_reader_,
        "Top": ScanPositionSettingPlateReader.top_scan_position__plate_reader_,
    }
    scan_position_setting = (
        filter_position_map.get("Bottom")
        if headers.get(str, "Top optic used") is None
        else filter_position_map.get("Top")
    )
    mass_concentration = row.get(float, "Standard Concentrations [ng/mL]")
    if mass_concentration is not None:
        # since this is ng/mL, we need to convert to pg/mL by multiplying by 1000
        mass_concentration *= 1000

    group = MeasurementGroup(
        analyst=headers.get(str, "User"),
        measurement_time=f"{headers[str, 'Date']} {headers[str, 'Time']}",
        experimental_data_identifier=headers.get(str, "ID1"),
        experiment_type=headers.get(str, "Test Name"),
        plate_well_count=try_float(
            headers[str, "Microplate name"].split()[-1], "plate well count"
        ),
        measurements=[
            Measurement(
                identifier=random_uuid_str(),
                compartment_temperature=row.get(float, TARGET_TEMPERATURE),
                fluorescence=fluorescence,
                sample_identifier=sample_identifier,
                sample_role_type=SAMPLE_ROLE_TYPE_MAPPING.get(
                    sample_identifier.split()[0]
                ),
                location_identifier=row[str, "Well"],
                well_plate_identifier=headers.get(str, "ID3"),
                mass_concentration=mass_concentration,
                device_type=DEVICE_TYPE,
                detection_type=headers[str, "Measurement type"].split()[0].lower(),
                detector_distance_setting=headers.get(float, "Focal height  [mm]"),
                number_of_averages=headers.get(float, "No. of flashes per well"),
                detector_gain_setting=headers.get(str, "Gain obtained by"),
                scan_position_setting=scan_position_setting,
                type_=MeasurementType.FLUORESCENCE,
                sample_custom_info={
                    "dilution factor setting": quantity_or_none(
                        TQuantityValueUnitless, row.get(float, "Dilutions")
                    ),
                    "container identifier": headers.get(str, "Microplate name"),
                },
                device_control_custom_info={
                    "settling time setting": quantity_or_none(
                        TQuantityValueSecondTime,
                        headers.get(float, "Settling time [s]"),
                    ),
                    "reading direction setting": headers.get(str, "Reading direction"),
                    "dichroic filter setting": headers.get(str, "Dichroic filter"),
                    "optic preset name": headers.get(str, "Presetname"),
                    "spoon type": headers.get(str, "Spoon type"),
                    "well used for focus adjustment": headers.get(
                        str, "Well used for focus adjustment"
                    ),
                    "focal height obtained by": headers.get(
                        str, "Focal height obtained by"
                    ),
                },
                detector_wavelength_setting=try_float(
                    headers[str, "Emission"].split("-")[0], "emission"
                ),
                detector_bandwidth_setting=try_float(
                    headers[str, "Emission"].split("-")[1], "emission"
                ),
                excitation_bandwidth_setting=try_float(
                    headers[str, "Excitation"].split("-")[1], "excitation"
                ),
                excitation_wavelength_setting=try_float(
                    headers[str, "Excitation"].split("-")[0], "excitation"
                ),
                measurement_custom_info=headers.get_unread(),
            )
        ],
    )
    # We read this value later when creating the calculated data items
    row.mark_read({"Blank corrected based on Raw Data (480-14/520-30)"})
    return group


def create_calculated_data_documents(
    measurement_groups: list[MeasurementGroup], reader: BmgLabtechSmartControlReader
) -> list[CalculatedDataItem] | None:
    blank_measurements = [
        group.measurements[0]
        for group in measurement_groups
        if group.measurements[0].sample_role_type == SampleRoleType.blank_role
    ]

    if not blank_measurements:
        return []

    if not reader.average_of_blank_used:
        logging.warning(
            "Microplate endpoint sheet does not contain average of blanks used value but blank measurements are present."
        )
        return []
    non_blank_measurements = [
        measurement
        for group in measurement_groups
        for measurement in group.measurements
        if measurement.sample_role_type != SampleRoleType.blank_role
    ]

    blank_average = reader.average_of_blank_used
    average_calc_document = CalculatedDataItem(
        identifier=random_uuid_str(),
        name="Average of all blanks used",
        value=blank_average,
        data_sources=[
            DataSource(
                identifier=measurement.identifier,
                feature="fluorescence",
            )
            for measurement in blank_measurements
        ],
        unit="RFU",
    )
    blank_corrected_calc_documents: list[CalculatedDataItem] = []
    for idx, measurement in enumerate(non_blank_measurements):
        corrected_value_sd = SeriesData(reader.data.iloc[idx])
        blank_corrected_calc_documents.append(
            CalculatedDataItem(
                identifier=random_uuid_str(),
                name="Blank corrected based on Raw Data (480-14/520-30)",
                value=corrected_value_sd[
                    float, "Blank corrected based on Raw Data (480-14/520-30)"
                ],
                data_sources=[
                    DataSource(
                        identifier=measurement.identifier,
                        feature="fluorescence",
                    ),
                    DataSource(
                        identifier=average_calc_document.identifier,
                        feature="Average of all blanks used",
                    ),
                ],
                unit="RFU",
            )
        )
        # We do not need the rest of the info in this series data for creating the calculated data item
        corrected_value_sd.get_unread()
    return [average_calc_document, *blank_corrected_calc_documents]
