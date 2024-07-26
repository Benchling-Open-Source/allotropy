from __future__ import annotations

from typing import Any
import xml.etree.ElementTree as Et

from allotropy.allotrope.models.adm.multi_analyte_profiling.benchling._2024._01.multi_analyte_profiling import (
    AnalyteAggregateDocument,
    AnalyteDocumentItem,
    DataSystemDocument,
    DeviceControlAggregateDocument,
    DeviceControlDocumentItem,
    DeviceSystemDocument,
    ErrorAggregateDocument,
    ErrorDocumentItem,
    MeasurementAggregateDocument,
    MeasurementDocumentItem,
    Model,
    MultiAnalyteProfilingAggregateDocument,
    MultiAnalyteProfilingDocumentItem,
    SampleDocument,
)
from allotropy.allotrope.models.shared.definitions.custom import (
    TQuantityValueMicroliter,
    TQuantityValueNumber,
    TQuantityValueRelativeFluorescenceUnit,
    TQuantityValueUnitless,
)
from allotropy.allotrope.models.shared.definitions.definitions import (
    TStatisticDatumRole,
)
from allotropy.constants import ASM_CONVERTER_VERSION
from allotropy.exceptions import AllotropeConversionError
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.biorad_bioplex_manager.biorad_bioplex_manager_structure import (
    AnalyteDocumentData,
    DeviceWellSettings,
    get_well_name,
    SampleDocumentAggregate,
    SampleDocumentStructure,
    validate_xml_structure,
    WellAnalyteMapping,
    WellSystemLevelMetadata,
)
from allotropy.parsers.biorad_bioplex_manager.constants import (
    BEAD_REGIONS,
    CONTAINER_TYPE,
    DESCRIPTION_TAG,
    DEVICE_TYPE,
    DOC_LOCATION_TAG,
    ERROR_MAPPING,
    PLATE_DIMENSIONS_TAG,
    PRODUCT_MANUFACTURER,
    SAMPLES,
    SOFTWARE_NAME,
    TOTAL_WELLS_ATTRIB,
    USER,
    VERSION_ATTRIB,
    WELLS_TAG,
)
from allotropy.parsers.release_state import ReleaseState
from allotropy.parsers.utils.uuids import random_uuid_str
from allotropy.parsers.utils.values import quantity_or_none
from allotropy.parsers.utils.xml import get_val_from_xml
from allotropy.parsers.vendor_parser import VendorParser


class BioradBioplexParser(VendorParser):
    @property
    def display_name(self) -> str:
        return "Bio-Rad Bio-Plex Manager"

    @property
    def release_state(self) -> ReleaseState:
        return ReleaseState.RECOMMENDED

    def to_allotrope(self, named_file_contents: NamedFileContents) -> Model:
        contents = named_file_contents.contents.read()
        xml_tree = Et.ElementTree(Et.fromstring(contents))  # noqa: S314
        root_xml = xml_tree.getroot()
        validate_xml_structure(root_xml)
        filename = named_file_contents.original_file_name
        return self._get_model(root_xml, filename)

    def _get_model(self, data: Et.Element, filename: str) -> Model:
        software_version_value = data.attrib[VERSION_ATTRIB]
        for child in data:
            if child.tag == SAMPLES:
                all_samples_xml = child
            elif child.tag == PLATE_DIMENSIONS_TAG:
                plate_well_count = int(child.attrib[TOTAL_WELLS_ATTRIB])
            elif child.tag == DOC_LOCATION_TAG:
                experimental_data_id = child.text
            elif child.tag == DESCRIPTION_TAG:
                experiment_type = child.text
        for child in data:
            if child.tag == WELLS_TAG:
                well_system_metadata = WellSystemLevelMetadata.create(child[0])
                device_document = BioradBioplexParser._get_device_system_document(
                    well_system_metadata
                )
                all_wells_xml = child
        multi_docs = self.get_measurement_document_aggregate(
            samples_xml=all_samples_xml,
            wells_xml=all_wells_xml,
            regions_of_interest=well_system_metadata.regions_of_interest,
            experimental_data_id=experimental_data_id,
            experiment_type=experiment_type,
            plate_well_count=plate_well_count,
            analytical_method_identifier=well_system_metadata.analytical_method,
        )

        return Model(
            field_asm_manifest="http://purl.allotrope.org/manifests/multi-analyte-profiling/BENCHLING/2024/01/multi-analyte-profiling.manifest",
            multi_analyte_profiling_aggregate_document=MultiAnalyteProfilingAggregateDocument(
                device_system_document=device_document,
                data_system_document=DataSystemDocument(
                    software_name=SOFTWARE_NAME,
                    software_version=software_version_value,
                    ASM_converter_name=self.get_asm_converter_name(),
                    ASM_converter_version=ASM_CONVERTER_VERSION,
                    file_name=filename,
                ),
                multi_analyte_profiling_document=multi_docs,
            ),
        )

    @staticmethod
    def _get_device_system_document(
        well_system_metadata: WellSystemLevelMetadata,
    ) -> DeviceSystemDocument:
        return DeviceSystemDocument(
            equipment_serial_number=well_system_metadata.serial_number,
            firmware_version=well_system_metadata.controller_version,
            product_manufacturer=PRODUCT_MANUFACTURER,
        )

    def get_measurement_document_aggregate(
        self,
        samples_xml: Et.Element,
        wells_xml: Et.Element,
        regions_of_interest: list[str],
        experimental_data_id: str | None,
        experiment_type: str | None,
        plate_well_count: int,
        analytical_method_identifier: str,
    ) -> list[MultiAnalyteProfilingDocumentItem]:
        sample_document_aggregated = SampleDocumentAggregate.create(samples_xml)
        multi_analyte_docs = []
        for well in wells_xml:
            well_name = get_well_name(well.attrib)
            sample = sample_document_aggregated.samples_dict[well_name]
            device_well_settings = DeviceWellSettings.create(well)
            measurement_doc = MeasurementDocumentItem(
                measurement_identifier=random_uuid_str(),
                measurement_time=self._get_date_time(
                    device_well_settings.acquisition_time
                ),
                assay_bead_count=TQuantityValueNumber(
                    value=device_well_settings.well_total_events
                ),
                sample_document=BioradBioplexParser._get_sample_document(
                    sample, well_name
                ),
                device_control_aggregate_document=BioradBioplexParser._get_device_control_aggregate(
                    device_well_settings, sample
                ),
                analyte_aggregate_document=BioradBioplexParser._get_analyte_aggregate_document(
                    well,
                    sample_document_aggregated.analyte_region_dict,
                    regions_of_interest,
                ),
                error_aggregate_document=BioradBioplexParser._get_error_aggregate_document(
                    sample.well_analyte_mapping
                ),
            )
            multi_analyte_docs.append(
                MultiAnalyteProfilingDocumentItem(
                    measurement_aggregate_document=MeasurementAggregateDocument(
                        measurement_document=[measurement_doc],
                        experiment_type=experiment_type,
                        plate_well_count=TQuantityValueNumber(value=plate_well_count),
                        analytical_method_identifier=analytical_method_identifier,
                        container_type=CONTAINER_TYPE,
                        experimental_data_identifier=experimental_data_id,
                    ),
                    analyst=get_val_from_xml(well, USER),
                )
            )

        return multi_analyte_docs

    @staticmethod
    def _get_sample_document(sample: SampleDocumentStructure, well_name: str) -> Any:
        return SampleDocument(
            description=sample.description,
            sample_identifier=sample.sample_identifier,
            location_identifier=well_name,
            sample_role_type=sample.sample_type,
        )

    @staticmethod
    def _get_device_control_aggregate(
        device_well_settings: DeviceWellSettings, sample: SampleDocumentStructure
    ) -> DeviceControlAggregateDocument:

        device_control_doc_item = DeviceControlDocumentItem(
            device_type=DEVICE_TYPE,
            sample_volume_setting=TQuantityValueMicroliter(
                value=device_well_settings.sample_volume_setting
            ),
            dilution_factor_setting=quantity_or_none(
                TQuantityValueUnitless, sample.sample_dilution
            ),
            detector_gain_setting=device_well_settings.detector_gain_setting,
            minimum_assay_bead_count_setting=quantity_or_none(
                TQuantityValueNumber,
                device_well_settings.minimum_assay_bead_count_setting,
            ),
        )
        return DeviceControlAggregateDocument(
            device_control_document=[device_control_doc_item]
        )

    @staticmethod
    def _get_analyte_aggregate_document(
        well: Et.Element,
        analyte_region_dict: dict[str, str],
        regions_of_interest: list[str],
    ) -> AnalyteAggregateDocument:
        analyte_docs = []
        for atr in well:
            if atr.tag == BEAD_REGIONS:
                for bead in atr:
                    analyte_structure_doc = AnalyteDocumentData.create(
                        bead_region_xml=bead,
                        analyte_region_dict=analyte_region_dict,
                        regions_of_interest=regions_of_interest,
                    )
                    if analyte_structure_doc is None:
                        continue
                    analyte_docs.append(
                        AnalyteDocumentItem(
                            analyte_identifier=random_uuid_str(),
                            analyte_name=analyte_structure_doc.analyte_name,
                            assay_bead_identifier=analyte_structure_doc.assay_bead_identifier,
                            assay_bead_count=TQuantityValueNumber(
                                value=analyte_structure_doc.assay_bead_count
                            ),
                            fluorescence=TQuantityValueRelativeFluorescenceUnit(
                                value=analyte_structure_doc.fluorescence,
                                has_statistic_datum_role=TStatisticDatumRole.median_role,
                            ),
                        )
                    )
        return AnalyteAggregateDocument(analyte_document=analyte_docs)

    @staticmethod
    def _get_error_aggregate_document(
        well_analyte_mapping: WellAnalyteMapping,
    ) -> ErrorAggregateDocument:
        error_docs = []
        for analyte in well_analyte_mapping.analytes:
            if analyte.analyte_error_code != "0":
                error_docs.append(
                    ErrorDocumentItem(
                        error=analyte.analyte_name,
                        error_feature=BioradBioplexParser._get_error_str_from_code(
                            analyte.analyte_error_code
                        ),
                    ),
                )
        return ErrorAggregateDocument(error_document=error_docs)

    @staticmethod
    def _get_error_str_from_code(error_code: str) -> str:
        try:
            error_str = ERROR_MAPPING[error_code]
            return error_str
        except KeyError as e:
            msg = f"{error_code} is not a valid error code. Valid error codes are:{ERROR_MAPPING.keys()}"
            raise AllotropeConversionError(msg) from e
