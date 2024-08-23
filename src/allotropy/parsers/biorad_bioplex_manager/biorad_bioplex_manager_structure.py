from __future__ import annotations

from dataclasses import dataclass, field
from xml.etree import ElementTree
import xml.etree.ElementTree as Et

from allotropy.allotrope.models.shared.components.plate_reader import SampleRoleType
from allotropy.allotrope.models.shared.definitions.definitions import (
    TStatisticDatumRole,
)
from allotropy.allotrope.schema_mappers.adm.multi_analyte_profiling.benchling._2024._01.multi_analyte_profiling import (
    Analyte,
    Error,
    Measurement,
    MeasurementGroup,
    Metadata,
)
from allotropy.exceptions import (
    AllotropeConversionError,
    AllotropyParserError,
    get_key_or_error,
)
from allotropy.parsers.biorad_bioplex_manager import constants
from allotropy.parsers.biorad_bioplex_manager.constants import (
    ACQ_TIME,
    ANALYTE_NAME,
    BEAD_COUNT,
    CODE,
    COLUMN_NUMBER,
    DESCRIPTION_TAG,
    DILUTION,
    DOC_LOCATION_TAG,
    ERROR_MAPPING,
    LABEL,
    MACHINE_INFO,
    MEDIAN,
    MEMBER_WELLS,
    MW_ANALYTES,
    PLATE_DIMENSIONS_TAG,
    READING,
    REGION_COUNT,
    REGION_NUMBER,
    REGIONS_OF_INTEREST,
    ROW_NAMES,
    ROW_NUMBER,
    RP1_GAIN,
    RUN_CONDITIONS,
    RUN_SETTINGS,
    SAMPLE_VOLUME,
    SAMPLES,
    SERIAL_NUMBER,
    SOFTWARE_NAME,
    STOP_READING_CRITERIA,
    TOTAL_EVENTS,
    WELLS_TAG,
)
from allotropy.parsers.utils.uuids import random_uuid_str
from allotropy.parsers.utils.values import (
    try_float,
    try_float_or_none,
    try_int,
)
from allotropy.parsers.utils.xml import (
    get_attrib_from_xml,
    get_element_from_xml,
    get_val_from_xml,
    get_val_from_xml_or_none,
)

SAMPLE_ROLE_TYPE_MAPPING = {
    "Blank": SampleRoleType.blank_role,
    "Control": SampleRoleType.control_sample_role,
    "Standard": SampleRoleType.standard_sample_role,
    "Unknown": SampleRoleType.unknown_sample_role,
}


@dataclass(frozen=True)
class AnalyteSample:
    analyte_name: str
    analyte_region: int
    analyte_error_code: str

    @staticmethod
    def create(analyte_xml: ElementTree.Element) -> AnalyteSample:
        return AnalyteSample(
            analyte_name=get_val_from_xml(analyte_xml, ANALYTE_NAME),
            analyte_region=try_int(analyte_xml.attrib[REGION_NUMBER], "analyte_region"),
            analyte_error_code=get_attrib_from_xml(analyte_xml, READING, CODE),
        )


@dataclass(frozen=True)
class WellAnalyteMapping:
    well_name: str
    analytes: list[AnalyteSample] = field(default_factory=list)


@dataclass
class SampleDocumentStructure:
    sample_type: SampleRoleType
    sample_identifier: str
    description: str | None
    well_name: str
    sample_dilution: float | None
    well_analyte_mapping: WellAnalyteMapping


@dataclass
class SampleDocumentAggregate:
    # This data class pulled from the <Samples> part of the xml.
    samples_dict: dict[str, SampleDocumentStructure] = field(default_factory=dict)
    # Default to empty dictionary.
    analyte_region_dict: dict[str, str] = field(default_factory=dict)

    @staticmethod
    def create(samples_xml: ElementTree.Element) -> SampleDocumentAggregate:
        sample_documents = SampleDocumentAggregate()
        for sample_types in samples_xml:
            for child_sample_type in sample_types:
                sample_type = map_sample_type(child_sample_type.tag)
                sample_description = get_val_from_xml_or_none(
                    child_sample_type, DESCRIPTION_TAG
                )
                sample_identifier = get_val_from_xml(child_sample_type, LABEL)
                sample_dilution = get_val_from_xml_or_none(child_sample_type, DILUTION)
                for child in child_sample_type:
                    if child.tag == MEMBER_WELLS:
                        for member_well in child:
                            sample_document = (
                                SampleDocumentAggregate._generate_sample_document(
                                    sample_documents=sample_documents,
                                    well_xml=member_well,
                                    sample_id=sample_identifier,
                                    sample_dilution=try_float_or_none(sample_dilution),
                                    sample_type=sample_type,
                                    sample_description=sample_description,
                                )
                            )
                            sample_documents.samples_dict[
                                sample_document.well_name
                            ] = sample_document
        return sample_documents

    @staticmethod
    def _generate_sample_document(
        sample_documents: SampleDocumentAggregate,
        well_xml: ElementTree.Element,
        sample_id: str,
        sample_dilution: float | None,
        sample_type: SampleRoleType,
        sample_description: str | None,
    ) -> SampleDocumentStructure:
        well_name = get_well_name(well_xml.attrib)
        mappings = WellAnalyteMapping(well_name=well_name, analytes=[])
        for analyte in get_element_from_xml(well_xml, MW_ANALYTES):
            # Create the analyte.
            new_analyte = AnalyteSample.create(analyte_xml=analyte)
            # Add the analyte to the well analyte mappings.
            mappings.analytes.append(new_analyte)
            # Update the analyte region dict
            sample_documents.analyte_region_dict[
                str(new_analyte.analyte_region)
            ] = new_analyte.analyte_name
        sample_document = SampleDocumentStructure(
            sample_type=sample_type,
            sample_identifier=sample_id,
            description=sample_description,
            well_name=well_name,
            well_analyte_mapping=mappings,
            sample_dilution=sample_dilution,
        )
        return sample_document


@dataclass
class DeviceWellSettings:
    # This data class is for all metadata needed in the <Wells> section, used in measurement and device control docs.
    well_name: str
    sample_volume_setting: int
    detector_gain_setting: str
    minimum_assay_bead_count_setting: int
    well_total_events: int
    acquisition_time: str

    @staticmethod
    def create(well_xml: ElementTree.Element) -> DeviceWellSettings:
        well_name = get_well_name(well_xml.attrib)
        well_acq_time = get_val_from_xml(well_xml, ACQ_TIME)
        total_events = get_val_from_xml(well_xml, TOTAL_EVENTS)
        sample_volume = try_int(
            get_val_from_xml(well_xml, RUN_SETTINGS, SAMPLE_VOLUME), "sample_volume"
        )

        detector_gain_setting = get_val_from_xml(well_xml, RUN_CONDITIONS, RP1_GAIN)
        min_assay_bead_count_setting = get_attrib_from_xml(
            well_xml, RUN_SETTINGS, BEAD_COUNT, STOP_READING_CRITERIA
        )
        return DeviceWellSettings(
            well_name=well_name,
            sample_volume_setting=sample_volume,
            detector_gain_setting=detector_gain_setting,
            minimum_assay_bead_count_setting=try_int(
                min_assay_bead_count_setting, "minimum_assay_bead_count_settings"
            ),
            acquisition_time=well_acq_time,
            well_total_events=try_int(total_events, "well_total_events"),
        )


@dataclass
class AnalyteDocumentData:
    analyte_name: str
    assay_bead_identifier: str
    assay_bead_count: int
    fluorescence: float

    @staticmethod
    def create(
        bead_region_xml: ElementTree.Element,
        analyte_region_dict: dict[str, str],
        regions_of_interest: list[str],
    ) -> AnalyteDocumentData | None:
        # Look up analyte name from sample
        assay_bead_identifier = bead_region_xml.attrib[REGION_NUMBER]

        # Look up bead region -> analyte name
        if assay_bead_identifier not in regions_of_interest:
            return None

        analyte_name = analyte_region_dict[assay_bead_identifier]
        assay_bead_count = try_int(
            get_val_from_xml(bead_region_xml, REGION_COUNT), "assay_bead_count"
        )
        # Median
        fluorescence = try_float(
            get_val_from_xml(bead_region_xml, MEDIAN), "fluorescence"
        )
        return AnalyteDocumentData(
            analyte_name=analyte_name,
            assay_bead_identifier=assay_bead_identifier,
            assay_bead_count=assay_bead_count,
            fluorescence=fluorescence,
        )


@dataclass
class WellSystemLevelMetadata:
    # This class is for data that should be the same across all wells, we just need to grab the data from one well.
    serial_number: str
    controller_version: str
    user: str
    analytical_method: str
    plate_id: str
    regions_of_interest: list[str] = field(default_factory=list)

    @staticmethod
    def create(xml_well: ElementTree.Element) -> WellSystemLevelMetadata:
        serial_number = get_val_from_xml(xml_well, MACHINE_INFO, SERIAL_NUMBER)
        controller_version = get_val_from_xml(
            xml_well, MACHINE_INFO, "MicroControllerVersion"
        )
        user = get_val_from_xml(xml_well, "User")
        analytical_method = get_val_from_xml(xml_well, "RunProtocolDocumentLocation")
        plate_id = get_val_from_xml(xml_well, "PlateID")
        regions = get_element_from_xml(xml_well, RUN_SETTINGS, REGIONS_OF_INTEREST)
        regions_of_interest = []
        for region in regions:
            region_str = str(region.attrib[REGION_NUMBER])
            regions_of_interest.append(region_str)
        return WellSystemLevelMetadata(
            serial_number=serial_number,
            controller_version=controller_version,
            user=user,
            analytical_method=analytical_method,
            plate_id=plate_id,
            regions_of_interest=regions_of_interest,
        )


def validate_xml_structure(full_xml: ElementTree.Element) -> None:
    expected_tags = [
        SAMPLES,
        DOC_LOCATION_TAG,
        DESCRIPTION_TAG,
        PLATE_DIMENSIONS_TAG,
        WELLS_TAG,
    ]
    missing_tags = []
    try:
        present_tags = {child.tag for child in full_xml}
        # Check for missing tags
        for tag in expected_tags:
            if tag not in present_tags:
                missing_tags.append(tag)
    except ElementTree.ParseError as err:
        # Return all expected tags if XML parsing fails
        msg = "Error parsing xml"
        raise AllotropyParserError(msg) from err
    if missing_tags:
        msg = f"Missing expected tags in xml: {missing_tags}"
        raise AllotropeConversionError(msg)


def get_well_name(well_attrib: dict[str, str]) -> str:
    row_name = ROW_NAMES[try_int(well_attrib[ROW_NUMBER], "row_number") - 1]
    column_name = str(well_attrib[COLUMN_NUMBER])
    well_name = row_name + column_name
    return well_name


def map_sample_type(sample_type_tag: str) -> SampleRoleType:
    try:
        sample_type = SAMPLE_ROLE_TYPE_MAPPING[sample_type_tag]
        return sample_type
    except KeyError as err:
        msg = f"{sample_type_tag} is not in the valid list of sample role types: {SAMPLE_ROLE_TYPE_MAPPING.keys()}"
        raise AllotropeConversionError(msg) from err


def create_metadata(root_xml: Et.Element, well_system_metadata: WellSystemLevelMetadata, file_name: str) -> Metadata:
    return Metadata(
        file_name=file_name,
        software_name=constants.SOFTWARE_NAME,
        software_version=root_xml.attrib[constants.VERSION_ATTRIB],
        equipment_serial_number=well_system_metadata.serial_number,
        firmware_version=well_system_metadata.controller_version,
        product_manufacturer=constants.PRODUCT_MANUFACTURER,
        device_type=constants.DEVICE_TYPE,
    )


def create_measurement_group(
    samples_xml: Et.Element,
    well_xml: Et.Element,
    regions_of_interest: list[str],
    experimental_data_id: str | None,
    experiment_type: str | None,
    plate_well_count: int,
    analytical_method_identifier: str,
    plate_id: str,
) -> MeasurementGroup:
    well_name = get_well_name(well_xml.attrib)

    sample_document_aggregated = SampleDocumentAggregate.create(samples_xml)
    sample = sample_document_aggregated.samples_dict[well_name]

    device_well_settings = DeviceWellSettings.create(well_xml)

    identifier = random_uuid_str()

    analytes = []
    for atr in well_xml:
        if atr.tag != constants.BEAD_REGIONS:
            continue
        for bead in atr:
            analyte_structure_doc = AnalyteDocumentData.create(
                bead_region_xml=bead,
                analyte_region_dict=sample_document_aggregated.analyte_region_dict,
                regions_of_interest=regions_of_interest,
            )
            if analyte_structure_doc is None:
                continue
            analytes.append(
                Analyte(
                    identifier=random_uuid_str(),
                    name=analyte_structure_doc.analyte_name,
                    assay_bead_identifier=analyte_structure_doc.assay_bead_identifier,
                    assay_bead_count=analyte_structure_doc.assay_bead_count,
                    value=analyte_structure_doc.fluorescence,
                    statistic_datum_role=TStatisticDatumRole.median_role,
                )
            )

    errors = [
        Error(
            error=analyte.analyte_name,
            feature=get_key_or_error(
                "error code", analyte.analyte_error_code, ERROR_MAPPING
            )
        )
        for analyte in sample.well_analyte_mapping.analytes if analyte.analyte_error_code != "0"
    ]

    return MeasurementGroup(
        experiment_type=experiment_type,
        plate_well_count=plate_well_count,
        analytical_method_identifier=analytical_method_identifier,
        experimental_data_identifier=experimental_data_id,
        analyst=get_val_from_xml(well_xml, constants.USER),
        container_type=constants.CONTAINER_TYPE,
        measurements=[
            Measurement(
                identifier=identifier,
                measurement_time=device_well_settings.acquisition_time,
                assay_bead_count=device_well_settings.well_total_events,
                description=sample.description,
                sample_identifier=sample.sample_identifier,
                location_identifier=well_name,
                sample_role_type=sample.sample_type,
                well_plate_identifier=plate_id,
                sample_volume_setting=device_well_settings.sample_volume_setting,
                dilution_factor_setting=sample.sample_dilution,
                detector_gain_setting=device_well_settings.detector_gain_setting,
                minimum_assay_bead_count_setting=device_well_settings.minimum_assay_bead_count_setting,
                analytes=analytes,
                errors=errors,
            )
        ]
    )
