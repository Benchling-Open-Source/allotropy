from dataclasses import dataclass, field

from defusedxml import ElementTree as DefusedElementTree

from allotropy.exceptions import AllotropeConversionError
from allotropy.parsers.utils.values import get_val_from_xml, try_int_or_none

WELLS_TAG = "Wells"
DOC_LOCATION_TAG = "NativeDocumentLocation"
DESCRIPTION_TAG = "Description"
PLATE_DIMENSIONS_TAG = "PlateDimensions"
TOTAL_WELLS_ATTRIB = "TotalWells"
VERSION_ATTRIB = "BioPlexManagerVersion"
SAMPLES = "Samples"
MEMBER_WELLS = "MemberWells"
ROW_NUMBER = "RowNo"
COLUMN_NUMBER = "ColNo"
WELL_NUMBER = "WellNumber"
WELL_NO = "WellNo"
REGION_NUMBER = "RegionNumber"
REGIONS_OF_INTEREST = "RegionsOfInterest"
CODE = "Code"
DILUTION = "Dilution"
ROW_NAMES = "ABCDEFGH"

SAMPLE_ROLE_TYPE_MAPPING = {
    "Blank": "blank role",
    "Control": "control sample role",
    "Standard": "standard sample role",
    "Unknown": "unknown sample role",
}


@dataclass(frozen=True)
class AnalyteSample:
    analyte_name: str
    analyte_region: int
    analyte_error_code: int

    @staticmethod
    def create(analyte_xml):
        return AnalyteSample(
            analyte_name=analyte_xml[0].text,
            analyte_region=try_int_or_none(analyte_xml.attrib[REGION_NUMBER]),
            analyte_error_code=try_int_or_none(analyte_xml[1].attrib[CODE]),
        )


@dataclass(frozen=True)
class WellAnalyteMapping:
    well_name: str
    analytes: list[AnalyteSample] = field(default_factory=list)


@dataclass
class SampleDocument:
    sample_type: str
    sample_identifier: str
    description: str
    well_name: str
    sample_dilution: float
    well_analyte_mapping: list[WellAnalyteMapping] = field(default_factory=list)


@dataclass
class SampleDocumentAggregate:
    # This data class pulled from the <Samples> part of the xml.
    samples: list[SampleDocument] = field(default_factory=list)
    # Default to empty dictionary.
    analyte_region_dict: dict[str, str] = field(default_factory=dict)

    @staticmethod
    def create(samples_xml):
        sample_documents = SampleDocumentAggregate()
        for sample_types in samples_xml:
            for child_sample_type in sample_types:
                # TODO: add catch of non mapping sample roles
                sample_type = SAMPLE_ROLE_TYPE_MAPPING[child_sample_type.tag]
                # NOTE: Assumption here is that the description and label are always here
                # This element is the "description"
                sample_description = get_val_from_xml(
                    child_sample_type, 0, "Sample Description"
                )
                # This element is the "label"
                sample_identifier = get_val_from_xml(
                    child_sample_type, 1, "Sample Identifier"
                )
                if child_sample_type[2].tag == DILUTION:
                    sample_dilution = get_val_from_xml(child_sample_type, 2, "Dilution")
                    for child in child_sample_type:
                        if child.tag == MEMBER_WELLS:
                            for member_well in child:
                                sample_document = (
                                    SampleDocumentAggregate._generate_sample_document(
                                        sample_documents=sample_documents,
                                        well_xml=member_well,
                                        sample_id=sample_identifier,
                                        sample_dilution=sample_dilution,
                                        sample_type=sample_type,
                                        sample_description=sample_description,
                                    )
                                )
                                sample_documents.samples.append(sample_document)

        return sample_documents

    @staticmethod
    def _generate_sample_document(
        sample_documents,
        well_xml,
        sample_id: str,
        sample_dilution: float,
        sample_type: str,
        sample_description: str,
    ):
        well_name = get_well_name(well_xml.attrib)
        mappings = WellAnalyteMapping(well_name=well_name, analytes=[])
        for analyte in well_xml[0]:
            # Create the analyte.
            new_analyte = AnalyteSample.create(analyte_xml=analyte)
            # Add the analyte to the well analyte mappings.
            mappings.analytes.append(new_analyte)
            # Update the analyte region dict
            sample_documents.analyte_region_dict[
                new_analyte.analyte_region
            ] = new_analyte.analyte_name
        sample_document = SampleDocument(
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
    minimum_assay_bead_count_setting: str
    well_total_events: int
    acquisition_time: str

    @staticmethod
    def create(well_xml):
        well_name = get_well_name(well_xml.attrib)
        well_acq_time = get_val_from_xml(well_xml, 2, "AcquisitionTime")
        total_events = get_val_from_xml(well_xml, 9, "TotalEvents")
        sample_volume = int(get_val_from_xml(well_xml, 6, "SampleVolume", 0))
        # RP1 Gain. 16th element of Run Conditions
        detector_gain_setting = get_val_from_xml(well_xml, 5, "RP1Gain", 15)
        # Assuming second element of Run Settings
        min_assay_bead_count_setting = get_val_from_xml(
            well_xml, 6, "StopReadingCriteria", 1
        )
        return DeviceWellSettings(
            well_name=well_name,
            sample_volume_setting=sample_volume,
            detector_gain_setting=detector_gain_setting,
            minimum_assay_bead_count_setting=min_assay_bead_count_setting,
            acquisition_time=well_acq_time,
            well_total_events=total_events,
        )


@dataclass
class AnalyteDocumentData:
    analyte_name: str
    assay_bead_identifier: str
    assay_bead_count: str
    fluorescence: float

    @staticmethod
    def create(
        bead_region_xml: str,
        analyte_region_dict: dict,
        regions_of_interest: list,
    ):
        # Look up analyte name from sample
        assay_bead_identifier = bead_region_xml.attrib[REGION_NUMBER]
        # Look up bead region -> analyte name
        if assay_bead_identifier in regions_of_interest:
            analyte_name = analyte_region_dict[assay_bead_identifier]
            # Region Count is first element of bead region.
            assay_bead_count = int(get_val_from_xml(bead_region_xml, 0, "RegionCount"))
            # Median
            fluorescence = float(get_val_from_xml(bead_region_xml, 1, "Median"))
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
    regions_of_interest: list[int] = field(default_factory=list)

    @staticmethod
    def create(xml_well):
        serial_number = get_val_from_xml(xml_well, 7, "SerialNumber", 3)
        controller_version = get_val_from_xml(xml_well, 7, "MicroControllerVersion", 0)
        user = get_val_from_xml(xml_well, 1, "User")
        # This is the RunProtocolDocumentLocation
        analytical_method = get_val_from_xml(xml_well, 4, "RunProtocolDocumentLocation")
        regions = xml_well[6][4]
        if regions.tag != REGIONS_OF_INTEREST:
            raise AllotropeConversionError(
                msg=f"Could not find {REGIONS_OF_INTEREST} in instrument xml"
            )
        regions_of_interest = []
        for region in regions:
            regions_of_interest.append(region.attrib[REGION_NUMBER])
        return WellSystemLevelMetadata(
            serial_number=serial_number,
            controller_version=controller_version,
            user=user,
            analytical_method=analytical_method,
            regions_of_interest=regions_of_interest,
        )


def validate_xml_structure(full_xml):
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
    except DefusedElementTree.ParseError as err:
        # Return all expected tags if XML parsing fails
        msg = "Error parsing xml"
        raise AllotropeConversionError(msg) from err
    if missing_tags:
        msg = f"Missing expected tags in xml: {missing_tags}"
        raise AllotropeConversionError(msg)


def get_well_name(well_attrib: dict) -> str:
    row_name = ROW_NAMES[int(well_attrib[ROW_NUMBER]) - 1]
    column_name = str(well_attrib[COLUMN_NUMBER])
    well_name = row_name + column_name
    return well_name
