from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from enum import Enum
import logging
from pathlib import Path
import re

import pandas as pd

from allotropy.allotrope.models.adm.plate_reader.benchling._2023._09.plate_reader import (
    ScanPositionSettingPlateReader,
    TransmittedLightSetting,
)
from allotropy.allotrope.models.shared.components.plate_reader import SampleRoleType
from allotropy.allotrope.schema_mappers.adm.plate_reader.benchling._2023._09.plate_reader import (
    DataSource,
    ImageFeature,
    ImageSource,
    Measurement,
    MeasurementGroup,
    MeasurementType,
    Metadata,
    ProcessedData,
)
from allotropy.exceptions import AllotropeConversionError, AllotropeParsingError
from allotropy.parsers.lines_reader import CsvReader, EMPTY_STR_OR_CSV_LINE
from allotropy.parsers.revvity_kaleido import constants
from allotropy.parsers.utils.pandas import df_to_series_data, SeriesData
from allotropy.parsers.utils.uuids import random_uuid_str
from allotropy.parsers.utils.values import (
    assert_not_none,
    try_float,
    try_float_or_none,
)


class ExperimentType(Enum):
    FLUORESCENCE = "fluorescence"
    ABSORBANCE = "absorbance"
    LUMINESCENCE = "luminescence"
    OPTICAL_IMAGING = "optical imaging"

    @staticmethod
    def create(experiment_type: str) -> ExperimentType:
        experiment_type_lower = experiment_type.lower()
        if "fluorescence" in experiment_type_lower or "alpha" in experiment_type_lower:
            return ExperimentType.FLUORESCENCE
        elif "abs" in experiment_type_lower:
            return ExperimentType.ABSORBANCE
        elif "luminescence" in experiment_type_lower:
            return ExperimentType.LUMINESCENCE
        elif "img" in experiment_type_lower:
            return ExperimentType.OPTICAL_IMAGING

        msg = f"Unable to determine experiment type from: '{experiment_type}'"
        raise AllotropeConversionError(msg)

    @property
    def measurement_type(self) -> MeasurementType:
        if self is ExperimentType.FLUORESCENCE:
            return MeasurementType.FLUORESCENCE
        elif self is ExperimentType.ABSORBANCE:
            return MeasurementType.ULTRAVIOLET_ABSORBANCE
        elif self is ExperimentType.LUMINESCENCE:
            return MeasurementType.LUMINESCENCE
        elif self is ExperimentType.OPTICAL_IMAGING:
            return MeasurementType.OPTICAL_IMAGING

    @property
    def device_type(self) -> str:
        if self is ExperimentType.OPTICAL_IMAGING:
            return "imaging detector"
        return f"{self.value} detector"

    @property
    def detection_type(self) -> str | None:
        # TODO(nstender): investigate why we override detection type for these two type but not others,
        # when we have detection type value for all examples.
        if self is ExperimentType.OPTICAL_IMAGING:
            return "optical-imaging"
        elif self is ExperimentType.FLUORESCENCE:
            return str(self.value)
        return None


class Version(Enum):
    V2 = "2.0"
    V3 = "3.0"


@dataclass
class BackgroundInfo:
    experiment_type_value: str

    @property
    def experiment_type(self) -> ExperimentType:
        return ExperimentType.create(self.experiment_type_value)

    @staticmethod
    def create(reader: CsvReader) -> BackgroundInfo:
        line = assert_not_none(
            reader.drop_until_inclusive("^Results? for.(.+) 1"),
            msg="Unable to find background information.",
        )

        experiment_type = assert_not_none(
            re.match("^Results? for.(.+) 1", line),
            msg="Unable to find experiment type from background information section.",
        ).group(1)

        return BackgroundInfo(experiment_type_value=experiment_type)


@dataclass(frozen=True)
class Results:
    barcode: str
    data: dict[str, str]

    @property
    def plate_well_count(self) -> int:
        return len(self.data)

    @classmethod
    def create(cls, reader: CsvReader) -> Results:
        barcode = cls.read_barcode(reader)

        results = assert_not_none(
            reader.pop_csv_block_as_df(
                header=0, index_col=0, empty_pat=EMPTY_STR_OR_CSV_LINE
            ),
            msg="Unable to find results table.",
        )

        for column in results:
            if str(column).startswith("Unnamed"):
                results = results.drop(columns=column)

        return Results(
            barcode=barcode,
            data={
                f"{row}{col}": str(values[col])
                for row, values in results.iterrows()
                for col in results.columns
            },
        )

    @classmethod
    def read_barcode(cls, reader: CsvReader) -> str:
        raise NotImplementedError


@dataclass(frozen=True)
class AnalysisResult:
    analysis_parameter: str
    results: dict[str, str]

    @staticmethod
    def create_results(
        reader: CsvReader, next_section_title: str
    ) -> list[AnalysisResult]:
        section_title = assert_not_none(
            reader.drop_until(f"^Results? for|^{next_section_title}"),
            msg=f"Unable to find Analysis Result or {next_section_title} section.",
        )

        if section_title.startswith(next_section_title):
            return []

        reader.drop_until("^Barcode")

        analysis_results = []
        while reader.match("^Barcode"):
            if analysis_result := AnalysisResult.create(reader):
                analysis_results.append(analysis_result)

        return analysis_results

    @staticmethod
    def create(reader: CsvReader) -> AnalysisResult | None:
        barcode_line = assert_not_none(
            reader.drop_until_inclusive("^Barcode:(.+),"),
            msg="Unable to find background information.",
        )

        analysis_parameter = None
        for element in barcode_line.split(","):
            if "AnalysisParameter" in element:
                analysis_parameter = element.split(":", maxsplit=1)[1]

        analysis_parameter = assert_not_none(
            analysis_parameter,
            msg="Unable to find analysis parameter in Analysis Results section.",
        )

        try:
            results_df = assert_not_none(
                reader.pop_csv_block_as_df(
                    header=0, index_col=0, empty_pat=EMPTY_STR_OR_CSV_LINE
                ),
                msg="Unable to find results table.",
            ).dropna(how="all")
        except AllotropeParsingError:
            logging.warning(
                f"Unable to read analysis result '{analysis_parameter}'. Ignoring"
            )
            return None

        results = {
            f"{row}{col}": str(values[col])
            for row, values in results_df.iterrows()
            for col in results_df.columns
        }

        # if first value is not a valid float value the results are not useful
        if try_float_or_none(results.get("A1")) is None:
            return None

        return AnalysisResult(
            analysis_parameter=analysis_parameter,
            results=results,
        )

    def get_image_feature_result(self, well_position: str) -> float:
        value_name = f"analysis result '{self.analysis_parameter}' at '{well_position}'"
        return try_float(
            assert_not_none(self.results.get(well_position), value_name), value_name
        )


@dataclass(frozen=True)
class MeasurementInfo:
    instrument_serial_number: str
    measurement_time: str
    protocol_signature: str
    measurement_signature: str

    @staticmethod
    def create(
        reader: CsvReader, section_name: str, next_section_title: str
    ) -> MeasurementInfo:
        assert_not_none(
            reader.drop_until_inclusive(f"^{section_name}"),
            msg=f"Unable to find {section_name} section.",
        )

        lines = list(reader.pop_until(f"^{next_section_title}"))
        # Because we may read over multiple sections of data to get all metadata for this section, there may
        # be varying number of columns. Get the max number of columns, so we can read in all sections without error.
        max_num_cols = max(len(line.split(",")) for line in lines)
        df = assert_not_none(
            reader.lines_as_df(lines, index_col=0, names=range(max_num_cols)),
            msg=f"Unable to parser data for {section_name} section.",
        ).T.dropna(how="all")
        df.columns = df.columns.astype(str).str.strip(":")
        data = df_to_series_data(df, index=0)

        return MeasurementInfo(
            instrument_serial_number=data[str, "Instrument Serial Number"],
            measurement_time=data[str, "Measurement Started"],
            protocol_signature=data[str, "Protocol Signature"],
            measurement_signature=data[str, "Measurement Signature"],
        )


@dataclass(frozen=True)
class Platemap:
    data: dict[str, str]

    @staticmethod
    def create(reader: CsvReader) -> Platemap:
        assert_not_none(
            reader.drop_until_inclusive("^Platemap"),
            msg="Unable to find Platemap section.",
        )
        reader.pop_if_match("^Plate")

        data = assert_not_none(
            reader.pop_csv_block_as_df(
                header=0, index_col=0, empty_pat=EMPTY_STR_OR_CSV_LINE
            ),
            msg="Unable to find platemap information.",
        )

        return Platemap(
            data={
                f"{row}{col}": str(values[col])
                for row, values in data.iterrows()
                for col in data.columns
            }
        )

    def get(self, well_position: str) -> str:
        return assert_not_none(
            self.data.get(well_position),
            f"platemap value for well position '{well_position}'",
        )

    def get_sample_role_type(self, well_position: str) -> SampleRoleType | None:
        raw_value = self.get(well_position)
        if raw_value == "-":
            return None

        value = assert_not_none(
            re.match(r"^([A-Z]+)\d+$", raw_value),
            msg=f"Unable to understand platemap value '{raw_value}' for well position '{well_position}'.",
        ).group(1)

        return assert_not_none(
            constants.PLATEMAP_TO_SAMPLE_ROLE_TYPE.get(value),
            msg=f"Unable to find sample role type for well position '{well_position}'.",
        )


@dataclass(frozen=True)
class Channel:
    name: str
    fluorescent_tag: str | None
    transmitted_light: TransmittedLightSetting | None
    excitation_wavelength: float
    illumination: float
    exposure_duration: float
    additional_focus_offset: float

    @staticmethod
    def create(
        name: str,
        excitation_wavelength: str,
        excitation_power: str,
        exposure_time: str,
        additional_focus_offset: str,
    ) -> Channel:
        return Channel(
            name=name,
            fluorescent_tag=None if name == "BRIGHTFIELD" else name,
            transmitted_light=constants.TRANSMITTED_LIGHT_CONVERSION.get(name),
            excitation_wavelength=try_float(
                excitation_wavelength.removesuffix("nm"), "excitation wavelength"
            ),
            illumination=try_float(excitation_power, "excitation power"),
            exposure_duration=try_float(exposure_time, "exposure time"),
            additional_focus_offset=try_float(
                additional_focus_offset, "additional focus offset"
            ),
        )


@dataclass(frozen=True)
class Measurements:
    channels: list[Channel]
    number_of_averages: float | None
    detector_distance: float | None
    scan_position: ScanPositionSettingPlateReader | None
    emission_wavelength: float | None
    excitation_wavelength: float | None
    focus_height: float | None

    @staticmethod
    def create(
        reader: CsvReader, section_title: str, next_section_title: str
    ) -> Measurements:
        assert_not_none(
            reader.drop_until_inclusive(f"^{section_title}"),
            msg=f"Unable to find {section_title} section.",
        )

        lines = list(reader.pop_until(f"^{next_section_title}"))
        # Because we may read over multiple sections of data to get all metadata for this section, there may
        # be varying number of columns. Get the max number of columns, so we can read in all sections without error.
        max_num_cols = max(len(line.split(",")) for line in lines)
        df = assert_not_none(
            reader.lines_as_df(lines, index_col=0, names=range(max_num_cols)),
            msg=f"Unable to parser data for {section_title} section.",
        ).T.dropna(how="all")
        df.columns = df.columns.astype(str).str.lower()
        data = df_to_series_data(df, index=0)

        scan_position = data.get(str, "excitation / emission")
        excitation_wavelength = data.get(str, "excitation wavelength [nm]")

        return Measurements(
            channels=Measurements.create_channels(data),
            number_of_averages=data.get(float, "number of flashes"),
            detector_distance=data.get(
                float, "distance between plate and detector [mm]"
            ),
            scan_position=(
                None
                if scan_position is None
                else assert_not_none(
                    constants.SCAN_POSITION_CONVERSION.get(scan_position),
                    msg=f"'{scan_position}' is not a valid scan position, expected TOP or BOTTOM.",
                )
            ),
            emission_wavelength=data.get(float, "emission wavelength [nm]"),
            excitation_wavelength=(
                None
                if excitation_wavelength is None
                else try_float_or_none(excitation_wavelength.removesuffix("nm"))
            ),
            focus_height=data.get(float, "focus height [µm]"),
        )

    @staticmethod
    def create_channels(data: SeriesData) -> list[Channel]:
        # Get all channel keys
        values = {
            key: data.series.get(key)
            for key in [
                "channel",
                "excitation wavelength [nm]",
                "excitation power [%]",
                "exposure time [ms]",
                "additional focus offset [mm]",
            ]
        }
        if values["channel"] is None:
            return []

        # Convert series values (multiple Channels == pd.Series, single Channel == str) to lists.
        channel_values: dict[str, list[str]] = {}
        if isinstance(values["channel"], str):
            for key, value in values.items():
                if not isinstance(value, str):
                    raise AllotropeConversionError(constants.CHANNEL_COLUMNS_ERROR)
                channel_values[key] = [value]
        elif isinstance(values["channel"], pd.Series):
            for key, value in values.items():
                if not isinstance(value, pd.Series):
                    raise AllotropeConversionError(constants.CHANNEL_COLUMNS_ERROR)
                channel_values[key] = list(value.values)
                if not len(channel_values["channel"]) == len(channel_values[key]):
                    raise AllotropeConversionError(constants.CHANNEL_COLUMNS_ERROR)

        return [
            Channel.create(
                name=channel_values["channel"][i],
                excitation_wavelength=channel_values["excitation wavelength [nm]"][i],
                excitation_power=channel_values["excitation power [%]"][i],
                exposure_time=channel_values["exposure time [ms]"][i],
                additional_focus_offset=channel_values["additional focus offset [mm]"][
                    i
                ],
            )
            for i in range(len(channel_values["channel"]))
        ]


@dataclass(frozen=True)
class Data:
    version: str
    background_info: BackgroundInfo
    results: Results
    analysis_results: list[AnalysisResult]
    measurement_info: MeasurementInfo
    platemap: Platemap
    measurements: Measurements

    def iter_wells(self) -> Iterator[tuple[str, str]]:
        yield from self.results.data.items()

    def get_sample_identifier(self, well_position: str) -> str:
        platemap_value = self.platemap.get(well_position)
        return (
            f"{self.results.barcode}_{well_position}"
            if platemap_value in ("-", None)
            else platemap_value
        )


def create_metadata(data: Data, file_path: str) -> Metadata:
    return Metadata(
        file_name=Path(file_path).name,
        unc_path=file_path,
        software_name=constants.SOFTWARE_NAME,
        software_version=data.version,
        device_identifier=constants.DEVICE_IDENTIFIER,
        model_number=constants.MODEL_NUMBER,
        product_manufacturer=constants.PRODUCT_MANUFACTURER,
        equipment_serial_number=data.measurement_info.instrument_serial_number,
    )


def _create_measurement(data: Data, well_position: str, well_value: str) -> Measurement:
    experiment_type = data.background_info.experiment_type

    if experiment_type is ExperimentType.ABSORBANCE:
        assert_not_none(
            data.measurements.number_of_averages,
            msg="Unable to find number of averages",
        )

    detector_wavelength_setting = (
        data.measurements.emission_wavelength
        if experiment_type is ExperimentType.FLUORESCENCE
        else (
            data.measurements.excitation_wavelength
            if experiment_type is ExperimentType.ABSORBANCE
            else None
        )
    )
    measurement_value = try_float(well_value, f"result well at '{well_position}'")

    return Measurement(
        type_=experiment_type.measurement_type,
        identifier=random_uuid_str(),
        device_type=experiment_type.device_type,
        detection_type=experiment_type.detection_type
        or data.background_info.experiment_type_value,
        sample_identifier=data.get_sample_identifier(well_position),
        location_identifier=well_position,
        well_plate_identifier=data.results.barcode,
        sample_role_type=data.platemap.get_sample_role_type(well_position),
        number_of_averages=data.measurements.number_of_averages,
        detector_distance_setting=data.measurements.detector_distance,
        scan_position_setting=data.measurements.scan_position,
        detector_wavelength_setting=detector_wavelength_setting,
        excitation_wavelength_setting=data.measurements.excitation_wavelength,
        fluorescence=measurement_value
        if experiment_type is ExperimentType.FLUORESCENCE
        else None,
        absorbance=measurement_value
        if experiment_type is ExperimentType.ABSORBANCE
        else None,
        luminescence=measurement_value
        if experiment_type is ExperimentType.LUMINESCENCE
        else None,
    )


def _create_optical_measurement(
    data: Data, well_position: str, channel: Channel
) -> Measurement:
    return Measurement(
        type_=data.background_info.experiment_type.measurement_type,
        identifier=random_uuid_str(),
        device_type=data.background_info.experiment_type.device_type,
        detection_type=data.background_info.experiment_type.detection_type
        or data.background_info.experiment_type_value,
        sample_identifier=data.get_sample_identifier(well_position),
        location_identifier=well_position,
        well_plate_identifier=data.results.barcode,
        sample_role_type=data.platemap.get_sample_role_type(well_position),
        detector_distance_setting=data.measurements.focus_height,
        excitation_wavelength_setting=channel.excitation_wavelength,
        magnification_setting=constants.MAGNIFICATION_SETTING,
        exposure_duration_setting=channel.exposure_duration,
        illumination_setting=channel.illumination,
        illumination_setting_unit="%",
        transmitted_light_setting=channel.transmitted_light,
        fluorescent_tag_setting=channel.fluorescent_tag,
    )


def _create_measurements(
    data: Data, well_position: str, well_value: str
) -> list[Measurement]:
    if data.background_info.experiment_type is ExperimentType.OPTICAL_IMAGING:
        return [
            _create_optical_measurement(data, well_position, channel)
            for channel in data.measurements.channels
        ]
    else:
        return [_create_measurement(data, well_position, well_value)]


def create_measurement_groups(data: Data) -> list[MeasurementGroup]:
    return [
        MeasurementGroup(
            measurement_time=data.measurement_info.measurement_time,
            plate_well_count=data.results.plate_well_count,
            experiment_type=data.background_info.experiment_type_value,
            analytical_method_identifier=data.measurement_info.protocol_signature,
            experimental_data_identifier=data.measurement_info.measurement_signature,
            measurements=_create_measurements(data, well_position, well_value),
            processed_data=ProcessedData(
                features=[
                    ImageFeature(
                        identifier=random_uuid_str(),
                        feature=analysis_result.analysis_parameter,
                        result=analysis_result.get_image_feature_result(well_position),
                        data_sources=[
                            DataSource(
                                identifier=well_value,
                                # TODO(nstender): I'm not sure what this original comment means, investigate.
                                feature="image feature",  # wait for actual value
                            )
                        ],
                    )
                    for analysis_result in data.analysis_results
                ]
            ),
            images=[
                ImageSource(identifier=well_value),
            ]
            if data.background_info.experiment_type is ExperimentType.OPTICAL_IMAGING
            else None,
        )
        for well_position, well_value in data.iter_wells()
    ]
