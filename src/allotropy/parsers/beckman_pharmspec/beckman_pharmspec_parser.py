import re
from typing import Any, Optional, Union

import pandas as pd

from allotropy.allotrope.models.light_obscuration_benchling_2023_12_light_obscuration import (
    CalculatedDataDocumentItem,
    DataProcessingDocument,
    DataSourceDocumentItem,
    DataSystemDocument,
    DeviceControlAggregateDocument,
    DeviceControlDocumentItem,
    DeviceDocumentItem,
    DeviceSystemDocument,
    DistributionAggregateDocument,
    DistributionDocumentItem,
    DistributionItem,
    LightObscurationAggregateDocument,
    LightObscurationDocumentItem,
    MeasurementAggregateDocument,
    MeasurementDocumentItem,
    Model,
    ProcessedDataAggregateDocument,
    ProcessedDataDocumentItem,
    SampleDocument,
    TCalculatedDataAggregateDocument,
    TDataSourceAggregateDocument,
)
from allotropy.allotrope.models.shared.definitions.custom import (
    TQuantityValueCountsPerMilliliter,
    TQuantityValueMicrometer,
    TQuantityValueMilliliter,
    TQuantityValueUnitless,
)
from allotropy.allotrope.models.shared.definitions.definitions import TStringValueItem
from allotropy.constants import ASM_CONVERTER_NAME, ASM_CONVERTER_VERSION
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.beckman_pharmspec.beckman_pharmspec_structure import (
    Distribution,
    PharmSpecData,
)
from allotropy.parsers.beckman_pharmspec.constants import PHARMSPEC_SOFTWARE_NAME
from allotropy.parsers.vendor_parser import VendorParser

# This map is used to coerce the column names coming in the raw data
# into names of the allotrope properties.
column_map = {
    "Cumulative Counts/mL": "cumulative particle density",
    "Cumulative Count": "cumulative count",
    "Particle Size(µm)": "particle size",
    "Differential Counts/mL": "differential particle density",
    "Differential Count": "differential count",
}

property_lookup = {
    "particle_size": TQuantityValueMicrometer,
    "cumulative_count": TQuantityValueUnitless,
    "cumulative_particle_density": TQuantityValueCountsPerMilliliter,
    "differential_particle_density": TQuantityValueCountsPerMilliliter,
    "differential_count": TQuantityValueUnitless,
}

VALID_CALCS = ["Average"]


def get_property_from_sample(property_name: str, value: Any) -> Any:
    return property_lookup[property_name](value=value)


class PharmSpecParser(VendorParser):
    def to_allotrope(self, named_file_contents: NamedFileContents) -> Model:
        df = pd.read_excel(named_file_contents.contents, header=None, engine="openpyxl")
        data = PharmSpecData.create(df)
        return self._setup_model(data, named_file_contents.original_file_name)

    def _get_data_using_key_bounds(
        self, df: pd.DataFrame, start_key: str, end_key: str
    ) -> pd.DataFrame:
        """Find the data in the raw dataframe. We identify the boundary of the data
        by finding the index first row which contains the word 'Particle' and ending right before
        the index of the first row containing 'Approver'.

        :param df: the raw dataframe
        :param start_key: the key to start the slice
        :parm end_key: the key to end the slice
        :return: the dataframe slice between the stard and end bounds
        """
        start = df[df[1].str.contains(start_key, na=False)].index.values[0]
        end = df[df[0].str.contains(end_key, na=False)].index.values[0] - 1
        return df.loc[start:end, :]

    def _extract_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Extract the Average data frame from the raw data. Initial use cases have focused on
        only extracting the Average data, not the individual runs. The ASM does support multiple
        Distribution objects, but they don't have names, so it's not possible to pick these out
        after the fact. As such, this extraction only includes the Average data.

        :param df: the raw dataframe
        :return: the average data frame
        """
        data = self._get_data_using_key_bounds(
            df, start_key="Particle", end_key="Approver_"
        )
        data = data.dropna(how="all").dropna(how="all", axis=1)
        data[0] = data[0].ffill()
        data = data.dropna(subset=1).reset_index(drop=True)
        data.columns = pd.Index([x.strip() for x in data.loc[0]])
        data = data.loc[1:, :]
        return data.rename(columns={x: column_map[x] for x in column_map})

    def _create_distribution_document_items(
        self, distribution: Distribution
    ) -> list[DistributionDocumentItem]:
        """Create the distribution document. First, we create the actual distribution, which itself
        contains a list of DistributionDocumentItem objects. The DistributionDocumentItem objects represent
        the values from the rows of the incoming dataframe.

        :param distribution: the Distribution object
        :return: The DistributionDocument
        """
        items = []
        for row in distribution.data:
            item = {}
            for key in property_lookup:
                value = getattr(row, key)
                if value is not None:
                    item[key] = get_property_from_sample(key, value)
            item["distribution_identifier"] = row.distribution_row_id
            items.append(DistributionItem(**item))
        return [DistributionDocumentItem(distribution=items)]

    def _create_calculated_document_items(
        self, data: PharmSpecData
    ) -> list[CalculatedDataDocumentItem]:
        calcs = [x for x in data.distributions if x.is_calculated]
        sources = [x for x in data.distributions if not x.is_calculated]
        items = []
        for calc in calcs:
            for row in calc.data:
                for prop in property_lookup:
                    value = getattr(row, prop)
                    if value:
                        source_rows = [
                            x
                            for source in sources
                            for x in source.data
                            if row.particle_size == x.particle_size
                        ]
                        items.append(
                            CalculatedDataDocumentItem(
                                calculated_data_identifier=row.distribution_row_id,
                                calculated_data_name=f"{calc.name}_{prop}".lower(),
                                calculated_result=get_property_from_sample(prop, value),
                                data_source_aggregate_document=TDataSourceAggregateDocument(
                                    data_source_document=[
                                        DataSourceDocumentItem(
                                            data_source_identifier=f"{x.distribution_row_id}",  # will be replaced by distribution id
                                            data_source_feature=prop.replace("_", " "),
                                        )
                                        for x in source_rows
                                    ]
                                ),
                            )
                        )
        return items

    def _get_software_version_report_string(self, report_string: str) -> str:
        match = re.search(r"v(\d+(?:\.\d+)?(?:\.\d+)?)", report_string)
        if match:
            return match.group(1)
        return "Unknown"

    def _create_calculated_data_aggregate_document(
        self, data: PharmSpecData
    ) -> TCalculatedDataAggregateDocument:
        return TCalculatedDataAggregateDocument(
            calculated_data_document=self._create_calculated_document_items(data)
        )

    def _create_measurement_document_items(
        self, data: PharmSpecData
    ) -> list[MeasurementDocumentItem]:
        items = []
        for d in [x for x in data.distributions if not x.is_calculated]:
            items.append(
                MeasurementDocumentItem(
                    measurement_identifier=d.name,
                    measurement_time=data.metadata.measurement_time,
                    device_control_aggregate_document=DeviceControlAggregateDocument(
                        device_control_document=[
                            DeviceControlDocumentItem(
                                flush_volume_setting=TQuantityValueMilliliter(
                                    value=data.metadata.flush_volume_setting
                                ),
                                detector_view_volume=TQuantityValueMilliliter(
                                    value=data.metadata.detector_view_volume
                                ),
                                repetition_setting=data.metadata.repetition_setting,
                                sample_volume_setting=TQuantityValueMilliliter(
                                    value=data.metadata.sample_volume_setting,
                                ),
                            )
                        ]
                    ),
                    sample_document=SampleDocument(
                        sample_identifier=data.metadata.sample_identifier,
                    ),
                    processed_data_aggregate_document=ProcessedDataAggregateDocument(
                        processed_data_document=[
                            ProcessedDataDocumentItem(
                                data_processing_document=DataProcessingDocument(
                                    dilution_factor_setting=TQuantityValueUnitless(
                                        value=data.metadata.dilution_factor_setting,
                                    )
                                ),
                                distribution_aggregate_document=DistributionAggregateDocument(
                                    distribution_document=self._create_distribution_document_items(
                                        d
                                    )
                                ),
                            )
                        ]
                    ),
                )
            )

        return items

    def _create_model(
        self,
        data: PharmSpecData,
        calc_agg_doc: Optional[TCalculatedDataAggregateDocument],
        measurement_doc_items: list[MeasurementDocumentItem],
        file_name: str,
    ) -> Model:
        return Model(
            field_asm_manifest="http://purl.allotrope.org/manifests/light-obscuration/BENCHLING/2023/12/light-obscuration.manifest",
            light_obscuration_aggregate_document=LightObscurationAggregateDocument(
                light_obscuration_document=[
                    LightObscurationDocumentItem(
                        measurement_aggregate_document=MeasurementAggregateDocument(
                            analyst=data.metadata.analyst,
                            submitter=data.metadata.submitter,
                            measurement_document=measurement_doc_items,
                        )
                    )
                ],
                data_system_document=DataSystemDocument(
                    file_name=file_name,
                    software_name=PHARMSPEC_SOFTWARE_NAME,
                    software_version=data.metadata.software_version,
                    ASM_converter_name=ASM_CONVERTER_NAME,
                    ASM_converter_version=ASM_CONVERTER_VERSION,
                ),
                device_system_document=DeviceSystemDocument(
                    equipment_serial_number=data.metadata.equipment_serial_number,
                    device_document=[
                        DeviceDocumentItem(
                            detector_identifier=data.metadata.detector_identifier,
                            detector_model_number=data.metadata.detector_model_number,
                        )
                    ],
                ),
                calculated_data_aggregate_document=calc_agg_doc,
            ),
        )

    def _get_distribution_id_for_run_and_particle_size(
        self,
        run_name: str,
        particle_size: float,
        measurement_doc_items: list[MeasurementDocumentItem],
    ) -> Optional[Union[str, TStringValueItem]]:
        item = next(
            x for x in measurement_doc_items if x.measurement_identifier == run_name
        )
        if (
            item.processed_data_aggregate_document is not None
            and item.processed_data_aggregate_document.processed_data_document
            is not None
        ):
            for pdd in item.processed_data_aggregate_document.processed_data_document:
                if (
                    pdd.distribution_aggregate_document is not None
                    and pdd.distribution_aggregate_document.distribution_document
                    is not None
                ):
                    for dd in pdd.distribution_aggregate_document.distribution_document:
                        for d in dd.distribution:
                            if d.particle_size.value == particle_size:
                                return d.distribution_identifier
        return None

    def _setup_model(self, data: PharmSpecData, file_name: str) -> Model:
        """Build the Model

        :param df: the raw dataframe
        :return: the model
        """
        measurement_doc_items = self._create_measurement_document_items(data)
        calc_agg_doc = self._create_calculated_data_aggregate_document(data)
        return self._create_model(data, calc_agg_doc, measurement_doc_items, file_name)
