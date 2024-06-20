from __future__ import annotations

from dataclasses import dataclass
from xml.etree import ElementTree as ET  # noqa: N817

from allotropy.allotrope.models.shared.definitions.definitions import JsonFloat
from allotropy.exceptions import AllotropeConversionError
from allotropy.parsers.agilent_tapestation_analysis.constants import (
    NO_SCREEN_TAPE_ID_MATCH,
)
from allotropy.parsers.utils.uuids import random_uuid_str
from allotropy.parsers.utils.values import (
    get_element_from_xml,
    get_val_from_xml,
    get_val_from_xml_or_none,
    try_float_or_nan,
    try_float_or_none,
)
from allotropy.types import IOType


@dataclass(frozen=True)
class MetaData:
    analyst: str | None
    analytical_method_identifier: str | None
    data_system_instance_identifier: str | None
    device_identifier: str | None
    equipment_serial_number: str | None
    experimental_data_identifier: str | None
    method_version: str | None
    software_version: str | None

    @staticmethod
    def create(root_element: ET.Element) -> MetaData:
        file_information = get_element_from_xml(root_element, "FileInformation")
        environment = get_element_from_xml(
            root_element, "ScreenTapes/ScreenTape/Environment"
        )

        return MetaData(
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
        )


@dataclass(frozen=True)
class Peak:
    peak_identifier: str
    peak_height: JsonFloat
    peak_start: JsonFloat
    peak_end: JsonFloat
    peak_position: JsonFloat
    peak_area: JsonFloat
    relative_peak_area: JsonFloat
    relative_corrected_peak_area: JsonFloat
    peak_name: str | None
    comment: str | None

    @staticmethod
    def create(peak_element: ET.Element) -> Peak:
        peak_height = get_val_from_xml_or_none(peak_element, "Height")
        peak_start = get_val_from_xml_or_none(peak_element, "FromMW")
        peak_end = get_val_from_xml_or_none(peak_element, "ToMW")
        peak_position = get_val_from_xml_or_none(peak_element, "Size")
        peak_area = get_val_from_xml_or_none(peak_element, "Area")
        relative_peak_area = get_val_from_xml_or_none(peak_element, "PercentOfTotal")
        relative_corrected_peak_area = get_val_from_xml_or_none(
            peak_element, "PercentIntegratedArea"
        )
        comment = get_val_from_xml_or_none(peak_element, "Comment")
        observations = get_val_from_xml_or_none(peak_element, "Observations")
        return Peak(
            peak_identifier=random_uuid_str(),
            peak_name=get_val_from_xml_or_none(peak_element, "Number"),
            peak_height=try_float_or_nan(peak_height),
            peak_start=try_float_or_nan(peak_start),
            peak_end=try_float_or_nan(peak_end),
            peak_position=try_float_or_nan(peak_position),
            peak_area=try_float_or_nan(peak_area),
            relative_peak_area=try_float_or_nan(relative_peak_area),
            relative_corrected_peak_area=try_float_or_nan(relative_corrected_peak_area),
            comment=f"{comment or ''} {observations or ''}".strip() or None,
        )


@dataclass(frozen=True)
class Sample:
    measurement_id: str
    measurement_time: str
    compartment_temperature: float | None
    location_identifier: str
    sample_identifier: str
    description: str | None
    peak_list: list[Peak]

    @staticmethod
    def create(sample_element: ET.Element, screen_tape: ET.Element) -> Sample:
        well_number = get_val_from_xml(sample_element, "WellNumber")
        screen_tape_id = get_val_from_xml(sample_element, "ScreenTapeID")
        comment = get_val_from_xml_or_none(sample_element, "Comment")
        observations = get_val_from_xml_or_none(sample_element, "Observations")
        description = f"{comment or ''} {observations or ''}".strip()
        peaks = get_element_from_xml(sample_element, "Peaks")

        return Sample(
            measurement_id=random_uuid_str(),
            measurement_time=get_val_from_xml(screen_tape, "TapeRunDate"),
            compartment_temperature=try_float_or_none(
                get_val_from_xml_or_none(screen_tape, "ElectrophoresisTemp")
            ),
            location_identifier=well_number,
            sample_identifier=f"{screen_tape_id}_{well_number}",
            description=description or None,
            peak_list=[Peak.create(peak) for peak in peaks.iter("Peak")],
        )


@dataclass(frozen=True)
class SamplesList:
    samples: list[Sample]

    @staticmethod
    def create(root_element: ET.Element) -> SamplesList:
        screen_tapes_element = get_element_from_xml(root_element, "ScreenTapes")
        screen_tapes = {
            get_val_from_xml(screen_tape, "ScreenTapeID"): screen_tape
            for screen_tape in screen_tapes_element.iter("ScreenTape")
        }

        samples_element = get_element_from_xml(root_element, "Samples")
        samples = []
        for sample_element in samples_element.iter("Sample"):
            screen_tape_id = get_val_from_xml(sample_element, "ScreenTapeID")
            if screen_tape_id not in screen_tapes:
                msg = NO_SCREEN_TAPE_ID_MATCH.format(screen_tape_id)
                raise AllotropeConversionError(msg)
            samples.append(Sample.create(sample_element, screen_tapes[screen_tape_id]))

        return SamplesList(samples=samples)


@dataclass(frozen=True)
class Data:
    root: ET.ElementTree
    metadata: MetaData
    samples_list: SamplesList

    @staticmethod
    def create(contents: IOType) -> Data:
        root = ET.parse(contents)  # noqa: S314
        root_element = root.getroot()

        return Data(
            root=root,
            metadata=MetaData.create(root_element),
            samples_list=SamplesList.create(root_element),
        )
