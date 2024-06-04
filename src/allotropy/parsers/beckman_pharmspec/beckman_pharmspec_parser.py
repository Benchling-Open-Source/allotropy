import re
from typing import Any, Optional, Union

import pandas as pd

from allotropy.allotrope.models.adm.light_obscuration.benchling._2023._12.light_obscuration import (
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
from allotropy.parsers.beckman_pharmspec.constants import PHARMSPEC_SOFTWARE_NAME
from allotropy.parsers.release_state import ReleaseState
from allotropy.parsers.utils.uuids import random_uuid_str
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
    @property
    def display_name(self) -> str:
        return "Beckman PharmSpec"

    @property
    def release_state(self) -> ReleaseState:
        return ReleaseState.RECOMMENDED

    def to_allotrope(self, named_file_contents: NamedFileContents) -> Model:
        df = pd.read_excel(named_file_contents.contents, header=None, engine="openpyxl")
        return self._setup_model(df, named_file_contents.original_file_name)

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
        self, df: pd.DataFrame
    ) -> list[DistributionDocumentItem]:
        """Create the distribution document. First, we create the actual distrituion, which itself
        contains a list of DistributionDocumentItem objects. The DistributionDocumentItem objects represent the values
        from the rows of the incoming dataframe.

        If we were able to support more than one data frame instead of just the average data, we could
        return a DistributionDocument with more than one item. For the use cases we've seen, there is
        only a single Distribution being returned at this time, containing the average data.

        :param df: The average dataframe
        :return: The DistributionDocument
        """
        cols = [v for k, v in column_map.items()]
        items = []
        for elem in df.to_dict("records"):
            item = {}
            for c in cols:
                prop = c.replace(
                    " ", "_"
                )  # to be able to set the props on the DistributionItem
                if c in elem:
                    item[prop] = get_property_from_sample(prop, float(elem[c]))
            item["distribution_identifier"] = random_uuid_str()
            items.append(DistributionItem(**item))
        # TODO get test example for data_processing_omission_setting
        dd = DistributionDocumentItem(distribution=items)
        return [dd]

    def _create_calculated_document_items(
        self, df: pd.DataFrame, feature: str, run_names: list[str]
    ) -> list[CalculatedDataDocumentItem]:
        cols = column_map.values()
        items = []
        for row in df.index:
            particle_size = df.at[
                row, "particle size"
            ]  # to track the calcuated data tuple
            for col in [x for x in cols if x in df.columns]:
                prop = col.replace(
                    " ", "_"
                )  # to be able to set the props on the DistributionItem
                items.append(
                    CalculatedDataDocumentItem(
                        calculated_data_identifier=random_uuid_str(),
                        calculated_data_name=f"{feature}_{prop}".lower(),
                        calculated_result=get_property_from_sample(
                            prop, df.at[row, col]
                        ),
                        data_source_aggregate_document=TDataSourceAggregateDocument(
                            data_source_document=[
                                DataSourceDocumentItem(
                                    data_source_identifier=f"{run_name}|{particle_size}",  # will be replaced by distribution id
                                    data_source_feature=col,
                                )
                                for run_name in run_names
                                if run_name not in VALID_CALCS
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
        self, df: pd.DataFrame, name: str, run_names: list[str]
    ) -> TCalculatedDataAggregateDocument:
        return TCalculatedDataAggregateDocument(
            calculated_data_document=self._create_calculated_document_items(
                df, name, run_names
            )
        )

    def _create_measurement_document_item(
        self, df: pd.DataFrame, gdf: pd.DataFrame, name: str
    ) -> MeasurementDocumentItem:
        return MeasurementDocumentItem(
            measurement_identifier=name,
            measurement_time=pd.to_datetime(
                str(df.at[8, 5]).replace(".", "-")
            ).isoformat(timespec="microseconds")
            + "Z",
            device_control_aggregate_document=DeviceControlAggregateDocument(
                device_control_document=[
                    DeviceControlDocumentItem(
                        flush_volume_setting=TQuantityValueMilliliter(value=0),
                        detector_view_volume=TQuantityValueMilliliter(
                            value=df.at[9, 5]
                        ),
                        repetition_setting=int(df.at[11, 5]),
                        sample_volume_setting=TQuantityValueMilliliter(
                            value=df.at[11, 2]
                        ),
                    )
                ]
            ),
            sample_document=SampleDocument(
                sample_identifier=str(df.at[2, 2]),
            ),
            processed_data_aggregate_document=ProcessedDataAggregateDocument(
                processed_data_document=[
                    ProcessedDataDocumentItem(
                        data_processing_document=DataProcessingDocument(
                            dilution_factor_setting=TQuantityValueUnitless(
                                value=df.at[13, 2]
                            ),
                        ),
                        distribution_aggregate_document=DistributionAggregateDocument(
                            distribution_document=self._create_distribution_document_items(
                                gdf
                            )
                        ),
                    )
                ]
            ),
        )

    def _create_model(
        self,
        df: pd.DataFrame,
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
                            analyst=str(df.at[6, 5]),
                            submitter=None,
                            measurement_document=measurement_doc_items,
                        )
                    )
                ],
                data_system_document=DataSystemDocument(
                    file_name=file_name,
                    software_name=PHARMSPEC_SOFTWARE_NAME,
                    software_version=self._get_software_version_report_string(
                        df.at[0, 2]
                    ),
                    ASM_converter_name=ASM_CONVERTER_NAME,
                    ASM_converter_version=ASM_CONVERTER_VERSION,
                ),
                device_system_document=DeviceSystemDocument(
                    equipment_serial_number=str(df.at[4, 5]),
                    device_document=[
                        DeviceDocumentItem(
                            detector_identifier="",
                            detector_model_number=str(df.at[2, 5]),
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

    def _add_data_source_to_calculated_data(
        self,
        calc_agg_doc: TCalculatedDataAggregateDocument,
        measurement_doc_items: list[MeasurementDocumentItem],
    ) -> None:
        if calc_agg_doc.calculated_data_document is not None:
            for cdd in calc_agg_doc.calculated_data_document:
                if (
                    cdd.data_source_aggregate_document is not None
                    and cdd.data_source_aggregate_document.data_source_document
                    is not None
                ):
                    for dsd in cdd.data_source_aggregate_document.data_source_document:
                        run_name, particle_size = str(dsd.data_source_identifier).split(
                            "|"
                        )
                        distribution_id = (
                            self._get_distribution_id_for_run_and_particle_size(
                                run_name, float(particle_size), measurement_doc_items
                            )
                        )
                        if distribution_id is not None:
                            dsd.data_source_identifier = distribution_id

    def _setup_model(self, df: pd.DataFrame, file_name: str) -> Model:
        """Build the Model

        :param df: the raw dataframe
        :return: the model
        """
        data = self._extract_data(df)
        measurement_doc_items = []
        calc_agg_doc = None
        run_names = list(data["Run No."].unique())
        for g, gdf in data.groupby("Run No."):
            name = str(g)
            if g in VALID_CALCS:
                calc_agg_doc = self._create_calculated_data_aggregate_document(
                    gdf, name, run_names
                )
            else:
                measurement_doc_items.append(
                    self._create_measurement_document_item(df, gdf, name)
                )
        if calc_agg_doc is not None:
            self._add_data_source_to_calculated_data(
                calc_agg_doc, measurement_doc_items
            )
        return self._create_model(df, calc_agg_doc, measurement_doc_items, file_name)
