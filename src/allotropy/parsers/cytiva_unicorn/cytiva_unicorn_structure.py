from io import BytesIO
import re
import struct

from allotropy.allotrope.models.shared.definitions.definitions import (
    FieldComponentDatatype,
)
from allotropy.allotrope.schema_mappers.adm.liquid_chromatography.benchling._2023._09.liquid_chromatography import (
    DataCube,
    DataCubeComponent,
    Measurement,
    MeasurementGroup,
    Metadata,
)
from allotropy.exceptions import AllotropeConversionError
from allotropy.parsers.cytiva_unicorn.cytiva_unicorn_reader import (
    StrictElement,
    UnicornFileHandler,
)
from allotropy.parsers.utils.uuids import random_uuid_str


def create_metadata(handler: UnicornFileHandler) -> Metadata:
    system_data = handler.get_system_data()
    results = handler.get_results()
    instrument_config_data = handler.get_instrument_config_data()

    return Metadata(
        asset_management_id=system_data.find_attr(
            ["System", "InstrumentConfiguration"], "Description"
        ),
        product_manufacturer="Cytiva Life Sciences",
        device_id=results.find_text(["SystemName"]),
        firmware_version=instrument_config_data.find_text(["FirmwareVersion"]),
        analyst=handler.get_audit_trail_entry_user(),
    )


def filter_curve(curve_elements: list[StrictElement], pattern: str) -> StrictElement:
    for element in curve_elements:
        if re.search(pattern, element.find_text(["Name"])):
            return element
    msg = f"Unable to find curve element with pattern {pattern}"
    raise AllotropeConversionError(msg)


def parse_data_cube_bynary(stream: BytesIO) -> tuple[float, ...]:
    data = stream.read()
    # assuming little endian float (4 bytes)
    return tuple(
        struct.unpack("<f", data[i : i + 4])[0] for i in range(47, len(data) - 48, 4)
    )


def create_data_cube(
    handler: UnicornFileHandler,
    curve_element: StrictElement,
    data_cuve_component: DataCubeComponent,
) -> DataCube:
    data_name = curve_element.find_text(
        ["CurvePoints", "CurvePoint", "BinaryCurvePointsFileName"]
    )
    data_handler = handler.get_content_from_pattern(data_name)

    return DataCube(
        label=curve_element.find_text(["Name"]),
        structure_dimensions=[
            DataCubeComponent(
                type_=FieldComponentDatatype.float,
                concept="retention time",
                unit="min",
            ),
        ],
        structure_measures=[data_cuve_component],
        dimensions=[
            parse_data_cube_bynary(
                data_handler.get_file_from_pattern("CoordinateData.Volumes$")
            )
        ],
        measures=[
            parse_data_cube_bynary(
                data_handler.get_file_from_pattern("CoordinateData.Amplitudes$")
            )
        ],
    )


def create_measurement_groups(handler: UnicornFileHandler) -> list[MeasurementGroup]:
    chrom_1 = handler.get_chrom_1()
    elements = chrom_1.find("Curves").findall("Curve")

    uv_component = DataCubeComponent(
        type_=FieldComponentDatatype.float,
        concept="absorbance",
        unit="mAU",
    )

    cond_component = DataCubeComponent(
        type_=FieldComponentDatatype.float,
        concept="electric conductivity",
        unit="S/m",
    )

    ph_component = DataCubeComponent(
        type_=FieldComponentDatatype.float,
        concept="pH",
        unit="pH",
    )

    uv1_curve = filter_curve(elements, r"^UV 1_\d+$")
    uv2_curve = filter_curve(elements, r"^UV 2_\d+$")
    uv3_curve = filter_curve(elements, r"^UV 3_\d+$")
    cond_curve = filter_curve(elements, r"^Cond$")
    ph_curve = filter_curve(elements, r"^pH$")

    return [
        MeasurementGroup(
            measurements=[
                Measurement(
                    measurement_identifier=random_uuid_str(),
                    data_cube=create_data_cube(handler, uv1_curve, uv_component),
                ),
                Measurement(
                    measurement_identifier=random_uuid_str(),
                    data_cube=create_data_cube(handler, uv2_curve, uv_component),
                ),
                Measurement(
                    measurement_identifier=random_uuid_str(),
                    data_cube=create_data_cube(handler, uv3_curve, uv_component),
                ),
                Measurement(
                    measurement_identifier=random_uuid_str(),
                    data_cube=create_data_cube(handler, cond_curve, cond_component),
                ),
                Measurement(
                    measurement_identifier=random_uuid_str(),
                    data_cube=create_data_cube(handler, ph_curve, ph_component),
                ),
            ]
        )
    ]
