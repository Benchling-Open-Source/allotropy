import io
from typing import Any

import pandas as pd

from allotropy.allotrope.models.light_obscuration_rec_2021_12_light_obscuration import (
    DistributionDocumentItem,
    DistributionItem,
    MeasurementDocument,
    Model,
)
from allotropy.allotrope.models.shared.definitions.custom import (
    TQuantityValueCountsPerMilliliter,
    TQuantityValueMicrometer,
    TQuantityValueMilliliter,
    TQuantityValueUnitless,
)
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


def get_property_from_sample(property_name: str, value: Any) -> Any:
    return property_lookup[property_name](value=value)


class PharmSpecParser(VendorParser):
    def _parse(self, contents: io.IOBase, _: str) -> Model:
        df = pd.read_excel(contents, header=None, engine="openpyxl")
        return self._get_model(df)

    def _get_model(self, df: pd.DataFrame) -> Model:
        model = self._setup_model(df)
        return model

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
        avg = data[data["Run No."] == "Average"].rename(
            columns={x: column_map[x] for x in column_map}
        )
        return avg

    def _create_distribution_document_items(
        self, df: pd.DataFrame
    ) -> list[DistributionDocumentItem]:
        """Create the distribution document. First, we create the actual distrituion, which itself
        contains a list of DistributionDocumentItem objects. The DistributionDocumentItem objects represent the values
        from the rows of the incoming dataframe.

        If we were able to support more than one data frame instead of just the average data, we could
        return a DistributionDocument with more than one item. For the use cases we've seen, there is
        only a single Distribution being returned at this time, containing the average data.

        :param df: The average datafreame
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
            items.append(DistributionItem(**item))
        # TODO get test example for data_processing_omission_setting
        dd = DistributionDocumentItem(
            distribution=items, data_processing_omission_setting=False
        )
        return [dd]

    def _setup_model(self, df: pd.DataFrame) -> Model:
        """Build the Model

        :param df: the raw dataframe
        :return: the model
        """
        data = self._extract_data(df)
        distribution_document_items = self._create_distribution_document_items(data)
        model = Model(
            dilution_factor_setting=TQuantityValueUnitless(df.at[13, 2]),
            detector_model_number=str(df.at[2, 5]),
            analyst=str(df.at[6, 5]),
            repetition_setting=int(df.at[11, 5]),
            sample_volume_setting=TQuantityValueMilliliter(df.at[11, 2]),
            detector_view_volume=TQuantityValueMilliliter(df.at[9, 5]),
            measurement_identifier=str(df.at[2, 2]),
            sample_identifier=str(df.at[2, 2]),
            equipment_serial_number=str(df.at[4, 5]),
            detector_identifier=str(df.at[4, 5]),
            measurement_document=MeasurementDocument(
                distribution_document=distribution_document_items
            ),
            flush_volume_setting=TQuantityValueMilliliter(
                0
            ),  # TODO get test example for this
            measurement_time=pd.to_datetime(
                str(df.at[8, 5]).replace(".", "-")
            ).isoformat(timespec="microseconds")
            + "Z",
        )
        return model
