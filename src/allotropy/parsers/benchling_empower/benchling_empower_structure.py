from collections import defaultdict
from pathlib import Path
from typing import Any

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
from allotropy.parsers.utils.uuids import random_uuid_str
from allotropy.parsers.utils.values import assert_not_none, try_float, try_float_or_none


def create_metadata(
    metadata: dict[str, Any],
    first_injection: dict[str, Any],
    file_path: str,
    instrument_methods: list[dict[str, Any]] | None = None,
    processing_methods: list[dict[str, Any]] | None = None,
) -> Metadata:
    data_system_custom_info = {
        "account_identifier": metadata.get("username"),
        "database": metadata.get("db"),
        "project": metadata.get("project"),
        "password": metadata.get("password"),
        "SystemCreateDate": metadata.get("SystemCreateDate"),
        "SystemComments": metadata.get("SystemComments"),
        "Node": metadata.get("Node"),
        "SampleSetName": metadata.get("SampleSetName"),
        "SampleSetType": metadata.get("SampleSetType"),
    }

    # Prepare device system custom info for instrument methods
    device_system_custom_info = {}

    # Process instrument methods if available
    if instrument_methods and len(instrument_methods) > 0:
        # Extract only the first instrument method as per requirements
        method = instrument_methods[0]
        id_value = method.get("id")
        device_system_custom_info["instrument_methods_id"] = (
            str(id_value) if id_value is not None else None
        )
        name_value = method.get("name")
        device_system_custom_info["instrument_methods_name"] = (
            str(name_value) if name_value is not None else None
        )
        comments_value = method.get("comments")
        device_system_custom_info["instrument_methods_comments"] = (
            str(comments_value) if comments_value is not None else None
        )
        date_value = method.get("date")
        device_system_custom_info["instrument_methods_date"] = (
            str(date_value) if date_value is not None else None
        )
        inst_on_status_value = method.get("InstOnStatus")
        device_system_custom_info["instrument_methods_InstOnStatus"] = (
            str(inst_on_status_value) if inst_on_status_value is not None else None
        )
        type_value = method.get("type")
        device_system_custom_info["instrument_methods_type"] = (
            str(type_value) if type_value is not None else None
        )

    # Process processing methods if available
    if processing_methods and len(processing_methods) > 0:
        # Extract only the first processing method
        proc_method = processing_methods[0]
        locked_value = proc_method.get("locked")
        device_system_custom_info["processing_methods_locked"] = (
            str(locked_value) if locked_value is not None else None
        )
        modified_by_value = proc_method.get("modified_by")
        device_system_custom_info["processing_methods_modified_by"] = (
            str(modified_by_value) if modified_by_value is not None else None
        )
        name_value = proc_method.get("name")
        device_system_custom_info["processing_methods_name"] = (
            str(name_value) if name_value is not None else None
        )
        revision_comment_value = proc_method.get("revision comment")
        device_system_custom_info["processing_methods_revision_comment"] = (
            str(revision_comment_value) if revision_comment_value is not None else None
        )
        revision_history_value = proc_method.get("revision history")
        device_system_custom_info["processing_methods_revision_history"] = (
            str(revision_history_value) if revision_history_value is not None else None
        )
        version_value = proc_method.get("version")
        device_system_custom_info["processing_methods_version"] = (
            str(version_value) if version_value is not None else None
        )

    return Metadata(
        asset_management_identifier=metadata.get("SystemName", NOT_APPLICABLE),
        analyst=metadata.get("SampleSetAcquiredBy", NOT_APPLICABLE),
        data_system_instance_identifier=metadata.get("SystemName", NOT_APPLICABLE),
        software_name=constants.SOFTWARE_NAME,
        software_version=first_injection.get("AcqSWVersion"),
        file_name=Path(file_path).name,
        unc_path=file_path,
        product_manufacturer=constants.PRODUCT_MANUFACTURER,
        device_system_custom_info=device_system_custom_info,
        data_system_custom_info=data_system_custom_info,
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


def _create_peak(peak: dict[str, Any]) -> Peak | None:
    if peak["PeakType"] in ["Missing", "Group"]:
        return None

    # Area and height are reported in μV, but are reported in ASM as mAU
    # For Empower software, 1V == 1AU, so we just need to convert μ to m
    if (area := try_float_or_none(peak.get("Area"))) is not None:
        area /= 1000
    if (height := try_float_or_none(peak.get("Height"))) is not None:
        height /= 1000
    # Times are reported in minutes by Empower - convert to seconds
    if (retention_time := try_float_or_none(peak.get("RetentionTime"))) is not None:
        retention_time *= 60

    custom_info = {
        "IntType": peak.get("IntType"),
        "PeakType": peak.get("PeakType"),
        "Slope": peak.get("Slope"),
        "StartHeight": peak.get("StartHeight"),
        "EndHeight": peak.get("EndHeight"),
        "InflectionWidth": peak.get("InflectionWidth"),
        "PointsAcrossPeak": peak.get("PointsAcrossPeak"),
        "Offset": peak.get("Offset"),
        "PctAdjustedArea": peak.get("PctAdjustedArea"),
        "PeakCodes": peak.get("PeakCodes"),
        "ICH_AdjArea": peak.get("ICH_AdjArea"),
        "ICHThreshold": peak.get("ICHThreshold"),
        "ImpurityType": peak.get("ImpurityType"),
        "NG_FinalResult": peak.get("NG_FinalResult"),
        "NG_RS_AdjAreaPct": peak.get("NG_RS_AdjAreaPct"),
        "RS_AdjAreaPct": peak.get("RS_AdjAreaPct"),
        "RS_FinalResult": peak.get("RS_FinalResult"),
        "UnnamedRS_AdjAreaPct": peak.get("UnnamedRS_AdjAreaPct"),
        "UnnamedRS_FinalResult": peak.get("UnnamedRS_FinalResult"),
        "AdjArea": peak.get("AdjArea"),
        "AdjAreaPct": peak.get("AdjAreaPct"),
        "FinalResult": peak.get("FinalResult"),
        "2ndDerivativeApex": peak.get("2ndDerivativeApex"),
        "CorrectedArea~": peak.get("CorrectedArea~"),
    }

    # Extract baseline values and convert from minutes to seconds
    baseline_start = try_float_or_none(peak.get("BaselineStart"))
    baseline_end = try_float_or_none(peak.get("BaselineEnd"))

    if baseline_start is not None:
        baseline_start *= 60  # Convert from minutes to seconds

    if baseline_end is not None:
        baseline_end *= 60  # Convert from minutes to seconds

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
        height_unit="mAU",
        relative_height=try_float_or_none(peak.get("PctHeight")),
        written_name=peak.get("Name"),
        relative_peak_analyte_amount=try_float_or_none(peak.get("PctAmount")),
        peak_analyte_amount=try_float_or_none(peak.get("Amount")),
        index=str(try_float_or_none(peak.get("PeakCounter"))),
        baseline_value_at_start_of_peak=baseline_start,
        baseline_value_at_end_of_peak=baseline_end,
        relative_corrected_peak_area=try_float_or_none(peak.get("CorrectedArea~")),
        custom_info=custom_info,
    )


def _create_measurements(
    injection: dict[str, Any], metadata_fields: dict[str, Any]
) -> list[Measurement]:
    peaks: list[dict[str, Any]] = injection.get("peaks", [])
    results: list[dict[str, Any]] = injection.get("results", [])
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

    # Get measurement time values from metadata_fields
    measurement_time = metadata_fields.get("SampleSetStartDate")

    measurement_custom_info = {
        "Comments": injection.get("Comments"),
        "measurement_end_time": metadata_fields.get("SampleSetFinishDate"),
        "DateAcquired": injection.get("DateAcquired"),
        "RunTime": injection.get("RunTime"),
    }

    device_control_custom_info = {
        "SolventA": injection.get("SolventA"),
        "SolventB": injection.get("SolventB"),
        "SolventC": injection.get("SolventC"),
        "SolventD": injection.get("SolventD"),
        "ChannelDescription": injection.get("ChannelDescription"),
        "ChannelType": injection.get("ChannelType"),
        "ChannelStatus": injection.get("ChannelStatus"),
        "DataStart": injection.get("DataStart"),
        "DataEnd": injection.get("DataEnd"),
        "CirculationNo": injection.get("CirculationNo"),
        "device acquisition method": injection.get("AcqMethodSet"),
        "total measurement duration setting": try_float_or_none(
            injection.get("RunTime")
        ),
        "Channel": injection.get("Channel"),
        "ScaletouV": injection.get("ScaletouV"),
        "SecondChannelId": injection.get("SecondChannelId"),
    }

    device_control_docs = [
        DeviceControlDoc(
            device_type=constants.DEVICE_TYPE,
            device_identifier=str(injection.get("ChannelId")),
            detector_sampling_rate_setting=try_float_or_none(
                injection.get("SamplingRate")
            ),
            device_control_custom_info=device_control_custom_info,
        )
    ]

    data_processing_doc = None
    if results and len(results) > 0:
        result = results[0]

        processing_custom_info = {
            "integration_algorithm_type": result.get("IntegrationAlgorithm"),
            "data_processing_method": result.get("ProcessingMethod"),
            "data_processing_time": result.get("DateProcessed"),
            "peak_width": try_float_or_none(result.get("PeakWidth")),
            "retention_time": try_float_or_none(result.get("RetentionTime")),
            "retention_time_window_width": try_float_or_none(result.get("RTWindow")),
            "relative_response": try_float_or_none(result.get("RelativeResponse")),
            "CalculationType": result.get("CalculationType"),
            "CalibrationId": result.get("CalibrationId"),
            "ProcessingLocked": result.get("ProcessingLocked"),
            "Manual": result.get("Manual"),
            "ProcessedBy": result.get("ProcessedBy"),
            "ProcessedAs": result.get("ProcessedAs"),
            "UseForPrecision": result.get("UseForPrecision"),
            "PrepType": result.get("PrepType"),
            "AnalysisMethod": result.get("AnalysisMethod"),
            "IntegrationSystemPolicies": result.get("IntegrationSystemPolicies"),
            "ProcessingMethodId": result.get("ProcessingMethodId"),
            "ProcessedChannelType": result.get("ProcessedChannelType"),
            "ProcessedChanDesc": result.get("ProcessedChanDesc"),
            "PeakRatioReference": result.get("PeakRatioReference"),
            "Threshold": result.get("Threshold"),
            "SourceSoftwareInfo": result.get("SourceSoftwareInfo"),
            "SampleValuesUsedinCalculations": result.get(
                "SampleValuesUsedinCalculations"
            ),
            "NumOfResultsStored": result.get("NumOfResultsStored"),
            "NumOfProcessOnlySampleSets": result.get("NumOfProcessOnlySampleSets"),
            "Factor1": result.get("Factor1"),
            "Factor2": result.get("Factor2"),
            "Factor3": result.get("Factor3"),
            "Factor1Operator": result.get("Factor1Operator"),
            "Factor2Operator": result.get("Factor2Operator"),
            "Factor3Operator": result.get("Factor3Operator"),
            "ResultSetId": result.get("ResultSetId"),
            "ResultSetName": result.get("ResultSetName"),
            "ResultSetDate": result.get("ResultSetDate"),
            "ResultId": result.get("ResultId"),
            "ResultType": result.get("ResultType"),
            "ResultComments": result.get("ResultComments"),
            "ResultCodes": result.get("ResultCodes"),
            "ResultNum": result.get("ResultNum"),
            "ResultSampleSetMethod": result.get("ResultSampleSetMethod"),
            "ResultSource": result.get("ResultSource"),
            "ResultSuperseded": result.get("ResultSuperseded"),
            "TotalArea": result.get("TotalArea"),
            "TotalAdjArea": result.get("TotalAdjArea"),
            "AdjustedTotalArea": result.get("AdjustedTotalArea"),
            "TotalRS_AdjAreaPct": result.get("TotalRS_AdjAreaPct"),
            "TotalRS_FinalResult": result.get("TotalRS_FinalResult"),
            "Largest_NG_RS_AdjAreaPct": result.get("Largest_NG_RS_AdjAreaPct"),
            "LargestNamedRS_FinalResult": result.get("LargestNamedRS_FinalResult"),
            "LargestRS_FinalResult": result.get("LargestRS_FinalResult"),
            "LargestUnnamedRS_FinalResult": result.get("LargestUnnamedRS_FinalResult"),
            "Total_ICH_AdjArea": result.get("Total_ICH_AdjArea"),
            "PercentUnknowns": result.get("PercentUnknowns"),
            "NumberofImpurityPeaks": result.get("NumberofImpurityPeaks"),
            "Faults": result.get("Faults"),
        }

        # Create data processing doc
        data_processing_doc = DataProcessing(
            custom_info=processing_custom_info,
        )

    # Prepare sample custom info
    sample_custom_info = {
        "SampleConcentration": injection.get("SampleConcentration"),
        "ELN_SampleID": injection.get("ELN_SampleID"),
        "PrepType": injection.get("PrepType"),
        "SampleSetAcquiring": injection.get("SampleSetAcquiring"),
        "SampleSetAltered": injection.get("SampleSetAltered"),
        "SampleSetCurrentId": injection.get("SampleSetCurrentId"),
        "OriginalSampleSetId": injection.get("OriginalSampleSetId"),
        "OriginalVialId": injection.get("OriginalVialId"),
        "Vial": injection.get("Vial"),
        "lot_number": injection.get("Lot"),
        "sample_weight": try_float_or_none(injection.get("SampleWeight")),
        "Label": injection.get("Label"),
        "VialId": injection.get("VialId"),
        "VialIdResult": injection.get("VialIdResult"),
        "SampleType": injection.get("SampleType"),
        "dilution_factor_setting": try_float_or_none(injection.get("Dilution")),
    }

    # Prepare injection custom info
    injection_custom_info = {
        "InjectionStatus": injection.get("InjectionStatus"),
        "InjectionType": injection.get("InjectionType"),
        "Injection": injection.get("Injection"),
        "Volume": injection.get("Volume"),
    }

    return [
        Measurement(
            measurement_identifier=random_uuid_str(),
            sample_identifier=assert_not_none(
                injection.get("SampleName"), "SampleName"
            ),
            batch_identifier=str(metadata_fields.get("sample_set_id")),
            sample_role_type=sample_role_type,
            written_name=injection.get("Label"),
            chromatography_serial_num=injection.get("ColumnSerialNumber")
            or NOT_APPLICABLE,
            autosampler_injection_volume_setting=injection["InjectionVolume"],
            injection_identifier=str(injection["InjectionId"]),
            injection_time=injection["DateAcquired"],
            peaks=[peak for peak in [_create_peak(peak) for peak in peaks] if peak],
            chromatogram_data_cube=_get_chromatogram(injection),
            device_control_docs=device_control_docs,
            measurement_time=measurement_time,
            location_identifier=str(injection.get("VialId"))
            if injection.get("VialId") is not None
            else None,
            flow_rate=try_float_or_none(injection.get("FlowRate")),
            measurement_custom_info=measurement_custom_info,
            data_processing_doc=data_processing_doc,
            sample_custom_info=sample_custom_info,
            injection_custom_info=injection_custom_info,
        )
    ]


def create_measurement_groups(
    injections: list[dict[str, Any]], metadata_fields: dict[str, Any]
) -> list[MeasurementGroup]:
    sample_to_injection: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
    for injection in injections:
        sample_to_injection[
            assert_not_none(injection.get("SampleName"), "SampleName")
        ].append(injection)

    measurement_aggregate_custom_info = {
        "Node": metadata_fields.get("Node"),
        "measurement_method_identifier": metadata_fields.get("SampleSetMethod"),
        "SampleSetName": metadata_fields.get("SampleSetName"),
        "SampleSetType": metadata_fields.get("SampleSetType"),
        "SampleSetComments": metadata_fields.get("SampleSetComments"),
    }

    return [
        MeasurementGroup(
            measurements=[
                measurement
                for injection in sample_injections
                for measurement in _create_measurements(injection, metadata_fields)
            ],
            measurement_aggregate_custom_info={
                "Altered": sample_injections[0].get("Altered"),
                "ELN_DocumentID": sample_injections[0].get("ELN_DocumentID"),
                "ELN_SectionGUID": sample_injections[0].get("ELN_SectionGUID"),
                "InstrumentMethodName": sample_injections[0].get(
                    "InstrumentMethodName"
                ),
                "InstrumentMethodId": sample_injections[0].get("InstrumentMethodId"),
                "SSM_Pattern": sample_injections[0].get("SSM_Pattern"),
                "Superseded": sample_injections[0].get("Superseded"),
                "SummaryFaults": sample_injections[0].get("SummaryFaults"),
                **measurement_aggregate_custom_info,
            },
        )
        for sample_injections in sample_to_injection.values()
    ]
