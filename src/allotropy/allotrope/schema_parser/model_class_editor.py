from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
import io
import json
import os
from pathlib import Path
import re
from typing import Any, Optional

from allotropy.allotrope.schema_parser.schema_cleaner import _should_filter_key
from allotropy.allotrope.schema_parser.schema_model import (
    get_all_schema_components,
    get_schema_definitions_mapping,
)
from allotropy.exceptions import AllotropeConversionError

SCHEMA_DIR_PATH = "src/allotropy/allotrope/schemas"
SHARED_FOLDER_MODULE = "allotropy.allotrope.models.shared"


def _values_equal(value1: Any, value2: Any):
    if isinstance(value1, dict):
        return isinstance(value2, dict) and _schemas_equal(value1, value2)
    elif isinstance(value1, list):
        return isinstance(value2, list) and all(
            _values_equal(v1, v2) for v1, v2 in zip(value1, value2)
        )
    else:
        return value1 == value2


def _schemas_equal(schema1: dict[str, Any], schema2: dict[str, Any]):
    schema1_keys = {key for key in schema1.keys() if not _should_filter_key(key)}
    schema2_keys = {key for key in schema2.keys() if not _should_filter_key(key)}
    return schema1_keys == schema2_keys and all(
        _values_equal(schema1[key], schema2[key]) for key in schema1_keys
    )


def get_shared_schema_info(schema_path: str) -> tuple[set[str], dict[str, set[str]]]:
    with open(schema_path) as f:
        schema = json.load(f)

    classes_to_skip = set()
    imports_to_add = defaultdict(set)

    # Get all properties from the schema and all definitions.
    schema_mapping = get_all_schema_components(schema)
    if "$defs" in schema:
        schema_mapping.update(schema["$defs"])
    if "$custom" in schema:
        schema_mapping.update(schema["$custom"])

    # Get schemas defined in models/shared
    shared_schema_mapping = get_schema_definitions_mapping()

    # Match schemas to get classes to remove from the generated code and imports to add.
    for name, component_schema in schema_mapping.items():
        for schema_model in shared_schema_mapping.get(name, []):
            # TODO: log warning visible in script output if schema name is found but no schemas match.
            if _schemas_equal(schema_model.schema, component_schema):
                classes_to_skip.add(schema_model.import_info[1])
                imports_to_add[schema_model.import_info[0]].add(
                    schema_model.import_info[1]
                )

    return classes_to_skip, dict(imports_to_add)


def get_manifest_from_schema_path(schema_path: str) -> str:
    relpath = Path(os.path.relpath(schema_path, SCHEMA_DIR_PATH))
    return (
        f"http://purl.allotrope.org/manifests/{relpath.parent}/{relpath.stem}.manifest"
    )


def _parse_types(type_string: str) -> set[str]:
    if "[" not in type_string:
        return {type_string}

    loc = type_string.find("[")
    identifier = type_string[:loc]
    inner = type_string[loc + 1 : -1]
    if identifier == "Union":
        types = set()
        for inner_ in inner.split(","):
            if not inner_:
                continue
            types |= _parse_types(inner_)
        return types
    elif identifier.lower() in ("list", "set", "tuple"):
        if not inner.lower().startswith("union["):
            inner = f"Union[{inner}]"
        types = _parse_types(inner)
    elif identifier in ("dict", "Dict", "Mapping"):
        key_type, value_types = inner.split(",", 1)
        value_types = _parse_types(value_types)
        return {f"{identifier}[{key_type},{','.join(value_types)}]"}
    else:
        types = _parse_types(inner)

    return {f"{identifier}[{','.join(sorted(types))}]"}


@dataclass
class Field:
    name: str
    is_required: bool
    default_value: Optional[str]
    field_types: set[str]

    @staticmethod
    def create(contents: str) -> Field:
        name, content = re.sub(r"\s", "", contents).split(":", maxsplit=1)
        type_string, default_value = (
            content.split("=") if "=" in content else (content, None)
        )
        is_required = True
        if type_string.startswith("Optional["):
            is_required = False
            type_string = type_string[9:-1]
        types = _parse_types(type_string)

        return Field(name, is_required, default_value, types)

    @property
    def contents(self) -> str:
        if len(self.field_types) > 1:
            types = f"Union[{','.join(sorted(self.field_types))}]"
        else:
            types = next(iter(self.field_types))
        if not self.is_required:
            types = f"Optional[{types}]"
        if self.default_value:
            types = f"{types}={self.default_value}"
        return f"{self.name}: {types}"

    def can_merge(self, other: Field) -> bool:
        return (
            self.name == other.name
            and self.is_required == other.is_required
            and self.default_value == other.default_value
        )

    def merge(self, other: Field) -> Field:
        if not self.can_merge(other):
            msg = f"Can not merge incompatible fields {self} and {other}"
            raise AssertionError(msg)
        return Field(
            name=self.name,
            is_required=self.is_required,
            default_value=self.default_value,
            field_types=self.field_types | other.field_types,
        )


@dataclass
class ClassLines:
    """Represents a set of lines defining a class."""

    lines: list[str]
    class_name: str
    is_dataclass: bool
    parent_class_names: Optional[list[str]] = None
    fields: dict[str, Field] = None
    field_name_order: Optional[list[str]] = None

    @staticmethod
    def create(lines: list[str]) -> ClassLines:
        is_dataclass = lines[0].startswith("@dataclass")
        class_start = 1 if is_dataclass else 0
        class_end = class_start
        while class_end < len(lines) and ":" not in lines[class_end]:
            class_end += 1
        class_definition = "".join(
            line.strip("\n") for line in lines[class_start : class_end + 1]
        )

        match = None
        if is_dataclass:
            match = re.match("class ([^\\(:]*)", class_definition)
        elif class_definition.startswith("class"):
            match = re.match("class ([^\\(:]*)", class_definition)
        elif " = " in class_definition:
            match = re.match("(\\S+) =", lines[0])
        if not match:
            error = f"Could not determine class name for: {''.join(lines)}."
            raise AllotropeConversionError(error)
        class_name = match.groups()[0]

        if not is_dataclass:
            return ClassLines(lines, class_name, is_dataclass)

        # Handle case where dataclass is just a rename of another dataclass.
        if "pass" in lines[class_end + 1] and ":" not in lines[class_end + 1]:
            return ClassLines(lines, class_name, is_dataclass=False)

        is_frozen = "frozen=True" in lines[0]

        parent_class_names = []
        match = re.match(f"class {class_name}\\((.*)\\):", class_definition)
        parent_class_names = (
            [name.strip() for name in match.groups()[0].split(",")] if match else []
        )

        fields: dict[str, Field] = {}
        field_name_order = []
        field_contents = ""
        for line in lines[class_end + 1 :]:
            if ":" in line and field_contents:
                field = Field.create(field_contents)
                fields[field.name] = field
                field_name_order.append(field.name)
                field_contents = line
            else:
                field_contents += line

        field = Field.create(field_contents)
        fields[field.name] = field
        field_name_order.append(field.name)

        return ClassLines.create_dataclass(
            class_name, parent_class_names, fields, field_name_order, is_frozen
        )

    @staticmethod
    def create_dataclass(
        name: str,
        parent_class_names: list[str],
        fields: dict[str, Field],
        field_name_order: Optional[list[str]] = None,
        is_frozen: Optional[bool] = False,  # noqa: FBT002
    ) -> ClassLines:
        lines = [f"@dataclass{'(frozen=True)' if is_frozen else ''}"]

        class_name_line = f"class {name}"
        if parent_class_names:
            class_name_line += f"({','.join(parent_class_names)})"
        class_name_line += ":"
        lines.append(class_name_line)

        field_name_order = field_name_order or list(fields.keys())
        fixed_field_name_order = [
            field_name
            for field_name in field_name_order
            if fields[field_name].is_required
        ] + [
            field_name
            for field_name in field_name_order
            if not fields[field_name].is_required
        ]

        for field_name in fixed_field_name_order:
            lines.append(f"    {fields[field_name].contents}")

        return ClassLines(
            [line + "\n" for line in lines],
            name,
            is_dataclass=True,
            parent_class_names=parent_class_names,
            fields=fields,
            field_name_order=fixed_field_name_order,
        )

    def merge_parent_class(self, parent_class: ClassLines) -> ClassLines:
        self.parent_class_names.remove(parent_class.class_name)

        self.fields |= parent_class.fields
        for field_name in parent_class.field_name_order:
            if field_name not in self.field_name_order:
                self.field_name_order.append(field_name)

        return ClassLines.create_dataclass(
            self.class_name,
            self.parent_class_names,
            self.fields,
            self.field_name_order,
            self.is_frozen,
        )

    @property
    def is_frozen(self) -> bool:
        return self.is_dataclass and "frozen=True" in self.lines[0]

    def has_required_fields(self) -> bool:
        return (
            self.is_dataclass
            and self.fields
            and any(field.is_required for field in self.fields.values())
        )

    def has_optional_fields(self) -> bool:
        return (
            self.is_dataclass
            and self.fields
            and any(not field.is_required for field in self.fields.values())
        )

    def has_identical_contents(self, other: ClassLines) -> bool:
        contents = "".join(self.lines)
        other_contents = "".join(other.lines)
        other_contents_subbed = re.sub(
            f"{other.class_name}([^0-9])", rf"{self.class_name}\g<1>", other_contents
        )
        return contents == other_contents_subbed

    def has_similar_contents(self, other: ClassLines) -> bool:
        # parent classes must match:
        if not set(self.parent_class_names) == set(other.parent_class_names):
            return False
        # There must be some overlapping fields
        if not self.fields.keys() & other.fields.keys():
            return False
        # There must be some overlapping fields with the same value
        if not any(
            self.fields[field_name].contents == other.fields[field_name].contents
            for field_name in self.fields.keys() & other.fields.keys()
        ):
            return False
        # Fields unique to one class must be optional.
        if any(
            self.fields[field_name].is_required
            for field_name in self.fields.keys() - other.fields.keys()
        ):
            return False
        if any(
            other.fields[field_name].is_required
            for field_name in other.fields.keys() - self.fields.keys()
        ):
            return False
        # Shared fields must agree on whether they are required
        if not all(
            self.fields[field_name].can_merge(other.fields[field_name])
            for field_name in self.fields.keys() & other.fields.keys()
        ):
            return False

        return True

    def merge_similar_class(self, other: ClassLines) -> ClassLines:
        for field_name in other.fields:
            if field_name not in self.fields:
                self.fields[field_name] = other.fields[field_name]
                self.field_name_order.append(field_name)

        for field_name in self.fields.keys() & other.fields.keys():
            if self.fields[field_name].contents == other.fields[field_name].contents:
                continue
            self.fields[field_name] = self.fields[field_name].merge(
                other.fields[field_name]
            )

        return ClassLines.create_dataclass(
            self.class_name,
            self.parent_class_names,
            self.fields,
            self.field_name_order,
            self.is_frozen,
        )


class ModelClassEditor:
    """
    Iterates over a file of generated models and rewrites it with modifications, including:

    - Adding manifest to base model
    - Factoring out models found in shared/models
    """

    def __init__(
        self,
        manifest: str,
        classes_to_skip: set[str],
        imports_to_add: dict[str, set[str]],
    ):
        self.manifest = manifest
        self.classes_to_skip = classes_to_skip
        self.imports_to_add = imports_to_add

    def _handle_class_lines(
        self, class_name: str, all_classes: dict[str, ClassLines]
    ) -> Optional[list[str]]:
        class_lines = all_classes[class_name]

        # A dataclass with required fields can not inherit from a dataclass with an optional field
        if class_lines.parent_class_names and class_lines.has_required_fields():
            for parent_class_name in class_lines.parent_class_names:
                if all_classes[parent_class_name].has_optional_fields():
                    class_lines = class_lines.merge_parent_class(
                        all_classes[parent_class_name]
                    )

        # Add manifest to base Model class.
        if class_lines.class_name == "Model" and "manifest" not in "".join(
            class_lines.lines
        ):
            class_lines.lines.append(f'    manifest: str = "{self.manifest}"\n')
        return class_lines.lines

    def _get_class_lines(
        self, file: io.TextIOBase, existing_lines: Optional[list[str]] = None
    ) -> Optional[ClassLines]:
        # Reads lines for the next class and returns as a ClassLines object.
        lines: list[str] = existing_lines or []
        started = False
        while True:
            line = file.readline()
            # Skip empty lines at the start, return when we hit a newline after the class.
            if line == "\n":
                if started:
                    return ClassLines.create(lines)
                else:
                    continue
            # End of file, return the class if we've read one in on this run.
            if not line:
                return ClassLines.create(lines) if started else None
            started = True
            lines.append(line)

    def modify_file(self, file_contents: str) -> str:
        new_contents: list[str] = []

        f = io.StringIO(file_contents)

        # Scan past comments and import lines.
        while True:
            line = f.readline()
            # TODO: this needs work to be more robust.
            if (
                line == "\n"
                or line.startswith("#")
                or line.startswith("from")
                or line.startswith("import")
            ):
                new_contents.append(line)
            else:
                break

        # We read the first line in the first class, so we need to add it back in
        existing_lines = [line]

        # Remove one newline after default imports
        if self.imports_to_add:
            new_contents = new_contents[:-1]
            # Add new imports
            for module, classes in self.imports_to_add.items():
                new_contents.append(
                    f"from {SHARED_FOLDER_MODULE}.{module} import {', '.join(sorted(classes))}\n"
                )
        else:
            new_contents = new_contents[:-2]

        # Parse classes
        classes_in_order = []
        all_classes: dict[str, ClassLines] = {}
        class_groups = defaultdict(set)
        while True:
            class_lines = self._get_class_lines(f, existing_lines)
            existing_lines = []
            if not class_lines:
                break
            class_name = class_lines.class_name
            classes_in_order.append(class_name)
            all_classes[class_name] = class_lines
            base_class_name = re.match("([A-Za-z]*)[0-9]*", class_name).groups(0)[0]
            class_groups[base_class_name].add(class_name)

        # If there are identical/similar classes with numerical suffixes, remove them.
        class_substitutions = defaultdict(list)
        for class_group in class_groups.values():
            if len(class_group) == 1:
                continue
            sorted_class_names = sorted(class_group)
            for i in range(len(sorted_class_names) - 1):
                class1 = all_classes[sorted_class_names[i]]
                for j in range(i + 1, len(sorted_class_names)):
                    class2 = all_classes[sorted_class_names[j]]
                    if class1.has_identical_contents(class2):
                        class_substitutions[class1.class_name].append(class2.class_name)
                        self.classes_to_skip.add(class2.class_name)
                    elif class1.is_dataclass and class1.has_similar_contents(class2):
                        all_classes[class1.class_name] = class1.merge_similar_class(
                            class2
                        )
                        class_substitutions[class1.class_name].append(class2.class_name)
                        self.classes_to_skip.add(class2.class_name)

        # Build the new file contents before we do substitutions and look for unused classes.
        for class_name in classes_in_order:
            if class_name in self.classes_to_skip:
                continue
            updated_lines = self._handle_class_lines(class_name, all_classes)
            if updated_lines:
                new_contents.extend(["\n", "\n", *updated_lines])

        # If there are any unused classes, remove them.
        new = "".join(new_contents)

        for class_name, to_substitute in class_substitutions.items():
            for class_to_sub in to_substitute:
                new = re.sub(f"{class_to_sub}([^0-9])", rf"{class_name}\g<1>", new)

        classes_to_remove: set[str] = set()
        for class_name in all_classes:
            if class_name == "Model":
                continue
            if not re.search(rf"(?<!class )(?<!\w){class_name}(?!\w)(?! = )", new):
                classes_to_remove.add(class_name)

        if classes_to_remove or class_substitutions:
            self.classes_to_skip = classes_to_remove
            self.imports_to_add = {}
            return self.modify_file(new)

        return new


def modify_file(model_path: str, schema_path: str) -> None:
    classes_to_skip, imports_to_add = get_shared_schema_info(schema_path)
    manifest = get_manifest_from_schema_path(schema_path)

    editor = ModelClassEditor(manifest, classes_to_skip, imports_to_add)

    with open(model_path) as f:
        contents = f.read()

    with open(model_path, "w") as f:
        f.write(editor.modify_file(contents))
