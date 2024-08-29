from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from enum import Enum
import logging
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
from allotropy.parsers.lines_reader import CsvReader
from allotropy.parsers.revvity_kaleido import constants
from allotropy.parsers.utils.pandas import SeriesData
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
    def from_str(experiment_type: str) -> ExperimentType:
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
        # TODO: this is weird
        if self is ExperimentType.OPTICAL_IMAGING:
            return "optical-imaging"
        elif self is ExperimentType.FLUORESCENCE:
            return self.value
        return None


class Version(Enum):
    V2 = "2.0"
    V3 = "3.0"


@dataclass
class BackgroundInfo:
    experiment_type: ExperimentType
    experiment_type_value: str

    def __init__(self, experiment_type_value: str) -> None:
        self.experiment_type_value = experiment_type_value
        self.experiment_type = ExperimentType.from_str(experiment_type_value)


@dataclass(frozen=True)
class Results:
    barcode: str
    data: dict[str, str]

    @property
    def plate_well_count(self) -> int:
        return len(self.data)


@dataclass(frozen=True)
class AnalysisResult:
    analysis_parameter: str
    results: dict[str, str]

    @staticmethod
    def create(reader: CsvReader) -> AnalysisResult | None:
        barcode_line = assert_not_none(
            reader.drop_until_inclusive("^Barcode:(.+),"),
            msg="Unable to find background information.",
        )

        analysis_parameter = None
        for element in barcode_line.split(","):
            if re.search("^.+:.+$", element):
                key, value = element.split(":", maxsplit=1)
                if "AnalysisParameter" in key:
                    analysis_parameter = value
                    break

        analysis_parameter = assert_not_none(
            analysis_parameter,
            msg="Unable to find analysis parameter in Analysis Results section.",
        )

        try:
            results_df = assert_not_none(
                reader.pop_csv_block_as_df(header=0, index_col=0),
                msg="Unable to find results table.",
            )
        except AllotropeParsingError:
            logging.warning(
                f"Unable to read analysis result '{analysis_parameter}'. Ignoring"
            )
            return None

        for column in results_df:
            if str(column).startswith("Unnamed"):
                results_df = results_df.drop(columns=column)

        results = {
            f"{row}{col}": str(values[col])
            for row, values in results_df.iterrows()
            for col in results_df.columns
        }

        a1_value = str(
            assert_not_none(
                results.get("A1"),
                msg=f"Unable to find first position of analysis result '{analysis_parameter}'.",
            )
        )

        # if first value is not a valid float value the results are not useful
        if try_float_or_none(a1_value) is None:
            return None

        return AnalysisResult(
            analysis_parameter=analysis_parameter,
            results=results,
        )

    def get_result(self, well_position: str) -> str:
        return str(
            assert_not_none(
                self.results.get(str(well_position)),
                msg=f"Unable to get well at position '{well_position}' from analysis result '{self.analysis_parameter}'.",
            )
        )

    def get_image_feature_result(self, well_position: str) -> float:
        return try_float(
            self.get_result(well_position),
            f"analysis result '{self.analysis_parameter}' at '{well_position}'",
        )


@dataclass(frozen=True)
class MeasurementInfo:
    instrument_serial_number: str
    measurement_time: str
    protocol_signature: str
    measurement_signature: str

    @staticmethod
    def create(elements: dict[str, str]) -> MeasurementInfo:
        instrument_serial_number = assert_not_none(
            elements.get("Instrument Serial Number"),
            msg="Unable to find Instrument Serial Number in Measurement Information section.",
        )

        measurement_time = assert_not_none(
            elements.get("Measurement Started"),
            msg="Unable to find Measurement time in Measurement Information section.",
        )

        protocol_signature = assert_not_none(
            elements.get("Protocol Signature"),
            msg="Unable to find Protocol Signature in Measurement Information section.",
        )

        measurement_signature = assert_not_none(
            elements.get("Measurement Signature"),
            msg="Unable to find Measurement Signature in Measurement Information section.",
        )

        return MeasurementInfo(
            instrument_serial_number,
            measurement_time,
            protocol_signature,
            measurement_signature,
        )


@dataclass(frozen=True)
class Platemap:
    data: dict[str, str]

    def get_well_value(self, well_position: str) -> str:
        return str(
            assert_not_none(
                self.data.get(well_position),
                msg=f"Unable to get well at position '{well_position}' from platemap section.",
            )
        )

    def get_sample_role_type(self, well_position: str) -> SampleRoleType | None:
        raw_value = self.get_well_value(well_position)
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
class MeasurementElement:
    title: str
    value: str


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
    def check_element_title(element: MeasurementElement, expected_title: str) -> None:
        if element.title != expected_title:
            msg = f"Expected to get '{expected_title}' but '{element.title}' was found."
            raise AllotropeConversionError(msg)

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
            excitation_wavelength=try_float(excitation_wavelength.removesuffix("nm"), "excitation wavelength"),
            illumination=try_float(excitation_power, "excitation power"),
            exposure_duration=try_float(exposure_time, "exposure time"),
            additional_focus_offset=try_float(additional_focus_offset, "additional focus offset"),
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
    def create_channels(data: SeriesData) -> list[Channel]:
        values: dict[str, str | pd.Series | None] = {
            key: data.series.get(key)
            for key in ["Channel", "Excitation wavelength [nm]", "Excitation Power [%]", "Exposure Time [ms]", "Additional Focus offset [mm]"]
        }
        if values["Channel"] is None:
            return None

        channel_values: dict[str, list[str]] = {}
        CHANNEL_COLUMNS_ERROR = "Expected every Channel be followed by: Excitation wavelength [nm], Excitation Power [%], Exposure Time [ms], Additional Focus offset [mm]"
        if isinstance(values["Channel"], str):
            for key, value in values.items():
                if not isinstance(value, str):
                    raise AllotropeConversionError(CHANNEL_COLUMNS_ERROR)
                channel_values[key] = [value]
        elif isinstance(values["Channel"], pd.Series):
            for key, value in values.items():
                if not isinstance(value, pd.Series):
                    raise AllotropeConversionError(CHANNEL_COLUMNS_ERROR)
                channel_values[key] = list(value.values)
                if not len(channel_values["Channel"]) == len(channel_values[key]):
                    raise AllotropeConversionError(CHANNEL_COLUMNS_ERROR)

        return [
            Channel.create(
                name=channel_values["Channel"][i],
                excitation_wavelength=channel_values["Excitation wavelength [nm]"][i],
                excitation_power=channel_values["Excitation Power [%]"][i],
                exposure_time=channel_values["Exposure Time [ms]"][i],
                additional_focus_offset=channel_values["Additional Focus offset [mm]"][i],
            )
            for i in range(len(channel_values["Channel"]))
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
        platemap_value = self.platemap.get_well_value(well_position)
        return (
            f"{self.results.barcode}_{well_position}"
            if platemap_value == "-"
            else platemap_value
        )


def create_metadata(data: Data, file_name: str) -> Metadata:
    return Metadata(
        file_name=file_name,
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
        assert_not_none(data.measurements.number_of_averages, msg="Unable to find number of averages")

    detector_wavelength_setting = data.measurements.emission_wavelength if experiment_type is ExperimentType.FLUORESCENCE else (data.measurements.excitation_wavelength if experiment_type is ExperimentType.ABSORBANCE else None)
    measurement_value = try_float(well_value, f"result well at '{well_position}'")

    return Measurement(
        type_=experiment_type.measurement_type,
        identifier=random_uuid_str(),
        device_type=experiment_type.device_type,
        detection_type=experiment_type.detection_type or data.background_info.experiment_type_value,
        sample_identifier=data.get_sample_identifier(well_position),
        location_identifier=well_position,
        well_plate_identifier=data.results.barcode,
        sample_role_type=data.platemap.get_sample_role_type(well_position),
        number_of_averages=data.measurements.number_of_averages if experiment_type in (ExperimentType.FLUORESCENCE, ExperimentType.ABSORBANCE) else None,
        detector_distance_setting=data.measurements.focus_height if experiment_type is ExperimentType.OPTICAL_IMAGING else data.measurements.detector_distance,
        scan_position_setting=data.measurements.scan_position if experiment_type is ExperimentType.FLUORESCENCE else None,
        detector_wavelength_setting=detector_wavelength_setting,
        excitation_wavelength_setting=data.measurements.excitation_wavelength if experiment_type is ExperimentType.FLUORESCENCE else None,
        fluorescence=measurement_value if experiment_type is ExperimentType.FLUORESCENCE else None,
        absorbance=measurement_value if experiment_type is ExperimentType.ABSORBANCE else None,
        luminescence=measurement_value if experiment_type is ExperimentType.LUMINESCENCE else None,
    )


def _create_optical_measurement(data: Data, well_position: str, channel: Channel) -> Measurement:
    return Measurement(
        type_=data.background_info.experiment_type.measurement_type,
        identifier=random_uuid_str(),
        device_type=data.background_info.experiment_type.device_type,
        detection_type=data.background_info.experiment_type.detection_type or data.background_info.experiment_type_value,
        sample_identifier=data.get_sample_identifier(well_position),
        location_identifier=well_position,
        well_plate_identifier=data.results.barcode,
        sample_role_type=data.platemap.get_sample_role_type(well_position),
        detector_distance_setting=data.measurements.focus_height,
        excitation_wavelength_setting=channel.excitation_wavelength,
        magnification_setting=4,
        exposure_duration_setting=channel.exposure_duration,
        illumination_setting=channel.illumination,
        illumination_setting_unit="%",
        transmitted_light_setting=channel.transmitted_light,
        fluorescent_tag_setting=channel.fluorescent_tag,
    )


def _create_measurements(data: Data, well_position: str, well_value: str) -> list[Measurement]:
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
                                feature="image feature"  # wait for actual value
                            )
                        ]
                    )
                    for analysis_result in data.analysis_results
                ]
            ),
            images=[
                ImageSource(identifier=well_value),
            ] if data.background_info.experiment_type is ExperimentType.OPTICAL_IMAGING else None,
        )
        for well_position, well_value in data.iter_wells()
    ]
