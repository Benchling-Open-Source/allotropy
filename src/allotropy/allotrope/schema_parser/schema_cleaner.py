import copy
import json
import os
from pathlib import Path
import re
from typing import Any, Optional

SCHEMAS_DIR = os.path.join(Path(__file__).parent.parent, "schemas")


class SchemaCleaner:
    def __init__(self):
        self.unit_to_name = self._load_units()

    def _load_units(self) -> dict[str, str]:
        with open(os.path.join(SCHEMAS_DIR, "shared", "definitions", "units.json")) as units_file:
            units_schema = json.load(units_file)
            return {unit["properties"]["unit"]["const"]: name for name, unit in units_schema.items()}

    def _add_embeded_units(self, unit_schemas: dict[str, Any]):
        for unit, unit_schema in unit_schemas.items():
            if unit in self.unit_to_name:
                continue
            # TODO: automatically add these to unit schemas
            # print(f"Unit '{unit}' missing from units schema!")
            unit_name = Path(unit_schema["properties"]["unit"]["$asm.unit-iri"]).name.split("#")[1]
            self.unit_to_name[unit] = unit_name

    def _combine_dicts(self, dict1: dict[str, Any], dict2: dict[str, Any]) -> dict[str, Any]:
        # Combines dictionaries recursively
        combined = copy.deepcopy(dict1)
        for key, value in dict2.items():
            if key in combined:
                combined[key] = self._combine_dicts(combined[key], value)
            else:
                combined[key] = value

        return combined

    def _clean_allof(self, values: list[Any]) -> dict[str, Any]:
        for value in values:
            if not isinstance(value, dict):
                # TODO: would be nice to track path to help with debugging.
                msg = "Unhandled case: expected every item in an allOf to be a dictionary"
                raise AssertionError(msg)

        if len(values) == 1:
            # datamodel-codegen can not handle single-value allOf entries.
            return self._clean_value(values[0])

        # datamodel-codegen can not handle oneOf nested inside allOf. Fix this by reversing the order,
        # making a oneOf with each possible product of allOf
        if any("oneOf" in value for value in values):
            new_values = []
            for value in [self._clean_value(v) for v in values]:
                values_list = value["oneOf"] if "oneOf" in value else [value]
                new_values = [
                    [*new_value, add_value]
                    for new_value in new_values
                    for add_value in values_list
                ] if new_values else [[value] for value in values_list]
            return self._clean_value({"oneOf": [{"allOf": values} for values in new_values]})

        return {"allOf": self._clean_value(values)}

    def _get_reference(self, value: Any) -> tuple[Optional[str], Optional[str]]:
        ref_match = re.match(r"http://purl.allotrope.org/json-schemas/(.*schema)(\#/\$defs/)?(.*)?", str(value))
        if not ref_match:
            return None, None
        if ref_match:
            def_schema, _, def_ = ref_match.groups()
            def_schema = def_schema.replace("/", "_").replace("-", "_").replace(".", "_")
            return def_schema, def_

    def _clean_value(self, value: Any) -> Any:
        if isinstance(value, dict):
            return self._clean(value)
        elif isinstance(value, list):
            return [self._clean_value(v) for v in value]

        def_schema, def_ = self._get_reference(value)
        if def_schema:
            return f"#/$defs/{def_schema}/$defs/{def_}" if def_ else f"#/$defs/{def_schema}"
        return value

    def _is_quantity_value(self, schema: dict[str, Any]) -> bool:
        if "allOf" not in schema or len(schema["allOf"]) != 2:
            return False
        for value in schema["allOf"]:
            if "$ref" in value and value["$ref"].endswith("$defs/tQuantityValue"):
                return True
        return False

    def _fix_quantity_value_reference(self, schema: dict[str, Any]) -> dict[str, Any]:
        for value in schema.pop("allOf"):
            if not value["$ref"].endswith("$defs/tQuantityValue"):
                unit = value["$ref"].split("/")[-1]
                schema["$ref"] = f"#/$defs/tQuantityValue{self.unit_to_name[unit]}"
                return schema

        return schema

    def _clean_defs(self, defs_schema: dict[str, Any]) -> dict[str, Any]:
        cleaned_defs = {}
        for key, value in defs_schema.items():
            def_schema, _ = self._get_reference(key)
            if def_schema:
                if def_schema.endswith("units_schema"):
                    self._add_embeded_units(value["$defs"])
                else:
                    cleaned_defs[def_schema] = self._clean(value)
            else:
                cleaned_defs[key] = value

        return cleaned_defs

    def _clean(self, schema: dict[str, Any]) -> dict[str, Any]:
        cleaned = {}

        for key, value in schema.items():
            if key == "allOf":
                cleaned |= self._clean_allof(value)
            else:
                cleaned[key] = self._clean_value(value)

        if self._is_quantity_value(cleaned):
            cleaned = self._fix_quantity_value_reference(cleaned)

        return cleaned

    def clean(self, schema: dict[str, Any]) -> dict[str, Any]:
        if "$defs" in schema:
            schema["$defs"] = self._clean_defs(schema["$defs"])
        return self._clean(schema)
