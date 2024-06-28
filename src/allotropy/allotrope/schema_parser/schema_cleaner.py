from collections import defaultdict
from collections.abc import Callable
import copy
import json
from pathlib import Path
import re
from typing import Any
import urllib.parse

from allotropy.allotrope.schema_parser.update_units import unit_name_from_iri
from allotropy.allotrope.schemas import (
    get_schema,
    get_shared_definitions,
    get_shared_unit_definitions,
)


def _is_array_schema(schema: dict[str, Any]) -> bool:
    return isinstance(schema, dict) and "items" in schema


def _is_direct_object_schema(schema: dict[str, Any]) -> bool:
    return (
        isinstance(schema, dict)
        and "type" in schema
        and schema["type"] == "object"
        or any(key in schema for key in ["properties", "required"])
    )


def _is_composed_object_schema(schema: dict[str, Any]) -> bool:
    return isinstance(schema, dict) and any(
        key in schema for key in ["anyOf", "oneOf", "allOf"]
    )


def _is_object_schema(schema: dict[str, Any]) -> bool:
    return _is_direct_object_schema(schema) or _is_composed_object_schema(schema)


def _create_object_schema(
    properties: dict[str, Any], required: list[str]
) -> dict[str, Any]:
    schema = {"properties": properties}
    if required:
        schema["required"] = required  # type: ignore[assignment]
    return schema


def _is_class_schema(schema: dict[str, Any]) -> bool:
    return _is_object_schema(schema) or _is_array_schema(schema)


def _is_ref_schema(schema: dict[str, Any]) -> bool:
    return isinstance(schema, dict) and "$ref" in schema


def _is_ref_schema_array(schema: dict[str, Any]) -> bool:
    return _is_array_schema(schema) and _is_ref_schema(schema["items"])


def _escape_def_name(def_name: str) -> str:
    return urllib.parse.unquote(def_name).replace("~1", "/")


def _get_def_name(reference: str) -> str:
    return _escape_def_name(reference.split("/")[-1])


def _get_reference_from_url(value: Any) -> tuple[str | None, str | None]:
    # Identify URL-like references, and return a sanitized version that can be followed by generation script.
    # Return schema_name and definition name separately for use in other logic.
    ref_match = re.match(
        r"http://purl.allotrope.org/json-schemas/(.*schema)(\#/\$defs/)?(.*)?",
        str(value),
    )
    if not ref_match:
        return None, None
    schema_name, _, def_name = ref_match.groups()
    schema_name = re.subn(r"[\/\-\.]", "_", schema_name)[0]
    return schema_name, _escape_def_name(def_name)


def _get_required(schema: dict[str, Any]) -> list[str]:
    if _is_array_schema(schema):
        required = schema["items"].get("required", [])
    else:
        required = schema.get("required", [])
    if not isinstance(required, list):
        msg = f"Invalid items in schema: {schema}"
        raise AssertionError(msg)
    return required


def _all_values_equal(values: list[Any]) -> bool:
    return len(values) <= 1 or all(value == values[0] for value in values[1:])


def _should_filter_key(key: str) -> bool:
    return key in (
        "if",
        "then",
        "prefixItems",
        "contains",
        "$comment",
        "minItems",
        "maxItems",
    )


def _should_skip_key(key: str) -> bool:
    return key in ("$defs", "$custom")


def _validate_dictionary_type(dict_value: Any) -> dict[str, Any]:
    if not isinstance(dict_value, dict):
        msg = f"Invalid result, expected dictionary: {dict_value}"
        raise AssertionError(msg)
    return dict_value


def _powerset_indices_from_index(index: int) -> set[int]:
    # Returns the list of indices that appear in the permutation of the powerset at index.
    # Does this by doing the binary expansion of the index, and then return the digits that are 1.
    return {j for j, digit in enumerate(f"{index:b}"[::-1]) if digit == "1"}


class SchemaCleaner:
    def __init__(self) -> None:
        # These are used to track unit references for auto-generating units file.
        self.unit_to_name: dict[str, str] = {}
        self.unit_to_iri: dict[str, str] = {}
        self.referenced_units: set[str] = set()
        for unit_schema in get_shared_unit_definitions().values():
            self._add_unit(
                unit=unit_schema["properties"]["unit"]["const"],
                unit_iri=unit_schema["properties"]["unit"]["$asm.unit-iri"],
            )
        # These are used to track definitions from shared/..., to properly replace the references.
        self.replaced_definitions: defaultdict[str, list[str]] = defaultdict(list)
        self.definitions = get_shared_definitions()

        # These are only used when cleaning definition schemas, and are needed to properly
        # dereference definition references. Though this smells, the flag is nested so deep in the
        # code, that it would be impractical to send this all the way down, and I think this is the
        # lesser evil.
        self.enclosing_schema_name: str | None = None
        self.enclosing_schema_keys: dict[str, Any] | None = None

    def _is_unit_name_ref(self, ref: str) -> bool:
        return _get_def_name(ref) in self.unit_to_name.values()

    def _add_unit(self, unit: str, unit_iri: str) -> None:
        self.unit_to_name[unit] = unit_name_from_iri(unit_iri)
        self.unit_to_iri[unit] = unit_iri

    def _is_quantity_value(self, values: list[dict[str, Any]]) -> bool:
        # Check if this schema is a special case of allOf: [tQuantityValue, unit] and if so replace.
        if len(values) != 2:  # noqa: PLR2004
            return False
        quantity_value_found = False
        unit_found = False
        for value in values:
            if not _is_ref_schema(value):
                return False
            if _get_def_name(value["$ref"]) == "tQuantityValue":
                quantity_value_found = True
            if self._is_unit_name_ref(value["$ref"]):
                unit_found = True
        return quantity_value_found and unit_found

    def _fix_quantity_value_reference(
        self, values: list[dict[str, Any]]
    ) -> dict[str, Any]:
        for value in values:
            def_name = _get_def_name(value["$ref"])
            if def_name == "tQuantityValue":
                continue
            return {"$ref": f"#/$defs/tQuantityValue{def_name}"}

        msg = f"Failed to find value unit in quantity value reference: {values}"
        raise AssertionError(msg)

    def _try_combine_object_schemas(
        self, schemas: list[dict[str, Any]]
    ) -> dict[str, Any]:
        # Try to combine a flattened list of object schemas
        if any(_is_array_schema(schema) for schema in schemas):
            msg = "Unexpected array schema in _try_combine_object_schemas"
            raise AssertionError(msg)

        if any(_is_composed_object_schema(schema) for schema in schemas):
            msg = "Unexpected composed object schema in _try_combine_object_schemas"
            raise AssertionError(msg)

        all_values = defaultdict(list)
        for schema in schemas:
            for key, value in schema.get("properties", {}).items():
                all_values[key].append(value)

        combined_props = {}
        for key, values in dict(all_values).items():
            if _all_values_equal(values):
                combined_props[key] = values[0]
            elif all(_is_class_schema(value) for value in values):
                combined_props[key] = self._combine_allof(values)
            elif any(
                _is_ref_schema(value) or _is_ref_schema_array(value) for value in values
            ):
                combined_props[key] = self._combine_allof(
                    self._dereference_values(values)
                )
            else:
                msg = f"Error combining schemas, conflicting values for key '{key}': {[f'{value}' for value in values]}"
                raise AssertionError(msg)

        return _create_object_schema(
            combined_props,
            sorted(set.union(*[set(schema.get("required", [])) for schema in schemas])),
        )

    def _try_combine_schemas(self, schemas: list[dict[str, Any]]) -> dict[str, Any]:
        schemas = self._flatten_schemas(schemas)

        # When combining schemas, we need to detect anyOf as we do when cleaning allOf, but here we force
        # combining values afterwards.
        if any("anyOf" in schema for schema in schemas):
            schemas = self._invert_allof(schemas, "anyOf")["anyOf"]
            return {
                "anyOf": [self._combine_allof(schema["allOf"]) for schema in schemas]
            }

        # Combine array schemas by combining their inner values.
        if any(_is_array_schema(schema) for schema in schemas):
            if not all(_is_array_schema(schema) for schema in schemas):
                msg = f"Could not combine array and object schemas: {schemas}"
                raise AssertionError(msg)
            return {
                "items": self._try_combine_schemas(
                    [schema["items"] for schema in schemas]
                )
            }

        return self._try_combine_object_schemas(schemas)

    def _flatten_schema(self, value: dict[str, Any]) -> dict[str, Any]:
        # Flattens a composed schema into a single list of schemas and combines them.
        if not _is_composed_object_schema(value):
            return value

        value = copy.deepcopy(value)
        allof_values = value.pop("allOf", [])
        if "anyOf" in value:
            allof_values.append({"anyOf": value.pop("anyOf")})
        if "oneOf" in value:
            if len(value["oneOf"]) > 1:
                msg = "Cannot flatten oneOf with more than one value in _flatten_schema"
                raise AssertionError(msg)
            allof_values.append(value.pop("oneOf")[0])

        if _is_class_schema(value):
            allof_values.append(value)

        if len(allof_values) == 1 and "allOf" not in allof_values[0]:
            return _validate_dictionary_type(allof_values[0])

        return _validate_dictionary_type(self._combine_allof_schemas(allof_values))

    def _flatten_schemas(self, values: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [self._flatten_schema(value) for value in values]

    def _dereference_value(self, value: dict[str, Any]) -> dict[str, Any]:
        # From a reference schema ({"$ref": <pointer>}) returns the specified schema
        result = copy.deepcopy(value)
        if _is_ref_schema(value):
            if (
                self._is_unit_name_ref(value["$ref"])
                or "tQuantityValue" in value["$ref"]
            ):
                return result
            # NOTE: assumes ref is cleaned.
            # NOTE: we do not further dereference values because we don't want to remove all
            # definitions and mess up class inheritance. We will do so if needed in combine_schemas
            reference = result.pop("$ref")
            match = re.match(r"\#/\$defs/(\w*)(?:/\$defs/)?(\w*)?", reference)
            if not match:
                msg = f"Invalid reference, it may not have been cleaned: {reference}"
                raise AssertionError(msg)
            def_1, def_2 = match.groups()
            if def_2:
                result |= self._dereference_value(
                    self.definitions[def_1]["$defs"][def_2]
                )
            else:
                result |= self._dereference_value(self.definitions[def_1])
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
        # Returns True is "required" key is found anywhere in a value recursively.
        # Used to check if there are any reqiured keys in a schema to determine if it should be combined.
        if _is_ref_schema(value):
            if (
                self._is_unit_name_ref(value["$ref"])
                or "QuantityValue" in value["$ref"]
            ):
                return False
            return self._required_anywhere(self._dereference_value(value))
        if isinstance(value, dict):
            return any(
                k == "required" or self._required_anywhere(v) for k, v in value.items()
            )
        elif isinstance(value, list):
            return any(self._required_anywhere(v) for v in value)
        return False

    def _combine_anyof_schemas(
        self, schemas: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        # For schemas without required values, we want to combine them as much as possible, but sometimes
        # can't due to keys with conflcting values. To do this, we take the power set of combinations and
        # try to combine each. When we succeed, remove other sets that are covered by that powerset.
        any_required_keys = self._required_anywhere(schemas)
        if not self._required_anywhere(schemas):
            try:
                return [self._try_combine_schemas(schemas)]
            except AssertionError:
                pass

        successful: list[tuple[dict[str, Any], set[int]]] = []
        # total = 2**len(schemas) - 1
        for index in range(2 ** len(schemas) - 1, 0, -1):
            indices = _powerset_indices_from_index(index)
            # If there are not any required keys we can check if the set is covered first.
            if not any_required_keys and any(
                indices.issubset(schema_indices) for _, schema_indices in successful
            ):
                continue

            # If there are required keys, we need to combine the schemas first so we can cross check the required
            # keys against covering sets.
            try:
                combined = self._try_combine_schemas([schemas[j] for j in indices])
            except AssertionError:
                continue
            covered = False
            for schema, schema_indices in successful:
                if indices.issubset(schema_indices) and _get_required(
                    combined
                ) == _get_required(schema):
                    covered = True
                    break
            if not covered:
                successful.append((combined, indices))

        return [schema for schema, _ in successful]

    def _combine_anyof(self, values: list[Any]) -> dict[str, Any]:
        if all(_is_class_schema(value) for value in values):
            values = self._combine_anyof_schemas(values)

        return _validate_dictionary_type(
            {"anyOf": values} if len(values) > 1 else values[0]
        )

    def _invert_allof(self, schemas: list[dict[str, Any]], key: str) -> dict[str, Any]:
        new_schemas: list[list[dict[str, Any]]] = []
        for schema in schemas:
            schemas_list = schema[key] if key in schema else [schema]
            new_schemas = (
                [
                    [*new_schema, add_schema]
                    for new_schema in new_schemas
                    for add_schema in schemas_list
                ]
                if new_schemas
                else [[schema] for schema in schemas_list]
            )
        return {key: [{"allOf": schemas} for schemas in new_schemas]}

    def _combine_allof_schemas(
        self, schemas: list[dict[str, Any]]
    ) -> dict[str, Any] | list[dict[str, Any]]:
        if not all(_is_class_schema(schema) for schema in schemas):
            if any(_is_class_schema(schema) for schema in schemas):
                msg = f"_combine_allof_schemas can only be called with a list of object schema dictionaries: {schemas}"
                raise AssertionError(msg)

            return schemas

        return self._try_combine_schemas(schemas)

    def _combine_allof(self, values: list[Any]) -> dict[str, Any]:
        if not all(isinstance(value, dict) for value in values):
            msg = "Unhandled case: expected every item in an allOf to be a dictionary"
            raise AssertionError(msg)

        if _all_values_equal(values):
            return _validate_dictionary_type(values[0])

        # If we are trying to combine tQuantityValue with tQuantityValue units, we can do so if there are
        # not conflicting units.
        if all(
            _is_ref_schema(schema) and "QuantityValue" in schema["$ref"]
            for schema in values
        ):
            unique = {_get_def_name(schema["$ref"]) for schema in values} - {
                "tQuantityValue"
            }
            if len(unique) == 1:
                return {"$ref": f"#/$defs/{next(iter(unique))}"}
            msg = f"Unable to combine multiple different tQuantityValue references: {values}"
            raise AssertionError(msg)

        # datamodel-codegen can not handle oneOf nested inside allOf. Fix this by reversing the order,
        # making a oneOf with each possible product of allOf
        if any("oneOf" in value for value in values):
            return self._clean_schema(self._invert_allof(values, "oneOf"))

        # This must come after fixing oneOf because oneOf may break into multiple quantity values.
        if self._is_quantity_value(values):
            return self._fix_quantity_value_reference(values)

        # Deference values and check for oneOf/anyOf inversion again.
        derefed_values = self._dereference_values(values)
        if any("oneOf" in value for value in derefed_values):
            return self._clean_schema(self._invert_allof(derefed_values, "oneOf"))
        if any("anyOf" in value for value in derefed_values):
            return self._clean_schema(self._invert_allof(derefed_values, "anyOf"))

        # If any object in the allOf has required fields, we must combine them in order for the generation
        # script to generate valid dataclasses. This is because dataclass inheritance with optional fields
        # is broken in python < 3.10.
        # If there is an allOf nested with this allOf, combine it.
        if self._required_anywhere(derefed_values) or any(
            "allOf" in schema for schema in derefed_values
        ):
            return _validate_dictionary_type(
                self._combine_allof_schemas(derefed_values)
            )

        # Otherwise, we try to combine the schemas in order to error if there are any conflicting keys,
        # but we don't save the result.
        self._try_combine_schemas(derefed_values)

        return {"allOf": values}

    def _clean_ref_value(self, value: str) -> str:
        # Get the schema and the definition name from the URL to create the local def path.
        schema_name, def_name = _get_reference_from_url(value)

        # If covered by a definition in shared definitions or if a unit, use those.
        if def_name in self.replaced_definitions.get(schema_name or "", []):
            return f"#/$defs/{def_name}"
        elif def_name and def_name in self.unit_to_name:
            self.referenced_units.add(def_name)
            return f"#/$defs/{self.unit_to_name[def_name]}"

        # Otherwise create the local definition path.
        if schema_name and def_name:
            cleaned_ref = f"#/$defs/{schema_name}/$defs/{def_name}"
        elif schema_name or def_name:
            cleaned_ref = f"#/$defs/{schema_name or def_name}"
        else:
            cleaned_ref = value

        # Finally we need to check if this is a path inside another definition schema, and if so use the
        # absolute path.
        def_name = _get_def_name(cleaned_ref)
        if (
            self.enclosing_schema_name
            and self.enclosing_schema_keys
            and def_name not in self.definitions
            and def_name in self.enclosing_schema_keys
        ):
            return f"#/$defs/{self.enclosing_schema_name}/$defs/{def_name}"

        return cleaned_ref

    def _clean_value(
        self,
        value: Any,
        cleaning_function: Callable[[dict[str, Any]], dict[str, Any]] | None = None,
    ) -> Any:
        # Fan out function for handling dict/list values. Calls cleaning_function on dictionaries
        # (assumed to be schemas). Allows passing custom cleaning_fuction to handle cleaning definitions.
        cleaning_function = cleaning_function or self._clean_schema
        if isinstance(value, dict):
            return cleaning_function(value)
        elif isinstance(value, list):
            return list(
                filter(
                    lambda v: bool(v),
                    (self._clean_value(v, cleaning_function) for v in value),
                )
            )
        return value

    def _clean_schema(self, schema: dict[str, Any]) -> dict[str, Any]:
        # If a schema is has properties on it and anyOf/oneOf/allOf composed components, it is essentially
        # an allOf with the parent schema and the rest, combine this way.
        schema = copy.deepcopy(schema)
        if _is_direct_object_schema(schema) and _is_composed_object_schema(schema):
            allof_values = [
                _create_object_schema(
                    schema.pop("properties", {}), schema.pop("required", [])
                ),
                *schema.pop("allOf", []),
            ]
            if "anyOf" in schema:
                allof_values.append({"anyOf": schema.pop("anyOf")})
            if "oneOf" in schema:
                allof_values.append({"oneOf": schema.pop("oneOf")})
            schema["allOf"] = allof_values

        cleaned = {}
        for key, value in schema.items():
            if _should_filter_key(key):
                continue
            if _should_skip_key(key):
                cleaned[key] = value
                continue

            if key == "allOf":
                clean_value = self._clean_value(value)
                cleaned |= self._combine_allof(clean_value)
            elif key == "$ref":
                cleaned[key] = self._clean_ref_value(value)
            elif key == "anyOf":
                clean_value = self._clean_value(value)
                cleaned |= self._combine_anyof(clean_value)
            else:
                cleaned[key] = self._clean_value(value)

        return {key: value for key, value in cleaned.items() if value not in (None, {})}

    def _clean_def_schema(self, schema: dict[str, Any]) -> dict[str, Any]:
        cleaned = {}
        for key, value in schema.items():
            if _should_filter_key(key):
                continue
            if _should_skip_key(key):
                cleaned[key] = value
                continue

            if key == "$ref":
                cleaned[key] = self._clean_ref_value(value)
            else:
                cleaned[key] = self._clean_value(value, self._clean_def_schema)

        return {key: value for key, value in cleaned.items() if value not in (None, {})}

    def _clean_defs(self, schema: dict[str, Any]) -> dict[str, Any]:
        for schema_name, defs_schema in schema.items():
            # Replace web address reference name with a version that can be followed in datamodel-codegen
            cleaned_schema_name = _get_reference_from_url(schema_name)[0] or schema_name
            # Units are treated specially. We rename the unit (to avoid non-variable names) and store
            # them in separate shared unit schema file, in order to allow for shared imports.
            if cleaned_schema_name.endswith("units_schema"):
                for unit, unit_schema in defs_schema["$defs"].items():
                    self._add_unit(
                        unit=unit,
                        unit_iri=unit_schema["properties"]["unit"]["$asm.unit-iri"],
                    )
            elif "$defs" in defs_schema:
                # Store defs that are replaced with definitions in common/definitions before cleaning.
                # NOTE: this does not attempt to handle futher nested $defs in schemas, but we have not
                # observed that in any schema files yet.
                self.definitions[cleaned_schema_name] = {"$defs": {}}
                for def_name, def_schema in defs_schema["$defs"].items():
                    if self.definitions.get(def_name) == def_schema:
                        self.replaced_definitions[cleaned_schema_name].append(def_name)
                    else:
                        self.definitions[cleaned_schema_name]["$defs"][
                            def_name
                        ] = def_schema
            else:
                self.definitions[cleaned_schema_name] = defs_schema

        cleaned = {}
        for schema_name, defs_schema in schema.items():
            cleaned_schema_name = _get_reference_from_url(schema_name)[0] or schema_name
            if cleaned_schema_name.endswith("units_schema"):
                continue
            elif "$defs" in defs_schema:
                # For references nested inside definitions, we need to change the ref into the full reference
                # path in order for the generation script to find them. e.g.
                #   {"someSchema": {"$ref": "#/$defs/someThing"}}
                #       becomes
                #   {"someSchema": {"$ref": "#/$defs/someSchema/$defs/someThing"}}
                # To accomplish this, we set enclosing_schema_name/keys while cleaning the def schema,
                # and use them in clean_ref_value
                self.enclosing_schema_name = cleaned_schema_name
                self.enclosing_schema_keys = defs_schema["$defs"].keys()
                cleaned_defs = {}
                for def_name, def_schema in defs_schema["$defs"].items():
                    if def_name not in self.replaced_definitions[cleaned_schema_name]:
                        cleaned_defs[def_name] = self._clean_def_schema(def_schema)
                self.enclosing_schema_name = None
                self.enclosing_schema_keys = None
                cleaned[cleaned_schema_name] = {"$defs": cleaned_defs}
            else:
                cleaned[cleaned_schema_name] = self._clean_def_schema(defs_schema)

        self.definitions |= cleaned
        return cleaned

    def get_referenced_units(self) -> dict[str, str]:
        # Returns all units seen in the schema, for auto-generating unit schemas externally.
        return {
            unit: iri
            for unit, iri in self.unit_to_iri.items()
            if unit in self.referenced_units
        }

    def clean(self, schema: dict[str, Any]) -> dict[str, Any]:
        # Call clean defs first, because we store some metadata about overridden definitions that is used in
        # the main body.
        cleaned = copy.deepcopy(schema)

        # Definitions are cleaned differently, because we don't want to change modify them more than we need
        # to. That is, we leave combining compound schemas to the main schema cleaning so we can tell if it
        # is necessary or not. Here, we simply clean up http references and store definitions for later reference.
        cleaned["$defs"] = self._clean_defs(cleaned.get("$defs", {}))

        return self._clean_schema(cleaned)

    def clean_file(self, schema_path: str) -> None:
        schema = self.clean(get_schema(Path(schema_path)))

        with open(schema_path, "w") as f:
            json.dump(schema, f, indent=2)
