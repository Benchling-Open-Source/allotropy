from itertools import chain

from allotropy.allotrope.models.adm.plate_reader.rec._2024._06.plate_reader import (
    CalculatedDataAggregateDocument,
    CalculatedDataDocumentItem,
    DataSourceAggregateDocument,
    DataSourceDocumentItem,
    DataSystemDocument,
    DeviceControlAggregateDocument,
    DeviceControlDocumentItem,
    DeviceSystemDocument,
    MeasurementAggregateDocument,
    MeasurementDocument,
    Model,
    PlateReaderAggregateDocument,
    PlateReaderDocumentItem,
    SampleDocument,
    TQuantityValueModel,
)
from allotropy.allotrope.models.shared.definitions.custom import (
    TQuantityValueDegreeCelsius,
    TQuantityValueMilliAbsorbanceUnit,
    TQuantityValueNanometer,
    TQuantityValueNumber,
    TQuantityValueRelativeFluorescenceUnit,
    TQuantityValueRelativeLightUnit,
)
from allotropy.allotrope.models.shared.definitions.units import UNITLESS
from allotropy.allotrope.schema_mappers.adm.plate_reader.rec._2024._06.plate_reader import (
    Data,
    Mapper,
)
from allotropy.constants import ASM_CONVERTER_VERSION
from allotropy.exceptions import (
    AllotropeConversionError,
)
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.constants import NOT_APPLICABLE
from allotropy.parsers.lines_reader import CsvReader, read_to_lines
from allotropy.parsers.moldev_softmax_pro.constants import EPOCH, REDUCED
from allotropy.parsers.moldev_softmax_pro.softmax_pro_structure import (
    create_calculated_data,
    create_measurement_groups,
    create_metadata,
    StructureData,
    GroupBlock,
    GroupSampleData,
    PlateBlock,
    ScanPosition,
)
from allotropy.parsers.release_state import ReleaseState
from allotropy.parsers.utils.uuids import random_uuid_str
from allotropy.parsers.utils.values import (
    assert_not_none,
    quantity_or_none,
)
from allotropy.parsers.vendor_parser import MapperVendorParser


class SoftmaxproParser(MapperVendorParser[Data, Model]):
    DISPLAY_NAME = "Molecular Devices SoftMax Pro"
    RELEASE_STATE = ReleaseState.RECOMMENDED
    SUPPORTED_EXTENSIONS = "txt"
    SCHEMA_MAPPER = Mapper

    def create_data(self, named_file_contents: NamedFileContents) -> Data:
        lines = read_to_lines(named_file_contents)
        reader = CsvReader(lines)
        data = StructureData.create(reader)

        return Data(
            create_metadata(named_file_contents.original_file_name),
            create_measurement_groups(data),
            create_calculated_data(),
        )

    ########

    # def _get_calc_docs(
    #     self, data: StructureData
    # ) -> CalculatedDataAggregateDocument | None:
    #     calc_docs = self._get_reduced_calc_docs(data) + self._get_group_calc_docs(data)
    #     return (
    #         CalculatedDataAggregateDocument(calculated_data_document=calc_docs)
    #         if calc_docs
    #         else None
    #     )

    # def _get_calc_docs_data_sources(
    #     self, plate_block: PlateBlock, position: str
    # ) -> list[DataSourceDocumentItem]:
    #     return [
    #         DataSourceDocumentItem(
    #             data_source_identifier=data_source.uuid,
    #             data_source_feature=plate_block.measurement_type,
    #         )
    #         for data_source in plate_block.iter_data_elements(position)
    #     ]

    # def _build_calc_doc(
    #     self,
    #     name: str,
    #     value: float,
    #     data_sources: list[DataSourceDocumentItem],
    #     description: str | None = None,
    # ) -> CalculatedDataDocumentItem:
    #     return CalculatedDataDocumentItem(
    #         calculated_data_identifier=random_uuid_str(),
    #         calculated_data_name=name,
    #         calculation_description=description,
    #         calculated_result=TQuantityValueModel(unit=UNITLESS, value=value),
    #         data_source_aggregate_document=DataSourceAggregateDocument(
    #             data_source_document=data_sources
    #         ),
    #     )

    # def _get_reduced_calc_docs(
    #     self, data: StructureData
    # ) -> list[CalculatedDataDocumentItem]:
    #     return [
    #         self._build_calc_doc(
    #             name=REDUCED,
    #             value=reduced_data_element.value,
    #             data_sources=self._get_calc_docs_data_sources(
    #                 plate_block,
    #                 reduced_data_element.position,
    #             ),
    #         )
    #         for plate_block in data.block_list.plate_blocks.values()
    #         for reduced_data_element in plate_block.iter_reduced_data()
    #     ]

    # def _get_group_agg_calc_docs(
    #     self,
    #     data: StructureData,
    #     group_block: GroupBlock,
    #     group_sample_data: GroupSampleData,
    # ) -> list[CalculatedDataDocumentItem]:
    #     return [
    #         self._build_calc_doc(
    #             name=aggregated_entry.name,
    #             value=aggregated_entry.value,
    #             data_sources=list(
    #                 chain.from_iterable(
    #                     self._get_calc_docs_data_sources(
    #                         data.block_list.plate_blocks[group_data_element.plate],
    #                         group_data_element.position,
    #                     )
    #                     for group_data_element in group_sample_data.data_elements
    #                 )
    #             ),
    #             description=group_block.group_columns.data.get(aggregated_entry.name),
    #         )
    #         for aggregated_entry in group_sample_data.aggregated_entries
    #     ]

    # def _get_group_simple_calc_docs(
    #     self,
    #     data: StructureData,
    #     group_block: GroupBlock,
    #     group_sample_data: GroupSampleData,
    # ) -> list[CalculatedDataDocumentItem]:
    #     calculated_documents = []
    #     for group_data_element in group_sample_data.data_elements:
    #         data_sources = self._get_calc_docs_data_sources(
    #             data.block_list.plate_blocks[group_data_element.plate],
    #             group_data_element.position,
    #         )
    #         for entry in group_data_element.entries:
    #             calculated_documents.append(
    #                 self._build_calc_doc(
    #                     name=entry.name,
    #                     value=entry.value,
    #                     data_sources=data_sources,
    #                     description=group_block.group_columns.data.get(entry.name),
    #                 )
    #             )
    #     return calculated_documents

    # def _get_group_calc_docs(
    #     self, data: StructureData
    # ) -> list[CalculatedDataDocumentItem]:
    #     calculated_documents = []
    #     for group_block in data.block_list.group_blocks:
    #         for group_sample_data in group_block.group_data.sample_data:
    #             calculated_documents += self._get_group_agg_calc_docs(
    #                 data, group_block, group_sample_data
    #             )
    #             calculated_documents += self._get_group_simple_calc_docs(
    #                 data, group_block, group_sample_data
    #             )
    #     return calculated_documents
