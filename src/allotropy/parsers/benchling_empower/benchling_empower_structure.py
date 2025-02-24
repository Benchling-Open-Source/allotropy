from collections import defaultdict
from pathlib import Path
from typing import Any

from allotropy.allotrope.models.shared.components.plate_reader import SampleRoleType
from allotropy.allotrope.models.shared.definitions.definitions import (
    FieldComponentDatatype,
)
from allotropy.allotrope.schema_mappers.adm.liquid_chromatography.benchling._2023._09.liquid_chromatography import (
    DeviceControlDoc,
    Measurement,
    MeasurementGroup,
    Metadata,
    Peak,
)
from allotropy.allotrope.schema_mappers.data_cube import DataCube, DataCubeComponent
from allotropy.exceptions import AllotropeConversionError
from allotropy.parsers.benchling_empower import constants
from allotropy.parsers.constants import NOT_APPLICABLE
from allotropy.parsers.utils.uuids import random_uuid_str
from allotropy.parsers.utils.values import assert_not_none, try_float, try_float_or_none


def create_metadata(
    metadata: dict[str, Any], first_injection: dict[str, Any], file_path: str
) -> Metadata:
    return Metadata(
        asset_management_identifier=metadata.get("SystemName", NOT_APPLICABLE),
        analyst=metadata.get("SampleSetAcquiredBy", NOT_APPLICABLE),
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

    # ASM expected chromatogram dimensions (x axis) to be in seconds, but Empower reports it in minutes,
    # so convert here.
    dimensions = [t * 60 for t in dimensions]

    return DataCube(
        label="absorbance",
        structure_dimensions=[
            DataCubeComponent(
                type_=FieldComponentDatatype.double,
                concept="retention time",
                unit="s",
            )
        ],
        structure_measures=[
            DataCubeComponent(
                type_=FieldComponentDatatype.double,
                concept="absorbance",
                unit="mAU",
            )
        ],
        dimensions=[dimensions],
        measures=[measures],
    )


def _create_peak(peak: dict[str, Any]) -> Peak:
    # Area and height are reported in μV, but are reported in ASM as mAU
    # For Empower software, 1V == 1AU, so we just need to convert μ to m
    if (area := try_float_or_none(peak.get("Area"))) is not None:
        area /= 1000
    if (height := try_float_or_none(peak.get("Height"))) is not None:
        height /= 1000
    # Times are reported in minutes by Empower - convert to seconds
    if (retention_time := try_float_or_none(peak.get("RetentionTime"))) is not None:
        retention_time *= 60

    return Peak(
        identifier=random_uuid_str(),
        # Times are reported in minutes by Empower - convert to seconds
        start=try_float(peak.get("StartTime"), "StartTime") * 60,
        start_unit="s",
        end=try_float(peak.get("EndTime"), "EndTime") * 60,
        end_unit="s",
        retention_time=retention_time,
        area=area,
        area_unit="mAU.s",
        relative_area=try_float_or_none(peak.get("PctArea")),
        width=try_float_or_none(peak.get("Width")),
        width_unit="s",
        height=height,
        relative_height=try_float_or_none(peak.get("PctHeight")),
        written_name=peak.get("Name"),
    )


def _create_measurements(injection: dict[str, Any]) -> list[Measurement]:
    peaks: list[dict[str, Any]] = injection.get("peaks", [])
    sample_type = injection.get("SampleType")
    sample_role_type = None
    if sample_type:
        sample_role_types = [
            srt.value for srt in SampleRoleType if str(sample_type).lower() in srt.value
        ]
        sample_role_type = (
            sample_role_types[0]
            if len(sample_role_types) > 0
            else SampleRoleType.unknown_sample_role.value
        )

    # NOTE: we return a single measurement because we are only have the absorbance data cube measurement at
    # this time, but if there were other measurements to include, we would create multiple measurements here.
    return [
        Measurement(
            measurement_identifier=random_uuid_str(),
            sample_identifier=assert_not_none(
                injection.get("SampleName"), "SampleName"
            ),
            batch_identifier=injection.get("SampleSetID"),
            sample_role_type=sample_role_type,
            written_name=injection.get("Label"),
            chromatography_serial_num=injection.get("ColumnSerialNumber")
            or NOT_APPLICABLE,
            autosampler_injection_volume_setting=injection["InjectionVolume"],
            injection_identifier=str(injection["InjectionId"]),
            injection_time=injection["DateAcquired"],
            peaks=[_create_peak(peak) for peak in peaks],
            chromatogram_data_cube=_get_chromatogram(injection),
            device_control_docs=[DeviceControlDoc(device_type=constants.DEVICE_TYPE)],
        )
    ]


def create_measurement_groups(
    injections: list[dict[str, Any]]
) -> list[MeasurementGroup]:
    sample_to_injection: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    for injection in injections:
        sample_to_injection[
            assert_not_none(injection.get("SampleName"), "SampleName")
        ].append(injection)
    return [
        MeasurementGroup(
            measurements=[
                measurement
                for injection in sample_injections
                for measurement in _create_measurements(injection)
            ]
        )
        for sample_injections in sample_to_injection.values()
    ]
