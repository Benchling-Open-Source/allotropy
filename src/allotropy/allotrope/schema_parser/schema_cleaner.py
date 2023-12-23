from collections import defaultdict
import copy
import itertools
from itertools import chain, combinations
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

        self.cleaning_defs = False
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

    def _is_array_schema(self, schema: dict[str, Any]) -> bool:
        return isinstance(schema, dict) and "items" in schema

    def _is_object_schema(self, schema: dict[str, Any]) -> bool:
        return isinstance(schema, dict) and "properties" in schema or "required" in schema

    def _is_class_schema(self, schema: dict[str, Any]) -> bool:
        return self._is_object_schema(schema) or self._is_array_schema(schema)

    def _create_object_schema(self, properties: dict[str, Any], required: list[str]):
        schema = {"properties": properties}
        if required:
            schema["required"] = required
        return schema

    def _try_combine_object_schemas(self, schemas: list[dict[str, Any]]) -> dict[str, Any]:
        print("HERE?")
        combined_props = {}
        for schema in schemas:
            for key, value in schema.get("properties", {}).items():
                if key in combined_props:
                    if self._is_class_schema(value):
                        combined_props[key] = self._try_combine_schemas([combined_props[key], value])
                    elif "allOf" in value:
                        values = value["allOf"]
                        if "allOf" in combined_props[key]:
                            values.extend(combined_props[key]["allOf"])
                        elif self._is_class_schema(combined_props[key]):
                            values.append(combined_props[key])
                        else:
                            assert False, "Bad allOf combo"
                        combined_props[key] = self._combine_allof_values(values)
                    elif value != combined_props[key]:
                        msg = f"Error combining schemas, conflicting values for key '{key}': ['{value}', '{combined_props[key]}']"
                        raise AssertionError(msg)
                else:
                    combined_props[key] = value

        print("RETURNING")
        return self._create_object_schema(
            combined_props,
            sorted(set.union(*[set(schema.get("required", [])) for schema in schemas]))
        )

    def _try_combine_schemas(self, schemas: list[dict[str, Any]]) -> dict[str, Any]:
        if self._is_array_schema(schemas[0]):
            if not all(self._is_array_schema(schema) for schema in schemas):
                raise AssertionError("Could array and object schemas")
            min_items = schemas[0].get("minItems", 0)
            if not all(schema.get("minItems", 0) == min_items for schema in schemas):
                raise AssertionError("Could not combine because minItems different")
            return {
                "items": self._try_combine_object_schemas([schema["items"] for schema in schemas]),
                "minItems": min_items
            }

        print("HERE")
        return self._try_combine_object_schemas(schemas)

    def _get_required(self, schema: dict[str, Any]) -> list[str]:
        if self._is_array_schema(schema):
            return schema["items"].get("required", [])
        return schema.get("required", [])

    def _combine_anyof_values(self, values: list[dict[str, Any]]) -> Any:
        if not all(self._is_class_schema(value) for value in values):
            return values

        # For schemas without required values, we want to combine them as much as possible, but sometimes
        # can't due to keys with conflcting values. To do this, we take the power set of combinations and
        # try to combine each. When we succeed, remove other sets that are covered by that powerset.
        # Then, for schemas with required keys, we try to combine with schema avaiable, and overwrite
        # conflicting keys if they are optional, only failing if two required keys conflict.
        # If there are no required keys, we can try to combine all of the schemas, this will only fail if there
        # are conflicting defintions for keys. This is possible, but not very common in practice. This special
        # case helps short circuit the power set explosion for long lists of anyOf that just add a couple fields.
        any_required_keys = self._required_anywhere(values)
        if not self._required_anywhere(values):
            try:
                return [self._try_combine_schemas(values)]
            except AssertionError:
                pass

        successful = []
        for i in range(2**len(values) - 1, 0, -1):
            indices = {j for j, digit in enumerate(f"{i:b}"[::-1]) if digit == "1"}
            # If there are not any required keys we can check if the set is covered first.
            if not any_required_keys and any(indices.issubset(schema_indices) for _, schema_indices in successful):
                continue

            # If there are required keys, we need to combine the schemas first so we can cross check the required
            # keys against covering sets.
            try:
                combined = self._try_combine_schemas([values[j] for j in indices])
            except AssertionError:
                continue
            covered = False
            for schema, schema_indices in successful:
                if indices.issubset(schema_indices) and self._get_required(combined) == self._get_required(schema):
                    covered = True
                    break
            if not covered:
                successful.append((combined, indices))

        return [schema for schema, _ in successful]

    def _clean_anyof(self, values: list[Any]) -> dict[str, Any]:
        values = self._clean_value(values)
        combined = self._combine_anyof_values(values)

        if len(combined) == 1:
            return combined[0]
        return {"anyOf": combined}

    def _dereference_value(self, value: dict[str, Any]) -> dict[str, Any]:
        result = copy.deepcopy(value)
        if "$ref" in value and not self._is_unit_name_ref(value["$ref"]):
            # NOTE: assumes ref is cleaned
            def_1, def_2 = re.match(r"\#/\$defs/(\w*)(?:/\$defs/)?(\w*)?", result.pop("$ref")).groups()
            if def_2:
                result |= self.definitions[def_1]["$defs"][def_2]
            else:
                result |= self.definitions[def_1]
        for group_key in ["anyOf", "allOf", "oneOf"]:
            if group_key in value:
                result[group_key] = self._dereference_values(result[group_key])
        if "properties" in value:
            result["properties"] = self._dereference_value(value["properties"])
        if "items" in value:
            result["items"] = self._dereference_value(value["items"])
        return result

    def _dereference_values(self, values: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [self._dereference_value(value) for value in values]

    def _required_anywhere(self, value: Any) -> bool:
        if isinstance(value, dict):
            return any(k == "required" or self._required_anywhere(v) for k, v in value.items())
        elif isinstance(value, list):
            return any(self._required_anywhere(v) for v in value)
        return False

    def _invert_allof(self, values: list[Any], key: str):
        new_values = []
        for value in values:
            values_list = value[key] if key in value else [value]
            new_values = [
                [*new_value, add_value]
                for new_value in new_values
                for add_value in values_list
            ] if new_values else [[value] for value in values_list]
        return self._clean_value({key: [{"allOf": values} for values in new_values]})

    def _combine_allof_values(self, values: list[dict[str, Any]]) -> Any:
        print("IN COMBINE ALLOF")
        for v in values:
            print(v)
        if not all(self._is_class_schema(value) for value in values):
            print("OH NO")
            if any(self._is_class_schema(value) for value in values):
                for value in values:
                    if not self._is_class_schema(value):
                        print("!!!!!")
                        print(value)
                msg = f"_combine_allof_values can only be called with list of object schema dictionaries: {values}"
                raise AssertionError(msg)
            return values

        return self._try_combine_schemas(values)

    def _clean_allof(self, values: list[Any]) -> dict[str, Any]:
        if not all(isinstance(value, dict) for value in values):
            msg = "Unhandled case: expected every item in an allOf to be a dictionary"
            raise AssertionError(msg)

        values = self._clean_value(values)

        if len(values) == 1:
            # datamodel-codegen can not handle single-value allOf entries.
            return values[0]

        # datamodel-codegen can not handle oneOf nested inside allOf. Fix this by reversing the order,
        # making a oneOf with each possible product of allOf
        if any("oneOf" in value for value in values):
            return self._invert_allof(values, "oneOf")

        # This must come after fixing oneOf because oneOf may break into multiple quantity values
        if self._is_quantity_value(values):
            return self._fix_quantity_value_reference(values)

        # Deference values and check for oneOf/anyOf inversion again.
        derefed_values = self._clean_value(self._dereference_values(values))
        if any("oneOf" in value for value in derefed_values):
            return self._invert_allof(derefed_values, "oneOf")

        if any("anyOf" in value for value in values):
            return self._invert_allof(derefed_values, "anyOf")

        print("\n\n\n============== COMBINING ALLOF VALUES ===================\n\n\n")
        import json
        for v in derefed_values:
            print("<---------------------->")
            print(json.dumps(v, indent=4))
        # We don't combine allOf for definitions because we don't want to flatten definitions and prevent
        # inheritance in generated dataclasses.
        if not self.cleaning_defs:
            # If any object in the allOf has required fields, we must combine them in order for the generation
            # script to generate valid dataclasses. This is because dataclass inheritance with optional fields
            # is broken in python<3.10.
            if self._required_anywhere(derefed_values):
                return self._combine_allof_values(derefed_values)
            # Otherwise, we try to combine the schemas in order to error if there are any conflicting keys,
            # but we don't save the result.
            self._try_combine_schemas(derefed_values)

        return {"allOf": values}

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
        self.cleaning_defs = True
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
                self.definitions[cleaned_schema_name] = {"$defs": {}}
                for def_name, def_schema in defs_schema["$defs"].items():
                    if self.definitions.get(def_name) == def_schema:
                        self.replaced_definitions[cleaned_schema_name].append(def_name)
                    else:
                        self.definitions[cleaned_schema_name]["$defs"][def_name] = def_schema
            else:
                self.definitions[cleaned_schema_name] = defs_schema

        cleaned = {}
        for schema_name, defs_schema in schema["$defs"].items():
            # Replace web address reference name with a version that can be followed in datamodel-codegen
            cleaned_schema_name = self._get_reference(schema_name)[0] or schema_name
            if cleaned_schema_name.endswith("units_schema"):
                continue
            elif "$defs" in defs_schema:
                # For references nested inside definitions, we need to change the ref into the full reference
                # path in order for the generation script to find them. e.g.
                #   {"someSchema": {"$ref": "#/$defs/someThing"}}
                #       becomes
                #   {"someSchema": {"$ref": "#/$defs/someSchema/$defs/someThing"}}
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

        self.definitions |= cleaned
        self.cleaning_defs = False
        return cleaned

    def _clean(self, schema: dict[str, Any]) -> dict[str, Any]:
        if self._is_object_schema(schema) and ("anyOf" in schema or "oneOf" in schema):
            fixed = {
                "allOf": [
                    self._create_object_schema(schema.get("properties", {}), schema.get("required", [])),
                    *schema.get("allOf", [])
                ],
            }
            if "anyOf" in schema:
                fixed["allOf"].append({"anyOf": schema["anyOf"]})
            if "oneOf" in schema:
                fixed["allOf"].append({"oneOf": schema["oneOf"]})
            return self._clean(fixed)

        cleaned = {}
        for key, value in schema.items():
            if key in ("$defs", "$custom"):
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
