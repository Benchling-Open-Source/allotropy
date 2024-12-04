from pathlib import Path
from typing import Any

from allotropy.allotrope.models.shared.definitions.definitions import (
    FieldComponentDatatype,
)
from allotropy.allotrope.schema_mappers.adm.liquid_chromatography.benchling._2023._09.liquid_chromatography import (
    DataCube,
    DataCubeComponent,
    Measurement,
    MeasurementGroup,
    Metadata,
    Peak,
)
from allotropy.exceptions import AllotropeConversionError
from allotropy.parsers.benchling_empower import constants
from allotropy.parsers.constants import NOT_APPLICABLE
from allotropy.parsers.utils.uuids import random_uuid_str
from allotropy.parsers.utils.values import assert_not_none, try_float, try_float_or_none


def create_metadata(metadata: dict[str, Any], first_injection: dict[str, Any], file_path: str) -> Metadata:
    return Metadata(
        asset_management_identifier=metadata.get("SystemName", NOT_APPLICABLE),
        analyst=metadata.get("SampleSetAcquiredBy", NOT_APPLICABLE),
        device_type=constants.DEVICE_TYPE,
        software_name=constants.SOFTWARE_NAME,
        software_version=first_injection.get("AcqSWVersion"),
        file_name=Path(file_path).name,
        unc_path=file_path,
        description=metadata.get("SystemComments", metadata.get("SampleSetComments")),
        product_manufacturer=constants.PRODUCT_MANUFACTURER,
    )


def _get_chromatogram(injection: dict[str, Any]) -> DataCube | None:
    chrom: list[list[float]] | None = injection.get("chrom")
    if not chrom:
        return None
    if len(chrom) != 2:
        msg = "Expected chrom to have two lists"
        raise AllotropeConversionError(msg)

    dimensions, measures = chrom

    # ASM expects chromatogram absorbance in mAU, convert units if different.
    detection_unit = injection["DetUnits"]
    if detection_unit == "AU":
        measures = [m * 1000 for m in measures]
    elif detection_unit != "mAU":
        msg = f"Unexpected Chromatogram detection unit: {detection_unit}"
        raise AllotropeConversionError(msg)

    return DataCube(
        label="absorbance",
        structure_dimensions=[
            DataCubeComponent(
                type_=FieldComponentDatatype.float,
                concept="retention time",
                unit="s",
            )
        ],
        structure_measures=[
            DataCubeComponent(
                type_=FieldComponentDatatype.float,
                concept="absorbance",
                unit="mAU",
            )
        ],
        dimensions=[dimensions],
        measures=[measures],
    )


def _create_measurement(injection: dict[str, Any]) -> Measurement:
    peaks: list[dict[str, Any]] = injection.get("peaks")
    return Measurement(
        measurement_identifier=random_uuid_str(),
        sample_identifier=assert_not_none(injection.get("SampleName"), "SampleName"),
        chromatography_serial_num=injection.get("ColumnSerialNumber"),
        autosampler_injection_volume_setting=injection["InjectionVolume"],
        injection_identifier=injection["InjectionId"],
        injection_time=injection["DateAcquired"],
        peaks=[
            Peak(
                start=try_float(peak.get("StartTime"), "StartTime"),
                start_unit="s",
                end=try_float(peak.get("EndTime"), "EndTime"),
                end_unit="s",
                area=try_float_or_none(peak.get("Area")),
                area_unit="mAU.s",
                relative_area=try_float_or_none(peak.get("PctArea")),
                width=try_float_or_none(peak.get("Width")),
                relative_width=try_float_or_none(peak.get("PctWidth")),
                height=try_float_or_none(peak.get("Height")),
                height_unit="mAU",
                relative_height=try_float_or_none(peak.get("PctHeight")),
                retention_time=try_float_or_none(peak.get("RetentionTime")),
                written_name=peak.get("PeakLabel")
            )
            for peak in peaks
        ],
        chromatogram_data_cube=_get_chromatogram(injection)
    )


def create_measurement_groups(injections: dict[str, dict[str, Any]]) -> MeasurementGroup:
    return [
        MeasurementGroup(
            measurements=[_create_measurement(injection) for injection in injections]
        )
    ]
