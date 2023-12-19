from collections import defaultdict
import copy
import json
import os
from pathlib import Path
import re
from typing import Any, Optional

from allotropy.allotrope.schema_parser.update_units import (
    unit_name_from_iri,
    update_unit_files,
)
from allotropy.allotrope.schemas import get_schema

SCHEMAS_DIR = os.path.join(Path(__file__).parent.parent, "schemas")
SHARED_SCHEMAS_DIR = os.path.join(SCHEMAS_DIR, "shared", "definitions")
MODELS_DIR = os.path.join(Path(__file__).parent.parent, "models")
SHARED_MODELS_DIR = os.path.join(MODELS_DIR, "shared", "definitions")


class SchemaCleaner:
    def __init__(self):
        self.unit_to_name = self._load_units()
        self.missing_unit_to_iri = {}
        self.missing_referenced_units = []
        self.definitions = self._load_definitions()
        self.replaced_definitions = defaultdict(list)

    def add_missing_units(self) -> None:
        # Update unit schemas and models with all units found in cleaned schemas.
        if not self.missing_referenced_units:
            return
        update_unit_files({unit: iri for unit, iri in self.missing_unit_to_iri.items() if unit in self.missing_referenced_units})
        self.missing_referenced_units = []

    def _get_unit_name(self, unit: str) -> str:
        if unit in self.missing_unit_to_iri:
            self.missing_referenced_units.append(unit)
        return self.unit_to_name[unit]

    def _load_definitions(self) -> dict[str, Any]:
        with open(os.path.join(SHARED_SCHEMAS_DIR, "definitions.json")) as f:
            return dict(json.load(f).items())

    def _load_units(self) -> dict[str, str]:
        with open(os.path.join(SHARED_SCHEMAS_DIR, "units.json")) as f:
            units_schema = json.load(f)
            return {unit["properties"]["unit"]["const"]: name for name, unit in units_schema.items()}

    def _add_embeded_units(self, unit_schemas: dict[str, Any]):
        for unit, unit_schema in unit_schemas.items():
            if unit in self.unit_to_name:
                continue
            unit_iri = unit_schema["properties"]["unit"]["$asm.unit-iri"]
            self.missing_unit_to_iri[unit] = unit_iri
            self.unit_to_name[unit] = unit_name_from_iri(unit_iri)

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
        # Identify URL-like references, and return a sanitized version that can be followed by generation script.
        # Also returns the schema and definition name separately for use in other logic.
        # Finally, replaces references to definitons we store in common.
        ref_match = re.match(r"http://purl.allotrope.org/json-schemas/(.*schema)(\#/\$defs/)?(.*)?", str(value))
        if not ref_match:
            return None, None
        if ref_match:
            def_schema, _, def_name = ref_match.groups()
            def_schema = def_schema.replace("/", "_").replace("-", "_").replace(".", "_")
            if def_name in self.replaced_definitions.get(def_schema, []):
                return None, def_name
            return def_schema, def_name

    def _clean_ref_value(self, value: str) -> str:
        def_schema, def_name = self._get_reference(value)
        if def_schema:
            return f"#/$defs/{def_schema}/$defs/{def_name}" if def_name else f"#/$defs/{def_schema}"
        elif def_name:
            return f"#/$defs/{def_name}"
        return value

    def _clean_value(self, value: Any) -> Any:
        if isinstance(value, dict):
            return self._clean(value)
        elif isinstance(value, list):
            return [self._clean_value(v) for v in value]

        return value

    def _is_quantity_value(self, schema: dict[str, Any]) -> bool:
        # Check if this schema is a special case of allOf: [tQuantityValue}, {unit] and if so replace.
        if "allOf" not in schema or len(schema["allOf"]) != 2:
            return False
        for value in schema["allOf"]:
            if "$ref" in value and value["$ref"].endswith("$defs/tQuantityValue"):
                return True
        return False

    def _fix_quantity_value_reference(self, schema: dict[str, Any]) -> dict[str, Any]:
        for value in schema.pop("allOf"):
            if value["$ref"].endswith("$defs/tQuantityValue"):
                continue
            unit = value["$ref"].split("/")[-1]
            schema["$ref"] = f"#/$defs/tQuantityValue{self._get_unit_name(unit)}"
            return schema

        return schema

    def _clean_defs(self, schema: dict[str, Any]) -> dict[str, Any]:
        cleaned = {}
        for schema_name, defs_schema in schema["$defs"].items():
            # Replace web address reference name with a version that can be followed in datamodel-codegen
            cleaned_schema_name, _ = self._get_reference(schema_name)
            if cleaned_schema_name:
                # Units are treated specially. We rename the unit (to avoid non-variable names) and store
                # them in separate shared unit schema file, in order to allow for shared imports.
                if cleaned_schema_name.endswith("units_schema"):
                    self._add_embeded_units(defs_schema["$defs"])
                elif "$defs" in defs_schema:
                    # For other definitions, we may have a shared copy for common definitons, but not all.
                    # For these, check if the schema matches a definition in shared. If so, we will replace
                    # the reference, otherwise we leave it as it.
                    cleaned_defs = {k: {} if k == "$defs" else v for k, v in defs_schema.items()}
                    for def_name, def_schema in defs_schema["$defs"].items():
                        if self.definitions.get(def_name) == def_schema:
                            self.replaced_definitions[cleaned_schema_name].append(def_name)
                        else:
                            cleaned_defs["$defs"][def_name] = def_schema
                    if cleaned_defs["$defs"]:
                        cleaned[cleaned_schema_name] = self._clean(cleaned_defs)
            else:
                cleaned[schema_name] = self._clean(defs_schema)

        return cleaned

    def _clean(self, schema: dict[str, Any]) -> dict[str, Any]:
        cleaned = {}

        for key, value in schema.items():
            if key == "$custom":
                cleaned[key] = value
            elif key == "allOf":
                cleaned |= self._clean_allof(value)
            elif key == "$ref":
                cleaned[key] = self._clean_ref_value(value)
            else:
                cleaned[key] = self._clean_value(value)

        if self._is_quantity_value(cleaned):
            cleaned = self._fix_quantity_value_reference(cleaned)

        return cleaned

    def clean(self, schema: dict[str, Any]) -> dict[str, Any]:
        # Call clean defs first, because we store some metadata about overriden definitions that is used in
        # the main body.
        if "$defs" in schema:
            schema["$defs"] = self._clean_defs(schema)
        return self._clean(schema)

    def clean_file(self, schema_path: str) -> None:
        schema = get_schema(schema_path)
        schema = self.clean(schema)
        self.add_missing_units()
        with open(schema_path, "w") as f:
            json.dump(schema, f, indent=2)
