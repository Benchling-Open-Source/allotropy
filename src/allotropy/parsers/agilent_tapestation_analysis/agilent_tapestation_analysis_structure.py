from __future__ import annotations

from dataclasses import dataclass
from xml.etree import ElementTree as ET  # noqa: N817

from allotropy.allotrope.models.shared.definitions.definitions import JsonFloat
from allotropy.allotrope.models.shared.definitions.units import UNITLESS
from allotropy.allotrope.schema_mappers.adm.electrophoresis.benchling._2024._06.electrophoresis import (
    CalculatedDataItem,
    Data as MapperData,
    DataSource,
    Error,
    Measurement,
    MeasurementGroup,
    Metadata as MapperMetadata,
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
from allotropy.types import IOType


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


@dataclass(frozen=True)
class Metadata:
    unit: str
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
            unit=Metadata._get_unit_class(root_element),
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
    calculated_data: list[CalculatedDataItem]

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
    calculated_data: list[CalculatedDataItem]

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
    calculated_data: list[CalculatedDataItem]
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
            samples.append(
                Sample.create(
                    sample_element,
                    get_key_or_error("ScreenTape ID", screen_tape_id, screen_tapes),
                )
            )

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
            raise AllotropeParsingError(msg) from e

        return Data(
            metadata=Metadata.create(root_element),
            samples_list=SamplesList.create(root_element),
        )


def create_data(named_file_contents: NamedFileContents) -> Data:
    data = Data.create(named_file_contents.contents)

    measurement_groups = [
        MeasurementGroup(
            measurements=[
                Measurement(
                    identifier=sample.measurement_identifier,
                    measurement_time=sample.measurement_time,
                    compartment_temperature=sample.compartment_temperature,
                    sample_identifier=sample.sample_identifier,
                    description=sample.description,
                    location_identifier=sample.location_identifier,
                    processed_data=ProcessedData(
                        peaks=[
                            ProcessedDataFeature(
                                identifier=peak.peak_identifier,
                                name=peak.peak_name,
                                height=peak.peak_height,
                                start=peak.peak_start,
                                start_unit=data.metadata.unit,
                                end=peak.peak_end,
                                end_unit=data.metadata.unit,
                                position=peak.peak_position,
                                position_unit=data.metadata.unit,
                                area=peak.peak_area,
                                relative_area=peak.relative_peak_area,
                                relative_corrected_area=peak.relative_corrected_peak_area,
                                comment=peak.comment,
                            )
                            for peak in sample.peak_list
                        ],
                        data_regions=[
                            ProcessedDataFeature(
                                identifier=region.region_identifier,
                                name=region.region_name,
                                start=region.region_start,
                                start_unit=data.metadata.unit,
                                end=region.region_end,
                                end_unit=data.metadata.unit,
                                area=region.region_area,
                                relative_area=region.relative_region_area,
                                comment=region.comment,
                            )
                            for region in (sample.data_regions or [])
                        ],
                    ),
                    errors=[Error(sample.error)] if sample.error else [],
                )
            ]
        )
        for sample in data.samples_list.samples
    ]

    calculated_data = []
    for sample in data.samples_list.samples:
        calculated_data.extend(sample.calculated_data)
        for peak in sample.peak_list:
            calculated_data.extend(peak.calculated_data)
        for region in sample.data_regions:
            calculated_data.extend(region.calculated_data)

    return MapperData(
        MapperMetadata(
            data_system_instance_identifier=data.metadata.data_system_instance_identifier,
            file_name=named_file_contents.original_file_name,
            software_name=SOFTWARE_NAME,
            software_version=data.metadata.software_version,
            brand_name=BRAND_NAME,
            product_manufacturer=PRODUCT_MANUFACTURER,
            device_identifier=data.metadata.device_identifier,
            equipment_serial_number=data.metadata.equipment_serial_number,
            analyst=data.metadata.analyst,
            analytical_method_identifier=data.metadata.analytical_method_identifier,
            method_version=data.metadata.method_version,
            experimental_data_identifier=data.metadata.experimental_data_identifier,
            device_type=DEVICE_TYPE,
            detection_type=DETECTION_TYPE,
        ),
        measurement_groups=measurement_groups,
        calculated_data=calculated_data
    )
