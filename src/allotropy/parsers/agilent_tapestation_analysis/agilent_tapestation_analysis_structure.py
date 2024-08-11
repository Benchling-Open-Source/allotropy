from __future__ import annotations

from xml.etree import ElementTree as ET  # noqa: N817

from allotropy.allotrope.models.shared.definitions.units import UNITLESS
from allotropy.allotrope.schema_mappers.adm.electrophoresis.benchling._2024._06.electrophoresis import (
    CalculatedDataItem,
    Data,
    DataSource,
    Error,
    Measurement,
    MeasurementGroup,
    Metadata,
    ProcessedData,
    ProcessedDataFeature,
)
from allotropy.exceptions import (
    AllotropeConversionError,
    AllotropeParsingError,
    get_key_or_error,
    msg_for_error_on_unrecognized_value,
)
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.agilent_tapestation_analysis.constants import (
    BRAND_NAME,
    DETECTION_TYPE,
    DEVICE_TYPE,
    NON_CALCULATED_DATA_TAGS_PEAK,
    NON_CALCULATED_DATA_TAGS_REGION,
    NON_CALCULATED_DATA_TAGS_SAMPLE,
    PRODUCT_MANUFACTURER,
    SOFTWARE_NAME,
    UNIT_CLASS_LOOKUP,
)
from allotropy.parsers.utils.uuids import random_uuid_str
from allotropy.parsers.utils.values import (
    try_float_or_nan,
    try_float_or_none,
)
from allotropy.parsers.utils.xml import (
    get_element_from_xml,
    get_val_from_xml,
    get_val_from_xml_or_none,
)


def _get_calculated_data(
    element: ET.Element, excluded_tags: list[str], source_id: str, feature: str
) -> list[CalculatedDataItem]:
    calculated_data = []
    for node in element:
        if (name := node.tag) in excluded_tags:
            continue
        if (value := try_float_or_none(node.text)) is None:
            continue
        calculated_data.append(
            CalculatedDataItem(
                identifier=random_uuid_str(),
                name=name,
                value=value,
                unit=UNITLESS,
                data_sources=[
                    DataSource(
                        identifier=source_id,
                        feature=feature
                    )
                ],
            )
        )

    return calculated_data


def create_metadata(root_element: ET.Element, file_name: str) -> Metadata:
    file_information = get_element_from_xml(root_element, "FileInformation")
    environment = get_element_from_xml(
        root_element, "ScreenTapes/ScreenTape/Environment"
    )
    return Metadata(
        file_name=file_name,
        analyst=get_val_from_xml_or_none(environment, "Experimenter"),
        analytical_method_identifier=get_val_from_xml_or_none(
            file_information, "Assay"
        ),
        data_system_instance_identifier=get_val_from_xml_or_none(
            environment, "Computer"
        ),
        device_identifier=get_val_from_xml_or_none(environment, "InstrumentType"),
        equipment_serial_number=get_val_from_xml_or_none(
            environment, "InstrumentSerialNumber"
        ),
        experimental_data_identifier=get_val_from_xml_or_none(
            file_information, "FileName"
        ),
        # If any, only one of those should appear, so we arbitrarily take the first one
        method_version=get_val_from_xml_or_none(file_information, "RINeVersion")
        or get_val_from_xml_or_none(file_information, "DINVersion"),
        software_version=get_val_from_xml_or_none(environment, "AnalysisVersion"),
        software_name=SOFTWARE_NAME,
        brand_name=BRAND_NAME,
        product_manufacturer=PRODUCT_MANUFACTURER,
        device_type=DEVICE_TYPE,
        detection_type=DETECTION_TYPE,
    )


def _get_description(xml_element: ET.Element) -> str | None:
    comment = get_val_from_xml_or_none(xml_element, "Comment")
    observations = get_val_from_xml_or_none(xml_element, "Observations")
    return f"{comment or ''} {observations or ''}".strip() or None


def _create_peak(peak_element: ET.Element, unit: str) -> ProcessedDataFeature:
    return ProcessedDataFeature(
        identifier=random_uuid_str(),
        height=try_float_or_nan(get_val_from_xml_or_none(peak_element, "Height")),
        start=try_float_or_nan(get_val_from_xml_or_none(peak_element, "FromMW")),
        start_unit=unit,
        end=try_float_or_nan(get_val_from_xml_or_none(peak_element, "ToMW")),
        end_unit=unit,
        position=try_float_or_nan(get_val_from_xml_or_none(peak_element, "Size")),
        position_unit=unit,
        area=try_float_or_nan(get_val_from_xml_or_none(peak_element, "Area")),
        relative_area=try_float_or_nan(get_val_from_xml_or_none(peak_element, "PercentOfTotal")),
        relative_corrected_area=try_float_or_nan(get_val_from_xml_or_none(
            peak_element, "PercentIntegratedArea"
        )),
        name=get_val_from_xml_or_none(peak_element, "Number"),
        comment=_get_description(peak_element),
    )


def _create_region(region_element: ET.Element, region_name: str, unit: str) -> ProcessedDataFeature:
    return ProcessedDataFeature(
        identifier=random_uuid_str(),
        start=try_float_or_nan(get_val_from_xml_or_none(region_element, "From")),
        start_unit=unit,
        end=try_float_or_nan(get_val_from_xml_or_none(region_element, "To")),
        end_unit=unit,
        area=try_float_or_nan(get_val_from_xml_or_none(region_element, "Area")),
        relative_area=try_float_or_nan(get_val_from_xml_or_none(
            region_element, "PercentOfTotal"
        )),
        name=region_name,
        comment=get_val_from_xml_or_none(region_element, "Comment"),
    )


def _create_measurement(sample_element: ET.Element, screen_tape: ET.Element, unit: str, calculated_data: list[CalculatedDataItem]) -> Measurement:
    measurement_id = random_uuid_str()
    well_number = get_val_from_xml(sample_element, "WellNumber")
    screen_tape_id = get_val_from_xml(sample_element, "ScreenTapeID")
    error = get_val_from_xml_or_none(sample_element, "Alert")
    if error is not None:
        error = error.strip()

    calculated_data.extend(_get_calculated_data(
        element=sample_element,
        excluded_tags=NON_CALCULATED_DATA_TAGS_SAMPLE,
        source_id=measurement_id,
        feature="sample",
    ))
    peaks: list[ProcessedDataFeature] = []
    for peak_element in get_element_from_xml(sample_element, "Peaks").iter("Peak"):
        peaks.append(_create_peak(peak_element, unit))
        calculated_data.extend(_get_calculated_data(
            element=peak_element,
            excluded_tags=NON_CALCULATED_DATA_TAGS_PEAK,
            source_id=peaks[-1].identifier,
            feature="peak",
        ))

    region_elements = sorted(
        sample_element.find("Regions").iter("Region"),
        key=lambda region: get_val_from_xml(region, "From"),
    )
    regions: list[ProcessedDataFeature] = []
    for idx, region_element in enumerate(region_elements, start=1):
        regions.append(_create_region(region_element, str(idx), unit))
        calculated_data.extend(_get_calculated_data(
            element=region_element,
            excluded_tags=NON_CALCULATED_DATA_TAGS_REGION,
            source_id=regions[-1].identifier,
            feature="data region",
        ))

    return Measurement(
        identifier=measurement_id,
        measurement_time=get_val_from_xml(screen_tape, "TapeRunDate"),
        compartment_temperature=try_float_or_none(
            get_val_from_xml_or_none(screen_tape, "ElectrophoresisTemp")
        ),
        location_identifier=well_number,
        sample_identifier=f"{screen_tape_id}_{well_number}",
        description=_get_description(sample_element),
        processed_data=ProcessedData(
            peaks=peaks,
            data_regions=regions,
        ),
        errors=[Error(error=error)] if error else None,
    )


def _get_unit_class(
    root_element: ET.Element,
) -> str:
    peak_unit = get_element_from_xml(
        root_element, "Assay/Units/MolecularWeightUnit"
    ).text
    try:
        peak_unit = peak_unit or ""
        return UNIT_CLASS_LOOKUP[peak_unit]
    except KeyError as e:
        msg = msg_for_error_on_unrecognized_value(
            "Molecular Weight Unit", peak_unit, UNIT_CLASS_LOOKUP.keys()
        )
        raise AllotropeConversionError(msg) from e


def _create_measurements(root_element: ET.Element, calculated_data: list[CalculatedDataItem]) -> list[Measurement]:
    screen_tapes_element = get_element_from_xml(root_element, "ScreenTapes")
    screen_tapes = {
        get_val_from_xml(screen_tape, "ScreenTapeID"): screen_tape
        for screen_tape in screen_tapes_element.iter("ScreenTape")
    }

    measurements = []
    for sample_element in get_element_from_xml(root_element, "Samples").iter("Sample"):
        screen_tape_id = get_val_from_xml(sample_element, "ScreenTapeID")
        measurements.append(
            _create_measurement(
                sample_element,
                get_key_or_error("ScreenTape ID", screen_tape_id, screen_tapes),
                _get_unit_class(root_element),
                calculated_data,
            )
        )

    return measurements


def create_data(named_file_contents: NamedFileContents) -> Data:
    try:
        root_element = ET.parse(named_file_contents.contents).getroot()  # noqa: S314
    except ET.ParseError as e:
        msg = f"There was an error when trying to read the xml file: {e}"
        raise AllotropeParsingError(msg) from e

    # TODO(nstender): passing in calculated data by reference to collect calculated data globally, but it
    # seems like this data should just be reported inside the measurement, which would remove the need for this.
    calculated_data = []
    return Data(
        metadata=create_metadata(root_element, named_file_contents.original_file_name),
        measurement_groups=[
            MeasurementGroup(measurements=[measurement])
            for measurement in _create_measurements(root_element, calculated_data)
        ],
        # NOTE: in current implementation, calculated data is reported at global level for some reason.
        # TODO(nstender): should we move this inside of measurements?
        calculated_data=calculated_data
    )
