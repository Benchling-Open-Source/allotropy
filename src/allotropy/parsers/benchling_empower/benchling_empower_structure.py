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
    ProcessingItem,
)
from allotropy.allotrope.schema_mappers.data_cube import DataCube, DataCubeComponent
from allotropy.exceptions import AllotropeConversionError
from allotropy.parsers.benchling_empower import constants
from allotropy.parsers.constants import NOT_APPLICABLE
from allotropy.parsers.utils.json import JsonData
from allotropy.parsers.utils.uuids import random_uuid_str
from allotropy.parsers.utils.values import try_float_or_none

T = TypeVar("T")


def filter_nulls(d: dict[str, Any]) -> dict[str, Any]:
    """Filter out any keys with None values from a dictionary."""
    return {k: v for k, v in d.items() if v is not None}


def create_metadata(
    metadata: JsonData,
    first_injection: JsonData,
    file_path: str,
) -> Metadata:
    data_system_custom_info = filter_nulls(
        {
            "account_identifier": metadata.get(str, "username"),
            "database": metadata.get(str, "db"),
            "project": metadata.get(str, "project"),
            "password": metadata.get(str, "password"),
            "SystemCreateDate": metadata.get(str, "SystemCreateDate"),
            "SystemComments": metadata.get(str, "SystemComments"),
            "Node": metadata.get(str, "Node"),
            "SampleSetName": metadata.get(str, "SampleSetName"),
            "SampleSetType": metadata.get(str, "SampleSetType"),
        }
    )

    device_system_custom_info = {}
    instrument_methods = metadata.data.get("instrument_methods", [])

    if instrument_methods and len(instrument_methods) > 0:
        method = instrument_methods[0]

        device_system_custom_info.update(
            filter_nulls(
                {
                    "instrument_methods_id": method.get("id"),
                    "instrument_methods_name": method.get("name"),
                    "instrument_methods_comments": method.get("comments"),
                    "instrument_methods_date": method.get("date"),
                    "instrument_methods_InstOnStatus": method.get("InstOnStatus"),
                    "instrument_methods_type": method.get("type"),
                }
            )
        )

    return Metadata(
        asset_management_identifier=metadata.get(str, "SystemName", NOT_APPLICABLE),
        analyst=metadata.get(str, "SampleSetAcquiredBy", NOT_APPLICABLE),
        data_system_instance_identifier=metadata.get(str, "SystemName", NOT_APPLICABLE),
        software_name=constants.SOFTWARE_NAME,
        software_version=first_injection.get(str, "AcqSWVersion"),
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
    detection_unit = injection.get("DetUnits")
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
    peak_type = peak.get("PeakType")
    if peak_type in ["Missing", "Group"]:
        return None

    # Area and height are reported in μV, but are reported in ASM as mAU
    # For Empower software, 1V == 1AU, so we just need to convert μ to m
    area = try_float_or_none(peak.get("Area"))
    if area is not None:
        area /= 1000

    height = try_float_or_none(peak.get("Height"))
    if height is not None:
        height /= 1000

    # Times are reported in minutes by Empower - convert to seconds
    retention_time = try_float_or_none(peak.get("RetentionTime"))
    if retention_time is not None:
        retention_time *= 60

    custom_info = filter_nulls(
        {
            "IntType": peak.get("IntType"),
            "PeakType": peak_type,
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
    )

    # Extract baseline values and convert from minutes to seconds
    baseline_start = try_float_or_none(peak.get("BaselineStart"))
    baseline_end = try_float_or_none(peak.get("BaselineEnd"))

    if baseline_start is not None:
        baseline_start *= 60  # Convert from minutes to seconds

    if baseline_end is not None:
        baseline_end *= 60  # Convert from minutes to seconds

    start_time = try_float_or_none(peak.get("StartTime"))
    end_time = try_float_or_none(peak.get("EndTime"))

    if start_time is not None:
        start_time *= 60  # Convert from minutes to seconds

    if end_time is not None:
        end_time *= 60  # Convert from minutes to seconds

    return Peak(
        identifier=random_uuid_str(),
        # Times are reported in minutes by Empower - convert to seconds
        start=start_time,
        start_unit="s",
        end=end_time,
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
    injection: JsonData,
    metadata_fields: JsonData,
) -> list[Measurement]:
    peaks: list[dict[str, Any]] = injection.data.get("peaks", [])
    results: list[dict[str, Any]] = injection.data.get("results", [])
    sample_type = injection.get(str, "SampleType")
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

    measurement_time = metadata_fields.get(str, "SampleSetStartDate")

    measurement_custom_info = filter_nulls(
        {
            "Comments": injection.get(str, "Comments"),
            "measurement_end_time": metadata_fields.get(str, "SampleSetFinishDate"),
            "DateAcquired": injection.get(str, "DateAcquired"),
            "RunTime": injection.get(str, "RunTime"),
        }
    )

    device_control_custom_info = filter_nulls(
        {
            "SolventA": injection.get(str, "SolventA"),
            "SolventB": injection.get(str, "SolventB"),
            "SolventC": injection.get(str, "SolventC"),
            "SolventD": injection.get(str, "SolventD"),
            "ChannelDescription": injection.get(str, "ChannelDescription"),
            "ChannelType": injection.get(str, "ChannelType"),
            "ChannelStatus": injection.get(str, "ChannelStatus"),
            "DataStart": injection.get(str, "DataStart"),
            "DataEnd": injection.get(str, "DataEnd"),
            "CirculationNo": injection.get(str, "CirculationNo"),
            "device acquisition method": injection.get(str, "AcqMethodSet"),
            "total measurement duration setting": try_float_or_none(
                injection.get(str, "RunTime")
            ),
            "Channel": injection.get(str, "Channel"),
            "ScaletouV": injection.get(str, "ScaletouV"),
            "SecondChannelId": injection.get(str, "SecondChannelId"),
        }
    )

    device_control_docs = [
        DeviceControlDoc(
            device_type=constants.DEVICE_TYPE,
            device_identifier=str(injection.get(str, "ChannelId") or ""),
            detector_sampling_rate_setting=try_float_or_none(
                injection.get(str, "SamplingRate")
            ),
            device_control_custom_info=device_control_custom_info,
        )
    ]

    processing_items = []
    data_processing_by_processing_method_id = defaultdict(list)
    processing_method_ids = set()
    processing_methods = metadata_fields.data.get("processing_methods", [])

    if results:
        for result_data in results:
            method_id = result_data.get("ProcessingMethodId")
            if method_id:
                processing_method_ids.add(method_id)

    if processing_methods and processing_method_ids:
        for proc_method in processing_methods:
            method_id = proc_method.get("id")

            if method_id and method_id in processing_method_ids:
                proc_method_info = filter_nulls(
                    {
                        "name": proc_method.get("name"),
                        "version": proc_method.get("version"),
                        "locked": proc_method.get("locked"),
                        "modified_by": proc_method.get("modified_by"),
                        "revision_comment": proc_method.get("revision comment"),
                        "revision_history": proc_method.get("revision history"),
                        "component_nodes": proc_method.get("component_nodes"),
                        "default_result_set": proc_method.get("default_result_set"),
                        "id": method_id,
                        "average_by": proc_method.get("average_by"),
                        "ccal_ref1": proc_method.get("ccal_ref1"),
                        "comments": proc_method.get("comments"),
                        "date": proc_method.get("date"),
                        "include_int_std_amounts": proc_method.get(
                            "include_int_std_amounts"
                        ),
                    }
                )
                integration_parameters = proc_method.get("integration_parameters")
                if integration_parameters:
                    integration_param_fields = integration_parameters.get("fields")
                    if integration_param_fields:
                        proc_method_info.update(integration_param_fields)
                components = proc_method.get("components")
                if components:
                    for component in components:
                        fields = component.get("fields")
                        if fields:
                            fields.update(proc_method_info)
                            data_processing_by_processing_method_id[method_id].append(
                                DataProcessing(data=filter_nulls(fields))
                            )

    if results:
        for result_data in results:
            processing_custom_info = filter_nulls(
                {
                    "integration_algorithm_type": result_data.get(
                        "IntegrationAlgorithm"
                    ),
                    "data_processing_method": result_data.get("ProcessingMethod"),
                    "data_processing_time": result_data.get("DateProcessed"),
                    "peak_width": try_float_or_none(result_data.get("PeakWidth")),
                    "retention_time": try_float_or_none(
                        result_data.get("RetentionTime")
                    ),
                    "retention_time_window_width": try_float_or_none(
                        result_data.get("RTWindow")
                    ),
                    "relative_response": try_float_or_none(
                        result_data.get("RelativeResponse")
                    ),
                    "CalculationType": result_data.get("CalculationType"),
                    "CalibrationId": result_data.get("CalibrationId"),
                    "ProcessingLocked": result_data.get("ProcessingLocked"),
                    "Manual": result_data.get("Manual"),
                    "ProcessedBy": result_data.get("ProcessedBy"),
                    "ProcessedAs": result_data.get("ProcessedAs"),
                    "UseForPrecision": result_data.get("UseForPrecision"),
                    "PrepType": result_data.get("PrepType"),
                    "AnalysisMethod": result_data.get("AnalysisMethod"),
                    "IntegrationSystemPolicies": result_data.get(
                        "IntegrationSystemPolicies"
                    ),
                    "ProcessingMethodId": result_data.get("ProcessingMethodId"),
                    "ProcessedChannelType": result_data.get("ProcessedChannelType"),
                    "ProcessedChanDesc": result_data.get("ProcessedChanDesc"),
                    "PeakRatioReference": result_data.get("PeakRatioReference"),
                    "Threshold": result_data.get("Threshold"),
                    "SourceSoftwareInfo": result_data.get("SourceSoftwareInfo"),
                    "SampleValuesUsedinCalculations": result_data.get(
                        "SampleValuesUsedinCalculations"
                    ),
                    "NumOfResultsStored": result_data.get("NumOfResultsStored"),
                    "NumOfProcessOnlySampleSets": result_data.get(
                        "NumOfProcessOnlySampleSets"
                    ),
                    "Factor1": result_data.get("Factor1"),
                    "Factor2": result_data.get("Factor2"),
                    "Factor3": result_data.get("Factor3"),
                    "Factor1Operator": result_data.get("Factor1Operator"),
                    "Factor2Operator": result_data.get("Factor2Operator"),
                    "Factor3Operator": result_data.get("Factor3Operator"),
                    "ResultSetId": result_data.get("ResultSetId"),
                    "ResultSetName": result_data.get("ResultSetName"),
                    "ResultSetDate": result_data.get("ResultSetDate"),
                    "ResultId": result_data.get("ResultId"),
                    "ResultType": result_data.get("ResultType"),
                    "ResultComments": result_data.get("ResultComments"),
                    "ResultCodes": result_data.get("ResultCodes"),
                    "ResultNum": result_data.get("ResultNum"),
                    "ResultSampleSetMethod": result_data.get("ResultSampleSetMethod"),
                    "ResultSource": result_data.get("ResultSource"),
                    "ResultSuperseded": result_data.get("ResultSuperseded"),
                    "TotalArea": result_data.get("TotalArea"),
                    "TotalAdjArea": result_data.get("TotalAdjArea"),
                    "AdjustedTotalArea": result_data.get("AdjustedTotalArea"),
                    "TotalRS_AdjAreaPct": result_data.get("TotalRS_AdjAreaPct"),
                    "TotalRS_FinalResult": result_data.get("TotalRS_FinalResult"),
                    "Largest_NG_RS_AdjAreaPct": result_data.get(
                        "Largest_NG_RS_AdjAreaPct"
                    ),
                    "LargestNamedRS_FinalResult": result_data.get(
                        "LargestNamedRS_FinalResult"
                    ),
                    "LargestRS_FinalResult": result_data.get("LargestRS_FinalResult"),
                    "LargestUnnamedRS_FinalResult": result_data.get(
                        "LargestUnnamedRS_FinalResult"
                    ),
                    "Total_ICH_AdjArea": result_data.get("Total_ICH_AdjArea"),
                    "PercentUnknowns": result_data.get("PercentUnknowns"),
                    "NumberofImpurityPeaks": result_data.get("NumberofImpurityPeaks"),
                    "Faults": result_data.get("Faults"),
                }
            )

            processing_method_id = result_data.get("ProcessingMethodId")
            processing_items.append(
                ProcessingItem(
                    custom_info=processing_custom_info,
                    data_processing=data_processing_by_processing_method_id.get(
                        processing_method_id
                    ),
                )
            )

    sample_custom_info = filter_nulls(
        {
            "SampleConcentration": injection.get(str, "SampleConcentration"),
            "ELN_SampleID": injection.get(str, "ELN_SampleID"),
            "PrepType": injection.get(str, "PrepType"),
            "SampleSetAcquiring": injection.get(str, "SampleSetAcquiring"),
            "SampleSetAltered": injection.get(str, "SampleSetAltered"),
            "SampleSetCurrentId": injection.get(str, "SampleSetCurrentId"),
            "OriginalSampleSetId": injection.get(str, "OriginalSampleSetId"),
            "OriginalVialId": injection.get(str, "OriginalVialId"),
            "Vial": injection.get(str, "Vial"),
            "lot_number": injection.get(str, "Lot"),
            "sample_weight": try_float_or_none(injection.get(str, "SampleWeight")),
            "Label": injection.get(str, "Label"),
            "VialId": injection.get(str, "VialId"),
            "VialIdResult": injection.get(str, "VialIdResult"),
            "SampleType": injection.get(str, "SampleType"),
            "dilution_factor_setting": try_float_or_none(
                injection.get(str, "Dilution")
            ),
        }
    )

    # Prepare injection custom info
    injection_custom_info = filter_nulls(
        {
            "InjectionStatus": injection.get(str, "InjectionStatus"),
            "InjectionType": injection.get(str, "InjectionType"),
            "Injection": injection.get(str, "Injection"),
            "Volume": injection.get(str, "Volume"),
        }
    )

    sample_name = injection[str, "SampleName"]
    injection_id = injection[str, "InjectionId"]
    date_acquired = injection[str, "DateAcquired"]

    vial_id = injection.get(str, "VialId")
    vial_id_str = str(vial_id) if vial_id is not None else None

    return [
        Measurement(
            measurement_identifier=random_uuid_str(),
            sample_identifier=sample_name,
            batch_identifier=str(metadata_fields.get(str, "sample_set_id") or ""),
            sample_role_type=sample_role_type,
            written_name=injection.get(str, "Label"),
            chromatography_serial_num=injection.get(str, "ColumnSerialNumber")
            or NOT_APPLICABLE,
            autosampler_injection_volume_setting=injection.get(
                float, "InjectionVolume"
            ),
            injection_identifier=str(injection_id),
            injection_time=date_acquired,
            peaks=[peak for peak in [_create_peak(peak) for peak in peaks] if peak],
            chromatogram_data_cube=_get_chromatogram(injection.data),
            device_control_docs=device_control_docs,
            measurement_time=measurement_time,
            location_identifier=vial_id_str,
            flow_rate=try_float_or_none(injection.get(str, "FlowRate")),
            measurement_custom_info=measurement_custom_info,
            processed_data=processing_items,
            sample_custom_info=sample_custom_info,
            injection_custom_info=injection_custom_info,
        )
    ]


def create_measurement_groups(
    injections: list[JsonData],
    metadata_fields: JsonData,
) -> list[MeasurementGroup]:
    sample_to_injection: defaultdict[str, list[JsonData]] = defaultdict(list)

    for injection in injections:
        sample_name = injection[str, "SampleName"]
        sample_to_injection[sample_name].append(injection)

    measurement_aggregate_custom_info = filter_nulls(
        {
            "Node": metadata_fields.get(str, "Node"),
            "measurement_method_identifier": metadata_fields.get(
                str, "SampleSetMethod"
            ),
            "SampleSetName": metadata_fields.get(str, "SampleSetName"),
            "SampleSetType": metadata_fields.get(str, "SampleSetType"),
            "SampleSetComments": metadata_fields.get(str, "SampleSetComments"),
        }
    )

    measurement_groups = []
    for _, sample_injections in sample_to_injection.items():
        if not sample_injections:
            continue

        first_injection = sample_injections[0]

        group_custom_info = filter_nulls(
            {
                "Altered": first_injection.get(str, "Altered"),
                "ELN_DocumentID": first_injection.get(str, "ELN_DocumentID"),
                "ELN_SectionGUID": first_injection.get(str, "ELN_SectionGUID"),
                "InstrumentMethodName": first_injection.get(
                    str, "InstrumentMethodName"
                ),
                "InstrumentMethodId": first_injection.get(str, "InstrumentMethodId"),
                "SSM_Pattern": first_injection.get(str, "SSM_Pattern"),
                "Superseded": first_injection.get(str, "Superseded"),
                "SummaryFaults": first_injection.get(str, "SummaryFaults"),
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
