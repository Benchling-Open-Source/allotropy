from collections import defaultdict
import copy
import itertools
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

        self.enclosing_schema_name: Optional[str] = None
        self.enclosing_schema_keys: Optional[dict[str, Any]] = None

    def add_missing_units(self) -> None:
        # Update unit schemas and models with all units found in cleaned schemas.
        if not self.missing_referenced_units:
            return
        update_unit_files({unit: iri for unit, iri in self.missing_unit_to_iri.items() if unit in self.missing_referenced_units})
        self.missing_referenced_units = []

    def _is_unit_name_ref(self, ref: str) -> Optional[str]:
        return ref.split("/")[-1] in self.unit_to_name.values()

    def _get_unit_name(self, unit: str) -> Optional[str]:
        unit_match = re.match(r"(?:\#/\$defs/)?(?:.*schema_)?(.*)", unit)
        if not unit_match:
            return None
        unit = unit_match.groups()[0]
        if unit not in self.unit_to_name:
            return None
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

    def _is_object_schema(self, value: dict[str, Any]) -> bool:
        return isinstance(value, dict) and "properties" in value

    def _cross_product_sets(self, sets: list[Any]) -> list[set[Any]]:
        include_empty_set = set() in sets
        if include_empty_set:
            sets.remove(set())
        result = [
            set.union(*x)
            for i in range(len(sets) + 1)
            for x in itertools.combinations(sets, i) if x
        ]
        if include_empty_set:
            result.insert(0, set())
        return result

    def _combine_anyof_values(self, values: list[dict[str, Any]]) -> Any:
        if not all(self._is_object_schema(value) for value in values):
            if any(self._is_object_schema(value) for value in values):
                msg = f"_combine_anyof_values can only be called with list of object schema dictionaries: {values}"
                raise AssertionError(msg)
            return values

        combined = {}
        conflicts = defaultdict(list)
        required_keys_sets = []
        for object_schema in values:
            if "required" in object_schema:
                required_keys_sets.append(set(object_schema["required"]))
            elif set() not in required_keys_sets:
                required_keys_sets.append(set())
            for key, value in object_schema.get("properties", {}).items():
                if key in conflicts:
                    conflicts[key].append(value)
                elif key in combined:
                    conflicts[key] = [combined.pop(key), value]
                else:
                    combined[key] = value

        # Combine conflicting values if possible, fan out where not possible.
        conflict_values: list[Any] = []
        for key, values in conflicts.items():
            if not all(v is None or isinstance(v, type(values[0])) for v in values):
                msg = f"Error: cannot combine keys with different types in {key}: {values}"
                raise AssertionError(msg)

            cleaned = [self._clean_value(v) for v in values]
            if self._is_object_schema(cleaned[0]):
                conflict_values.append([{key: v} for v in self._combine_anyof_values(cleaned)])
            else:
                conflict_values.append([{key: v} for v in cleaned])

        # Cross-product all lists of values that could not be combined.
        results = [combined]
        for conflict_value_list in conflict_values:
            new_results = []
            for value in conflict_value_list:
                for result in results:
                    new_results.append(result | value)
            results = new_results

        # Cross-product all lists of required keys
        all_required_sets = self._cross_product_sets(required_keys_sets)

        # Transform back into object schemas
        final_results = []
        all_required_keys = set.union(*required_keys_sets) if required_keys_sets else [set()]
        for result in results:
            for required_key_set in all_required_sets:
                final_result = {
                    "properties": {
                        key: value for key, value in result.items() if key in required_key_set or key not in all_required_keys
                    },
                    "required": sorted(required_key_set)
                }
                if not final_result["required"]:
                    final_result.pop("required")
                if final_result not in final_results:
                    final_results.append(final_result)

        return final_results

    def _clean_anyof(self, values: list[Any]) -> dict[str, Any]:
        for value in values:
            if not isinstance(value, dict):
                # TODO: would be nice to track path to help with debugging.
                msg = "Unhandled case: expected every item in an anyOf to be a dictionary"
                raise AssertionError(msg)

        combined = self._combine_anyof_values(values)

        if len(combined) == 1:
            return self._clean_value(combined[0])
        return {"anyOf": self._clean_value(combined)}

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

        cleaned_values = self._clean_value(values)

        if self._is_quantity_value(cleaned_values):
            return self._fix_quantity_value_reference(cleaned_values)

        return {"allOf": cleaned_values}

    def _get_reference(self, value: Any) -> tuple[Optional[str], Optional[str]]:
        # Identify URL-like references, and return a sanitized version that can be followed by generation script.
        # Return schema_name and definition name separately for use in other logic.
        ref_match = re.match(r"http://purl.allotrope.org/json-schemas/(.*schema)(\#/\$defs/)?(.*)?", str(value))
        if not ref_match:
            return None, None
        schema_name, _, def_name = ref_match.groups()
        schema_name = re.subn(r"[\/\-\.]", "_", schema_name)[0]
        return schema_name, def_name

    def _clean_ref_value(self, value: str) -> str:
        schema_name, def_name = self._get_reference(value)
        if def_name in self.replaced_definitions.get(schema_name, []):
            return f"#/$defs/{def_name}"
        elif def_name and self._get_unit_name(def_name):
            return f"#/$defs/{self._get_unit_name(def_name)}"

        if schema_name and def_name:
            cleaned_ref = f"#/$defs/{schema_name}/$defs/{def_name}"
        elif schema_name or def_name:
            cleaned_ref = f"#/$defs/{schema_name or def_name}"
        else:
            cleaned_ref = value

        def_name = cleaned_ref.split("/")[-1]

        if self.enclosing_schema_name and def_name not in self.definitions and def_name in self.enclosing_schema_keys:
            cleaned_ref = f"#/$defs/{self.enclosing_schema_name}/$defs/{def_name}"

        return cleaned_ref

    def _clean_value(self, value: Any) -> Any:
        if isinstance(value, dict):
            return self._clean(value)
        elif isinstance(value, list):
            return [self._clean_value(v) for v in value]
        return value

    def _is_quantity_value(self, values: list[dict[str, Any]]) -> bool:
        # Check if this schema is a special case of allOf: [tQuantityValue, unit] and if so replace.
        if len(values) != 2:
            return False
        quantity_value_found = False
        unit_found = False
        for value in values:
            if "$ref" not in value:
                return False
            if value["$ref"].endswith("$defs/tQuantityValue"):
                quantity_value_found = True
            if self._is_unit_name_ref(value["$ref"]):
                unit_found = True
        return quantity_value_found and unit_found

    def _fix_quantity_value_reference(self, values: list[dict[str, Any]]) -> dict[str, Any]:
        for value in values:
            if value["$ref"].endswith("$defs/tQuantityValue"):
                continue
            unit_name = value["$ref"].split("/")[-1]
            return {"$ref": f"#/$defs/tQuantityValue{unit_name}"}

        msg = f"Failed to find value unit in quantity value reference: {values}"
        raise AssertionError(msg)

    def _clean_defs(self, schema: dict[str, Any]) -> dict[str, Any]:
        for schema_name, defs_schema in schema["$defs"].items():
            # Replace web address reference name with a version that can be followed in datamodel-codegen
            cleaned_schema_name = self._get_reference(schema_name)[0] or schema_name
            # Units are treated specially. We rename the unit (to avoid non-variable names) and store
            # them in separate shared unit schema file, in order to allow for shared imports.
            if cleaned_schema_name.endswith("units_schema"):
                self._add_embeded_units(defs_schema["$defs"])
            elif "$defs" in defs_schema:
                # Store defs that are replaced with definitions in common/definitions before cleaning.
                # NOTE: this does not attempt to handle futher nested $defs, in schemas, but we have not
                # observed that in any schema files yet.
                for def_name, def_schema in defs_schema["$defs"].items():
                    if self.definitions.get(def_name) == def_schema:
                        self.replaced_definitions[cleaned_schema_name].append(def_name)

        cleaned = {}
        for schema_name, defs_schema in schema["$defs"].items():
            # Replace web address reference name with a version that can be followed in datamodel-codegen
            cleaned_schema_name = self._get_reference(schema_name)[0] or schema_name
            if cleaned_schema_name.endswith("units_schema"):
                continue
            elif "$defs" in defs_schema:
                # For nested definitions, we need to flatten then into a single $defs entry in order
                # for the generation script to work correctly.
                self.enclosing_schema_name = cleaned_schema_name
                self.enclosing_schema_keys = defs_schema["$defs"].keys()
                cleaned_defs = {}
                for def_name, def_schema in defs_schema["$defs"].items():
                    if def_name not in self.replaced_definitions[cleaned_schema_name]:
                        cleaned_defs[def_name] = self._clean(def_schema)
                self.enclosing_schema_name = None
                self.enclosing_schema_keys = None
                cleaned[cleaned_schema_name] = {"$defs": cleaned_defs}
            else:
                cleaned[cleaned_schema_name] = self._clean(defs_schema)

        return cleaned

    def _clean(self, schema: dict[str, Any]) -> dict[str, Any]:

        if "anyOf" in schema and self._is_object_schema(schema):
            values = schema.pop("anyOf")
            schema = self._clean_anyof([schema, *values])

        cleaned = {}
        for key, value in schema.items():
            if key == "$custom":
                cleaned[key] = value
            elif key == "allOf":
                cleaned |= self._clean_allof(value)
            elif key == "$ref":
                cleaned[key] = self._clean_ref_value(value)
            elif key == "anyOf":
                cleaned |= self._clean_anyof(value)
            else:
                cleaned[key] = self._clean_value(value)

        return cleaned

    def clean(self, schema: dict[str, Any]) -> dict[str, Any]:
        # Call clean defs first, because we store some metadata about overriden definitions that is used in
        # the main body.
        cleaned = copy.deepcopy(schema)
        if "$defs" in cleaned:
            cleaned["$defs"] = self._clean_defs(cleaned)
        return self._clean(cleaned)

    def clean_file(self, schema_path: str) -> None:
        schema = get_schema(schema_path)
        schema = self.clean(schema)
        self.add_missing_units()
        with open(schema_path, "w") as f:
            json.dump(schema, f, indent=2)
