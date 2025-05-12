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
    ProcessedData,
)
from allotropy.allotrope.schema_mappers.data_cube import DataCube, DataCubeComponent
from allotropy.exceptions import AllotropeConversionError
from allotropy.parsers.benchling_empower import constants
from allotropy.parsers.constants import NOT_APPLICABLE
from allotropy.parsers.utils.json import JsonData
from allotropy.parsers.utils.uuids import random_uuid_str
from allotropy.parsers.utils.values import try_float_or_none


def filter_nulls(d: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in d.items() if v is not None and v != ""}


def create_metadata(
    metadata_json: JsonData,
    first_injection: JsonData,
    file_path: str,
) -> Metadata:
    data_system_field_mappings = {
        "account_identifier": (str, "username", None),
        "database": (str, "db", None),
        "project": (str, "project", None),
        "password": (str, "password", None),
        "SystemCreateDate": (str, "SystemCreateDate", None),
        "SystemComments": (str, "SystemComments", None),
        "Node": (str, "Node", None),
        "SampleSetName": (str, "SampleSetName", None),
        "SampleSetType": (str, "SampleSetType", None),
    }

    data_system_custom_info = metadata_json.get_keys_as_dict(data_system_field_mappings)

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


def _create_peak(peak: JsonData) -> Peak | None:
    peak_type = peak.get(str, "PeakType")
    if peak_type in ["Missing", "Group"]:
        return None

    area, height = _convert_peak_area_and_height(
        peak.get(float, "Area"), peak.get(float, "Height")
    )
    retention_time = _convert_minutes_to_seconds(
        try_float_or_none(peak.get(str, "RetentionTime"))
    )

    field_mappings = {
        "IntType": (str, "IntType", None),
        "PeakType": (str, "PeakType", None),
        "Slope": (str, "Slope", None),
        "StartHeight": (str, "StartHeight", None),
        "EndHeight": (str, "EndHeight", None),
        "InflectionWidth": (str, "InflectionWidth", None),
        "PointsAcrossPeak": (str, "PointsAcrossPeak", None),
        "Offset": (str, "Offset", None),
        "PctAdjustedArea": (str, "PctAdjustedArea", None),
        "PeakCodes": (str, "PeakCodes", None),
        "ICH_AdjArea": (str, "ICH_AdjArea", None),
        "ICHThreshold": (str, "ICHThreshold", None),
        "ImpurityType": (str, "ImpurityType", None),
        "NG_FinalResult": (str, "NG_FinalResult", None),
        "NG_RS_AdjAreaPct": (str, "NG_RS_AdjAreaPct", None),
        "RS_AdjAreaPct": (str, "RS_AdjAreaPct", None),
        "RS_FinalResult": (str, "RS_FinalResult", None),
        "UnnamedRS_AdjAreaPct": (str, "UnnamedRS_AdjAreaPct", None),
        "UnnamedRS_FinalResult": (str, "UnnamedRS_FinalResult", None),
        "AdjArea": (str, "AdjArea", None),
        "AdjAreaPct": (str, "AdjAreaPct", None),
        "FinalResult": (str, "FinalResult", None),
        "2ndDerivativeApex": (str, "2ndDerivativeApex", None),
        "CorrectedArea~": (str, "CorrectedArea~", None),
    }

    custom_info = peak.get_keys_as_dict(field_mappings, include_unread=True)

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
        index=peak.get(str, "PeakCounter"),
        baseline_value_at_start_of_peak=baseline_start,
        baseline_value_at_end_of_peak=baseline_end,
        relative_corrected_peak_area=try_float_or_none(peak.get(str, "CorrectedArea~")),
        custom_info=custom_info,
    )

    return peak_item


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


def _build_data_processing_by_method_id(
    processing_methods: list[dict[str, Any]], processing_method_ids: set[str]
) -> defaultdict[str, list[dict[str, Any]]]:
    data_processing_by_processing_method_id: defaultdict[
        str, list[dict[str, Any]]
    ] = defaultdict(list)

    for proc_method in processing_methods:
        method_id = proc_method.get("id")

        if method_id and method_id in processing_method_ids:
            proc_json = JsonData(proc_method)
            field_mappings = {
                "name": (str, "name", None),
                "version": (str, "version", None),
                "locked": (str, "locked", None),
                "modified_by": (str, "modified_by", None),
                "revision_comment": (str, "revision comment", None),
                "revision_history": (str, "revision history", None),
                "component_nodes": (str, "component_nodes", None),
                "default_result_set": (str, "default_result_set", None),
                "average_by": (str, "average_by", None),
                "ccal_ref1": (str, "ccal_ref1", None),
                "comments": (str, "comments", None),
                "date": (str, "date", None),
                "include_int_std_amounts": (str, "include_int_std_amounts", None),
            }

            proc_method_info = proc_json.get_keys_as_dict(
                field_mappings,
                skip={"integration_parameters", "components"},
                include_unread=True,
            )

            # Add method_id directly since it doesn't come from get_keys_as_dict
            proc_method_info["id"] = str(method_id)

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


def _process_components(
    components: list[dict[str, Any]],
    proc_method_info: dict[str, Any],
    data_processing_by_method_id: defaultdict[str, list[dict[str, Any]]],
    method_id: int,
) -> None:
    for component in components:
        fields = component.get("fields")
        if fields:
            fields.update(proc_method_info)
            data_processing_by_method_id[str(method_id)].append(filter_nulls(fields))


def _build_processing_items(
    results: list[dict[str, Any]],
    data_processing_by_method_id: defaultdict[str, list[dict[str, Any]]],
) -> list[ProcessedData]:
    processing_items = []

    for data in results:
        result_data = JsonData(data)
        field_mappings = {
            "integration_algorithm_type": (str, "IntegrationAlgorithm", None),
            "data_processing_method": (str, "ProcessingMethod", None),
            "data_processing_time": (str, "DateProcessed", None),
            "peak_width": (float, "PeakWidth", None),
            "retention_time": (float, "RetentionTime", None),
            "retention_time_window_width": (float, "RTWindow", None),
            "relative_response": (float, "RelativeResponse", None),
            "CalculationType": (str, "CalculationType", None),
            "CalibrationId": (str, "CalibrationId", None),
            "ProcessingLocked": (str, "ProcessingLocked", None),
            "Manual": (str, "Manual", None),
            "ProcessedBy": (str, "ProcessedBy", None),
            "ProcessedAs": (str, "ProcessedAs", None),
            "UseForPrecision": (str, "UseForPrecision", None),
            "PrepType": (str, "PrepType", None),
            "AnalysisMethod": (str, "AnalysisMethod", None),
            "IntegrationSystemPolicies": (str, "IntegrationSystemPolicies", None),
            "ProcessingMethodId": (str, "ProcessingMethodId", None),
            "ProcessedChannelType": (str, "ProcessedChannelType", None),
            "ProcessedChanDesc": (str, "ProcessedChanDesc", None),
            "PeakRatioReference": (str, "PeakRatioReference", None),
            "Threshold": (str, "Threshold", None),
            "SourceSoftwareInfo": (str, "SourceSoftwareInfo", None),
            "SampleValuesUsedinCalculations": (
                str,
                "SampleValuesUsedinCalculations",
                None,
            ),
            "NumOfResultsStored": (str, "NumOfResultsStored", None),
            "NumOfProcessOnlySampleSets": (str, "NumOfProcessOnlySampleSets", None),
            "Factor1": (str, "Factor1", None),
            "Factor2": (str, "Factor2", None),
            "Factor3": (str, "Factor3", None),
            "Factor1Operator": (str, "Factor1Operator", None),
            "Factor2Operator": (str, "Factor2Operator", None),
            "Factor3Operator": (str, "Factor3Operator", None),
            "ResultSetId": (str, "ResultSetId", None),
            "ResultSetName": (str, "ResultSetName", None),
            "ResultSetDate": (str, "ResultSetDate", None),
            "ResultId": (str, "ResultId", None),
            "ResultType": (str, "ResultType", None),
            "ResultComments": (str, "ResultComments", None),
            "ResultCodes": (str, "ResultCodes", None),
            "ResultNum": (str, "ResultNum", None),
            "ResultSampleSetMethod": (str, "ResultSampleSetMethod", None),
            "ResultSource": (str, "ResultSource", None),
            "ResultSuperseded": (str, "ResultSuperseded", None),
            "TotalArea": (str, "TotalArea", None),
            "TotalAdjArea": (str, "TotalAdjArea", None),
            "AdjustedTotalArea": (str, "AdjustedTotalArea", None),
            "TotalRS_AdjAreaPct": (str, "TotalRS_AdjAreaPct", None),
            "TotalRS_FinalResult": (str, "TotalRS_FinalResult", None),
            "Largest_NG_RS_AdjAreaPct": (str, "Largest_NG_RS_AdjAreaPct", None),
            "LargestNamedRS_FinalResult": (str, "LargestNamedRS_FinalResult", None),
            "LargestRS_FinalResult": (str, "LargestRS_FinalResult", None),
            "LargestUnnamedRS_FinalResult": (str, "LargestUnnamedRS_FinalResult", None),
            "Total_ICH_AdjArea": (str, "Total_ICH_AdjArea", None),
            "PercentUnknowns": (str, "PercentUnknowns", None),
            "NumberofImpurityPeaks": (str, "NumberofImpurityPeaks", None),
            "Faults": (str, "Faults", None),
        }

        processing_custom_info = result_data.get_keys_as_dict(
            field_mappings, include_unread=True
        )
        processing_method_id = result_data.get(str, "ProcessingMethodId")

        # Use an empty list as default when method_id is None or when it's not in the dictionary
        data_items = []
        if processing_method_id is not None:
            data_items = data_processing_by_method_id.get(processing_method_id, [])

        processing_items.append(
            ProcessedData(
                custom_info=processing_custom_info,
                data=data_items,
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

    # Get measurement custom info
    measurement_custom_info = injection.get_keys_as_dict(
        {
            "Comments": (str, "Comments", None),
            "DateAcquired": (str, "DateAcquired", None),
            "RunTime": (str, "RunTime", None),
        }
    )
    measurement_custom_info.update(
        metadata_fields.get_keys_as_dict(
            {
                "measurement_end_time": (str, "SampleSetFinishDate", None),
            }
        )
    )

    # Create device control docs
    device_control_field_mappings = {
        "SolventA": (str, "SolventA", None),
        "SolventB": (str, "SolventB", None),
        "SolventC": (str, "SolventC", None),
        "SolventD": (str, "SolventD", None),
        "ChannelDescription": (str, "ChannelDescription", None),
        "ChannelType": (str, "ChannelType", None),
        "ChannelStatus": (str, "ChannelStatus", None),
        "DataStart": (str, "DataStart", None),
        "DataEnd": (str, "DataEnd", None),
        "CirculationNo": (str, "CirculationNo", None),
        "device acquisition method": (str, "AcqMethodSet", None),
        "total measurement duration setting": (float, "RunTime", None),
        "Channel": (str, "Channel", None),
        "ScaletouV": (str, "ScaletouV", None),
        "SecondChannelId": (str, "SecondChannelId", None),
    }

    device_control_custom_info = injection.get_keys_as_dict(
        device_control_field_mappings
    )

    instrument_methods = metadata_fields.data.get("instrument_methods", [])
    if instrument_methods:
        instrument_method_id = injection.get(str, "InstrumentMethodId")
        if instrument_method_id:
            for method in instrument_methods:
                method_id = method.get("id")
                if method_id and str(method_id) == str(instrument_method_id):
                    instrument_method_field_mapping = {
                        "device method identifier": (str, "id", None),
                        "name": (str, "name", None),
                        "comments": (str, "comments", None),
                        "methods_date": (str, "date", None),
                        "InstOnStatus": (str, "InstOnStatus", None),
                        "type": (str, "type", None),
                    }
                    temp_json_data = JsonData(method)
                    device_control_custom_info.update(
                        temp_json_data.get_keys_as_dict(
                            instrument_method_field_mapping, include_unread=True
                        )
                    )

    device_control_docs = [
        DeviceControlDoc(
            device_type=constants.DEVICE_TYPE,
            device_identifier=injection.get(str, "ChannelId"),
            detector_sampling_rate_setting=injection.get(float, "SamplingRate"),
            device_control_custom_info=device_control_custom_info,
        )
    ]

    processing_method_ids = set()
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

    # Get sample and injection custom info
    sample_custom_info = injection.get_keys_as_dict(
        {
            "SampleConcentration": (str, "SampleConcentration", None),
            "ELN_SampleID": (str, "ELN_SampleID", None),
            "PrepType": (str, "PrepType", None),
            "SampleSetAcquiring": (str, "SampleSetAcquiring", None),
            "SampleSetAltered": (str, "SampleSetAltered", None),
            "SampleSetCurrentId": (str, "SampleSetCurrentId", None),
            "OriginalSampleSetId": (str, "OriginalSampleSetId", None),
            "OriginalVialId": (str, "OriginalVialId", None),
            "Vial": (str, "Vial", None),
            "lot_number": (str, "Lot", None),
            "sample_weight": (float, "SampleWeight", None),
            "Label": (str, "Label", None),
            "VialId": (str, "VialId", None),
            "VialIdResult": (str, "VialIdResult", None),
            "SampleType": (str, "SampleType", None),
            "dilution_factor_setting": (float, "Dilution", None),
        }
    )

    injection_custom_info = injection.get_keys_as_dict(
        {
            "InjectionStatus": (str, "InjectionStatus", None),
            "InjectionType": (str, "InjectionType", None),
            "Injection": (str, "Injection", None),
            "Volume": (str, "Volume", None),
        }
    )

    # Get required values
    sample_name = injection[str, "SampleName"]
    date_acquired = injection[str, "DateAcquired"]

    injection.mark_read({"chrom", "peaks", "results", "curves"})

    # Create and return the measurement
    return [
        Measurement(
            measurement_identifier=random_uuid_str(),
            sample_identifier=sample_name,
            batch_identifier=metadata_fields.get(str, "sample_set_id"),
            sample_role_type=sample_role_type,
            written_name=injection.get(str, "Label"),
            chromatography_serial_num=injection.get(
                str, "ColumnSerialNumber", NOT_APPLICABLE
            ),
            autosampler_injection_volume_setting=injection.get(
                float, "InjectionVolume"
            ),
            injection_identifier=injection[str, "InjectionId"],
            injection_time=date_acquired,
            peaks=[
                peak
                for peak in [_create_peak(JsonData(peak_dict)) for peak_dict in peaks]
                if peak
            ],
            chromatogram_data_cube=_get_chromatogram(injection),
            device_control_docs=device_control_docs,
            measurement_time=measurement_time,
            location_identifier=injection.get(str, "VialId"),
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

    measurement_aggregate_field_mappings = {
        "Node": (str, "Node", None),
        "measurement_method_identifier": (str, "SampleSetMethod", None),
        "SampleSetName": (str, "SampleSetName", None),
        "SampleSetType": (str, "SampleSetType", None),
        "SampleSetComments": (str, "SampleSetComments", None),
    }

    measurement_aggregate_custom_info = metadata_fields.get_keys_as_dict(
        measurement_aggregate_field_mappings
    )

    measurement_groups = []
    for _, sample_injections in sample_to_injection.items():
        if not sample_injections:
            continue

        first_injection = sample_injections[0]

        group_field_mappings = {
            "Altered": (str, "Altered", None),
            "ELN_DocumentID": (str, "ELN_DocumentID", None),
            "ELN_SectionGUID": (str, "ELN_SectionGUID", None),
            "InstrumentMethodName": (str, "InstrumentMethodName", None),
            "InstrumentMethodId": (str, "InstrumentMethodId", None),
            "SSM_Pattern": (str, "SSM_Pattern", None),
            "Superseded": (str, "Superseded", None),
            "SummaryFaults": (str, "SummaryFaults", None),
        }

        group_custom_info = first_injection.get_keys_as_dict(group_field_mappings)
        group_custom_info.update(measurement_aggregate_custom_info)

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
