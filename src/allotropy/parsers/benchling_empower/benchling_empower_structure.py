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
    return {k: v for k, v in d.items() if v is not None and v != ""}


def _extract_data_system_custom_info(metadata_json: JsonData) -> dict[str, Any]:
    return filter_nulls(
        {
            "account_identifier": metadata_json.get(str, "username"),
            "database": metadata_json.get(str, "db"),
            "project": metadata_json.get(str, "project"),
            "password": metadata_json.get(str, "password"),
            "SystemCreateDate": metadata_json.get(str, "SystemCreateDate"),
            "SystemComments": metadata_json.get(str, "SystemComments"),
            "Node": metadata_json.get(str, "Node"),
            "SampleSetName": metadata_json.get(str, "SampleSetName"),
            "SampleSetType": metadata_json.get(str, "SampleSetType"),
        }
    )


def _extract_device_system_custom_info(
    instrument_methods: list[dict[str, Any]]
) -> dict[str, Any]:
    if not instrument_methods or len(instrument_methods) == 0:
        return {}

    method = instrument_methods[0]
    return filter_nulls(
        {
            "instrument_methods_id": method.get("id"),
            "instrument_methods_name": method.get("name"),
            "instrument_methods_comments": method.get("comments"),
            "instrument_methods_date": method.get("date"),
            "instrument_methods_InstOnStatus": method.get("InstOnStatus"),
            "instrument_methods_type": method.get("type"),
        }
    )


def create_metadata(
    metadata_json: JsonData,
    first_injection: JsonData,
    file_path: str,
) -> Metadata:
    data_system_custom_info = _extract_data_system_custom_info(metadata_json)
    device_system_custom_info = _extract_device_system_custom_info(
        metadata_json.data.get("instrument_methods", [])
    )

    software_version = first_injection.get(str, "AcqSWVersion")
    metadata_json.mark_read(
        {
            "OriginalSampleSetId",
            "SampleSetAcquiring",
            "SampleSetAltered",
            "SampleSetCurrentId",
            "instrument_methods",
            "processing_methods",
        }
    )

    return Metadata(
        asset_management_identifier=metadata_json.get(
            str, "SystemName", NOT_APPLICABLE
        ),
        analyst=metadata_json.get(str, "SampleSetAcquiredBy", NOT_APPLICABLE),
        data_system_instance_identifier=metadata_json.get(
            str, "SystemName", NOT_APPLICABLE
        ),
        software_name=constants.SOFTWARE_NAME,
        software_version=software_version,
        file_name=Path(file_path).name,
        unc_path=file_path,
        product_manufacturer=constants.PRODUCT_MANUFACTURER,
        device_system_custom_info=device_system_custom_info,
        data_system_custom_info={
            **data_system_custom_info,
            **metadata_json.get_unread(),
        },
    )


def _convert_chromatogram_units(
    measures: list[float], detection_unit: str
) -> list[float]:
    if detection_unit == "AU":
        return [m * 1000 for m in measures]
    elif detection_unit != "mAU":
        msg = f"Unexpected Chromatogram detection unit: {detection_unit}"
        raise AllotropeConversionError(msg)
    return measures


def _convert_time_units(dimensions: list[float]) -> list[float]:
    # ASM expected chromatogram dimensions (x axis) to be in seconds, but Empower reports it in minutes,
    # so convert here.
    return [t * 60 for t in dimensions]


def _get_chromatogram(injection: JsonData) -> DataCube | None:
    chrom: list[list[float]] | None = injection.data.get("chrom")
    if not chrom:
        return None
    if len(chrom) != 2:
        msg = "Expected chrom to have two lists"
        raise AllotropeConversionError(msg)

    dimensions, measures = chrom

    # Convert units based on ASM expectations
    detection_unit = injection.get(str, "DetUnits")
    if detection_unit is None:
        detection_unit = "mAU"  # Default to mAU if no unit is specified
    measures = _convert_chromatogram_units(measures, detection_unit)
    dimensions = _convert_time_units(dimensions)

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


def _convert_minutes_to_seconds(value: float | None) -> float | None:
    if value is not None:
        return value * 60
    return None


def _convert_peak_area_and_height(
    area: float | None, height: float | None
) -> tuple[float | None, float | None]:
    # Area and height are reported in μV, but are reported in ASM as mAU
    # For Empower software, 1V == 1AU, so we just need to convert μ to m
    if area is not None:
        area /= 1000

    if height is not None:
        height /= 1000

    return area, height


def _extract_peak_custom_info(peak: JsonData) -> dict[str, Any]:
    return filter_nulls(
        {
            "IntType": peak.get(str, "IntType"),
            "PeakType": peak.get(str, "PeakType"),
            "Slope": peak.get(str, "Slope"),
            "StartHeight": peak.get(str, "StartHeight"),
            "EndHeight": peak.get(str, "EndHeight"),
            "InflectionWidth": peak.get(str, "InflectionWidth"),
            "PointsAcrossPeak": peak.get(str, "PointsAcrossPeak"),
            "Offset": peak.get(str, "Offset"),
            "PctAdjustedArea": peak.get(str, "PctAdjustedArea"),
            "PeakCodes": peak.get(str, "PeakCodes"),
            "ICH_AdjArea": peak.get(str, "ICH_AdjArea"),
            "ICHThreshold": peak.get(str, "ICHThreshold"),
            "ImpurityType": peak.get(str, "ImpurityType"),
            "NG_FinalResult": peak.get(str, "NG_FinalResult"),
            "NG_RS_AdjAreaPct": peak.get(str, "NG_RS_AdjAreaPct"),
            "RS_AdjAreaPct": peak.get(str, "RS_AdjAreaPct"),
            "RS_FinalResult": peak.get(str, "RS_FinalResult"),
            "UnnamedRS_AdjAreaPct": peak.get(str, "UnnamedRS_AdjAreaPct"),
            "UnnamedRS_FinalResult": peak.get(str, "UnnamedRS_FinalResult"),
            "AdjArea": peak.get(str, "AdjArea"),
            "AdjAreaPct": peak.get(str, "AdjAreaPct"),
            "FinalResult": peak.get(str, "FinalResult"),
            "2ndDerivativeApex": peak.get(str, "2ndDerivativeApex"),
            "CorrectedArea~": peak.get(str, "CorrectedArea~"),
        }
    )


def _create_peak(peak: JsonData) -> Peak | None:
    peak_type = peak.get(str, "PeakType")
    if peak_type in ["Missing", "Group"]:
        return None

    # Convert area and height from μV to mAU
    area = try_float_or_none(peak.get(str, "Area"))
    height = try_float_or_none(peak.get(str, "Height"))
    area, height = _convert_peak_area_and_height(area, height)

    # Convert times from minutes to seconds
    retention_time = _convert_minutes_to_seconds(
        try_float_or_none(peak.get(str, "RetentionTime"))
    )

    # Extract custom info
    custom_info = _extract_peak_custom_info(peak)

    # Extract baseline and time values and convert from minutes to seconds
    baseline_start = _convert_minutes_to_seconds(
        try_float_or_none(peak.get(str, "BaselineStart"))
    )
    baseline_end = _convert_minutes_to_seconds(
        try_float_or_none(peak.get(str, "BaselineEnd"))
    )

    start_time = _convert_minutes_to_seconds(
        try_float_or_none(peak.get(str, "StartTime"))
    )
    end_time = _convert_minutes_to_seconds(try_float_or_none(peak.get(str, "EndTime")))

    peak_item = Peak(
        identifier=random_uuid_str(),
        # Times are reported in minutes by Empower - convert to seconds
        start=start_time,
        start_unit="s",
        end=end_time,
        end_unit="s",
        retention_time=retention_time,
        area=area,
        area_unit="mAU.s",
        relative_area=try_float_or_none(peak.get(str, "PctArea")),
        width=try_float_or_none(peak.get(str, "Width")),
        width_unit="s",
        height=height,
        height_unit="mAU",
        relative_height=try_float_or_none(peak.get(str, "PctHeight")),
        written_name=peak.get(str, "Name"),
        relative_peak_analyte_amount=try_float_or_none(peak.get(str, "PctAmount")),
        peak_analyte_amount=try_float_or_none(peak.get(str, "Amount")),
        index=str(try_float_or_none(peak.get(str, "PeakCounter"))),
        baseline_value_at_start_of_peak=baseline_start,
        baseline_value_at_end_of_peak=baseline_end,
        relative_corrected_peak_area=try_float_or_none(peak.get(str, "CorrectedArea~")),
        custom_info={**custom_info, **peak.get_unread()},
    )

    return peak_item


def _create_device_control_docs(injection: JsonData) -> list[DeviceControlDoc]:
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

    return [
        DeviceControlDoc(
            device_type=constants.DEVICE_TYPE,
            device_identifier=str(injection.get(str, "ChannelId") or ""),
            detector_sampling_rate_setting=try_float_or_none(
                injection.get(str, "SamplingRate")
            ),
            device_control_custom_info=device_control_custom_info,
        )
    ]


def _get_sample_role_type(sample_type: str | None) -> str | None:
    if not sample_type:
        return None

    sample_role_types = [
        srt.value for srt in SampleRoleType if str(sample_type).lower() in srt.value
    ]
    return (
        sample_role_types[0]
        if len(sample_role_types) > 0
        else SampleRoleType.unknown_sample_role.value
    )


def _extract_measurement_custom_info(
    injection: JsonData, metadata_fields: JsonData
) -> dict[str, Any]:
    return filter_nulls(
        {
            "Comments": injection.get(str, "Comments"),
            "measurement_end_time": metadata_fields.get(str, "SampleSetFinishDate"),
            "DateAcquired": injection.get(str, "DateAcquired"),
            "RunTime": injection.get(str, "RunTime"),
        }
    )


def _extract_sample_custom_info(injection: JsonData) -> dict[str, Any]:
    return filter_nulls(
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


def _extract_injection_custom_info(injection: JsonData) -> dict[str, Any]:
    return filter_nulls(
        {
            "InjectionStatus": injection.get(str, "InjectionStatus"),
            "InjectionType": injection.get(str, "InjectionType"),
            "Injection": injection.get(str, "Injection"),
            "Volume": injection.get(str, "Volume"),
        }
    )


def _build_data_processing_by_method_id(
    processing_methods: list[dict[str, Any]], processing_method_ids: set[str]
) -> defaultdict[str, list[DataProcessing]]:
    data_processing_by_processing_method_id: defaultdict[
        str, list[DataProcessing]
    ] = defaultdict(list)

    for proc_method in processing_methods:
        method_id = proc_method.get("id")

        if method_id and method_id in processing_method_ids:
            proc_method_info = _extract_proc_method_info(proc_method, method_id)

            integration_parameters = proc_method.get("integration_parameters")
            if integration_parameters:
                integration_param_fields = integration_parameters.get("fields")
                if integration_param_fields:
                    proc_method_info.update(integration_param_fields)

            components = proc_method.get("components")
            if components:
                _process_components(
                    components,
                    proc_method_info,
                    data_processing_by_processing_method_id,
                    method_id,
                )

    return data_processing_by_processing_method_id


def _extract_proc_method_info(
    proc_method: dict[str, Any], method_id: str
) -> dict[str, Any]:
    return filter_nulls(
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
            "include_int_std_amounts": proc_method.get("include_int_std_amounts"),
        }
    )


def _process_components(
    components: list[dict[str, Any]],
    proc_method_info: dict[str, Any],
    data_processing_by_method_id: defaultdict[str, list[DataProcessing]],
    method_id: int,
) -> None:
    for component in components:
        fields = component.get("fields")
        if fields:
            fields.update(proc_method_info)
            data_processing_by_method_id[str(method_id)].append(
                DataProcessing(data=filter_nulls(fields))
            )


def _extract_processing_custom_info(result_data: JsonData) -> dict[str, Any]:
    return filter_nulls(
        {
            "integration_algorithm_type": result_data.get(str, "IntegrationAlgorithm"),
            "data_processing_method": result_data.get(str, "ProcessingMethod"),
            "data_processing_time": result_data.get(str, "DateProcessed"),
            "peak_width": try_float_or_none(result_data.get(str, "PeakWidth")),
            "retention_time": try_float_or_none(result_data.get(str, "RetentionTime")),
            "retention_time_window_width": try_float_or_none(
                result_data.get(str, "RTWindow")
            ),
            "relative_response": try_float_or_none(
                result_data.get(str, "RelativeResponse")
            ),
            "CalculationType": result_data.get(str, "CalculationType"),
            "CalibrationId": result_data.get(str, "CalibrationId"),
            "ProcessingLocked": result_data.get(str, "ProcessingLocked"),
            "Manual": result_data.get(str, "Manual"),
            "ProcessedBy": result_data.get(str, "ProcessedBy"),
            "ProcessedAs": result_data.get(str, "ProcessedAs"),
            "UseForPrecision": result_data.get(str, "UseForPrecision"),
            "PrepType": result_data.get(str, "PrepType"),
            "AnalysisMethod": result_data.get(str, "AnalysisMethod"),
            "IntegrationSystemPolicies": result_data.get(
                str, "IntegrationSystemPolicies"
            ),
            "ProcessingMethodId": result_data.get(str, "ProcessingMethodId"),
            "ProcessedChannelType": result_data.get(str, "ProcessedChannelType"),
            "ProcessedChanDesc": result_data.get(str, "ProcessedChanDesc"),
            "PeakRatioReference": result_data.get(str, "PeakRatioReference"),
            "Threshold": result_data.get(str, "Threshold"),
            "SourceSoftwareInfo": result_data.get(str, "SourceSoftwareInfo"),
            "SampleValuesUsedinCalculations": result_data.get(
                str, "SampleValuesUsedinCalculations"
            ),
            "NumOfResultsStored": result_data.get(str, "NumOfResultsStored"),
            "NumOfProcessOnlySampleSets": result_data.get(
                str, "NumOfProcessOnlySampleSets"
            ),
            "Factor1": result_data.get(str, "Factor1"),
            "Factor2": result_data.get(str, "Factor2"),
            "Factor3": result_data.get(str, "Factor3"),
            "Factor1Operator": result_data.get(str, "Factor1Operator"),
            "Factor2Operator": result_data.get(str, "Factor2Operator"),
            "Factor3Operator": result_data.get(str, "Factor3Operator"),
            "ResultSetId": result_data.get(str, "ResultSetId"),
            "ResultSetName": result_data.get(str, "ResultSetName"),
            "ResultSetDate": result_data.get(str, "ResultSetDate"),
            "ResultId": result_data.get(str, "ResultId"),
            "ResultType": result_data.get(str, "ResultType"),
            "ResultComments": result_data.get(str, "ResultComments"),
            "ResultCodes": result_data.get(str, "ResultCodes"),
            "ResultNum": result_data.get(str, "ResultNum"),
            "ResultSampleSetMethod": result_data.get(str, "ResultSampleSetMethod"),
            "ResultSource": result_data.get(str, "ResultSource"),
            "ResultSuperseded": result_data.get(str, "ResultSuperseded"),
            "TotalArea": result_data.get(str, "TotalArea"),
            "TotalAdjArea": result_data.get(str, "TotalAdjArea"),
            "AdjustedTotalArea": result_data.get(str, "AdjustedTotalArea"),
            "TotalRS_AdjAreaPct": result_data.get(str, "TotalRS_AdjAreaPct"),
            "TotalRS_FinalResult": result_data.get(str, "TotalRS_FinalResult"),
            "Largest_NG_RS_AdjAreaPct": result_data.get(
                str, "Largest_NG_RS_AdjAreaPct"
            ),
            "LargestNamedRS_FinalResult": result_data.get(
                str, "LargestNamedRS_FinalResult"
            ),
            "LargestRS_FinalResult": result_data.get(str, "LargestRS_FinalResult"),
            "LargestUnnamedRS_FinalResult": result_data.get(
                str, "LargestUnnamedRS_FinalResult"
            ),
            "Total_ICH_AdjArea": result_data.get(str, "Total_ICH_AdjArea"),
            "PercentUnknowns": result_data.get(str, "PercentUnknowns"),
            "NumberofImpurityPeaks": result_data.get(str, "NumberofImpurityPeaks"),
            "Faults": result_data.get(str, "Faults"),
        }
    )


def _build_processing_items(
    results: list[dict[str, Any]],
    data_processing_by_method_id: defaultdict[str, list[DataProcessing]],
) -> list[ProcessingItem]:
    processing_items = []

    for data in results:
        result_data = JsonData(data)
        processing_custom_info = _extract_processing_custom_info(result_data)
        processing_method_id = result_data.get(str, "ProcessingMethodId")

        processing_custom_info = {
            **processing_custom_info,
            **result_data.get_unread(),
        }

        processing_items.append(
            ProcessingItem(
                custom_info=processing_custom_info,
                data_processing=data_processing_by_method_id.get(
                    processing_method_id or "", []
                ),
            )
        )

    return processing_items


def _create_measurements(
    injection: JsonData,
    metadata_fields: JsonData,
) -> list[Measurement]:
    peaks = injection.data.get("peaks", [])
    results = injection.data.get("results", [])

    sample_type = injection.get(str, "SampleType")
    sample_role_type = _get_sample_role_type(sample_type)
    measurement_time = metadata_fields.get(str, "SampleSetStartDate")

    measurement_custom_info = _extract_measurement_custom_info(
        injection, metadata_fields
    )
    device_control_docs = _create_device_control_docs(injection)

    processing_method_ids = set()
    if results:
        for result_item in results:
            if method_id := result_item.get("ProcessingMethodId"):
                processing_method_ids.add(method_id)

    processing_methods = metadata_fields.data.get("processing_methods", [])
    data_processing_by_method_id = (
        _build_data_processing_by_method_id(processing_methods, processing_method_ids)
        if processing_methods and processing_method_ids
        else defaultdict(list)
    )

    processing_items = _build_processing_items(results, data_processing_by_method_id)

    # Extract more custom info dictionaries
    sample_custom_info = _extract_sample_custom_info(injection)
    injection_custom_info = _extract_injection_custom_info(injection)

    # Get required values
    sample_name = injection[str, "SampleName"]
    injection_id = injection[str, "InjectionId"]
    date_acquired = injection[str, "DateAcquired"]

    vial_id = injection.get(str, "VialId")
    vial_id_str = str(vial_id) if vial_id is not None else None

    injection.mark_read({"chrom", "peaks", "results", "curves"})

    # Create and return the measurement
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
            peaks=[
                peak
                for peak in [_create_peak(JsonData(peak_dict)) for peak_dict in peaks]
                if peak
            ],
            chromatogram_data_cube=_get_chromatogram(injection),
            device_control_docs=device_control_docs,
            measurement_time=measurement_time,
            location_identifier=vial_id_str,
            flow_rate=try_float_or_none(injection.get(str, "FlowRate")),
            measurement_custom_info={
                **measurement_custom_info,
                **injection.get_unread(),
            },
            processed_data=processing_items,
            sample_custom_info=sample_custom_info,
            injection_custom_info=injection_custom_info,
        )
    ]


def _extract_measurement_aggregate_custom_info(
    metadata_fields: JsonData,
) -> dict[str, Any]:
    return filter_nulls(
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


def _extract_group_custom_info(
    first_injection: JsonData, measurement_aggregate_custom_info: dict[str, Any]
) -> dict[str, Any]:
    return filter_nulls(
        {
            "Altered": first_injection.get(str, "Altered"),
            "ELN_DocumentID": first_injection.get(str, "ELN_DocumentID"),
            "ELN_SectionGUID": first_injection.get(str, "ELN_SectionGUID"),
            "InstrumentMethodName": first_injection.get(str, "InstrumentMethodName"),
            "InstrumentMethodId": first_injection.get(str, "InstrumentMethodId"),
            "SSM_Pattern": first_injection.get(str, "SSM_Pattern"),
            "Superseded": first_injection.get(str, "Superseded"),
            "SummaryFaults": first_injection.get(str, "SummaryFaults"),
            **measurement_aggregate_custom_info,
        }
    )


def _group_injections_by_sample(
    injections: list[JsonData],
) -> defaultdict[str, list[JsonData]]:
    sample_to_injection: defaultdict[str, list[JsonData]] = defaultdict(list)

    for injection in injections:
        sample_name = injection[str, "SampleName"]
        sample_to_injection[sample_name].append(injection)

    return sample_to_injection


def create_measurement_groups(
    injections: list[JsonData],
    metadata_fields: JsonData,
) -> list[MeasurementGroup]:
    sample_to_injection = _group_injections_by_sample(injections)
    measurement_aggregate_custom_info = _extract_measurement_aggregate_custom_info(
        metadata_fields
    )

    measurement_groups = []
    for _, sample_injections in sample_to_injection.items():
        if not sample_injections:
            continue

        first_injection = sample_injections[0]
        group_custom_info = _extract_group_custom_info(
            first_injection, measurement_aggregate_custom_info
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
