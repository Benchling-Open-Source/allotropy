from __future__ import annotations

from dataclasses import dataclass
from xml.etree import ElementTree as ET  # noqa: N817

from allotropy.allotrope.models.shared.definitions.definitions import JsonFloat
from allotropy.exceptions import AllotropeConversionError
from allotropy.parsers.agilent_tapestation_analysis.constants import (
    NO_SCREEN_TAPE_ID_MATCH,
    NON_CALCULATED_DATA_TAGS_PEAK,
    NON_CALCULATED_DATA_TAGS_REGION,
    NON_CALCULATED_DATA_TAGS_SAMPLE,
    UNIT_CLASS_LOOKUP,
    UNIT_CLASSES,
)
from allotropy.parsers.utils.calculated_data_documents.definition import (
    CalculatedDocument,
    DataSource,
    Referenceable,
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
from allotropy.types import IOType


def _get_calculated_data(
    element: ET.Element, excluded_tags: list[str], source_id: str, feature: str
) -> list[CalculatedDocument]:
    calculated_data = []
    for node in element:
        if (name := node.tag) in excluded_tags:
            continue
        if (value := try_float_or_none(node.text)) is None:
            continue
        calculated_data.append(
            CalculatedDocument(
                uuid=random_uuid_str(),
                name=name,
                value=value,
                data_sources=[
                    DataSource(feature=feature, reference=Referenceable(uuid=source_id))
                ],
            )
        )

    return calculated_data


@dataclass(frozen=True)
class Metadata:
    unit_cls: UNIT_CLASSES
    analyst: str | None
    analytical_method_identifier: str | None
    data_system_instance_identifier: str | None
    device_identifier: str | None
    equipment_serial_number: str | None
    experimental_data_identifier: str | None
    method_version: str | None
    software_version: str | None

    @staticmethod
    def create(root_element: ET.Element) -> Metadata:
        file_information = get_element_from_xml(root_element, "FileInformation")
        environment = get_element_from_xml(
            root_element, "ScreenTapes/ScreenTape/Environment"
        )

        return Metadata(
            unit_cls=Metadata._get_unit_class(root_element),
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

    @staticmethod
    def _get_unit_class(
        root_element: ET.Element,
    ) -> UNIT_CLASSES:
        peak_unit = get_element_from_xml(
            root_element, "Assay/Units/MolecularWeightUnit"
        ).text
        try:
            peak_unit = peak_unit or ""
            return UNIT_CLASS_LOOKUP[peak_unit]
        except KeyError as e:
            msg = f"Unrecognized Molecular Weight Unit: {peak_unit}"
            raise AllotropeConversionError(msg) from e


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
    calculated_data: list[CalculatedDocument]

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
        peak_identifier = random_uuid_str()

        return Peak(
            peak_identifier=peak_identifier,
            peak_height=try_float_or_nan(peak_height),
            peak_start=try_float_or_nan(peak_start),
            peak_end=try_float_or_nan(peak_end),
            peak_position=try_float_or_nan(peak_position),
            peak_area=try_float_or_nan(peak_area),
            relative_peak_area=try_float_or_nan(relative_peak_area),
            relative_corrected_peak_area=try_float_or_nan(relative_corrected_peak_area),
            peak_name=get_val_from_xml_or_none(peak_element, "Number"),
            comment=f"{comment or ''} {observations or ''}".strip() or None,
            calculated_data=_get_calculated_data(
                element=peak_element,
                excluded_tags=NON_CALCULATED_DATA_TAGS_PEAK,
                source_id=peak_identifier,
                feature="peak",
            ),
        )


@dataclass(frozen=True)
class DataRegion:
    region_identifier: str
    region_start: JsonFloat
    region_end: JsonFloat
    region_area: JsonFloat
    relative_region_area: JsonFloat
    region_name: str | None
    comment: str | None
    calculated_data: list[CalculatedDocument]

    @staticmethod
    def create(region_element: ET.Element, region_name: str) -> DataRegion:
        region_start = get_val_from_xml_or_none(region_element, "From")
        region_end = get_val_from_xml_or_none(region_element, "To")
        region_area = get_val_from_xml_or_none(region_element, "Area")
        relative_region_area = get_val_from_xml_or_none(
            region_element, "PercentOfTotal"
        )
        region_identifier = random_uuid_str()

        return DataRegion(
            region_identifier=region_identifier,
            region_start=try_float_or_nan(region_start),
            region_end=try_float_or_nan(region_end),
            region_area=try_float_or_nan(region_area),
            relative_region_area=try_float_or_nan(relative_region_area),
            region_name=region_name,
            comment=get_val_from_xml_or_none(region_element, "Comment"),
            calculated_data=_get_calculated_data(
                element=region_element,
                excluded_tags=NON_CALCULATED_DATA_TAGS_REGION,
                source_id=region_identifier,
                feature="data region",
            ),
        )


@dataclass(frozen=True)
class Sample:
    measurement_identifier: str
    measurement_time: str
    compartment_temperature: float | None
    location_identifier: str
    sample_identifier: str
    description: str | None
    peak_list: list[Peak]
    data_regions: list[DataRegion]
    calculated_data: list[CalculatedDocument]
    error: str | None

    @staticmethod
    def create(sample_element: ET.Element, screen_tape: ET.Element) -> Sample:
        measurement_id = random_uuid_str()
        well_number = get_val_from_xml(sample_element, "WellNumber")
        screen_tape_id = get_val_from_xml(sample_element, "ScreenTapeID")
        comment = get_val_from_xml_or_none(sample_element, "Comment")
        observations = get_val_from_xml_or_none(sample_element, "Observations")
        description = f"{comment or ''} {observations or ''}".strip()

        peaks = get_element_from_xml(sample_element, "Peaks")
        regions: list[ET.Element] = []

        regions_element = sample_element.find("Regions")
        if regions_element is not None:
            regions = sorted(
                regions_element.iter("Region"),
                key=lambda region: get_val_from_xml(region, "From"),
            )
        error = get_val_from_xml_or_none(sample_element, "Alert")
        if error is not None:
            error = error.strip()

        return Sample(
            measurement_identifier=measurement_id,
            measurement_time=get_val_from_xml(screen_tape, "TapeRunDate"),
            compartment_temperature=try_float_or_none(
                get_val_from_xml_or_none(screen_tape, "ElectrophoresisTemp")
            ),
            location_identifier=well_number,
            sample_identifier=f"{screen_tape_id}_{well_number}",
            description=description or None,
            peak_list=[Peak.create(peak) for peak in peaks.iter("Peak")],
            data_regions=[
                DataRegion.create(region, str(idx))
                for idx, region in enumerate(regions, start=1)
            ],
            calculated_data=_get_calculated_data(
                element=sample_element,
                excluded_tags=NON_CALCULATED_DATA_TAGS_SAMPLE,
                source_id=measurement_id,
                feature="sample",
            ),
            error=error,
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
    metadata: Metadata
    samples_list: SamplesList

    @staticmethod
    def create(contents: IOType) -> Data:
        try:
            root_element = ET.parse(contents).getroot()  # noqa: S314
        except ET.ParseError as e:
            msg = f"There was an error when trying to read the xml file: {e}"
            raise AllotropeConversionError(message=msg) from e

        return Data(
            metadata=Metadata.create(root_element),
            samples_list=SamplesList.create(root_element),
        )
