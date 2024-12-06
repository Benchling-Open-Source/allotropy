import json
from typing import Any

from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.utils.values import assert_not_none


class BenchlingEmpowerReader:
    SUPPORTED_EXTENSIONS = "json"

    metadata_fields: dict[str, Any]
    injections: list[dict[str, Any]]

    def __init__(self, named_file_contents: NamedFileContents) -> None:
        contents: dict[str, Any] = json.load(named_file_contents.contents)
        values: dict[str, Any] = assert_not_none(contents.get("values"), "values")

        self.metadata_fields = assert_not_none(values.get("fields"), "values/fields")

        # Each injection corresponds to a measurement document
        injections: list[dict[str, Any]] = assert_not_none(
            values.get("injections"), "values/injections"
        )
        for idx, injection in enumerate(injections):
            if "fields" not in injection:
                msg = f"Missing 'fields' for injection at index {idx}"
                raise AssertionError(msg)
            if "InjectionId" not in injection["fields"]:
                msg = f"Missing 'InjectionId' for injection at index {idx}"
                raise AssertionError(msg)
        id_to_injection = {
            injection["fields"]["InjectionId"]: injection["fields"]
            for injection in injections
        }

        # Channels contain fields and chromatograms
        channels: list[dict[str, Any]] = values.get("channels", [])
        for channel in channels:
            fields: dict[str, Any] = assert_not_none(
                channel.get("fields"), "channels/fields"
            )
            if (inj_id := fields.get("InjectionId")) is None:
                msg = f"Expected InjectionId in 'fields' for channel: {fields['ChannelId']}"
                raise AssertionError(msg)
            for key, value in fields.items():
                if (
                    key in id_to_injection[inj_id]
                    and id_to_injection[inj_id][key] != value
                ):
                    msg = f"Mismatch between injection field and channel field for key: {key}"
                    raise AssertionError(msg)
                id_to_injection[inj_id][key] = value
            if "chrom" in channel:
                id_to_injection[inj_id]["chrom"] = channel["chrom"]

        # Results contain peaks and calibration cureves
        results: list[dict[str, Any]] = values.get("results", [])
        for result in results:
            fields = assert_not_none(result.get("fields"), "results/fields")
            if (inj_id := fields.get("InjectionId")) is None:
                msg = (
                    f"Expected InjectionId in 'fields' for result: {fields['ResultId']}"
                )
                raise AssertionError(msg)
            for key, value in fields.items():
                if (
                    key in id_to_injection[inj_id]
                    and id_to_injection[inj_id][key] != value
                ):
                    msg = f"Mismatch between injection field and result field for key: {key}"
                    raise AssertionError(msg)
                id_to_injection[inj_id][key] = value
            if "peaks" in result:
                id_to_injection[inj_id]["peaks"] = [
                    peak["fields"] for peak in result["peaks"]
                ]
            if "curves" in result:
                id_to_injection[inj_id]["curves"] = result["curves"]

        self.injections = list(id_to_injection.values())
