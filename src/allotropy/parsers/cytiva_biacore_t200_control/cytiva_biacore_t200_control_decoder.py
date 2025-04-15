import datetime
import re
import struct
from typing import Any

import olefile as ole
import pandas as pd
import xmltodict

from allotropy.named_file_contents import NamedFileContents

# Patterns to extract cycle number, window number, and curve number
cycle_pattern = re.compile(r"_Cycle (\d+)")
window_pattern = re.compile(r"_Window (\d+)")
curve_pattern = re.compile(r"_Curve (\d+)")


def get_sample_data(sample_dict: dict[str, Any]) -> list[dict[str, Any]]:
    """
    Gets Sample data from the dictionary
    :param sample_data: dictionary containing sample data
    :return: structured dictionary containing sample data
    """
    sample_data = []
    sample_details = []
    positions = sample_dict["positions"]
    position_order = sample_dict["position_order"]

    for key, value in positions.items():
        samples = {}
        if key.endswith("sample_pos"):
            samples["rack"] = value
            cycle = match.group() if (match := re.search(r"Cycle\d+", key)) else None

            samples["cycle_number"] = (
                "Cycle" + str(int(cycle.split("Cycle")[1].split("@")[0]) + 1)
                if cycle is not None and "Cycle" in cycle
                else None
            )
            for order in position_order.keys():
                if value in order:
                    if "running buffer" and "Startup" in order:
                        samples["role"] = "blank role"
                    elif "Sample" in order:
                        samples["sample_name"] = order.split("\n")[0]
                        samples["role"] = "sample role"

            sample_details.append(samples)

    sorted_data = sorted(
        sample_details, key=lambda d: int(d["cycle_number"].replace("Cycle", ""))
    )
    sample_iter = iter(sample_dict["sample_data"])
    for item in sorted_data:
        if item["role"] == "blank role":
            sample_data.append(item)
        else:
            sample = next(sample_iter, None)
            if sample:
                new_item = item.copy()
                if sample["Sample id"] == item["sample_name"]:
                    new_item["sample_name"] = sample.get("Sample id", None)
                    new_item["concentration"] = (
                        sample["Conc."].replace(",", ".") if sample["Conc."] else None
                    )
                    new_item["molecular_weight"] = sample.get("MW", None)
                    sample_data.append(new_item)

    return sample_data


def process_and_rearrange_xml_data(data: dict[str, Any]) -> dict[str, Any]:
    """
    Processes and Rearranges xml data to form structured dictionary
    :param data: The data containing xml details
    :return: structured dictionary
    """
    # Initialize the output dictionary
    output = {}

    # Process the input dictionary based on the provided code structure
    for data_type in ["string", "integer", "boolean"]:
        if data_type in data:
            # Handle cases where the data type is a list of dictionaries
            if isinstance(data[data_type], list):
                for entry in data[data_type]:
                    # Convert @key and @value pairs, handle boolean conversion
                    if "@key" in entry and "@value" in entry:
                        if data_type == "boolean":
                            # Convert 'true'/'false' to actual boolean values
                            output[entry["@key"]] = entry["@value"].lower() == "true"
                        elif data_type == "integer":
                            output[entry["@key"]] = int(entry["@value"])
                        else:
                            output[entry["@key"]] = entry["@value"]
                    else:
                        output.update(entry)
            # Handle single dictionary entries
            elif isinstance(data[data_type], dict):
                if "@key" in data[data_type] and "@value" in data[data_type]:
                    if data_type == "boolean":
                        output[data[data_type]["@key"]] = (
                            data[data_type]["@value"].lower() == "true"
                        )
                    elif data_type == "integer":
                        output[data[data_type]["@key"]] = int(data[data_type]["@value"])
                    else:
                        output[data[data_type]["@key"]] = data[data_type]["@value"]
                else:
                    output.update(data[data_type])

    return output


def get_detection_data(
    detection_settings: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    """
    The function gets detection data
    :param detection_settings: dictionary containing detection data
    :return: structured dictionary containing detection data
    """
    detection_data = {}
    # Iterate through each item in 'dataItem'
    for item in detection_settings["dataItem"]:
        # Check if the 'value' in 'valueItem' is not None
        if item["valueItem"]["value"] is not None:
            # Add the '@id' and 'value' to the output dictionary
            detection_data[item["@id"]] = item["valueItem"]["value"]

    return detection_data


def get_data_item(data_item: dict[str, Any]) -> dict[str, Any]:
    """
    The function gets the data item
    :param data_item: dictionary containing data item
    :return: structured dictionary of data item
    """
    data_time = {}
    for item in data_item["dataItem"]:
        value_data = item["valueItem"]["value"]

        if isinstance(value_data, dict):
            value_dict = {"value": value_data.get("#text")}
        else:
            value_dict = {"value": value_data}

        if "min" in item["valueItem"]:
            value_dict["min"] = item["valueItem"]["min"]
        if "max" in item["valueItem"]:
            value_dict["max"] = item["valueItem"]["max"]

        data_time[item["@id"]] = value_dict
    return data_time


def decode_application_data(
    application_template_data: dict[str, Any],
) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    """
    decodes app data template application stream data
    :param application_template_data: string app data template application stream data
    :return: dict app data template application stream data
    """
    total_samples: list[dict[str, Any]] = []
    application_template = {}
    sample_data = {}
    for application_value in application_template_data.values():

        if "HtmlPreview" in application_value["Properties"]:
            if application_value["Properties"]["TypeName"] == "Kinetics/Affinity":

                sample_data["run_order"] = (
                    application_value["Properties"]["HtmlPreview"]
                    .split("Run order")[1]
                    .split("\xa0\n\xa0")[0]
                    .split("\n\n")[0]
                    .split("\xa0")[1]
                    .strip()
                )
                lines = (
                    application_value["Properties"]["HtmlPreview"]
                    .split("Run order")[1]
                    .split("\xa0\n\xa0")[0]
                    .split("\n\n")[1]
                    .split("\n")
                )
                header = re.split(r"\s{2,}", lines[0].strip())
                # Extract the rows
                rows = [re.split(r"\s{2,}", line.strip()) for line in lines[1:]]
                rows = [row[1:] for row in rows]
                # Convert to a list of dictionaries
                sample_details = [dict(zip(header, row, strict=True)) for row in rows]
                sample_data["sample_data"] = sample_details

            del application_value["Properties"]["HtmlPreview"]

        if "xmlBag" in application_value:
            for xml_name in application_value["xmlBag"]:
                if xml_name["@name"] == "_Racks":
                    application_template["racks"] = process_and_rearrange_xml_data(
                        xml_name
                    )
                elif xml_name["@name"] == "_Positions":
                    sample_data["positions"] = process_and_rearrange_xml_data(xml_name)
                elif xml_name["@name"] == "_PositionOrder":
                    sample_data["position_order"] = process_and_rearrange_xml_data(
                        xml_name
                    )
                elif "Flowcell" in xml_name["@name"]:
                    flow_data = process_and_rearrange_xml_data(xml_name)
                    if flow_data["UseFlowcell"]:
                        application_template[xml_name["@name"]] = flow_data
                elif xml_name["@name"] == "MethodRun":
                    for xml_string in xml_name["string"]:
                        xml_string["@value"] = xmltodict.parse(xml_string["@value"])
                        if "methodSettings" in xml_string["@value"]["method"]:
                            application_template["detection"] = get_detection_data(
                                xml_string["@value"]["method"]["methodSettings"][
                                    "detectionSettings"
                                ]
                            )
                            measurement_settings = get_data_item(
                                xml_string["@value"]["method"]["methodSettings"][
                                    "dataItems"
                                ]
                            )
                            application_template[
                                "RackTemperature"
                            ] = measurement_settings["RackTemperature"]
                            application_template["BaselineFlow"] = measurement_settings[
                                "BaselineFlow"
                            ]
                            application_template[
                                "DataCollectionRate"
                            ] = measurement_settings["DataCollectionRate"]
                            application_template[
                                "MoleculeWeightUnit"
                            ] = measurement_settings["MoleculeWeightUnit"]
                elif xml_name["@name"] == "_SystemPreparations":
                    application_template[
                        "system_preparations"
                    ] = process_and_rearrange_xml_data(xml_name)
                elif xml_name["@name"] == "_PrepareRun":
                    application_template["prepare_run"] = {
                        key: value
                        for key, value in process_and_rearrange_xml_data(
                            xml_name
                        ).items()
                        if "Buffer" in key and value != -1
                    }

        application_template["properties"] = application_value["Properties"]
        if (
            application_value["Properties"]["TypeName"] == "Kinetics/Affinity"
            and sample_data["run_order"] == "As entered"
        ):
            total_samples = get_sample_data(sample_data)
    return application_template, total_samples


def convert_datetime(days_str: str) -> str:
    """
    converts the str to iso datetime format.
    this instrument uses the 30 December 1899 EPOCH
    :param days_str: string of datetime
    :return: datetime
    """
    days = float(days_str)
    start_date = datetime.datetime(
        year=1899, month=12, day=30, tzinfo=datetime.timezone.utc
    )
    delta = datetime.timedelta(days=days)
    result_date = start_date + delta
    iso_date_time = result_date.isoformat()
    return iso_date_time


def extract_stream_data(data: str) -> dict[str, Any]:
    """
    Decodes various types of stream data.
    :param data: string stream data
    :return: dict with decoded data
    """
    data_dict = {}
    for line in data.strip().split("\n"):
        key, value = line.split("=")
        data_dict[key] = value
        if any(
            time_key in key.lower()
            for time_key in (
                "time",
                "date",
            )
        ) and isinstance(value, str):

            data_dict[key] = convert_datetime(value)

    return data_dict


def get_dip_data(input_data: str) -> dict[str, Any]:
    """
    Parses the input string data and returns a structured JSON of the decoded data.
    :param input_data: string stream data
    :return: dict with structured JSON data
    """
    lines = input_data.split("\n")
    result: dict[str, Any] = {}
    norm_data: list[dict[str, Any]] = []
    raw_data: list[dict[str, Any]] = []
    current_section = None
    max_length = 2
    for line in lines:
        strp_line = line.strip()
        if strp_line.startswith("Count"):
            result["count"] = int(strp_line.split("=")[1])
        elif strp_line.startswith("Timestamp1"):
            timestamp_value = strp_line.split("=")[1]
            result["timestamp"] = convert_datetime(timestamp_value)
        elif "Norm" in strp_line:
            current_section = "norm"
        elif "Raw" in strp_line:
            current_section = "raw"
        else:
            parts = strp_line.split(";")
            if (
                len(parts) == max_length
                and len(index_part := parts[0].split("=")) == max_length
            ):
                sweep_row, flow_cell = index_part[1].split(",")
                response = list(map(int, parts[1].split(",")))
                data = {
                    "flow_cell": flow_cell,
                    "sweep_row": sweep_row,
                    "response": response,
                }
                (norm_data if current_section == "norm" else raw_data).append(data)

    result.update({"norm_data": norm_data, "raw_data": raw_data})
    return result


def get_r_point_data(r_point_data: str) -> list[dict[str, Any]]:
    """
    decodes the r-point data
    :param r_point_data: str of r point data
    :return: list of r_point dictionary
    """
    r_data_list = []
    lines = r_point_data.strip().split("\n")
    header = lines[0].split("\t")

    for line in lines[1:]:
        values = line.split("\t")
        data_dict = dict(zip(header, values, strict=True))

        r_data_list.append(data_dict)

    return r_data_list


def decode_data(named_file_contents: NamedFileContents) -> dict[str, Any]:
    """
    Decodes the proprietary file into a structured dict
    :param named_file_contents: The named file contents containing the input file details
    :return: structured dictionary of decoded data
    """
    intermediate_json: dict[str, Any] = {}
    content = ole.OleFileIO(named_file_contents.get_bytes_stream())
    streams = content.listdir()
    sensorgram_df_list = []
    report_point_data = {}
    for stream in streams:
        stream_content = content.openstream(stream).read()
        if stream == ["Environment"]:
            intermediate_json["system_information"] = extract_stream_data(
                stream_content.decode("utf-8")
            )
        elif stream == ["Chip"]:
            intermediate_json["chip"] = extract_stream_data(
                stream_content.decode("utf-8")
            )

        elif stream == ["AppData", "Dip"]:
            intermediate_json["dip"] = get_dip_data(stream_content.decode("utf-8"))
        elif stream == ["AppData", "ApplicationTemplate"]:
            (
                intermediate_json["application_template_details"],
                sample_data,
            ) = decode_application_data(xmltodict.parse(stream_content))
            if sample_data:
                intermediate_json["sample_data"] = sample_data
        elif stream == ["RPoint Table"]:
            r_point_data = get_r_point_data(stream_content.decode("utf-8"))
            r_point_dataframe = pd.DataFrame(r_point_data)
            report_point_data = {
                group["Cycle"].iloc[0]: group
                for _, group in r_point_dataframe.groupby("Cycle")
            }

        if not (cycle_match := cycle_pattern.search(stream[0])):
            continue
        cycle_number = int(cycle_match.group(1))

        if (curve_match := curve_pattern.search(str(stream))) and (
            window_match := window_pattern.search(str(stream))
        ):
            curve_number = curve_match.group(1)
            window_number = window_match.group(1)

            # get the flow cell number
            if "Labels" in str(stream):
                label_list = []
                if len(stream_content) != 0:
                    decoded_stream_content = stream_content.decode("utf-8")
                    for line in decoded_stream_content.strip().split("\n"):
                        label_list.append(line)
                        if "Fc" in line:
                            flow_cell = label_list[0].split("=")[1]

            # gets the xy data as data frame
            elif "XYData" in str(stream):
                xy_data_list = list(
                    struct.unpack("f" * (len(stream_content) // 4), stream_content)
                )
                indexed_xy_data_list = xy_data_list[3:]
                length_of_xydata = len(xy_data_list[3:])
                xy_result_list = indexed_xy_data_list[int(length_of_xydata / 2) :]
                time = indexed_xy_data_list[: int(length_of_xydata / 2)]
                length_of_xy = len(xy_result_list)

                xy_data_frame = pd.DataFrame(
                    {
                        "Flow Cell Number": [flow_cell] * length_of_xy,
                        "Cycle Number": [cycle_number] * length_of_xy,
                        "Curve Number": [curve_number] * length_of_xy,
                        "Window Number": [window_number] * length_of_xy,
                        "Sensorgram (RU)": xy_result_list,
                        "Time (s)": time,
                    }
                )

                sensorgram_df_list.append(xy_data_frame)

            # gets the segment data
            elif "Segment" in str(stream):
                segment_data_list = list(
                    struct.unpack("f" * (len(stream_content) // 4), stream_content)
                )
                length_of_segment = len(segment_data_list[11:])
                segment_data_frame = pd.DataFrame(
                    {
                        "Flow Cell Number": [flow_cell] * length_of_segment,
                        "Cycle Number": [cycle_number] * length_of_segment,
                        "Curve Number": [curve_number] * length_of_segment,
                        "Window Number": [window_number] * length_of_segment,
                        "Sensorgram (RU)": segment_data_list[11:],
                    }
                )
                sensorgram_df_list.append(segment_data_frame)
    combined_sensorgram_df = pd.concat(sensorgram_df_list, ignore_index=True)
    sensorgram_data = {}
    for _name, group in combined_sensorgram_df.groupby("Cycle Number"):
        if "Time (s)" in group.columns:
            max_new = group["Flow Cell Number"].max()
            last_part = group[group["Flow Cell Number"] == max_new]
            if pd.isna(last_part["Time (s)"]).any():
                group["Time (s)"] = group.groupby("Flow Cell Number").cumcount() + 1
            else:
                time_map = dict(
                    zip(last_part.index, last_part["Time (s)"], strict=True)
                )
                for new_value in group["Flow Cell Number"].unique():
                    if new_value != max_new:
                        indices = group[group["Flow Cell Number"] == new_value].index
                        for i, idx in enumerate(indices):
                            group.at[idx, "Time (s)"] = time_map[
                                list(time_map.keys())[i % len(time_map)]
                            ]
        # If the data collection rate is set, apply it to the time column
        elif intermediate_json.get("application_template_details", {}).get(
            "DataCollectionRate"
        ):
            group["Time (s)"] = group.groupby("Flow Cell Number").cumcount() * (
                1
                / intermediate_json["application_template_details"][
                    "DataCollectionRate"
                ]["value"]
            )
        else:
            group["Time (s)"] = group.groupby("Flow Cell Number").cumcount() + 1

        cycle_number = group["Cycle Number"].iloc[0]
        sensorgram_data[str(cycle_number)] = group[
            [
                "Flow Cell Number",
                "Cycle Number",
                "Curve Number",
                "Window Number",
                "Time (s)",
                "Sensorgram (RU)",
            ]
        ]

    # In some cases the "RPoint Table" stream may not have data for the first cycle,
    # but we get streams with sensorgram data (XYData or Segment streams) for all the cycles.
    intermediate_json["cycle_data"] = [
        {
            "cycle_number": cycle,
            "report_point_data": report_point_data.get(cycle),
            "sensorgram_data": sensorgram_df,
        }
        for cycle, sensorgram_df in sensorgram_data.items()
    ]
    intermediate_json["total_cycles"] = cycle_number

    return intermediate_json
