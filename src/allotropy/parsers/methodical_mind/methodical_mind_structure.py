from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from allotropy.parsers.lines_reader import CsvReader
from allotropy.parsers.utils.values import assert_not_none

FILENAME = "FileName"
BARCODE_1 = "Barcode1"
READ_TIME = "Read Time"
VERSION = "Version"
USER = "User"
SERIAL_NO = "Serial"
MODEL = "Model"
DATA = "Data"
PLATE_END = "==="


@dataclass(frozen=True)
class CombinedData:
    file_name: str
    version: str
    model: str
    serial_number: str
    plate_doc_info: list[PlateData]

    @staticmethod
    def create(reader: CsvReader) -> CombinedData:
        file_name = assert_not_none(CombinedData.get_parameter(reader, FILENAME))
        barcode_1 = assert_not_none(
            CombinedData.get_parameter(reader, BARCODE_1)
        ).strip("<>")
        read_time = assert_not_none(
            CombinedData.get_parameter(reader, READ_TIME, all_vals_after_tab=True)
        )
        version = assert_not_none(CombinedData.get_parameter(reader, VERSION))
        user = CombinedData.get_parameter(reader, USER)
        serial_no = assert_not_none(CombinedData.get_parameter(reader, SERIAL_NO))
        model = assert_not_none(CombinedData.get_parameter(reader, MODEL))

        plate_data = []
        while reader.current_line < len(reader.lines):
            assert_not_none(
                reader.drop_until_inclusive(DATA),
                "Data",
                "Missing Data section in file",
            )
            plate_start = reader.current_line
            reader.drop_until(PLATE_END)
            plate_end = reader.current_line

            # Create dataframe of the plate, drop any columns with all Nan values
            plate_df = assert_not_none(
                reader.lines_as_df(
                    reader.lines[plate_start:plate_end], sep="\t", header=0
                ),
                "Luminescence data table",
            ).dropna(axis=1, how="all")

            # Drop rows with nans in the first column since they don't represent a row in a plate
            # Drop the first column to get total wells since it's just a "label"
            dropped_nans = plate_df.dropna(subset=[plate_df.columns[0]]).drop(
                columns=[plate_df.columns[0]]
            )
            # Get the well count by multiplying number of rows by number of cols
            well_count = dropped_nans.shape[0] * dropped_nans.shape[1]
            plate_data.append(
                PlateData.create(
                    plate_df=plate_df,
                    measurement_time=read_time,
                    analyst=user,
                    well_plate_id=barcode_1,
                    plate_well_count=well_count,
                )
            )

            # Attempt to get the next plate's barcode, read time, and analyst.
            next_barcode = reader.drop_until_inclusive(BARCODE_1)
            next_read_time = reader.drop_until_inclusive(READ_TIME)
            next_user = reader.drop_until_inclusive(USER)

            if all(
                var is not None for var in [next_barcode, next_read_time, next_user]
            ):
                barcode_1 = assert_not_none(next_barcode).split("\t")[1].strip("<>")
                read_time = " ".join(assert_not_none(next_read_time).split("\t")[1:])
                user = assert_not_none(next_user).split("\t")[1]
            # Exception if the next plate isn't found, stop looking for more plates
            else:
                break
        return CombinedData(
            file_name=file_name,
            version=version,
            model=model,
            serial_number=serial_no,
            plate_doc_info=plate_data,
        )

    @staticmethod
    def get_parameter(
        reader: CsvReader, name: str, *, all_vals_after_tab: bool = False
    ) -> str | None:
        val_line = reader.drop_until_inclusive(name)
        if val_line is not None:
            try:
                if all_vals_after_tab:
                    return " ".join(val_line.split("\t")[1:])
                else:
                    return val_line.split("\t")[1]
            except IndexError:
                return None
        else:
            return None


@dataclass(frozen=True)
class PlateData:
    measurement_time: str
    plate_well_count: int
    analyst: str | None
    well_plate_id: str
    well_data: list[WellData]

    @staticmethod
    def create(
        plate_df: pd.DataFrame,
        measurement_time: str,
        analyst: str | None,
        well_plate_id: str,
        plate_well_count: int,
    ) -> PlateData:
        well_data = []
        spot_index_counter = 0
        for _index, row in plate_df.iterrows():
            # Increment the spot index counter for every new row
            spot_index_counter += 1
            # Skip the first column since it's the well names (no luminescence values)
            for col in plate_df.columns[1:]:
                if pd.notna(row.iloc[0]):
                    # This is the row well name-- A, B, C, etc.
                    well_row = row.iloc[0].strip()
                    # If we've detected a new well row, reset the spot index counter
                    spot_index_counter = 1
                location_name = well_row + col.strip() + "_" + str(spot_index_counter)
                luminescence = row[col]
                well_data.append(
                    WellData.create(
                        luminescence=luminescence,
                        location_id=location_name,
                        well_plate_id=well_plate_id,
                    )
                )
        return PlateData(
            measurement_time=measurement_time,
            plate_well_count=plate_well_count,
            analyst=analyst,
            well_plate_id=well_plate_id,
            well_data=well_data,
        )


@dataclass(frozen=True)
class WellData:
    luminescence: int
    location_identifier: str
    sample_identifier: str

    @staticmethod
    def create(luminescence: int, location_id: str, well_plate_id: str) -> WellData:
        sample_id = well_plate_id + "_" + location_id
        return WellData(
            luminescence=luminescence,
            location_identifier=location_id,
            sample_identifier=sample_id,
        )
