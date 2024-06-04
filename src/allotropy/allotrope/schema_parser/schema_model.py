from collections import defaultdict
from dataclasses import dataclass
import json
from pathlib import Path
import re
from typing import Any

from allotropy.allotrope.schema_parser.backup_manager import is_backup_file
from allotropy.allotrope.schema_parser.path_util import SHARED_SCHEMAS_PATH


# Used to match and locate the model definiton defined in allotropy/allotrope/models/shared
@dataclass
class SchemaModel:
    name: str
    # The ASM schema of the model, used to match against schemas when refactoring genrated models.
    schema: dict[str, Any]
    # The location of the defined shared class, relative to allotropy.allotrope.models.shared
    import_info: tuple[str, str]


# TODO: roughly copied from datamodel-codegen. There is probably more to use/import here to cover all cases.
def snake_to_upper_camel(word: str, delimiter: str = "_") -> str:
    prefix = ""
    if word.startswith(delimiter):
        prefix = "_"
        word = word[1:]

    return prefix + "".join(
        x[0].upper() + x[1:] for x in re.split(delimiter, word) if x
    )


# TODO: this isn't complete. It covers the current schemas in shared/models, but needs:
# - Hardening (e.g. check type and use that to find properties)
# - More cases (e.g. oneOf / allOf)
def get_all_schema_components(schema: dict[str, Any]) -> dict[str, dict[str, Any]]:
    if "items" in schema:
        schema = schema["items"]

    if "allOf" in schema:
        mapping = {}
        for item in schema["allOf"]:
            mapping.update(get_all_schema_components(item))
        return mapping

    if not isinstance(schema, dict) or "properties" not in schema:
        return {}

    mapping = {}
    for prop_name, prop in schema["properties"].items():
        if "oneOf" in prop:
            count = 0
            for item in prop["oneOf"]:
                if item.get("type") == "object":
                    mapping[f"{prop_name} item{count if count else ''}"] = item
                    mapping.update(get_all_schema_components(item))
                    count += 1
        else:
            mapping[prop_name] = prop
            mapping.update(get_all_schema_components(prop))

    return mapping


def get_schema_definitions_mapping() -> dict[str, list[SchemaModel]]:
    schema_mapping = defaultdict(list)

    definition_files = [
        (path.name, directory)
        for directory in ["definitions", "components"]
        for path in Path(SHARED_SCHEMAS_PATH, directory).iterdir()
        if not is_backup_file(path)
    ]

    for schema_file, directory in definition_files:
        schema_module = f"{directory}.{schema_file[:-5]}"

        with open(Path(SHARED_SCHEMAS_PATH, directory, schema_file)) as f:
            schemas = json.load(f)

        for schema_name, schema in schemas.items():
            schema_mapping[schema_name].append(
                SchemaModel(
                    schema_name,
                    schema,
                    (schema_module, snake_to_upper_camel(schema_name, "\\W")),
                )
            )
            components = get_all_schema_components(schema)
            for component_name, component_schema in components.items():
                schema_mapping[component_name].append(
                    SchemaModel(
                        component_name,
                        component_schema,
                        (schema_module, snake_to_upper_camel(component_name, "\\W")),
                    )
                )

    return dict(schema_mapping)
