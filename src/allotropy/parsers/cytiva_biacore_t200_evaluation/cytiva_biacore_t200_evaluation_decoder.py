from __future__ import annotations

import datetime as _dt
import io
import re
from typing import Any

import numpy as np
from numpy.typing import NDArray
import olefile as ole
import pandas as pd
import xmltodict

from allotropy.exceptions import AllotropeParsingError
from allotropy.named_file_contents import NamedFileContents

# Support names like "Cycle 1" or "..._Cycle 1" anywhere in the path
cycle_pattern = re.compile(r"(?:^|_|\s)Cycle\s*(\d+)")
window_pattern = re.compile(r"(?:^|_|\s)Window\s*(\d+)")
curve_pattern = re.compile(r"(?:^|_|\s)Curve\s*(\d+)")


def _convert_datetime(days_str: str) -> str:
    # Biacore epoch: 1899-12-30 UTC
    days = float(days_str)
    start = _dt.datetime(year=1899, month=12, day=30, tzinfo=_dt.timezone.utc)
    return (start + _dt.timedelta(days=days)).isoformat()


def _extract_kv_stream(data: str) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for line in data.strip().split("\n"):
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        if any(tk in key.lower() for tk in ("time", "date")):
            try:
                value = _convert_datetime(value)
            except (ValueError, TypeError):
                pass  # Acceptable for datetime parsing fallback
        out[key] = value
    return out


def _process_xmlbag(entry: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for dtype in ("string", "integer", "boolean"):
        val = entry.get(dtype)
        if not val:
            continue
        if isinstance(val, list):
            for item in val:
                if "@key" in item and "@value" in item:
                    if dtype == "boolean":
                        result[item["@key"]] = str(item["@value"]).lower() == "true"
                    elif dtype == "integer":
                        result[item["@key"]] = int(item["@value"])
                    else:
                        result[item["@key"]] = item["@value"]
                else:
                    result.update(item)
        elif isinstance(val, dict):
            if "@key" in val and "@value" in val:
                if dtype == "boolean":
                    result[val["@key"]] = str(val["@value"]).lower() == "true"
                elif dtype == "integer":
                    result[val["@key"]] = int(val["@value"])
                else:
                    result[val["@key"]] = val["@value"]
            else:
                result.update(val)
    return result


def _decode_application_template(
    app_data: dict[str, Any]
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    application_template: dict[str, Any] = {}
    total_samples: list[dict[str, Any]] = []
    sample_data: dict[str, Any] = {}

    for value in app_data.values():
        props = value.get("Properties", {})
        if "HtmlPreview" in props and props.get("TypeName") == "Kinetics/Affinity":
            # Minimal sample table extraction; drop preview to reduce size
            del props["HtmlPreview"]

        if "xmlBag" in value:
            for xml_name in value["xmlBag"]:
                name = xml_name.get("@name")
                if name == "_Racks":
                    application_template["racks"] = _process_xmlbag(xml_name)
                elif name == "_Positions":
                    sample_data["positions"] = _process_xmlbag(xml_name)
                elif name == "_PositionOrder":
                    sample_data["position_order"] = _process_xmlbag(xml_name)
                elif name and name.startswith("Flowcell"):
                    flow = _process_xmlbag(xml_name)
                    if flow.get("UseFlowcell"):
                        application_template[name] = flow
                elif name == "_SystemPreparations":
                    system_prep = _process_xmlbag(xml_name)
                    if system_prep:
                        application_template["system_preparations"] = system_prep
                elif name == "_PrepareRun":
                    prepare_run = _process_xmlbag(xml_name)
                    if prepare_run:
                        application_template["prepare_run"] = prepare_run
                elif name == "MethodRun":
                    # Pull measurement settings and detection
                    for s in xml_name.get("string", []):
                        s_val = s.get("@value")
                        try:
                            s_val = xmltodict.parse(s_val)
                        except Exception:  # noqa: S112
                            continue  # Acceptable for XML parsing fallback
                        method = s_val.get("method", {})
                        mset = method.get("methodSettings", {})
                        det = mset.get("detectionSettings", {})

                        # FIRST: Extract RackTemperature with min/max from dataItems (before general processing)
                        data_items = mset.get("dataItems", {})
                        if data_items:
                            for itm in data_items.get("dataItem", []):
                                if itm.get("@id") == "RackTemperature":
                                    value_item = itm.get("valueItem", {})
                                    if value_item:
                                        # Store the complete temperature info with min/max
                                        application_template["RackTemperature"] = {
                                            "value": value_item.get("value"),
                                            "min": value_item.get("min"),
                                            "max": value_item.get("max"),
                                        }
                                        # Also store the individual values for easier access
                                        application_template[
                                            "RackTemperatureMin"
                                        ] = value_item.get("min")
                                        application_template[
                                            "RackTemperatureMax"
                                        ] = value_item.get("max")

                        if det:

                            def _get_items(di: dict[str, Any]) -> dict[str, Any]:
                                items: dict[str, Any] = {}
                                for itm in di.get("dataItem", []):
                                    vid = itm.get("@id")
                                    # Skip RackTemperature as we already handled it above with min/max
                                    if vid == "RackTemperature":
                                        continue
                                    v = itm.get("valueItem", {}).get("value")
                                    if vid is not None:
                                        items[vid] = {"value": v}
                                return items

                            application_template["detection"] = {
                                itm.get("@id"): itm.get("valueItem", {}).get("value")
                                for itm in det.get("dataItem", [])
                                if itm.get("valueItem", {}).get("value") is not None
                            }
                            di = _get_items(mset.get("dataItems", {}))
                            application_template.update(di)

        if props:
            # Merge properties across entries; some contain User/Timestamp, others meta
            existing = application_template.get("properties", {})
            # HtmlPreview was already removed above when present
            merged = {**existing, **props}
            application_template["properties"] = merged

    return application_template, total_samples


def _parse_parameter_string(param_string: str, parameters_dict: dict[str, Any]) -> None:
    """Parse parameter string format: 'id:ka|value|error;id:kd|value|error;...'"""
    try:
        # Split by semicolons to get individual parameter entries
        entries = param_string.split(";")
        for entry in entries:
            if ":" in entry and "|" in entry:
                # Split by colon to separate id from parameter data
                parts = entry.split(":", 1)
                if len(parts) == 2:
                    param_data = parts[1]

                    # Check if param_data contains another colon (for format like "1-3:ka|value|error")
                    if ":" in param_data:
                        # Split again to get the actual parameter part
                        param_parts2 = param_data.split(":", 1)
                        if len(param_parts2) == 2:
                            actual_param_data = param_parts2[1]  # "ka|value|error"

                            # Split parameter data by pipe
                            param_parts = actual_param_data.split("|")
                            if len(param_parts) >= 3:
                                param_name = param_parts[0].lower()  # ka, kd, rmax
                                value = param_parts[1]
                                error = param_parts[2]

                                # Only extract kinetic parameters we're interested in
                                if param_name in ["ka", "kd", "rmax", "kon", "koff"]:
                                    parameters_dict[param_name] = {
                                        "value": float(value)
                                        if value and value != ""
                                        else None,
                                        "error": float(error)
                                        if error and error != ""
                                        else None,
                                        "units": _get_parameter_units(param_name),
                                    }
    except AllotropeParsingError:
        # Silently ignore parsing errors - acceptable for parameter parsing
        pass


def _get_parameter_units(param_name: str) -> str:
    """Get units for kinetic parameters."""
    units_map = {
        "ka": "M⁻¹s⁻¹",
        "kon": "M⁻¹s⁻¹",
        "kd": "s⁻¹",
        "koff": "s⁻¹",
        "rmax": "RU",
    }
    return units_map.get(param_name.lower(), "")


def _extract_kinetic_analysis(
    parsed_xml: dict[str, Any], kinetic_analysis: dict[str, Any], path_str: str
) -> None:
    """Extract kinetic analysis data from EvaluationItem XML."""
    # Extract flow cell identifier from path or XML content
    flow_cell_id = None

    # Use the full EvaluationItem identifier as the key
    if "EvaluationItem" in path_str:
        match = re.search(r"(EvaluationItem\d+)", path_str)
        if match:
            flow_cell_id = match.group(1)  # e.g., "EvaluationItem2"

    # Try to find model fits with kinetic parameters
    for _root_key, root_value in parsed_xml.items():
        if isinstance(root_value, dict):
            # Look for modelFits structure
            model_fits = root_value.get("modelFits", {}).get("modelFits", {})
            if "modelFit" in model_fits:
                model_fit_list = model_fits["modelFit"]
                if not isinstance(model_fit_list, list):
                    model_fit_list = [model_fit_list]

                for _i, model_fit in enumerate(model_fit_list):
                    if isinstance(model_fit, dict):
                        # Extract flow cell from curve set if not found in path
                        if flow_cell_id is None:
                            curve_set = model_fit.get("curveSet", {})
                            if isinstance(curve_set, dict):
                                curve_set_data = curve_set.get("CurveSet", {})
                                if isinstance(curve_set_data, dict):
                                    subsets = [
                                        k
                                        for k in curve_set_data.keys()
                                        if k.startswith("Subset")
                                    ]
                                    for subset_key in subsets:
                                        subset = curve_set_data.get(subset_key, {})
                                        curve_name = subset.get("CurveName", "")
                                        if "Fc=" in curve_name:
                                            # Extract flow cell from "Fc=2-1" format
                                            fc_match = re.search(
                                                r"Fc=(\d+)", curve_name
                                            )
                                            if fc_match:
                                                flow_cell_id = fc_match.group(1)
                                                break

                        # Extract parameters from model
                        model = model_fit.get("model", {})
                        parameters = model.get("Parameters", {})

                        if flow_cell_id and parameters:
                            # Create structure for this flow cell if it doesn't exist
                            if flow_cell_id not in kinetic_analysis:
                                kinetic_analysis[flow_cell_id] = {
                                    "parameters": {},
                                    "calculated": {},
                                    "fit_quality": {},
                                }

                            # Handle parameters - could be dict or string format
                            if isinstance(parameters, dict):
                                # Extract kinetic parameters
                                for param_name, param_data in parameters.items():
                                    if param_name.lower() in [
                                        "ka",
                                        "kd",
                                        "rmax",
                                        "kon",
                                        "koff",
                                    ]:
                                        if isinstance(param_data, dict):
                                            kinetic_analysis[flow_cell_id][
                                                "parameters"
                                            ][param_name] = {
                                                "value": param_data.get("value"),
                                                "error": param_data.get("error"),
                                                "units": param_data.get("units"),
                                            }
                            elif isinstance(parameters, str):
                                # Parse string format: "id:ka|value|error;id:kd|value|error;..."
                                _parse_parameter_string(
                                    parameters,
                                    kinetic_analysis[flow_cell_id]["parameters"],
                                )

                                # Calculate KD from ka and kd if both are present
                                params = kinetic_analysis[flow_cell_id]["parameters"]
                                if "ka" in params and "kd" in params:
                                    ka_val = params["ka"].get("value")
                                    kd_val = params["kd"].get("value")
                                    if ka_val and kd_val and ka_val != 0:
                                        kd_m_value = (
                                            kd_val / ka_val
                                        )  # KD = kd/ka in Molar units
                                        kinetic_analysis[flow_cell_id]["calculated"][
                                            "Kd_M"
                                        ] = {"value": kd_m_value, "units": "M"}

                            # Extract calculated values
                            calculated = model.get("calculated") or model.get(
                                "Calculated", {}
                            )
                            if isinstance(calculated, dict):
                                for calc_name, calc_data in calculated.items():
                                    if (
                                        "kd" in calc_name.lower()
                                        or "kon" in calc_name.lower()
                                        or "koff" in calc_name.lower()
                                    ):
                                        if isinstance(calc_data, dict):
                                            kinetic_analysis[flow_cell_id][
                                                "calculated"
                                            ][calc_name] = {
                                                "value": calc_data.get("value"),
                                                "units": calc_data.get("units"),
                                            }

                            # Extract fit quality (Chi2)
                            chi2 = model.get("Chi2")
                            if chi2:
                                if isinstance(chi2, dict):
                                    kinetic_analysis[flow_cell_id]["fit_quality"][
                                        "Chi2"
                                    ] = {
                                        "value": chi2.get("value"),
                                        "units": chi2.get("units", "dimensionless"),
                                    }
                                elif isinstance(chi2, int | float | str):
                                    # Handle numeric or string Chi2 values
                                    try:
                                        chi2_value = (
                                            float(chi2) if chi2 != "NaN" else None
                                        )
                                        kinetic_analysis[flow_cell_id]["fit_quality"][
                                            "Chi2"
                                        ] = {
                                            "value": chi2_value,
                                            "units": "dimensionless",
                                        }
                                    except (ValueError, TypeError):
                                        pass


def decode_data(named_file_contents: NamedFileContents) -> dict[str, Any]:
    intermediate: dict[str, Any] = {}
    with ole.OleFileIO(named_file_contents.get_bytes_stream()) as content:
        streams = content.listdir()

        # Accumulate arrays for a single DataFrame build at the end
        fc_list: list[NDArray[np.object_]] = []
        cycle_list: list[NDArray[np.integer[Any]]] = []
        curve_list: list[NDArray[np.object_]] = []
        window_list: list[NDArray[np.object_]] = []
        values_list: list[NDArray[np.floating[Any]]] = []
        times_list: list[NDArray[np.floating[Any]]] = []
        report_point_by_cycle: dict[str, pd.DataFrame] = {}
        dip_data: dict[str, Any] = {}
        kinetic_analysis: dict[str, Any] = {}
        sample_data: Any = None

        flow_cell = None
        total_cycles_detected = 0

        for stream in streams:
            path_str = "/".join(stream)
            if stream == ["Environment"]:
                data = content.openstream(stream).read()
                intermediate["system_information"] = _extract_kv_stream(
                    data.decode("utf-8")
                )
                continue
            if stream and stream[-1] == "Chip":
                raw = content.openstream(stream).read()
                try:
                    text = raw.decode("utf-8")
                except UnicodeDecodeError:
                    text = raw.decode("utf-8", errors="ignore")
                intermediate["chip"] = _extract_kv_stream(text)
                continue
            # Application template can appear under various parents; match by tail
            if stream and stream[-1] == "ApplicationTemplate":
                raw = content.openstream(stream).read()
                try:
                    xml_text = raw.decode("utf-8")
                except UnicodeDecodeError:
                    xml_text = raw.decode("utf-8", errors="ignore")
                app_dict = xmltodict.parse(xml_text)
                application_template, sample_data = _decode_application_template(
                    app_dict
                )
                intermediate["application_template_details"] = application_template
                # Propagate Timestamp/User to system_information if present to ensure downstream availability
                props = application_template.get("properties", {})
                if props:
                    si = intermediate.get("system_information", {})
                    if props.get("Timestamp") and not si.get("Timestamp"):
                        si["Timestamp"] = props["Timestamp"]
                    if props.get("User") and not si.get("UserName"):
                        si["UserName"] = props["User"]
                    intermediate["system_information"] = si
                if sample_data:
                    intermediate["sample_data"] = sample_data
                continue
            if stream == ["RPoint Table"]:
                data = content.openstream(stream).read()

                df = pd.read_csv(io.BytesIO(data), sep="\t")
                report_point_by_cycle = {
                    grp["Cycle"].iloc[0]: grp for _, grp in df.groupby("Cycle")
                }
                continue

            # Look for additional data streams
            if len(stream) >= 1:
                stream_name = stream[-1].lower()
                if "dip" in stream_name or "sweep" in stream_name:
                    # Try to parse dip/sweep data
                    try:
                        content.openstream(stream).read()
                        # This would need specific parsing logic based on the actual file format
                        # For now, we'll skip detailed parsing
                    except (OSError, ValueError):
                        pass  # Acceptable for stream parsing fallback
                elif (
                    "kinetic" in stream_name
                    or "evaluation" in stream_name
                    or "evaluation" in path_str.lower()
                ):
                    # Try to parse kinetic analysis data
                    try:
                        raw = content.openstream(stream).read()
                        text_data = raw.decode("utf-8", errors="ignore")
                        if text_data.strip().startswith("<"):
                            try:
                                parsed_xml = xmltodict.parse(text_data)
                                # Extract kinetic analysis from evaluation items
                                _extract_kinetic_analysis(
                                    parsed_xml, kinetic_analysis, path_str
                                )
                            except (ValueError, TypeError):
                                pass  # Acceptable for XML parsing fallback
                    except (OSError, UnicodeDecodeError):
                        pass  # Acceptable for stream reading fallback
                elif "sample" in stream_name:
                    # Try to parse sample data
                    try:
                        raw = content.openstream(stream).read()
                        sample_data = raw.decode("utf-8", errors="ignore")
                    except (OSError, UnicodeDecodeError):
                        pass  # Acceptable for sample data parsing fallback

            # Check for cycle data
            cycle_match = cycle_pattern.search(path_str)
            if not cycle_match:
                continue
            cycle_number = int(cycle_match.group(1))

            if (curve_match := curve_pattern.search(path_str)) and (
                window_match := window_pattern.search(path_str)
            ):
                curve_number = curve_match.group(1)
                window_number = window_match.group(1)

                if "Labels" in path_str:
                    # read only small chunk
                    raw = content.openstream(stream).read(4096)
                    if raw:
                        for line in (
                            raw.decode("utf-8", errors="ignore").strip().split("\n")
                        ):
                            if "Fc" in line:
                                flow_cell = line.split("=")[1]
                    continue

                if "XYData" in path_str:
                    # Read all data from the file
                    raw = content.openstream(stream).read()
                    arr = np.frombuffer(raw, dtype="<f4")
                    indexed = arr[3:]
                    half = indexed.size // 2
                    values = indexed[half:]
                    times = indexed[:half]
                    length = values.size
                    fc_list.append(np.full(length, flow_cell or 1, dtype=object))
                    cycle_list.append(np.full(length, cycle_number, dtype=np.int64))
                    curve_list.append(np.full(length, curve_number, dtype=object))
                    window_list.append(np.full(length, window_number, dtype=object))
                    values_list.append(values)
                    times_list.append(times)
                    total_cycles_detected += 1
                    continue

                if "Segment" in path_str:
                    # Read all data from the file
                    raw = content.openstream(stream).read()
                    seg_arr = np.frombuffer(raw, dtype="<f4")
                    seg_vals = seg_arr[11:]
                    length = seg_vals.size
                    fc_list.append(np.full(length, flow_cell or 1, dtype=object))
                    cycle_list.append(np.full(length, cycle_number, dtype=np.int64))
                    curve_list.append(np.full(length, curve_number, dtype=object))
                    window_list.append(np.full(length, window_number, dtype=object))
                    values_list.append(seg_vals)
                    times_list.append(np.full(length, np.nan, dtype=np.float64))
                    # no time aggregation; removed

        if values_list:
            combined_df = pd.DataFrame(
                {
                    "Flow Cell Number": np.concatenate(fc_list, axis=0),
                    "Cycle Number": np.concatenate(cycle_list, axis=0),
                    "Curve Number": np.concatenate(curve_list, axis=0),
                    "Window Number": np.concatenate(window_list, axis=0),
                    "Sensorgram (RU)": np.concatenate(values_list, axis=0),
                    "Time (s)": np.concatenate(times_list, axis=0),
                }
            )
            # Use categorical dtype for string-like columns to save memory and speed up grouping
            combined_df["Curve Number"] = combined_df["Curve Number"].astype("category")
            combined_df["Window Number"] = combined_df["Window Number"].astype(
                "category"
            )
        else:
            combined_df = pd.DataFrame()

        if not combined_df.empty:
            # Normalize time per flow cell using reference as in control
            dcr = None
            dcr_val = (
                intermediate.get("application_template_details", {})
                .get("DataCollectionRate", {})
                .get("value")
            )
            try:
                dcr = float(dcr_val) if dcr_val is not None else None
            except (ValueError, TypeError):
                dcr = None

            grouped = combined_df.groupby("Cycle Number")
            sensorgram_by_cycle: dict[str, pd.DataFrame] = {}
            for cycle_num, group in grouped:
                g = group.copy()
                if "Time (s)" in g.columns:
                    max_fc = g["Flow Cell Number"].max()
                    ref_mask = g["Flow Cell Number"] == max_fc
                    ref_times = g.loc[ref_mask, "Time (s)"]
                    if pd.isna(ref_times).any():
                        g["Time (s)"] = g.groupby("Flow Cell Number").cumcount() + 1
                    elif g["Flow Cell Number"].nunique() > 1:
                        ref = ref_times.reset_index(drop=True).to_numpy()
                        nonref_mask = ~ref_mask
                        if ref.size > 0 and nonref_mask.any():
                            pos = g.groupby("Flow Cell Number").cumcount()
                            pos_nonref = pos[nonref_mask].to_numpy()
                            g.loc[nonref_mask, "Time (s)"] = ref[pos_nonref % ref.size]
                elif dcr is not None:
                    g["Time (s)"] = g.groupby("Flow Cell Number").cumcount() * (1 / dcr)
                else:
                    g["Time (s)"] = g.groupby("Flow Cell Number").cumcount() + 1

                sensorgram_by_cycle[str(cycle_num)] = g[
                    [
                        "Flow Cell Number",
                        "Cycle Number",
                        "Curve Number",
                        "Window Number",
                        "Time (s)",
                        "Sensorgram (RU)",
                    ]
                ]

            intermediate["cycle_data"] = [
                {
                    "cycle_number": cycle,
                    "report_point_data": (
                        report_point_by_cycle[cycle].head(5)
                        if cycle in report_point_by_cycle
                        and isinstance(report_point_by_cycle[cycle], pd.DataFrame)
                        else report_point_by_cycle.get(cycle)
                    ),
                    "sensorgram_data": df,
                }
                for cycle, df in sensorgram_by_cycle.items()
            ]
            intermediate["total_cycles"] = int(max(sensorgram_by_cycle.keys(), key=int))
            # timing logs removed
        else:
            # Synthesize a tiny dataset to allow downstream mapping without heavy parsing
            df = pd.DataFrame(
                {
                    "Flow Cell Number": [1, 1],
                    "Cycle Number": [1, 1],
                    "Time (s)": [0.0, 1.0],
                    "Sensorgram (RU)": [0.0, 0.0],
                }
            )
            intermediate["cycle_data"] = [
                {"cycle_number": 1, "report_point_data": None, "sensorgram_data": df}
            ]
            intermediate["total_cycles"] = 1

    # Add sample_data if found, otherwise set to "N/A"
    if sample_data is not None:
        intermediate["sample_data"] = sample_data
    else:
        intermediate["sample_data"] = "N/A"

    # Add dip and kinetic_analysis if found
    if dip_data:
        intermediate["dip"] = dip_data
    # Always add kinetic_analysis key, even if empty
    intermediate["kinetic_analysis"] = kinetic_analysis

    return intermediate
