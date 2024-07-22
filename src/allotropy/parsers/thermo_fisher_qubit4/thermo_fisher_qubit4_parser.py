""" Parser file for ThermoFisher Qubit 4 Adapter """


from allotropy.allotrope.converter import add_custom_information_document
from allotropy.allotrope.models.adm.spectrophotometry.benchling._2023._12.spectrophotometry import (
    ContainerType,
    DataSystemDocument,
    DeviceSystemDocument,
    FluorescencePointDetectionDeviceControlAggregateDocument,
    FluorescencePointDetectionDeviceControlDocumentItem,
    FluorescencePointDetectionMeasurementDocumentItems,
    MeasurementAggregateDocument,
    Model,
    SampleDocument,
    SpectrophotometryAggregateDocument,
    SpectrophotometryDocumentItem,
)
from allotropy.allotrope.models.shared.definitions.custom import (
    TQuantityValueMicroliter,
    TQuantityValueRelativeFluorescenceUnit,
    TQuantityValueUnitless,
)
from allotropy.constants import ASM_CONVERTER_VERSION
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.constants import NOT_APPLICABLE
from allotropy.parsers.release_state import ReleaseState
from allotropy.parsers.thermo_fisher_qubit4 import constants
from allotropy.parsers.thermo_fisher_qubit4.thermo_fisher_qubit4_reader import (
    ThermoFisherQubit4Reader,
)
from allotropy.parsers.thermo_fisher_qubit4.thermo_fisher_qubit4_structure import Row
from allotropy.parsers.utils.units import get_quantity_class
from allotropy.parsers.utils.uuids import random_uuid_str
from allotropy.parsers.utils.values import quantity_or_none
from allotropy.parsers.vendor_parser import VendorParser


class ThermoFisherQubit4Parser(VendorParser):
    """
    Parser for the ThermoFisher Qubit 4 data files.

    This parser reads data from ThermoFisher Qubit 4 files and converts it into an Allotrope model. The main functionalities
    include extracting and converting specific measurement and device control data, as well as handling custom sample and
    device information.
    """

    @property
    def display_name(self) -> str:
        return constants.DISPLAY_NAME

    @property
    def release_state(self) -> ReleaseState:
        return ReleaseState.RECOMMENDED

    def to_allotrope(self, named_file_contents: NamedFileContents) -> Model:
        """
        Converts the given named file contents to an Allotrope model.

        :param named_file_contents: The contents of the file to convert.
        :return: The converted Allotrope model.
        """
        return self._get_model(
            rows=Row.create_rows(ThermoFisherQubit4Reader.read(named_file_contents)),
            filename=named_file_contents.original_file_name,
        )

    def _get_model(self, rows: list[Row], filename: str) -> Model:
        """
        Generates an Allotrope model from the given data and filename.

        :param rows: The Rows to create the model from.
        :param filename: The original filename.
        :return: The Allotrope model.
        """
        return Model(
            field_asm_manifest="http://purl.allotrope.org/manifests/spectrophotometry/BENCHLING/2023/12/spectrophotometry.manifest",
            spectrophotometry_aggregate_document=SpectrophotometryAggregateDocument(
                spectrophotometry_document=[
                    self._get_spectrophotometry_document(row) for row in rows
                ],
                data_system_document=DataSystemDocument(
                    file_name=filename,
                    ASM_converter_name=self.get_asm_converter_name(),
                    ASM_converter_version=ASM_CONVERTER_VERSION,
                    software_name=constants.QUBIT_SOFTWARE,
                ),
                device_system_document=DeviceSystemDocument(
                    model_number=constants.MODEL_NUMBER,
                    device_identifier=NOT_APPLICABLE,
                    brand_name=constants.BRAND_NAME,
                    product_manufacturer=constants.PRODUCT_MANUFACTURER,
                ),
            ),
        )

    def _get_spectrophotometry_document(
        self, row: Row
    ) -> SpectrophotometryDocumentItem:
        """
        Generates a spectrophotometry document item for the given Row.

        :param row: The Row to create the document from.
        :return: A list of `SpectrophotometryDocumentItem`.
        """
        return SpectrophotometryDocumentItem(
            measurement_aggregate_document=MeasurementAggregateDocument(
                measurement_time=self._get_date_time(row.timestamp),
                experiment_type=row.assay_name,
                container_type=ContainerType.tube,
                measurement_document=[
                    FluorescencePointDetectionMeasurementDocumentItems(
                        fluorescence=TQuantityValueRelativeFluorescenceUnit(
                            value=row.fluorescence
                        ),
                        measurement_identifier=random_uuid_str(),
                        sample_document=self._get_sample_document(row),
                        device_control_aggregate_document=self._get_device_control_document(
                            row
                        ),
                    )
                ],
            )
        )

    def _get_sample_document(self, row: Row) -> SampleDocument:
        """
        Generates a sample document from the given data and index.

        :param row: The Row to create the document from.
        :return: The `SampleDocument`.
        """
        sample_custom_document = {
            "original sample concentration": quantity_or_none(
                get_quantity_class(row.original_sample_unit) or TQuantityValueUnitless,
                row.original_sample_concentration,
            ),
            "qubit tube concentration": quantity_or_none(
                get_quantity_class(row.qubit_tube_unit) or TQuantityValueUnitless,
                row.qubit_tube_concentration,
            ),
            "standard 1 concentration": quantity_or_none(
                TQuantityValueRelativeFluorescenceUnit, row.std_1_rfu
            ),
            "standard 2 concentration": quantity_or_none(
                TQuantityValueRelativeFluorescenceUnit, row.std_2_rfu
            ),
            "standard 3 concentration": quantity_or_none(
                TQuantityValueRelativeFluorescenceUnit, row.std_3_rfu
            ),
        }
        return add_custom_information_document(
            SampleDocument(
                sample_identifier=row.sample_identifier,
                batch_identifier=row.batch_identifier,
            ),
            sample_custom_document,
        )

    def _get_device_control_document(
        self, row: Row
    ) -> FluorescencePointDetectionDeviceControlAggregateDocument:
        """
        Generates a device control aggregate document from the given data and index.

        :param row: The Row to create the document from.
        :return: The `FluorescencePointDetectionDeviceControlAggregateDocument`.
        """
        custom_device_document = {
            "sample volume setting": quantity_or_none(
                TQuantityValueMicroliter, row.sample_volume
            ),
            "excitation setting": row.excitation,
            "emission setting": row.emission,
            "dilution factor": quantity_or_none(
                TQuantityValueUnitless, row.dilution_factor
            ),
        }
        return FluorescencePointDetectionDeviceControlAggregateDocument(
            device_control_document=[
                add_custom_information_document(
                    FluorescencePointDetectionDeviceControlDocumentItem(
                        device_type=constants.DEVICE_TYPE
                    ),
                    custom_device_document,
                )
            ]
        )
