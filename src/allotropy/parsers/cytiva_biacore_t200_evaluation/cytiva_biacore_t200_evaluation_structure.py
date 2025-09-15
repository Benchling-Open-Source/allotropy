from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pandas as pd

from allotropy.parsers.constants import NOT_APPLICABLE
from allotropy.parsers.utils.strict_xml_element import StrictXmlElement
from allotropy.parsers.utils.values import (
    assert_not_none,
    try_float_or_none,
    try_int_or_none,
)
from allotropy.types import DictType


def _extract_value_from_xml_like_dict(xml_dict: DictType) -> str | None:
    """Extract value from XML-like dictionary structure.

    Handles structures like:
    - {"value": "25"} -> "25"
    - {"value": {"#text": "25"}} -> "25"
    - {"value": {"@IsUndefined": "False", "#text": "25"}} -> "25"
    """
    if not xml_dict:
        return None

    value = xml_dict.get("value")
    if value is None:
        return None

    # If value is a simple string/number, return it
    if isinstance(value, str | int | float):
        return str(value)

    # If value is a dict with #text, extract the text
    if isinstance(value, dict) and "#text" in value:
        return str(value["#text"])

    # If value is a dict but no #text, try to convert to string
    if isinstance(value, dict):
        return str(value)

    return str(value)


def _extract_value_from_xml_element(
    xml_element: StrictXmlElement, value_name: str = "value"
) -> str | None:
    """Extract value from StrictXmlElement structure.

    Handles XML structures like:
    - <element value="25"/> -> "25"
    - <element><value>25</value></element> -> "25"
    - <element><value IsUndefined="False">25</value></element> -> "25"

    Args:
        xml_element: The StrictXmlElement to extract value from
        value_name: The name of the value element/attribute to look for (default: "value")

    Returns:
        The extracted value as a string, or None if not found
    """
    if xml_element is None:
        return None

    # Try to get value as an attribute first
    value = xml_element.get_attr_or_none(value_name)
    if value is not None:
        return str(value)

    # Try to find value as a child element
    value_element = xml_element.find_or_none(value_name)
    if value_element is not None:
        # Check if the value element has text content
        text_value = value_element.get_text_or_none()
        if text_value is not None:
            return str(text_value)

        # If no text, check if it has a value attribute
        attr_value = value_element.get_attr_or_none("value")
        if attr_value is not None:
            return str(attr_value)

    # If no value found in child element, try getting text content directly
    text_value = xml_element.get_text_or_none()
    if text_value is not None:
        return str(text_value)

    return None


def _extract_min_max_from_xml_dict(xml_dict: DictType, key: str) -> str | None:
    """Extract min or max value from XML-like dictionary structure.

    Handles structures like:
    - {"min": "4", "max": "45", "value": {...}} -> "4" or "45"
    """
    if not xml_dict:
        return None

    value = xml_dict.get(key)
    if value is None:
        return None

    # If value is a simple string/number, return it
    if isinstance(value, str | int | float):
        return str(value)

    # If value is a dict with #text, extract the text
    if isinstance(value, dict) and "#text" in value:
        return str(value["#text"])

    return str(value)


def _extract_min_max_from_xml_element(
    xml_element: StrictXmlElement, key: str
) -> str | None:
    """Extract min or max value from StrictXmlElement structure.

    Handles XML structures like:
    - <element min="4" max="45" value="25"/> -> "4" or "45"
    - <element><min>4</min><max>45</max><value>25</value></element> -> "4" or "45"

    Args:
        xml_element: The StrictXmlElement to extract value from
        key: Either "min" or "max"

    Returns:
        The extracted min/max value as a string, or None if not found
    """
    if xml_element is None:
        return None

    # Try to get min/max as an attribute first
    value = xml_element.get_attr_or_none(key)
    if value is not None:
        return str(value)

    # Try to find min/max as a child element
    child_element = xml_element.find_or_none(key)
    if child_element is not None:
        text_value = child_element.get_text_or_none()
        if text_value is not None:
            return str(text_value)

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
    custom_info: DictType

    @staticmethod
    def create(chip_data: DictType) -> ChipData:
        immobilizations: list[LigandImmobilization] = []
        # Collect entries like Ligand{fc},1, Level{fc},1, ImmobFile{fc},1, ImmobDate{fc},1, Comment{fc},1
        for flow_cell in range(1, try_int_or_none(chip_data.get("NoFcs")) or 0 + 1):
            if flow_cell < 1:
                continue
            ligand = chip_data.get(f"Ligand{flow_cell},1")
            immob_file_path = chip_data.get(f"ImmobFile{flow_cell},1")
            immob_date_time = chip_data.get(f"ImmobDate{flow_cell},1")
            level = try_float_or_none(chip_data.get(f"Level{flow_cell},1"))
            comment = chip_data.get(f"Comment{flow_cell},1")
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

        return ChipData(
            sensor_chip_identifier=assert_not_none(chip_data.get("Id"), "Chip ID"),
            sensor_chip_type=chip_data.get("Name"),
            number_of_flow_cells=try_int_or_none(chip_data.get("NoFcs")),
            number_of_spots=try_int_or_none(chip_data.get("NoSpots")),
            lot_number=chip_data.get("LotNo"),
            immobilizations=immobilizations,
            custom_info={
                "display name": chip_data.get("DisplayName"),
                "IFC": chip_data.get("IFC"),
                "IFC Description": chip_data.get("IFCDesc"),
                "First Dock Date": chip_data.get("FirstDockDate"),
                "Last Use Time": chip_data.get("LastUseTime"),
                "Last Modified Time": chip_data.get("LastModTime"),
                "Number of Flow Cells": chip_data.get("NoFcs"),
                "Number of Spots": chip_data.get("NoSpots"),
            },
        )


@dataclass(frozen=True)
class DetectionConfig:
    config: DictType = field(default_factory=dict)

    @staticmethod
    def create(detection: DictType | None) -> DetectionConfig:
        return DetectionConfig(config=detection or {})


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
                _extract_min_max_from_xml_dict(
                    application_template_details.get("RackTemperature", {}), "min"
                )
                or application_template_details.get("RackTemperatureMin")
            ),
            rack_temperature_max=try_float_or_none(
                _extract_min_max_from_xml_dict(
                    application_template_details.get("RackTemperature", {}), "max"
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

    @staticmethod
    def create(
        system_information: DictType | None, application_properties: DictType | None
    ) -> SystemInformation:
        return SystemInformation(
            application_name=(system_information or {}).get("Application"),
            application_version=(system_information or {}).get("Version"),
            user_name=(system_information or {}).get("UserName"),
            system_controller_identifier=(system_information or {}).get(
                "SystemControllerId"
            ),
            os_type=(system_information or {}).get("OSType"),
            os_version=(system_information or {}).get("OSVersion"),
            measurement_time=(application_properties or {}).get("Timestamp")
            or (system_information or {}).get("Timestamp"),
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
    results_by_identifier: dict[str, KineticResult] = field(default_factory=dict)

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
    if xml_data is None:
        return None

    # If it's a StrictXmlElement, use the new extraction method
    if isinstance(xml_data, StrictXmlElement):
        return _extract_value_from_xml_element(xml_data, value_name)

    # If it's a dictionary, use the legacy extraction method
    if isinstance(xml_data, dict):
        return _extract_value_from_xml_like_dict(xml_data)

    return None
