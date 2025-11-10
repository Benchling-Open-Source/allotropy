from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import xml.etree.ElementTree as Et

from allotropy.allotrope.models.shared.components.plate_reader import SampleRoleType
from allotropy.allotrope.schema_mappers.adm.multi_analyte_profiling.benchling._2024._09.multi_analyte_profiling import (
    Analyte,
    Error,
    Measurement,
    MeasurementGroup,
    Metadata,
    StatisticDimension,
    StatisticsDocument,
)
from allotropy.exceptions import get_key_or_error
from allotropy.parsers.biorad_bioplex_manager import constants
from allotropy.parsers.constants import NOT_APPLICABLE
from allotropy.parsers.utils.strict_xml_element import StrictXmlElement
from allotropy.parsers.utils.uuids import random_uuid_str
from allotropy.parsers.utils.values import (
    num_to_chars,
    try_float,
    try_float_or_none,
    try_int,
)


@dataclass(frozen=True)
class AnalyteMetadata:
    name: str
    region: int
    error_msg: str | None
    custom_info: dict[str, str | None]

    @property
    def error(self) -> Error | None:
        if not self.error_msg:
            return None
        return Error(error=self.error_msg, feature=self.name)

    @staticmethod
    def create(analyte_xml: StrictXmlElement) -> AnalyteMetadata:

        reading_element = analyte_xml.find("Reading")
        error_code = reading_element.get_attr("Code")
        return AnalyteMetadata(
            name=analyte_xml.find("AnalyteName").get_text("AnalyteName"),
            region=try_int(analyte_xml.get_attr("RegionNumber"), "analyte_region"),
            error_msg=(
                get_key_or_error("error code", error_code, constants.ERROR_MAPPING)
                if error_code != "0"
                else None
            ),
            custom_info={
                **analyte_xml.get_unread(),
                **reading_element.get_unread(),
            },
        )


@dataclass
class SampleMetadata:
    sample_type: SampleRoleType
    sample_identifier: str
    description: str | None
    sample_dilution: float | None
    errors: list[Error]
    analyte_region_dict: dict[str, str]
    custom_info: dict[str, str | None]

    @staticmethod
    def create(
        sample_metadata: StrictXmlElement,
        member_well: StrictXmlElement,
    ) -> SampleMetadata:

        mw_analytes_element = member_well.find("MWAnalytes")
        analyte_metadata = [
            AnalyteMetadata.create(analyte_xml)
            for analyte_xml in mw_analytes_element.findall("MWAnalyte")
        ]

        # Get optional elements
        description_element = sample_metadata.find_or_none("Description")
        dilution_element = sample_metadata.find_or_none("Dilution")

        return SampleMetadata(
            sample_type=get_key_or_error(
                "sample role type",
                sample_metadata.element.tag,
                constants.SAMPLE_ROLE_TYPE_MAPPING,
            ),
            sample_identifier=sample_metadata.find("Label").get_text("Label"),
            description=(
                description_element.get_text_or_none() if description_element else None
            ),
            errors=[analyte.error for analyte in analyte_metadata if analyte.error],
            sample_dilution=try_float_or_none(
                dilution_element.get_text_or_none() if dilution_element else None
            ),
            analyte_region_dict={
                str(analyte.region): analyte.name for analyte in analyte_metadata
            },
            custom_info={
                **sample_metadata.get_unread(),
                **member_well.get_unread(skip={"WellNumber", "WellNo"}),
            },
        )

    @staticmethod
    def create_samples(samples_xml: StrictXmlElement) -> dict[str, SampleMetadata]:

        return {
            get_well_name(member_well.attrib): SampleMetadata.create(
                StrictXmlElement(sample_metadata), StrictXmlElement(member_well)
            )
            for sample_types in samples_xml.element
            for sample_metadata in sample_types
            for member_well_group in sample_metadata.findall("MemberWells")
            for member_well in member_well_group.findall("MemberWell")
        }


@dataclass
class Well:
    name: str
    sample_volume_setting: float
    detector_gain_setting: str
    minimum_assay_bead_count_setting: int
    well_total_events: int
    acquisition_time: str
    analyst: str
    xml: Et.Element
    custom_info: dict[str, str | None]

    @staticmethod
    def create(well_xml: StrictXmlElement) -> Well:
        sample_volume_element = well_xml.recursive_find(["RunSettings", "SampleVolume"])
        stop_reading_criteria_element = well_xml.recursive_find(
            ["RunSettings", "StopReadingCriteria"]
        )

        return Well(
            name=get_well_name(well_xml.element.attrib),
            sample_volume_setting=try_float(
                sample_volume_element.get_text("SampleVolume"),
                "sample_volume",
            ),
            detector_gain_setting=well_xml.recursive_find(
                ["RunConditions", "RP1Gain"]
            ).get_text("RP1Gain"),
            minimum_assay_bead_count_setting=try_int(
                stop_reading_criteria_element.get_attr("BeadCount"),
                "minimum_assay_bead_count_settings",
            ),
            acquisition_time=well_xml.find("AcquisitionTime").get_text(
                "AcquisitionTime"
            ),
            well_total_events=try_int(
                well_xml.find("TotalEvents").get_text("TotalEvents"),
                "well_total_events",
            ),
            analyst=well_xml.find("User").get_text("User"),
            xml=well_xml.element,
            custom_info={
                **well_xml.get_unread(skip={"WellNo"}),
                **sample_volume_element.get_unread(),
                **stop_reading_criteria_element.get_unread(),
            },
        )


def create_analyte(
    bead_region_xml: StrictXmlElement,
    analyte_region_dict: dict[str, str],
) -> Analyte:
    # Look up analyte name from sample
    assay_bead_identifier = bead_region_xml.get_attr("RegionNumber")

    # Create statistics dimensions from available statistics in the XML
    statistic_dimensions = []
    for statistic_name, statistic_config in constants.STATISTIC_SECTIONS_CONF.items():
        statistic_value = bead_region_xml.find(statistic_name).get_text(statistic_name)
        statistic_dimensions.append(
            StatisticDimension(
                value=try_float(statistic_value, f"{statistic_name} statistic"),
                unit=statistic_config.unit,
                statistic_datum_role=statistic_config.role,
            )
        )

    return Analyte(
        identifier=random_uuid_str(),
        name=analyte_region_dict[assay_bead_identifier],
        assay_bead_identifier=assay_bead_identifier,
        assay_bead_count=try_int(
            bead_region_xml.find("RegionCount").get_text("RegionCount"),
            "assay_bead_count",
        ),
        statistics=[
            StatisticsDocument(
                statistical_feature="fluorescence",
                statistic_dimensions=statistic_dimensions,
            )
        ],
        custom_info=bead_region_xml.get_unread(),
    )


def create_analytes(
    well_xml: StrictXmlElement,
    analyte_region_dict: dict[str, str],
    regions_of_interest: list[str],
) -> list[Analyte]:
    well_xml.get_unread()  # already being captured by the Well class
    return [
        create_analyte(bead, analyte_region_dict)
        for child in well_xml.findall("BeadRegions")
        for bead in child.findall("BeadRegion")
        if bead.get_attr("RegionNumber") in regions_of_interest
    ]


@dataclass
class SystemMetadata:
    serial_number: str
    controller_version: str
    analytical_method: str
    plate_id: str
    custom_info: dict[str, str | None]
    regions_of_interest: list[str] = field(default_factory=list)

    @staticmethod
    def create(xml_well: StrictXmlElement) -> SystemMetadata:

        return SystemMetadata(
            serial_number=xml_well.find("MachineInfo")
            .find("SerialNumber")
            .get_text("SerialNumber"),
            controller_version=xml_well.find("MachineInfo")
            .find("MicroControllerVersion")
            .get_text("MicroControllerVersion"),
            analytical_method=xml_well.find("RunProtocolDocumentLocation").get_text(
                "RunProtocolDocumentLocation"
            ),
            plate_id=xml_well.find("PlateID").get_text("PlateID"),
            regions_of_interest=[
                str(region.get_attr("RegionNumber"))
                for region in xml_well.find("RunSettings")
                .find("RegionsOfInterest")
                .findall("Region")
            ],
            custom_info=xml_well.get_unread(),
        )


def get_well_name(well_attrib: dict[str, str]) -> str:
    row_name = num_to_chars(try_int(well_attrib["RowNo"], "row_number") - 1)
    col_name = str(well_attrib["ColNo"])
    return f"{row_name}{col_name}"


def create_metadata(
    root_xml: StrictXmlElement, system_metadata: SystemMetadata, file_path: str
) -> Metadata:
    path = Path(file_path)
    return Metadata(
        file_name=path.name,
        unc_path=file_path,
        software_name=constants.SOFTWARE_NAME,
        software_version=root_xml.get_attr("BioPlexManagerVersion"),
        equipment_serial_number=system_metadata.serial_number,
        firmware_version=system_metadata.controller_version,
        product_manufacturer=constants.PRODUCT_MANUFACTURER,
        device_type=constants.DEVICE_TYPE,
        asm_file_identifier=path.with_suffix(".json").name,
        data_system_instance_identifier=NOT_APPLICABLE,
        custom_info=root_xml.get_unread(),
    )


def create_measurement_group(
    well: Well,
    sample: SampleMetadata,
    system_metadata: SystemMetadata,
    experimental_data_id: str | None,
    experiment_type: str | None,
    plate_well_count: int,
) -> MeasurementGroup:
    return MeasurementGroup(
        experiment_type=experiment_type,
        plate_well_count=plate_well_count,
        analytical_method_identifier=system_metadata.analytical_method,
        experimental_data_identifier=experimental_data_id,
        analyst=well.analyst,
        container_type=constants.CONTAINER_TYPE,
        measurements=[
            Measurement(
                identifier=random_uuid_str(),
                measurement_time=well.acquisition_time,
                assay_bead_count=well.well_total_events,
                description=sample.description,
                sample_identifier=sample.sample_identifier,
                location_identifier=well.name,
                sample_role_type=sample.sample_type,
                well_plate_identifier=system_metadata.plate_id,
                sample_volume_setting=well.sample_volume_setting,
                dilution_factor_setting=sample.sample_dilution,
                detector_gain_setting=well.detector_gain_setting,
                minimum_assay_bead_count_setting=well.minimum_assay_bead_count_setting,
                analytes=create_analytes(
                    StrictXmlElement(well.xml),
                    sample.analyte_region_dict,
                    system_metadata.regions_of_interest,
                ),
                errors=sample.errors,
                measurement_custom_info=sample.custom_info,
            )
        ],
        custom_info=well.custom_info,
    )
