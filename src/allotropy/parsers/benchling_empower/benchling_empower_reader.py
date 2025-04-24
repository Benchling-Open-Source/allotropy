import json
from typing import Any, cast

from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.utils.json import JsonData
from allotropy.parsers.utils.values import assert_not_none


class BenchlingEmpowerReader:
    SUPPORTED_EXTENSIONS = "json"

    metadata_fields: dict[str, Any]
    injections: list[dict[str, Any]]
    instrument_methods: list[dict[str, Any]]
    processing_methods: list[dict[str, Any]]

    def __init__(self, named_file_contents: NamedFileContents) -> None:
        contents_dict: dict[str, Any] = json.load(named_file_contents.contents)
        contents = JsonData(contents_dict)

        # Get values dictionary
        values_data: dict[str, Any] = assert_not_none(
            contents.data.get("values"), "values"
        )
        values = JsonData(values_data)

        # Get fields and metadata
        fields: dict[str, Any] = assert_not_none(
            values.data.get("fields"), "values/fields"
        )
        metadata: dict[str, Any] = contents.data.get("metadata", {})

        self.metadata_fields = {**fields, **metadata}

        # Get methods
        self.instrument_methods = values.data.get("instrument_methods", [])
        self.processing_methods = values.data.get("processing_methods", [])

        # Each injection corresponds to a measurement document
        injections_list: list[dict[str, Any]] = assert_not_none(
            values.data.get("injections"), "values/injections"
        )

        id_to_injection = {}
        for idx, injection_dict in enumerate(injections_list):
            injection = JsonData(injection_dict)
            fields_dict = injection.data.get("fields")
            if not fields_dict:
                msg = f"Missing 'fields' for injection at index {idx}"
                raise AssertionError(msg)

            fields_json = JsonData(fields_dict)
            injection_id = fields_json.get(int, "InjectionId")
            if injection_id is None:
                msg = f"Missing 'InjectionId' for injection at index {idx}"
                raise AssertionError(msg)

            id_to_injection[injection_id] = fields_dict

        # Channels contain fields and chromatograms
        channels: list[dict[str, Any]] = values.data.get("channels", [])
        for channel_dict in channels:
            channel = JsonData(channel_dict)
            channel_fields_dict: dict[str, Any] = assert_not_none(
                channel.data.get("fields"), "channels/fields"
            )
            channel_fields = JsonData(channel_fields_dict)

            inj_id = channel_fields.get(int, "InjectionId")
            if inj_id is None:
                channel_id = channel_fields.get(str, "ChannelId", "Unknown")
                msg = f"Expected InjectionId in 'fields' for channel: {channel_id}"
                raise AssertionError(msg)

            # Update injection fields with channel fields
            for key, value in channel_fields_dict.items():
                if (
                    key in id_to_injection[inj_id]
                    and id_to_injection[inj_id][key] != value
                ):
                    msg = f"Mismatch between injection field and channel field for key: {key}"
                    raise AssertionError(msg)
                id_to_injection[inj_id][key] = value

            # Add chromatogram data if present
            chrom: list[list[float]] | None = channel.data.get("chrom")
            if chrom is not None:
                id_to_injection[inj_id]["chrom"] = chrom

        # Results contain peaks and calibration curves
        results: list[dict[str, Any]] = values.data.get("results", [])
        for result_dict in results:
            result = JsonData(result_dict)
            result_fields_dict: dict[str, Any] = assert_not_none(
                result.data.get("fields"), "results/fields"
            )
            result_fields = JsonData(result_fields_dict)

            inj_id = result_fields.get(int, "InjectionId")
            if inj_id is None:
                result_id = result_fields.get(str, "ResultId", "Unknown")
                msg = f"Expected InjectionId in 'fields' for result: {result_id}"
                raise AssertionError(msg)

            if "results" not in id_to_injection[inj_id]:
                id_to_injection[inj_id]["results"] = []
            id_to_injection[inj_id]["results"].append(result_fields_dict)

            # Add peaks if present
            peaks: list[dict[str, Any]] | None = result.data.get("peaks")
            if peaks is not None:
                id_to_injection[inj_id]["peaks"] = [
                    cast(dict[str, Any], JsonData(peak).data.get("fields", {}))
                    for peak in peaks
                ]

            # Add calibration curves if present
            curves: list[Any] | None = result.data.get("curves")
            if curves is not None:
                id_to_injection[inj_id]["curves"] = curves

        self.injections = list(id_to_injection.values())
