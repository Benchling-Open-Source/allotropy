import json
from typing import Any, cast

from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.utils.json import JsonData
from allotropy.parsers.utils.values import assert_not_none


class BenchlingEmpowerReader:
    SUPPORTED_EXTENSIONS = "json"

    metadata_fields: JsonData
    injections: list[JsonData]

    def __init__(self, named_file_contents: NamedFileContents) -> None:
        contents_dict: dict[str, Any] = json.load(named_file_contents.contents)
        contents = JsonData(contents_dict)

        values_data: dict[str, Any] = assert_not_none(
            contents.data.get("values"), "values"
        )
        metadata: dict[str, Any] = contents.data.get("metadata", {})

        contents.mark_read({"values", "metadata"})

        values = JsonData(values_data)

        fields: dict[str, Any] = assert_not_none(
            values.data.get("fields"), "values/fields"
        )

        self.metadata_fields = JsonData(
            {
                **fields,
                **metadata,
                "instrument_methods": values.data.get("instrument_methods", []),
                "processing_methods": values.data.get("processing_methods", []),
            }
        )

        values.mark_read(
            {
                "fields",
                "instrument_methods",
                "processing_methods",
                "injections",
                "channels",
                "results",
            }
        )

        # Each injection corresponds to a measurement document
        injections_list: list[dict[str, Any]] = assert_not_none(
            values.data.get("injections"), "values/injections"
        )

        id_to_injection_data = {}
        for idx, injection_dict in enumerate(injections_list):
            injection = JsonData(injection_dict)
            injection.mark_read("fields")
            fields_dict = injection.data.get("fields")
            if not fields_dict:
                msg = f"Missing 'fields' for injection at index {idx}"
                raise AssertionError(msg)

            injection_id = fields_dict.get("InjectionId")
            if injection_id is None:
                msg = f"Missing 'InjectionId' for injection at index {idx}"
                raise AssertionError(msg)

            id_to_injection_data[injection_id] = fields_dict

        # Channels contain fields and chromatograms
        channels: list[dict[str, Any]] = values.data.get("channels", [])
        for channel_dict in channels:
            channel = JsonData(channel_dict)
            channel_fields_dict: dict[str, Any] = assert_not_none(
                channel.data.get("fields"), "channels/fields"
            )

            inj_id = channel_fields_dict.get("InjectionId")
            if inj_id is None:
                channel_id = channel_fields_dict.get("ChannelId", "Unknown")
                msg = f"Expected InjectionId in 'fields' for channel: {channel_id}"
                raise AssertionError(msg)

            # Update injection fields with channel fields
            for key, value in channel_fields_dict.items():
                if (
                    key in id_to_injection_data[inj_id]
                    and id_to_injection_data[inj_id][key] != value
                ):
                    msg = f"Mismatch between injection field and channel field for key: {key}"
                    raise AssertionError(msg)
                id_to_injection_data[inj_id][key] = value

            # Add chromatogram data if present
            chrom: list[list[float]] | None = channel.data.get("chrom")
            if chrom is not None:
                id_to_injection_data[inj_id]["chrom"] = chrom

            channel.mark_read({"fields", "chrom"})

        # Results contain peaks and calibration curves
        results: list[dict[str, Any]] = values.data.get("results", [])
        for result_dict in results:
            result = JsonData(result_dict)
            result_fields_dict: dict[str, Any] = assert_not_none(
                result.data.get("fields"), "results/fields"
            )

            inj_id = result_fields_dict.get("InjectionId")
            if inj_id is None:
                result_id = result_fields_dict.get("ResultId", "Unknown")
                msg = f"Expected InjectionId in 'fields' for result: {result_id}"
                raise AssertionError(msg)

            if "results" not in id_to_injection_data[inj_id]:
                id_to_injection_data[inj_id]["results"] = []
            id_to_injection_data[inj_id]["results"].append(result_fields_dict)

            # Add peaks if present
            peaks: list[dict[str, Any]] | None = result.data.get("peaks")
            if peaks is not None:
                id_to_injection_data[inj_id]["peaks"] = [
                    cast(dict[str, Any], peak.get("fields", {})) for peak in peaks
                ]

            # Add calibration curves if present
            curves: list[Any] | None = result.data.get("curves")
            if curves is not None:
                id_to_injection_data[inj_id]["curves"] = curves

            result.mark_read({"fields", "peaks", "curves"})

        self.injections = [JsonData(data) for data in id_to_injection_data.values()]
