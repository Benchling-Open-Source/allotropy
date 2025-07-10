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
from allotropy.parsers.utils.uuids import random_uuid_str
from allotropy.parsers.utils.values import (
    num_to_chars,
    try_float,
    try_float_or_none,
    try_int,
)
from allotropy.parsers.utils.xml import (
    get_attrib_from_xml,
    get_children_with_tag,
    get_element_from_xml,
    get_val_from_xml,
    get_val_from_xml_or_none,
)


@dataclass(frozen=True)
class AnalyteMetadata:
    name: str
    region: int
    error_msg: str | None

    @property
    def error(self) -> Error | None:
        if not self.error_msg:
            return None
        return Error(error=self.error_msg, feature=self.name)

    @staticmethod
    def create(analyte_xml: Et.Element) -> AnalyteMetadata:
        error_code = get_attrib_from_xml(analyte_xml, "Reading", "Code")
        return AnalyteMetadata(
            name=get_val_from_xml(analyte_xml, "AnalyteName"),
            region=try_int(analyte_xml.attrib["RegionNumber"], "analyte_region"),
            error_msg=get_key_or_error(
                "error code", error_code, constants.ERROR_MAPPING
            )
            if error_code != "0"
            else None,
        )


@dataclass
class SampleMetadata:
    sample_type: SampleRoleType
    sample_identifier: str
    description: str | None
    sample_dilution: float | None
    errors: list[Error]
    analyte_region_dict: dict[str, str]

    @staticmethod
    def create(
        sample_metadata: Et.Element,
        member_well: Et.Element,
    ) -> SampleMetadata:
        analyte_metadata = [
            AnalyteMetadata.create(analyte_xml)
            for analyte_xml in get_element_from_xml(member_well, "MWAnalytes")
        ]

        return SampleMetadata(
            sample_type=get_key_or_error(
                "sample role type",
                sample_metadata.tag,
                constants.SAMPLE_ROLE_TYPE_MAPPING,
            ),
            sample_identifier=get_val_from_xml(sample_metadata, "Label"),
            description=get_val_from_xml_or_none(sample_metadata, "Description"),
            errors=[analyte.error for analyte in analyte_metadata if analyte.error],
            sample_dilution=try_float_or_none(
                get_val_from_xml_or_none(sample_metadata, "Dilution")
            ),
            analyte_region_dict={
                str(analyte.region): analyte.name for analyte in analyte_metadata
            },
        )

    @staticmethod
    def create_samples(samples_xml: Et.Element) -> dict[str, SampleMetadata]:
        return {
            get_well_name(member_well.attrib): SampleMetadata.create(
                sample_metadata, member_well
            )
            for sample_types in samples_xml
            for sample_metadata in sample_types
            for member_well_group in get_children_with_tag(
                sample_metadata, "MemberWells"
            )
            for member_well in member_well_group
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

    @staticmethod
    def create(well_xml: Et.Element) -> Well:
        return Well(
            name=get_well_name(well_xml.attrib),
            sample_volume_setting=try_float(
                get_val_from_xml(well_xml, "RunSettings", "SampleVolume"),
                "sample_volume",
            ),
            detector_gain_setting=get_val_from_xml(
                well_xml, "RunConditions", "RP1Gain"
            ),
            minimum_assay_bead_count_setting=try_int(
                get_attrib_from_xml(
                    well_xml, "RunSettings", "BeadCount", "StopReadingCriteria"
                ),
                "minimum_assay_bead_count_settings",
            ),
            acquisition_time=get_val_from_xml(well_xml, "AcquisitionTime"),
            well_total_events=try_int(
                get_val_from_xml(well_xml, "TotalEvents"), "well_total_events"
            ),
            analyst=get_val_from_xml(well_xml, "User"),
            xml=well_xml,
        )


def create_analyte(
    bead_region_xml: Et.Element,
    analyte_region_dict: dict[str, str],
) -> Analyte:
    # Look up analyte name from sample
    assay_bead_identifier = bead_region_xml.attrib["RegionNumber"]

    # Create statistics dimensions from available statistics in the XML
    statistic_dimensions = []
    for statistic_name, statistic_config in constants.STATISTIC_SECTIONS_CONF.items():
        statistic_value = get_val_from_xml(bead_region_xml, statistic_name)
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
            get_val_from_xml(bead_region_xml, "RegionCount"), "assay_bead_count"
        ),
        statistics=[
            StatisticsDocument(
                statistical_feature="fluorescence",
                statistic_dimensions=statistic_dimensions,
            )
        ],
    )


def create_analytes(
    well_xml: Et.Element,
    analyte_region_dict: dict[str, str],
    regions_of_interest: list[str],
) -> list[Analyte]:
    return [
        create_analyte(bead, analyte_region_dict)
        for child in get_children_with_tag(well_xml, "BeadRegions")
        for bead in child
        if bead.attrib["RegionNumber"] in regions_of_interest
    ]


@dataclass
class SystemMetadata:
    serial_number: str
    controller_version: str
    analytical_method: str
    plate_id: str
    regions_of_interest: list[str] = field(default_factory=list)

    @staticmethod
    def create(xml_well: Et.Element) -> SystemMetadata:
        return SystemMetadata(
            serial_number=get_val_from_xml(xml_well, "MachineInfo", "SerialNumber"),
            controller_version=get_val_from_xml(
                xml_well, "MachineInfo", "MicroControllerVersion"
            ),
            analytical_method=get_val_from_xml(xml_well, "RunProtocolDocumentLocation"),
            plate_id=get_val_from_xml(xml_well, "PlateID"),
            regions_of_interest=[
                str(region.attrib["RegionNumber"])
                for region in get_element_from_xml(
                    xml_well, "RunSettings", "RegionsOfInterest"
                )
            ],
        )


def get_well_name(well_attrib: dict[str, str]) -> str:
    row_name = num_to_chars(try_int(well_attrib["RowNo"], "row_number") - 1)
    col_name = str(well_attrib["ColNo"])
    return f"{row_name}{col_name}"


def create_metadata(
    root_xml: Et.Element, system_metadata: SystemMetadata, file_path: str
) -> Metadata:
    path = Path(file_path)
    return Metadata(
        file_name=path.name,
        unc_path=file_path,
        software_name=constants.SOFTWARE_NAME,
        software_version=root_xml.attrib["BioPlexManagerVersion"],
        equipment_serial_number=system_metadata.serial_number,
        firmware_version=system_metadata.controller_version,
        product_manufacturer=constants.PRODUCT_MANUFACTURER,
        device_type=constants.DEVICE_TYPE,
        asm_file_identifier=path.with_suffix(".json").name,
        data_system_instance_identifier=NOT_APPLICABLE,
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
                    well.xml,
                    sample.analyte_region_dict,
                    system_metadata.regions_of_interest,
                ),
                errors=sample.errors,
            )
        ],
    )
