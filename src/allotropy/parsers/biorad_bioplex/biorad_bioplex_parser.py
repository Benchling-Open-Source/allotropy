from __future__ import annotations
import xml.etree.ElementTree as ET
import pandas as pd

from allotropy.allotrope.models.multi_analyte_profiling_benchling_2024_01_multi_analyte_profiling import (
MultiAnalyteProfilingAggregateDocument,
DeviceSystemDocument,
DataSystemDocument,
MultiAnalyteProfilingDocumentItem,
MeasurementAggregateDocument,
MeasurementDocumentItem,
SampleDocument,
DeviceControlAggregateDocument,
DeviceControlDocumentItem,
AnalyteAggregateDocument,
AnalyteDocumentItem,
ErrorAggregateDocument,
ErrorDocumentItem,
Model
)

from allotropy.allotrope.models.shared.components.plate_reader import (
    SampleRoleType,
)
from allotropy.parsers.biorad_bioplex.biorad_bioplex_structure import (
SampleDocumentAggregate,
SampleDocumentStructure,
AnalyteSample,
validate_xml_structure,
DeviceWellSettings,
AnalyteDocumentData,
WellSystemLevelMetadata,
get_well_name

)
from allotropy.parsers.utils.uuids import random_uuid_str
from allotropy.parsers.vendor_parser import VendorParser

from allotropy.constants import ASM_CONVERTER_NAME, ASM_CONVERTER_VERSION

from allotropy.allotrope.models.shared.definitions.custom import (
    TQuantityValueMicroliter,
    TQuantityValueNumber,
    TQuantityValueRelativeFluorescenceUnit,
    TQuantityValueUnitless,
)

from allotropy.allotrope.models.shared.definitions.definitions import (
    TDateTimeStampValue,
    TQuantityValue,
    TStringValue,
)


WELLS_TAG = "Wells"
DOC_LOCATION_TAG = "NativeDocumentLocation"
BEAD_REGIONS = "BeadRegions"
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
BEAD_COUNT = "BeadCount"

PRODUCT_MANUFACTURER = "Bio-Rad"
SOFTWARE_NAME = "“Bio-Plex Manager"
DEVICE_TYPE = "Multi Analyte Profiling Analyzer"

from allotropy.constants import ASM_CONVERTER_NAME, ASM_CONVERTER_VERSION




class BioradBioplexParser(VendorParser):
    def to_allotrope(self, named_file_contents: NamedFileContents) -> Model:
        contents = named_file_contents.contents.read().decode('utf-8')
        xml_tree = tree = ET.ElementTree(ET.fromstring(contents))
        root_xml = xml_tree.getroot()
        validate_xml_structure(root_xml)
        filename = named_file_contents.original_file_name
        return self._get_model(root_xml, filename)

    def _get_model(self, data: Data, filename: str) -> Model:
        software_version_value = data.attrib[VERSION_ATTRIB]
        for child in data:
            if child.tag == SAMPLES:
                sample_aggregate_doc = SampleDocumentAggregate(child)
                all_samples_xml = child
            elif child.tag == DOC_LOCATION_TAG:
                experimental_data_identifier = child.text
            elif child.tag == DESCRIPTION_TAG:
                experiment_type = child.text
            elif child.tag == PLATE_DIMENSIONS_TAG:
                plate_well_count = int(child.attrib[TOTAL_WELLS_ATTRIB])
        # Double loop because wells comes before
        for child in data:
            if child.tag == WELLS_TAG:
                well_system_metadata = WellSystemLevelMetadata.create(child[0])
                device_document = BioradBioplexParser._get_device_system_document(well_system_metadata)
                all_wells_xml = child
        multi_docs= BioradBioplexParser._get_measurement_document_aggregate(samples_xml=all_samples_xml, wells_xml=all_wells_xml, regions_of_interest=well_system_metadata.regions_of_interest)

        return Model(field_asm_manifest="http://purl.allotrope.org/manifests/multi-analyte-profiling/BENCHLING/2024/01/multi-analyte-profiling.manifest",
                    multi_analyte_profiling_aggregate_document= MultiAnalyteProfilingAggregateDocument(
            device_system_document=device_document,
            data_system_document=self._get_data_system_document(software_version=software_version_value),
            multi_analyte_profiling_document=multi_docs
        ))

    @staticmethod
    def _get_device_system_document(well_system_metadata: WellSystemLevelMetadata) -> DeviceSystemDocument:
        return DeviceSystemDocument(
            equipment_serial_number=well_system_metadata.serial_number,
            firmware_version=well_system_metadata.controller_version,
            product_manufacturer=PRODUCT_MANUFACTURER
        )
    @staticmethod
    def _get_data_system_document(software_version: str) -> DataSystemDocument:
        return DataSystemDocument(
            software_name=SOFTWARE_NAME,
            software_version=software_version,
            ASM_converter_name=ASM_CONVERTER_NAME,
            ASM_converter_version=ASM_CONVERTER_VERSION,
        )
    @staticmethod
    def _get_measurement_document_aggregate(samples_xml, wells_xml, regions_of_interest):
        sample_document_aggregated = SampleDocumentAggregate.create(samples_xml)
        device_well_settings_all = [DeviceWellSettings.create(xml_well) for xml_well in wells_xml]
        multi_analyte_docs = []
        for sample in sample_document_aggregated.samples:
            for well in wells_xml:
                well_name = get_well_name(well.attrib)
                if sample.well_name == well_name:

                    device_well_settings = DeviceWellSettings.create(well)
                    #print(sample.well_name, well_name, device_well_settings.well_name)
                    measurement_doc = MeasurementDocumentItem(measurement_identifier=random_uuid_str(),
                                                              measurement_time= device_well_settings.acquisition_time,
                                                              assay_bead_count= TQuantityValueNumber(device_well_settings.well_total_events),
                                                              sample_document=SampleDocument(
                                                                  description=sample.description,
                                                                  sample_identifier=sample.sample_identifier,
                                                                  location_identifier=well_name,
                                                                  sample_role_type=sample.sample_type
                                                              ),
                                                              device_control_aggregate_document=BioradBioplexParser._get_device_control_aggregate(device_well_settings, sample),
                                                              analyte_aggregate_document=BioradBioplexParser._get_analyte_aggregate_document(well, sample_document_aggregated.analyte_region_dict,regions_of_interest),
                                                              error_aggregate_document=BioradBioplexParser._get_error_aggregate_document(sample.well_analyte_mapping)
                                                              )
                    multi_analyte_docs.append(MultiAnalyteProfilingDocumentItem(measurement_aggregate_document=MeasurementAggregateDocument(measurement_document=[measurement_doc]),
                                                                          analyst="abc"))

        return multi_analyte_docs


    @staticmethod
    def _get_device_control_aggregate(device_well_settings: DeviceWellSettings, sample: SampleDocument) -> DeviceControlAggregateDocument:
        return DeviceControlAggregateDocument(
            device_control_document=[DeviceControlDocumentItem(
                device_type=DEVICE_TYPE,
                sample_volume_setting=TQuantityValueMicroliter(device_well_settings.sample_volume_setting),
                dilution_factor_setting=TQuantityValueUnitless(sample.sample_dilution),
                detector_gain_setting=device_well_settings.detector_gain_setting,
                minimum_assay_bead_count_setting= TQuantityValueUnitless(device_well_settings.minimum_assay_bead_count_setting)
            )]
        )

    @staticmethod
    def _get_analyte_aggregate_document(well: ElementTree.element, analyte_region_dict: SampleDocumentAggregate.analyte_region_dict,
                                        regions_of_interest: WellSystemLevelMetadata.regions_of_interest) -> AnalyteAggregateDocument:
        analyte_docs = []
        for atr in well:
            if atr.tag == BEAD_REGIONS:
                for bead in atr:
                    analyte_structure_doc = AnalyteDocumentData.create(
                        bead_region_xml=bead,
                        analyte_region_dict=analyte_region_dict,
                        regions_of_interest=regions_of_interest,
                    )
                    if analyte_structure_doc is not None:
                        analyte_docs.append(AnalyteDocumentItem(
                            #TODO: right now this is unique for every appearance of an analyte, I think this is wrong
                            analyte_identifier=random_uuid_str(),
                            analyte_name=analyte_structure_doc.analyte_name,
                            assay_bead_identifier=analyte_structure_doc.assay_bead_identifier,
                            assay_bead_count=TQuantityValueNumber(analyte_structure_doc.assay_bead_count),
                            fluorescence=TQuantityValueRelativeFluorescenceUnit(analyte_structure_doc.fluorescence)
                        ))
        return AnalyteAggregateDocument(
            analyte_document=analyte_docs
        )

    @staticmethod
    def _get_error_aggregate_document(well_analyte_mapping: SampleDocument.well_analyte_mapping):
        error_docs = []
        for analyte in well_analyte_mapping.analytes:
            error_docs.append(ErrorDocumentItem(
                error=analyte.analyte_name,
                error_feature=str(analyte.analyte_error_code)
            ))
        return ErrorAggregateDocument(
            error_document=error_docs
        )










