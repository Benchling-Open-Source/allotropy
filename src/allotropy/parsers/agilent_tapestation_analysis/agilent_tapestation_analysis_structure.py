from __future__ import annotations

from pathlib import Path
from xml.etree import ElementTree as ET  # noqa: N817

from allotropy.allotrope.models.shared.definitions.units import UNITLESS
from allotropy.allotrope.schema_mappers.adm.electrophoresis.benchling._2024._09.electrophoresis import (
    CalculatedDataItem,
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
    msg_for_error_on_unrecognized_value,
)
from allotropy.parsers.agilent_tapestation_analysis.constants import (
    BRAND_NAME,
    DETECTION_TYPE,
    DEVICE_TYPE,
    NON_CALCULATED_DATA_TAGS_PEAK,
    NON_CALCULATED_DATA_TAGS_REGION,
    NON_CALCULATED_DATA_TAGS_SAMPLE,
    PRODUCT_MANUFACTURER,
    SCREEN_TAPE_MISMATCH_ERROR,
    SOFTWARE_NAME,
    UNIT_CLASS_LOOKUP,
)
from allotropy.parsers.utils.uuids import random_uuid_str
from allotropy.parsers.utils.values import try_float_or_none
from allotropy.parsers.utils.xml import (
    get_element_from_xml,
    get_float_from_xml_or_none,
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
                data_sources=[DataSource(identifier=source_id, feature=feature)],
            )
        )

    return calculated_data


def create_metadata(root_element: ET.Element, file_path: str) -> Metadata:
    file_information = get_element_from_xml(root_element, "FileInformation")
    environment = get_element_from_xml(
        root_element, "ScreenTapes/ScreenTape/Environment"
    )
    path = Path(file_path)
    return Metadata(
        file_name=path.name,
        file_identifier=path.with_suffix(".json").name,
        unc_path=file_path,
        analyst=get_val_from_xml(environment, "Experimenter"),
        analytical_method_identifier=get_val_from_xml_or_none(
            file_information, "Assay"
        ),
        data_system_instance_identifier=get_val_from_xml(environment, "Computer"),
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
        height=get_float_from_xml_or_none(peak_element, "Height"),
        start=get_float_from_xml_or_none(peak_element, "FromMW"),
        start_unit=unit,
        end=get_float_from_xml_or_none(peak_element, "ToMW"),
        end_unit=unit,
        position=get_float_from_xml_or_none(peak_element, "Size"),
        position_unit=unit,
        area=get_float_from_xml_or_none(peak_element, "Area"),
        relative_area=get_float_from_xml_or_none(peak_element, "PercentOfTotal"),
        relative_corrected_area=get_float_from_xml_or_none(
            peak_element, "PercentIntegratedArea"
        ),
        name=get_val_from_xml_or_none(peak_element, "Number"),
        comment=_get_description(peak_element),
    )


def _create_region(
    region_element: ET.Element, region_name: str, unit: str
) -> ProcessedDataFeature:
    return ProcessedDataFeature(
        identifier=random_uuid_str(),
        start=get_float_from_xml_or_none(region_element, "From"),
        start_unit=unit,
        end=get_float_from_xml_or_none(region_element, "To"),
        end_unit=unit,
        area=get_float_from_xml_or_none(region_element, "Area"),
        relative_area=get_float_from_xml_or_none(region_element, "PercentOfTotal"),
        name=region_name,
        comment=get_val_from_xml_or_none(region_element, "Comment"),
    )


def _create_measurement(
    sample_element: ET.Element, screen_tape: ET.Element, unit: str
) -> tuple[Measurement, list[CalculatedDataItem]]:
    measurement_id = random_uuid_str()
    calculated_data: list[CalculatedDataItem] = []
    calculated_data.extend(
        _get_calculated_data(
            element=sample_element,
            excluded_tags=NON_CALCULATED_DATA_TAGS_SAMPLE,
            source_id=measurement_id,
            feature="sample",
        )
    )
    if rna_element := sample_element.find("RNA"):
        calculated_data.extend(
            _get_calculated_data(
                element=rna_element,
                excluded_tags=[],
                source_id=measurement_id,
                feature="sample",
            )
        )
    peaks: list[ProcessedDataFeature] = []
    for peak_element in get_element_from_xml(sample_element, "Peaks").iter("Peak"):
        peaks.append(_create_peak(peak_element, unit))
        calculated_data.extend(
            _get_calculated_data(
                element=peak_element,
                excluded_tags=NON_CALCULATED_DATA_TAGS_PEAK,
                source_id=peaks[-1].identifier,
                feature="peak",
            )
        )

    regions_element = sample_element.find("Regions")
    region_elements = (
        regions_element.iter("Region") if regions_element is not None else []
    )
    regions: list[ProcessedDataFeature] = []
    for idx, region_element in enumerate(
        sorted(
            region_elements,
            key=lambda region: get_val_from_xml(region, "From"),
        ),
        start=1,
    ):
        regions.append(_create_region(region_element, str(idx), unit))
        calculated_data.extend(
            _get_calculated_data(
                element=region_element,
                excluded_tags=NON_CALCULATED_DATA_TAGS_REGION,
                source_id=regions[-1].identifier,
                feature="data region",
            )
        )

    well_number = get_val_from_xml(sample_element, "WellNumber")
    error = (get_val_from_xml_or_none(sample_element, "Alert") or "").strip() or None
    measurement = Measurement(
        identifier=measurement_id,
        measurement_time=get_val_from_xml(screen_tape, "TapeRunDate"),
        compartment_temperature=get_float_from_xml_or_none(
            screen_tape, "ElectrophoresisTemp"
        ),
        location_identifier=well_number,
        sample_identifier=f"{get_val_from_xml(sample_element, 'ScreenTapeID')}_{well_number}",
        description=_get_description(sample_element),
        processed_data=ProcessedData(
            peaks=peaks,
            data_regions=regions,
        ),
        errors=[Error(error=error)] if error else None,
    )
    return measurement, calculated_data


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


def create_measurement_groups(
    root_element: ET.Element,
) -> tuple[list[MeasurementGroup], list[CalculatedDataItem]]:
    screen_tapes_element = get_element_from_xml(root_element, "ScreenTapes")
    screen_tapes = {
        get_val_from_xml(screen_tape, "ScreenTapeID"): screen_tape
        for screen_tape in screen_tapes_element.iter("ScreenTape")
    }

    measurement_groups: list[MeasurementGroup] = []
    calculated_data: list[CalculatedDataItem] = []
    for sample_element in get_element_from_xml(root_element, "Samples").iter("Sample"):
        screen_tape_id = get_val_from_xml(sample_element, "ScreenTapeID")
        try:
            screen_tape = screen_tapes[screen_tape_id]
        except KeyError as e:
            msg = SCREEN_TAPE_MISMATCH_ERROR.format(
                screen_tape_id, list(screen_tapes.keys())
            )
            raise AllotropeConversionError(msg) from e
        measurement, measurement_calculated_data = _create_measurement(
            sample_element, screen_tape, _get_unit_class(root_element)
        )
        measurement_groups.append(MeasurementGroup(measurements=[measurement]))
        calculated_data.extend(measurement_calculated_data)

    return measurement_groups, calculated_data
