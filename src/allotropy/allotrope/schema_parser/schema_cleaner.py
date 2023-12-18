import copy
import re
from typing import Any


class SchemaCleaner:
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
                raise AssertionError("Unhandled case: expected every item in an allOf to be a dictionary")

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
            return {"oneOf": [{"allOf": values} for values in new_values]}

        return {"allOf": self._clean_value(values)}

    def _clean_value(self, value: Any) -> Any:
        if isinstance(value, dict):
            return self._clean(value)
        elif isinstance(value, list):
            return [self._clean_value(v) for v in value]

        ref_match = re.match(r"http://purl.allotrope.org/json-schemas/(.*schema)(\#/)?(\$defs/.*)?", str(value))
        if ref_match:
            def_schema, _, def_ = ref_match.groups()
            def_schema = def_schema.replace("/", "_").replace("-", "_").replace(".", "_")
            return f"#/$defs/{def_schema}/{def_}" if def_ else f"#/$defs/{def_schema}"
        return value

    def _clean(self, schema: dict[str, Any]) -> dict[str, Any]:
        cleaned = {}
        for key, value in schema.items():
            if key == "allOf":
                cleaned |= self._clean_allof(value)
            else:
                cleaned[key] = self._clean_value(value)

        if "$defs" in schema:
            cleaned_defs = {}
            for key, value in schema.get("$defs", {}).items():
                ref_match = re.match(r"http://purl.allotrope.org/json-schemas/(.*schema)", str(key))
                if ref_match:
                    def_schema = ref_match.groups()[0]
                    key = def_schema.replace("/", "_").replace("-", "_").replace(".", "_")
                cleaned_defs[key] = self._clean(value)
                """
                if "$defs" in value:
                    cleaned_defs |= value
                else:
                    cleaned_defs[key] = value
                """
            cleaned["$defs"] = cleaned_defs

        return cleaned

    def clean(self, schema: dict[str, Any]) -> dict[str, Any]:
        return self._clean(schema)
