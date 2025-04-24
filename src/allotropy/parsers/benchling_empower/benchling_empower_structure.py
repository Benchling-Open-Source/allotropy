from collections import defaultdict
from pathlib import Path
from typing import Any, TypeVar

from allotropy.allotrope.models.shared.components.plate_reader import SampleRoleType
from allotropy.allotrope.models.shared.definitions.definitions import (
    FieldComponentDatatype,
)
from allotropy.allotrope.schema_mappers.adm.liquid_chromatography.benchling._2023._09.liquid_chromatography import (
    DataProcessing,
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
from allotropy.parsers.utils.json import JsonData
from allotropy.parsers.utils.uuids import random_uuid_str
from allotropy.parsers.utils.values import assert_not_none, try_float, try_float_or_none

T = TypeVar("T")


def filter_nulls(d: dict[str, Any]) -> dict[str, Any]:
    """Filter out any keys with None values from a dictionary."""
    return {k: v for k, v in d.items() if v is not None}


def create_metadata(
    metadata: dict[str, Any],
    first_injection: dict[str, Any],
    file_path: str,
    instrument_methods: list[dict[str, Any]] | None = None,
    processing_methods: list[dict[str, Any]] | None = None,
) -> Metadata:
    metadata_data = JsonData(metadata)
    first_injection_data = JsonData(first_injection)

    data_system_custom_info = filter_nulls(
        {
            "account_identifier": metadata_data.get(str, "username"),
            "database": metadata_data.get(str, "db"),
            "project": metadata_data.get(str, "project"),
            "password": metadata_data.get(str, "password"),
            "SystemCreateDate": metadata_data.get(str, "SystemCreateDate"),
            "SystemComments": metadata_data.get(str, "SystemComments"),
            "Node": metadata_data.get(str, "Node"),
            "SampleSetName": metadata_data.get(str, "SampleSetName"),
            "SampleSetType": metadata_data.get(str, "SampleSetType"),
        }
    )

    device_system_custom_info = {}

    if instrument_methods and len(instrument_methods) > 0:
        method = JsonData(instrument_methods[0])

        device_system_custom_info.update(
            filter_nulls(
                {
                    "instrument_methods_id": method.get(str, "id"),
                    "instrument_methods_name": method.get(str, "name"),
                    "instrument_methods_comments": method.get(str, "comments"),
                    "instrument_methods_date": method.get(str, "date"),
                    "instrument_methods_InstOnStatus": method.get(bool, "InstOnStatus"),
                    "instrument_methods_type": method.get(str, "type"),
                }
            )
        )

    if processing_methods and len(processing_methods) > 0:
        proc_method = JsonData(processing_methods[0])

        device_system_custom_info.update(
            filter_nulls(
                {
                    "processing_methods_locked": proc_method.get(bool, "locked"),
                    "processing_methods_modified_by": proc_method.get(
                        str, "modified_by"
                    ),
                    "processing_methods_name": proc_method.get(str, "name"),
                    "processing_methods_revision_comment": proc_method.get(
                        str, "revision comment"
                    ),
                    "processing_methods_revision_history": proc_method.get(
                        str, "revision history"
                    ),
                    "processing_methods_version": proc_method.get(str, "version"),
                }
            )
        )

    return Metadata(
        asset_management_identifier=metadata_data.get(
            str, "SystemName", NOT_APPLICABLE
        ),
        analyst=metadata_data.get(str, "SampleSetAcquiredBy", NOT_APPLICABLE),
        data_system_instance_identifier=metadata_data.get(
            str, "SystemName", NOT_APPLICABLE
        ),
        software_name=constants.SOFTWARE_NAME,
        software_version=first_injection_data.get(str, "AcqSWVersion"),
        file_name=Path(file_path).name,
        unc_path=file_path,
        product_manufacturer=constants.PRODUCT_MANUFACTURER,
        device_system_custom_info=device_system_custom_info,
        data_system_custom_info=data_system_custom_info,
    )


def _get_chromatogram(injection: dict[str, Any]) -> DataCube | None:
    injection_data = JsonData(injection)

    chrom: list[list[float]] | None = injection_data.data.get("chrom")
    if not chrom:
        return None
    if len(chrom) != 2:
        msg = "Expected chrom to have two lists"
        raise AllotropeConversionError(msg)

    dimensions, measures = chrom

    # ASM expects chromatogram absorbance in mAU, convert units if different.
    detection_unit = injection_data.get(str, "DetUnits")
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


def _create_peak(peak: dict[str, Any]) -> Peak | None:
    peak_data = JsonData(peak)

    if peak_data.get(str, "PeakType") in ["Missing", "Group"]:
        return None

    # Area and height are reported in μV, but are reported in ASM as mAU
    # For Empower software, 1V == 1AU, so we just need to convert μ to m
    if (area := try_float_or_none(peak_data.get(float, "Area"))) is not None:
        area /= 1000
    if (height := try_float_or_none(peak_data.get(float, "Height"))) is not None:
        height /= 1000
    # Times are reported in minutes by Empower - convert to seconds
    if (
        retention_time := try_float_or_none(peak_data.get(float, "RetentionTime"))
    ) is not None:
        retention_time *= 60

    custom_info = filter_nulls(
        {
            "IntType": peak_data.get(str, "IntType"),
            "PeakType": peak_data.get(str, "PeakType"),
            "Slope": peak_data.get(float, "Slope"),
            "StartHeight": peak_data.get(float, "StartHeight"),
            "EndHeight": peak_data.get(float, "EndHeight"),
            "InflectionWidth": peak_data.get(float, "InflectionWidth"),
            "PointsAcrossPeak": peak_data.get(int, "PointsAcrossPeak"),
            "Offset": peak_data.get(float, "Offset"),
            "PctAdjustedArea": peak_data.get(float, "PctAdjustedArea"),
            "PeakCodes": peak_data.get(str, "PeakCodes"),
            "ICH_AdjArea": peak_data.get(float, "ICH_AdjArea"),
            "ICHThreshold": peak_data.get(float, "ICHThreshold"),
            "ImpurityType": peak_data.get(str, "ImpurityType"),
            "NG_FinalResult": peak_data.get(str, "NG_FinalResult"),
            "NG_RS_AdjAreaPct": peak_data.get(float, "NG_RS_AdjAreaPct"),
            "RS_AdjAreaPct": peak_data.get(float, "RS_AdjAreaPct"),
            "RS_FinalResult": peak_data.get(str, "RS_FinalResult"),
            "UnnamedRS_AdjAreaPct": peak_data.get(float, "UnnamedRS_AdjAreaPct"),
            "UnnamedRS_FinalResult": peak_data.get(str, "UnnamedRS_FinalResult"),
            "AdjArea": peak_data.get(float, "AdjArea"),
            "AdjAreaPct": peak_data.get(float, "AdjAreaPct"),
            "FinalResult": peak_data.get(str, "FinalResult"),
            "2ndDerivativeApex": peak_data.get(float, "2ndDerivativeApex"),
            "CorrectedArea~": peak_data.get(float, "CorrectedArea~"),
        }
    )

    # Extract baseline values and convert from minutes to seconds
    baseline_start = try_float_or_none(peak_data.get(float, "BaselineStart"))
    baseline_end = try_float_or_none(peak_data.get(float, "BaselineEnd"))

    if baseline_start is not None:
        baseline_start *= 60  # Convert from minutes to seconds

    if baseline_end is not None:
        baseline_end *= 60  # Convert from minutes to seconds

    return Peak(
        identifier=random_uuid_str(),
        # Times are reported in minutes by Empower - convert to seconds
        start=try_float(peak_data.get(float, "StartTime"), "StartTime") * 60,
        start_unit="s",
        end=try_float(peak_data.get(float, "EndTime"), "EndTime") * 60,
        end_unit="s",
        retention_time=retention_time,
        area=area,
        area_unit="mAU.s",
        relative_area=try_float_or_none(peak_data.get(float, "PctArea")),
        width=try_float_or_none(peak_data.get(float, "Width")),
        width_unit="s",
        height=height,
        height_unit="mAU",
        relative_height=try_float_or_none(peak_data.get(float, "PctHeight")),
        written_name=peak_data.get(str, "Name"),
        relative_peak_analyte_amount=try_float_or_none(
            peak_data.get(float, "PctAmount")
        ),
        peak_analyte_amount=try_float_or_none(peak_data.get(float, "Amount")),
        index=str(try_float_or_none(peak_data.get(float, "PeakCounter"))),
        baseline_value_at_start_of_peak=baseline_start,
        baseline_value_at_end_of_peak=baseline_end,
        relative_corrected_peak_area=try_float_or_none(
            peak_data.get(float, "CorrectedArea~")
        ),
        custom_info=custom_info,
    )


def _create_measurements(
    injection: dict[str, Any], metadata_fields: dict[str, Any]
) -> list[Measurement]:
    injection_data = JsonData(injection)
    metadata_data = JsonData(metadata_fields)

    # Access raw data for complex types
    peaks: list[dict[str, Any]] = injection_data.data.get("peaks", [])
    results: list[dict[str, Any]] = injection_data.data.get("results", [])
    sample_type = injection_data.get(str, "SampleType")
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

    measurement_time = metadata_data.get(str, "SampleSetStartDate")

    measurement_custom_info = filter_nulls(
        {
            "Comments": injection_data.get(str, "Comments"),
            "measurement_end_time": metadata_data.get(str, "SampleSetFinishDate"),
            "DateAcquired": injection_data.get(str, "DateAcquired"),
            "RunTime": injection_data.get(float, "RunTime"),
        }
    )

    device_control_custom_info = filter_nulls(
        {
            "SolventA": injection_data.get(str, "SolventA"),
            "SolventB": injection_data.get(str, "SolventB"),
            "SolventC": injection_data.get(str, "SolventC"),
            "SolventD": injection_data.get(str, "SolventD"),
            "ChannelDescription": injection_data.get(str, "ChannelDescription"),
            "ChannelType": injection_data.get(str, "ChannelType"),
            "ChannelStatus": injection_data.get(str, "ChannelStatus"),
            "DataStart": injection_data.get(float, "DataStart"),
            "DataEnd": injection_data.get(float, "DataEnd"),
            "CirculationNo": injection_data.get(int, "CirculationNo"),
            "device acquisition method": injection_data.get(str, "AcqMethodSet"),
            "total measurement duration setting": try_float_or_none(
                injection_data.get(str, "RunTime")
            ),
            "Channel": injection_data.get(str, "Channel"),
            "ScaletouV": injection_data.get(float, "ScaletouV"),
            "SecondChannelId": injection_data.get(str, "SecondChannelId"),
        }
    )

    device_control_docs = [
        DeviceControlDoc(
            device_type=constants.DEVICE_TYPE,
            device_identifier=str(injection_data.get(str, "ChannelId")),
            detector_sampling_rate_setting=try_float_or_none(
                injection_data.get(str, "SamplingRate")
            ),
            device_control_custom_info=device_control_custom_info,
        )
    ]

    data_processing_doc = None
    if results and len(results) > 0:
        result = JsonData(results[0])

        processing_custom_info = filter_nulls(
            {
                "integration_algorithm_type": result.get(str, "IntegrationAlgorithm"),
                "data_processing_method": result.get(str, "ProcessingMethod"),
                "data_processing_time": result.get(str, "DateProcessed"),
                "peak_width": try_float_or_none(result.get(str, "PeakWidth")),
                "retention_time": try_float_or_none(result.get(str, "RetentionTime")),
                "retention_time_window_width": try_float_or_none(
                    result.get(str, "RTWindow")
                ),
                "relative_response": try_float_or_none(
                    result.get(str, "RelativeResponse")
                ),
                "CalculationType": result.get(str, "CalculationType"),
                "CalibrationId": result.get(str, "CalibrationId"),
                "ProcessingLocked": result.get(bool, "ProcessingLocked"),
                "Manual": result.get(bool, "Manual"),
                "ProcessedBy": result.get(str, "ProcessedBy"),
                "ProcessedAs": result.get(str, "ProcessedAs"),
                "UseForPrecision": result.get(bool, "UseForPrecision"),
                "PrepType": result.get(str, "PrepType"),
                "AnalysisMethod": result.get(str, "AnalysisMethod"),
                "IntegrationSystemPolicies": result.get(
                    str, "IntegrationSystemPolicies"
                ),
                "ProcessingMethodId": result.get(str, "ProcessingMethodId"),
                "ProcessedChannelType": result.get(str, "ProcessedChannelType"),
                "ProcessedChanDesc": result.get(str, "ProcessedChanDesc"),
                "PeakRatioReference": result.get(str, "PeakRatioReference"),
                "Threshold": result.get(float, "Threshold"),
                "SourceSoftwareInfo": result.get(str, "SourceSoftwareInfo"),
                "SampleValuesUsedinCalculations": result.get(
                    str, "SampleValuesUsedinCalculations"
                ),
                "NumOfResultsStored": result.get(int, "NumOfResultsStored"),
                "NumOfProcessOnlySampleSets": result.get(
                    int, "NumOfProcessOnlySampleSets"
                ),
                "Factor1": result.get(float, "Factor1"),
                "Factor2": result.get(float, "Factor2"),
                "Factor3": result.get(float, "Factor3"),
                "Factor1Operator": result.get(str, "Factor1Operator"),
                "Factor2Operator": result.get(str, "Factor2Operator"),
                "Factor3Operator": result.get(str, "Factor3Operator"),
                "ResultSetId": result.get(str, "ResultSetId"),
                "ResultSetName": result.get(str, "ResultSetName"),
                "ResultSetDate": result.get(str, "ResultSetDate"),
                "ResultId": result.get(str, "ResultId"),
                "ResultType": result.get(str, "ResultType"),
                "ResultComments": result.get(str, "ResultComments"),
                "ResultCodes": result.get(str, "ResultCodes"),
                "ResultNum": result.get(int, "ResultNum"),
                "ResultSampleSetMethod": result.get(str, "ResultSampleSetMethod"),
                "ResultSource": result.get(str, "ResultSource"),
                "ResultSuperseded": result.get(bool, "ResultSuperseded"),
                "TotalArea": result.get(float, "TotalArea"),
                "TotalAdjArea": result.get(float, "TotalAdjArea"),
                "AdjustedTotalArea": result.get(float, "AdjustedTotalArea"),
                "TotalRS_AdjAreaPct": result.get(float, "TotalRS_AdjAreaPct"),
                "TotalRS_FinalResult": result.get(str, "TotalRS_FinalResult"),
                "Largest_NG_RS_AdjAreaPct": result.get(
                    float, "Largest_NG_RS_AdjAreaPct"
                ),
                "LargestNamedRS_FinalResult": result.get(
                    str, "LargestNamedRS_FinalResult"
                ),
                "LargestRS_FinalResult": result.get(str, "LargestRS_FinalResult"),
                "LargestUnnamedRS_FinalResult": result.get(
                    str, "LargestUnnamedRS_FinalResult"
                ),
                "Total_ICH_AdjArea": result.get(float, "Total_ICH_AdjArea"),
                "PercentUnknowns": result.get(float, "PercentUnknowns"),
                "NumberofImpurityPeaks": result.get(int, "NumberofImpurityPeaks"),
                "Faults": result.get(str, "Faults"),
            }
        )

        data_processing_doc = DataProcessing(
            custom_info=processing_custom_info,
        )

    sample_custom_info = filter_nulls(
        {
            "SampleConcentration": injection_data.get(float, "SampleConcentration"),
            "ELN_SampleID": injection_data.get(str, "ELN_SampleID"),
            "PrepType": injection_data.get(str, "PrepType"),
            "SampleSetAcquiring": injection_data.get(bool, "SampleSetAcquiring"),
            "SampleSetAltered": injection_data.get(bool, "SampleSetAltered"),
            "SampleSetCurrentId": injection_data.get(str, "SampleSetCurrentId"),
            "OriginalSampleSetId": injection_data.get(str, "OriginalSampleSetId"),
            "OriginalVialId": injection_data.get(str, "OriginalVialId"),
            "Vial": injection_data.get(str, "Vial"),
            "lot_number": injection_data.get(str, "Lot"),
            "sample_weight": try_float_or_none(injection_data.get(str, "SampleWeight")),
            "Label": injection_data.get(str, "Label"),
            "VialId": injection_data.get(str, "VialId"),
            "VialIdResult": injection_data.get(str, "VialIdResult"),
            "SampleType": injection_data.get(str, "SampleType"),
            "dilution_factor_setting": try_float_or_none(
                injection_data.get(str, "Dilution")
            ),
        }
    )

    # Prepare injection custom info
    injection_custom_info = filter_nulls(
        {
            "InjectionStatus": injection_data.get(str, "InjectionStatus"),
            "InjectionType": injection_data.get(str, "InjectionType"),
            "Injection": injection_data.get(int, "Injection"),
            "Volume": injection_data.get(float, "Volume"),
        }
    )

    # Ensure we have a valid injection_time (required field)
    injection_time = injection_data.get(str, "DateAcquired")
    if injection_time is None:
        injection_time = "unknown"

    return [
        Measurement(
            measurement_identifier=random_uuid_str(),
            sample_identifier=assert_not_none(
                injection_data.get(str, "SampleName"), "SampleName"
            ),
            batch_identifier=str(metadata_data.get(str, "sample_set_id")),
            sample_role_type=sample_role_type,
            written_name=injection_data.get(str, "Label"),
            chromatography_serial_num=injection_data.get(str, "ColumnSerialNumber")
            or NOT_APPLICABLE,
            autosampler_injection_volume_setting=injection_data.get(
                float, "InjectionVolume"
            ),
            injection_identifier=str(injection_data.get(int, "InjectionId")),
            injection_time=injection_time,
            peaks=[peak for peak in [_create_peak(peak) for peak in peaks] if peak],
            chromatogram_data_cube=_get_chromatogram(injection),
            device_control_docs=device_control_docs,
            measurement_time=measurement_time,
            location_identifier=str(injection_data.get(str, "VialId"))
            if injection_data.get(str, "VialId") is not None
            else None,
            flow_rate=try_float_or_none(injection_data.get(str, "FlowRate")),
            measurement_custom_info=measurement_custom_info,
            data_processing_doc=data_processing_doc,
            sample_custom_info=sample_custom_info,
            injection_custom_info=injection_custom_info,
        )
    ]


def create_measurement_groups(
    injections: list[dict[str, Any]], metadata_fields: dict[str, Any]
) -> list[MeasurementGroup]:
    metadata_data = JsonData(metadata_fields)
    sample_to_injection: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)

    for injection in injections:
        injection_data = JsonData(injection)
        sample_to_injection[
            assert_not_none(injection_data.get(str, "SampleName"), "SampleName")
        ].append(injection)

    measurement_aggregate_custom_info = filter_nulls(
        {
            "Node": metadata_data.get(str, "Node"),
            "measurement_method_identifier": metadata_data.get(str, "SampleSetMethod"),
            "SampleSetName": metadata_data.get(str, "SampleSetName"),
            "SampleSetType": metadata_data.get(str, "SampleSetType"),
            "SampleSetComments": metadata_data.get(str, "SampleSetComments"),
        }
    )

    measurement_groups = []
    for _, sample_injections in sample_to_injection.items():
        if not sample_injections:
            continue

        first_injection_data = JsonData(sample_injections[0])

        group_custom_info = filter_nulls(
            {
                "Altered": first_injection_data.get(bool, "Altered"),
                "ELN_DocumentID": first_injection_data.get(str, "ELN_DocumentID"),
                "ELN_SectionGUID": first_injection_data.get(str, "ELN_SectionGUID"),
                "InstrumentMethodName": first_injection_data.get(
                    str, "InstrumentMethodName"
                ),
                "InstrumentMethodId": first_injection_data.get(
                    str, "InstrumentMethodId"
                ),
                "SSM_Pattern": first_injection_data.get(str, "SSM_Pattern"),
                "Superseded": first_injection_data.get(bool, "Superseded"),
                "SummaryFaults": first_injection_data.get(str, "SummaryFaults"),
                **measurement_aggregate_custom_info,
            }
        )

        measurements = [
            measurement
            for injection in sample_injections
            for measurement in _create_measurements(injection, metadata_fields)
        ]

        measurement_groups.append(
            MeasurementGroup(
                measurements=measurements,
                measurement_aggregate_custom_info=group_custom_info,
            )
        )

    return measurement_groups
