from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, cast

import pandas as pd

from allotropy.parsers.constants import NOT_APPLICABLE
from allotropy.parsers.utils.json import JsonData
from allotropy.parsers.utils.strict_xml_element import StrictXmlElement
from allotropy.parsers.utils.values import (
    assert_not_none,
    try_float_or_none,
    try_int_or_none,
)
from allotropy.types import DictType


def _extract_from_xml_data(
    xml_data: StrictXmlElement | DictType | None, key: str = "value"
) -> str | None:
    """Extract a value from either StrictXmlElement or dictionary structure.

    Unified function that handles both XML element and dictionary structures,
    supporting extraction of any key (value, min, max, etc.).

    Handles structures like:
    Dictionary:
    - {"value": "25"} -> "25"
    - {"value": {"#text": "25"}} -> "25"
    - {"value": {"@IsUndefined": "False", "#text": "25"}} -> "25"
    - {"min": "4", "max": "45"} -> "4" or "45"

    StrictXmlElement:
    - <element value="25"/> -> "25"
    - <element><value>25</value></element> -> "25"
    - <element><value IsUndefined="False">25</value></element> -> "25"
    - <element min="4" max="45"/> -> "4" or "45"

    Args:
        xml_data: Either a StrictXmlElement or dictionary structure
        key: The name of the key/element/attribute to extract (default: "value")

    Returns:
        The extracted value as a string, or None if not found
    """
    if xml_data is None:
        return None

    # Handle StrictXmlElement
    if isinstance(xml_data, StrictXmlElement):
        value = xml_data.get_attr_or_none(key)
        if value is not None:
            return str(value)

        child_element = xml_data.find_or_none(key)
        if child_element is not None:
            text_value = child_element.get_text_or_none()
            if text_value is not None:
                return str(text_value)

            attr_value = child_element.get_attr_or_none("value")
            if attr_value is not None:
                return str(attr_value)

        # If key is "value" and no value found, try getting text content directly
        if key == "value":
            text_value = xml_data.get_text_or_none()
            if text_value is not None:
                return str(text_value)

        return None

    if isinstance(xml_data, dict):
        value = xml_data.get(key)
        if value is None:
            return None

        # Handle different value types
        if isinstance(value, str | int | float):
            return str(value)
        elif isinstance(value, dict):
            # If value is a dict with #text, extract the text
            value_dict = cast(dict[str, Any], value)
            text_content = value_dict.get("#text")
            if text_content is not None:
                return str(text_content)
            return str(value_dict)
        else:
            return str(value)

    return None


@dataclass(frozen=True)
class LigandImmobilization:
    flow_cell_index: int
    ligand: str | None
    immob_file_path: str | None
    immob_date_time: str | None
    level: float | None
    comment: str | None


@dataclass(frozen=True)
class ChipData:
    sensor_chip_identifier: str
    sensor_chip_type: str | None
    number_of_flow_cells: int | None
    number_of_spots: int | None
    lot_number: str | None
    immobilizations: list[LigandImmobilization]
    custom_info: dict[str, Any]

    @staticmethod
    def create(chip_data: DictType) -> ChipData:
        json_data = JsonData(dict(chip_data))

        immobilizations: list[LigandImmobilization] = []
        # Collect entries like Ligand{fc},1, Level{fc},1, ImmobFile{fc},1, ImmobDate{fc},1, Comment{fc},1
        num_flow_cells = json_data.get(int, "NoFcs", 0)
        for flow_cell in range(1, num_flow_cells + 1):
            if flow_cell < 1:
                continue
            ligand = json_data.get(str, f"Ligand{flow_cell},1")
            immob_file_path = json_data.get(str, f"ImmobFile{flow_cell},1")
            immob_date_time = json_data.get(str, f"ImmobDate{flow_cell},1")
            level = json_data.get(float, f"Level{flow_cell},1")
            comment = json_data.get(str, f"Comment{flow_cell},1")
            immobilizations.append(
                LigandImmobilization(
                    flow_cell_index=flow_cell,
                    ligand=ligand,
                    immob_file_path=immob_file_path,
                    immob_date_time=immob_date_time,
                    level=level,
                    comment=comment,
                )
            )

        sensor_chip_identifier = json_data[str, "Id", "Chip ID not found"]
        sensor_chip_type = json_data.get(str, "Name")
        number_of_flow_cells = json_data.get(int, "NoFcs")
        number_of_spots = json_data.get(int, "NoSpots")
        lot_number = json_data.get(str, "LotNo")

        custom_info = {
            "display name": json_data.get(str, "DisplayName"),
            "IFC": json_data.get(str, "IFC"),
            "IFC Description": json_data.get(str, "IFCDesc"),
            "First Dock Date": json_data.get(str, "FirstDockDate"),
            "Last Use Time": json_data.get(str, "LastUseTime"),
            "Last Modified Time": json_data.get(str, "LastModTime"),
            "Number of Flow Cells": json_data.get(str, "NoFcs"),
            "Number of Spots": json_data.get(str, "NoSpots"),
        }

        # Add any remaining unread fields to preserve all data
        custom_info.update(json_data.get_unread())
        custom_info = {k: v for k, v in custom_info.items() if v is not None}

        return ChipData(
            sensor_chip_identifier=sensor_chip_identifier,
            sensor_chip_type=sensor_chip_type,
            number_of_flow_cells=number_of_flow_cells,
            number_of_spots=number_of_spots,
            lot_number=lot_number,
            immobilizations=immobilizations,
            custom_info=custom_info,
        )


@dataclass(frozen=True)
class DetectionConfig:
    detection: str | None = None
    detection_dual: str | None = None
    detection_multi: str | None = None
    flow_cell_single: str | None = None
    flow_cell_dual: str | None = None
    flow_cell_multi: str | None = None
    unread_detection_data: dict[str, Any] = field(default_factory=dict)

    @staticmethod
    def create(detection: DictType | None) -> DetectionConfig:
        if detection is None:
            return DetectionConfig()

        json_data = JsonData(dict(detection))

        return DetectionConfig(
            detection=json_data.get(str, "Detection"),
            detection_dual=json_data.get(str, "DetectionDual"),
            detection_multi=json_data.get(str, "DetectionMulti"),
            flow_cell_single=json_data.get(str, "FlowCellSingle"),
            flow_cell_dual=json_data.get(str, "FlowCellDual"),
            flow_cell_multi=json_data.get(str, "FlowCellMulti"),
            unread_detection_data=json_data.get_unread(),
        )


@dataclass(frozen=True)
class RunMetadata:
    analyst: str | None = None
    compartment_temperature: float | None = None
    baseline_flow: float | None = None
    data_collection_rate: float | None = None
    molecule_weight_unit: str | None = None
    detection_config: DetectionConfig | None = None
    buffer_volume: float | None = None
    rack_temperature_min: float | None = None
    rack_temperature_max: float | None = None
    analysis_temperature: float | None = None
    prime: bool | None = None
    normalize: bool | None = None
    timestamp: str | None = None

    @staticmethod
    def create(application_template_details: DictType | None) -> RunMetadata:
        if application_template_details is None:
            return RunMetadata()
        props = application_template_details.get("properties", {})
        return RunMetadata(
            analyst=props.get("User"),
            compartment_temperature=try_float_or_none(
                _extract_value_from_xml_element_or_dict(
                    application_template_details.get("RackTemperature", {})
                )
            ),
            baseline_flow=try_float_or_none(
                _extract_value_from_xml_element_or_dict(
                    application_template_details.get("BaselineFlow", {})
                )
            ),
            data_collection_rate=try_float_or_none(
                _extract_value_from_xml_element_or_dict(
                    application_template_details.get("DataCollectionRate", {})
                )
            ),
            molecule_weight_unit=_extract_value_from_xml_element_or_dict(
                application_template_details.get("MoleculeWeightUnit", {})
            ),
            detection_config=DetectionConfig.create(
                application_template_details.get("detection")
            ),
            buffer_volume=try_float_or_none(
                (application_template_details.get("prepare_run", {}) or {}).get(
                    "BufferAVolume"
                )
            ),
            rack_temperature_min=try_float_or_none(
                _extract_min_from_xml_data(
                    application_template_details.get("RackTemperature", {})
                )
                or application_template_details.get("RackTemperatureMin")
            ),
            rack_temperature_max=try_float_or_none(
                _extract_max_from_xml_data(
                    application_template_details.get("RackTemperature", {})
                )
                or application_template_details.get("RackTemperatureMax")
            ),
            analysis_temperature=try_float_or_none(
                (application_template_details.get("system_preparations", {}) or {}).get(
                    "AnalTemp"
                )
            ),
            prime=(
                application_template_details.get("system_preparations", {}) or {}
            ).get("Prime"),
            normalize=(
                application_template_details.get("system_preparations", {}) or {}
            ).get("Normalize"),
            timestamp=props.get("Timestamp"),
        )


@dataclass(frozen=True)
class SystemInformation:
    application_name: str | None
    application_version: str | None
    user_name: str | None
    system_controller_identifier: str | None
    os_type: str | None
    os_version: str | None
    measurement_time: str | None
    unread_system_data: dict[str, Any] = field(default_factory=dict)
    unread_application_properties: dict[str, Any] = field(default_factory=dict)

    @staticmethod
    def create(
        system_information: DictType | None, application_properties: DictType | None
    ) -> SystemInformation:
        system_info_data = JsonData(dict(system_information or {}))
        app_props_data = JsonData(dict(application_properties or {}))

        # Get measurement time from either source, preferring application properties
        measurement_time = app_props_data.get(str, "Timestamp") or system_info_data.get(
            str, "Timestamp"
        )

        return SystemInformation(
            application_name=system_info_data.get(str, "Application"),
            application_version=system_info_data.get(str, "Version"),
            user_name=system_info_data.get(str, "UserName"),
            system_controller_identifier=system_info_data.get(
                str, "SystemControllerId"
            ),
            os_type=system_info_data.get(str, "OSType"),
            os_version=system_info_data.get(str, "OSVersion"),
            measurement_time=measurement_time,
            unread_system_data=system_info_data.get_unread(skip={"HtmlPreview"}),
            unread_application_properties=app_props_data.get_unread(
                skip={"HtmlPreview"}
            ),
        )


@dataclass(frozen=True)
class CycleData:
    cycle_number: int
    sensorgram_data: pd.DataFrame
    report_point_data: pd.DataFrame | None = None

    @staticmethod
    def create(cycle_dict: DictType) -> CycleData:
        # Handle both old format (with DataFrames) and new format (with file paths)
        sensorgram_data = cycle_dict.get("sensorgram_data")
        if sensorgram_data is None:
            # If no DataFrame provided, create a minimal one for compatibility
            import pandas as pd

            sensorgram_data = pd.DataFrame(
                {
                    "Flow Cell Number": [1, 1],
                    "Cycle Number": [cycle_dict.get("cycle_number", 1)] * 2,
                    "Time (s)": [0.0, 1.0],
                    "Sensorgram (RU)": [0.0, 0.0],
                }
            )

        return CycleData(
            cycle_number=assert_not_none(
                cycle_dict.get("cycle_number"), "cycle_number"
            ),
            sensorgram_data=sensorgram_data,
            report_point_data=cycle_dict.get("report_point_data"),
        )


@dataclass(frozen=True)
class DipSweep:
    flow_cell: str
    sweep_row: str
    response: list[int]


@dataclass(frozen=True)
class DipData:
    count: int
    timestamp: str
    norm_data: list[DipSweep]
    raw_data: list[DipSweep]

    @staticmethod
    def create(dip_dict: DictType | None) -> DipData | None:
        if dip_dict is None:
            return None

        def _make(entries: list[DictType]) -> list[DipSweep]:
            return [
                DipSweep(
                    flow_cell=e["flow_cell"],
                    sweep_row=e["sweep_row"],
                    response=list(e["response"]),
                )
                for e in entries
            ]

        return DipData(
            count=int(dip_dict.get("count", 0)),
            timestamp=assert_not_none(dip_dict.get("timestamp"), "dip.timestamp"),
            norm_data=_make(dip_dict.get("norm_data", [])),
            raw_data=_make(dip_dict.get("raw_data", [])),
        )


@dataclass(frozen=True)
class FitQuality:
    chi2_value: float | None
    chi2_units: str | None

    @staticmethod
    def create(fq: DictType | None) -> FitQuality:
        if not fq or "Chi2" not in fq:
            return FitQuality(None, None)
        chi2 = fq["Chi2"]
        return FitQuality(try_float_or_none(chi2.get("value")), chi2.get("units"))


@dataclass(frozen=True)
class Parameter:
    name: str
    value: float | None
    error: float | None
    units: str | None


@dataclass(frozen=True)
class CalculatedValue:
    name: str
    value: float | None
    units: str | None


@dataclass(frozen=True)
class KineticResult:
    fit_quality: FitQuality
    parameters: list[Parameter] = field(default_factory=list)
    calculated: list[CalculatedValue] = field(default_factory=list)

    @staticmethod
    def create(result_dict: DictType) -> KineticResult:
        fit_quality = FitQuality.create(result_dict.get("fit_quality"))
        params = [
            Parameter(
                name=key,
                value=try_float_or_none(val.get("value")),
                error=try_float_or_none(val.get("error")),
                units=val.get("units"),
            )
            for key, val in (result_dict.get("parameters", {}) or {}).items()
        ]
        calcs = [
            CalculatedValue(
                name=key,
                value=try_float_or_none(val.get("value")),
                units=val.get("units"),
            )
            for key, val in (result_dict.get("calculated", {}) or {}).items()
        ]
        return KineticResult(
            fit_quality=fit_quality, parameters=params, calculated=calcs
        )


@dataclass(frozen=True)
class KineticAnalysis:
    results_by_identifier: dict[str, KineticResult]

    @staticmethod
    def create(ka_dict: DictType | None) -> KineticAnalysis | None:
        if not ka_dict:
            return None
        return KineticAnalysis(
            results_by_identifier={
                k: KineticResult.create(v) for k, v in ka_dict.items()
            }
        )


@dataclass(frozen=True)
class Data:
    run_metadata: RunMetadata
    chip_data: ChipData
    system_information: SystemInformation
    total_cycles: int
    cycle_data: list[CycleData]
    dip: DipData | None
    kinetic_analysis: KineticAnalysis | None
    sample_data: Any | None
    application_template_details: DictType | None = None

    @staticmethod
    def create(intermediate_structured_data: DictType) -> Data:
        app_details: DictType | None = intermediate_structured_data.get(
            "application_template_details"
        )
        system_info: DictType | None = intermediate_structured_data.get(
            "system_information"
        )
        chip: DictType = intermediate_structured_data.get(
            "chip",
            {
                "Id": "N/A",
                "Name": None,
                "NoFcs": 4,
                "NoSpots": None,
                "LotNo": None,
            },
        )
        cycles_raw: list[DictType] = intermediate_structured_data.get("cycle_data", [])
        return Data(
            run_metadata=RunMetadata.create(app_details),
            chip_data=ChipData.create(chip),
            system_information=SystemInformation.create(
                system_info, (app_details or {}).get("properties")
            ),
            total_cycles=try_int_or_none(
                intermediate_structured_data.get("total_cycles")
            )
            or 0,
            cycle_data=[CycleData.create(c) for c in cycles_raw],
            dip=DipData.create(intermediate_structured_data.get("dip")),
            kinetic_analysis=KineticAnalysis.create(
                intermediate_structured_data.get("kinetic_analysis")
            ),
            sample_data=intermediate_structured_data.get("sample_data", NOT_APPLICABLE),
            application_template_details=app_details,
        )


# Convenience functions for common use cases
def _extract_value_from_xml_element_or_dict(
    xml_data: StrictXmlElement | DictType | None, value_name: str = "value"
) -> str | None:
    """Extract value from either StrictXmlElement or dictionary structure.

    This function serves as a bridge between the old xmltodict-based approach
    and the new StrictXmlElement approach.

    Args:
        xml_data: Either a StrictXmlElement or dictionary structure
        value_name: The name of the value element/attribute to look for

    Returns:
        The extracted value as a string, or None if not found
    """
    return _extract_from_xml_data(xml_data, value_name)


def _extract_min_from_xml_data(
    xml_data: StrictXmlElement | DictType | None,
) -> str | None:
    """Extract min value from either StrictXmlElement or dictionary structure."""
    return _extract_from_xml_data(xml_data, "min")


def _extract_max_from_xml_data(
    xml_data: StrictXmlElement | DictType | None,
) -> str | None:
    """Extract max value from either StrictXmlElement or dictionary structure."""
    return _extract_from_xml_data(xml_data, "max")
