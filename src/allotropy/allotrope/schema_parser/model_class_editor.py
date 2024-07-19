from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
import io
import json
from pathlib import Path
import re
from typing import Any

from allotropy.allotrope.schema_parser.path_util import get_manifest_from_schema_path
from allotropy.allotrope.schema_parser.schema_cleaner import _should_filter_key
from allotropy.allotrope.schema_parser.schema_model import (
    get_all_schema_components,
    get_schema_definitions_mapping,
)
from allotropy.parsers.utils.values import assert_not_none

SCHEMA_DIR_PATH = "src/allotropy/allotrope/schemas"
SHARED_FOLDER_MODULE = "allotropy.allotrope.models.shared"


def _values_equal(value1: Any, value2: Any) -> bool:
    if isinstance(value1, dict):
        return isinstance(value2, dict) and _schemas_equal(value1, value2)
    elif isinstance(value1, list):
        return (
            isinstance(value2, list)
            and len(value1) == len(value2)
            and all(
                _values_equal(v1, v2) for v1, v2 in zip(value1, value2, strict=True)
            )
        )
    else:
        return bool(
            value1 == value2
        )  # typing does not like using == on any to return bool


def _schemas_equal(schema1: dict[str, Any], schema2: dict[str, Any]) -> bool:
    schema1_keys = {key for key in schema1.keys() if not _should_filter_key(key)}
    schema2_keys = {key for key in schema2.keys() if not _should_filter_key(key)}
    return schema1_keys == schema2_keys and all(
        _values_equal(schema1[key], schema2[key]) for key in schema1_keys
    )


def get_shared_schema_info(schema_path: Path) -> tuple[set[str], dict[str, set[str]]]:
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


def _to_or_union(types: set[str]) -> str:
    return "|".join(
        sorted(t for t in types if t not in ("", "None"))
        + (["None"] if "None" in types else [])
    )


def _is_or_union(type_string: str, sep: str = "|") -> bool:
    # A type string is an | union if there is a | not nested in brackets.
    nested = 0
    for char in type_string:
        if char == "]":
            nested -= 1
        if char == "[":
            nested += 1
        if char == sep and not nested:
            return True
    return False


def _split_types(type_string: str, sep: str) -> tuple[set[str], int]:
    # Given a string representing some or all of a type specification, returns the types up to the first
    # closing bracket, or all types if no bracket if found. If a closing bracket is found, returns the
    # index of that bracket in the string.
    #
    #    "str|int" -> {"str, "int"}, 6 (6 == length of string)
    #
    #    "str|int]|float" -> {"str, "int"}, 7 (7 == index of ])
    #
    inner_types = [""]
    nested = 0
    for index, char in enumerate(type_string):  # noqa: B007
        if char == "]":
            if nested == 0:
                break
            nested -= 1
        if char == "[":
            nested += 1
        # Build up inner_type, breaking on outermost commas
        if char == sep and not nested:
            inner_types.append("")
        else:
            inner_types[-1] += char
    return set(inner_types), index


def _union_to_or(type_string: str) -> str:
    type_string = type_string.replace("Union", "union")
    while "union" in type_string:
        before, after = type_string.split("union[", 1)
        inner_types, end_index = _split_types(after, ",")
        type_string = before + _to_or_union(inner_types) + after[end_index + 1 :]
        # type_string = before + "|".join(sorted(it for it in inner_types if it)) + after[end_index + 1:]
    return type_string


def _parse_field_types(type_string: str) -> set[str]:
    # Parses a set of types from a dataclass field type specification, e.g.
    #   key: Union[str, int] / int|str -> {int, str}
    #
    # Combined duplicated values recursively. These can happen due to class substitutions, e.g.
    #   item: Union[Type, Type1], where Type1 gets replaced with Type becomes:
    #   item: Union[Type, Type] / Type|Type -> {Type}

    # Convert all unions to | operators, as this makes the rest of the logic easier
    type_string = _union_to_or(type_string)

    # In a union, parse each type recursively to clean up inner types and combine duplicates
    if _is_or_union(type_string):
        return set.union(
            *[_parse_field_types(ts) for ts in _split_types(type_string, "|")[0]]
        )

    # If it is not a union and it doesn't end with a bracket, nothing left to do
    if not type_string.endswith("]"):
        return {type_string}

    identifier, inner = type_string.split("[", 1)
    inner = inner[:-1]

    if identifier.lower() in ("list", "set", "tuple"):
        # Special handling for type specifications with lowercase (typedef) identifiers, which
        # can specify a list of types without a union. e.g.
        #     list[str,int] == list[str|int]
        # Handle this by replacing with an or union
        if _is_or_union(inner, ","):
            inner = _to_or_union(_split_types(inner, ",")[0])
        types = _parse_field_types(inner)
    elif identifier.lower() in ("dict", "mapping"):
        key_type, value_types = inner.split(",", 1)
        return {
            f"{identifier}[{key_type},{_to_or_union(_parse_field_types(value_types))}]"
        }
    elif identifier.lower() == "optional":
        return _parse_field_types(inner) | {"None"}
    else:
        types = _parse_field_types(inner)

    if len(types) > 1:
        types_string = _to_or_union(types)
    else:
        types_string = next(iter(types))
    return {f"{identifier}[{types_string}]"}


@dataclass
class DataclassField:
    """Represents a dataclass field."""

    name: str
    default_value: str | None
    field_types: set[str]

    @staticmethod
    def create(contents: str) -> DataclassField:
        name, content = re.sub(r"\s", "", contents).split(":", maxsplit=1)
        type_string, default_value = (
            content.split("=") if "=" in content else (content, None)
        )
        types = _parse_field_types(assert_not_none(type_string))

        return DataclassField(name, default_value, types)

    @property
    def is_required(self) -> bool:
        return "None" not in self.field_types

    @property
    def contents(self) -> str:
        if len(self.field_types) > 1:
            types = _to_or_union(self.field_types)
        else:
            types = next(iter(self.field_types))
        if self.default_value:
            types = f"{types}={self.default_value}"
        return f"{self.name}: {types}"

    def make_optional(self) -> None:
        self.field_types.add("None")
        self.default_value = "None"

    def merge(self, other: DataclassField) -> DataclassField:
        return DataclassField(
            name=self.name,
            # If default values disagree - this must be a now optional field, make it None
            default_value=self.default_value
            if self.default_value == other.default_value
            else "None",
            # Note that combining required + not required == not required
            # When combining types, drop a general dict[str, Any] type. This happens when the schema
            # does not specify any fields, but that's a mistake.
            field_types={
                type_
                for type_ in self.field_types | other.field_types
                if type_.lower() != "dict[str,any]"
            },
        )


@dataclass
class ClassLines:
    """Represents a set of lines defining a class."""

    lines: list[str]
    class_name: str

    @property
    def base_class_name(self) -> str:
        match = re.match("([A-Za-z]*)[0-9]*", self.class_name)
        if not match:
            msg = f"Could not extract base class name from {self.class_name}"
            raise AssertionError(msg)
        return str(match.groups(0)[0])

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ClassLines):
            return False

        if self.base_class_name != other.base_class_name:
            return False

        contents = "".join(self.lines)
        other_contents = "".join(other.lines)
        other_contents_subbed = re.sub(
            f"{other.class_name}([^0-9])", rf"{self.class_name}\g<1>", other_contents
        )
        return contents == other_contents_subbed

    def __repr__(self) -> str:
        return "".join(self.lines)


@dataclass(eq=False)
class DataClassLines(ClassLines):
    """Represents a set of lines defining a dataclass."""

    parent_class_names: list[str]
    fields: dict[str, DataclassField]
    field_name_order: list[str]

    @staticmethod
    def create(
        name: str,
        parent_class_names: list[str],
        fields: dict[str, DataclassField],
        field_name_order: list[str] | None = None,
        is_frozen: bool | None = False,  # noqa: FBT002
    ) -> DataClassLines:
        # Recreate lines with no whitespace from parsed values
        kwargs = ({"frozen": True} if is_frozen else {}) | {"kw_only": True}
        kwargs_string = ",".join(f"{key}={value}" for key, value in kwargs.items())
        lines = [f"@dataclass({kwargs_string})"]

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

        return DataClassLines(
            lines=[line + "\n" for line in lines],
            class_name=name,
            parent_class_names=parent_class_names,
            fields=fields,
            field_name_order=fixed_field_name_order,
        )

    @property
    def is_frozen(self) -> bool:
        return "frozen=True" in self.lines[0]

    def has_required_fields(self) -> bool:
        return any(field.is_required for field in self.fields.values())

    def has_optional_fields(self) -> bool:
        return any(not field.is_required for field in self.fields.values())

    def merge_parent(self, parent_class: DataClassLines) -> DataClassLines:
        self.parent_class_names.remove(parent_class.class_name)

        self.fields |= parent_class.fields
        for field_name in parent_class.field_name_order:
            if field_name not in self.field_name_order:
                self.field_name_order.append(field_name)

        return DataClassLines.create(
            self.class_name,
            self.parent_class_names,
            self.fields,
            self.field_name_order,
            self.is_frozen,
        )

    def should_merge(self, other: DataClassLines) -> bool:
        # parent classes must match
        if set(self.parent_class_names) != set(other.parent_class_names):
            # Special case for OrderedItem, which sometimes gets combined and sometimes does not.
            if set(self.parent_class_names) | set(other.parent_class_names) != {
                "OrderedItem"
            }:
                return False

        # There must be some overlapping fields with the same values
        if not any(
            self.fields[name].contents == other.fields[name].contents
            for name in self.fields.keys() & other.fields.keys()
        ):
            return False

        return True

    def merge_similar(self, other: DataClassLines) -> DataClassLines:
        # Merge another class that has similar fields with this one.

        # Add fields from the other class to this one.
        for field_name in other.fields:
            if field_name not in self.fields:
                self.fields[field_name] = other.fields[field_name]
                self.fields[field_name].make_optional()
                self.field_name_order.append(field_name)

        # For fields in this class not in the other, mark as optional
        for field_name in self.fields:
            if field_name not in other.fields:
                self.fields[field_name].make_optional()

        # Merge fields by combining types into a single union.
        for field_name in self.fields.keys() & other.fields.keys():
            if self.fields[field_name].contents == other.fields[field_name].contents:
                continue
            self.fields[field_name] = self.fields[field_name].merge(
                other.fields[field_name]
            )

        # Special case for OrderedItem, which sometimes gets combined and sometimes does not.
        # If parents do not match, and it is only ordered item, it is because one class got
        # ordered item merged in, so drop it.
        if set(self.parent_class_names) != set(other.parent_class_names):
            if set(self.parent_class_names) | set(other.parent_class_names) == {
                "OrderedItem"
            }:
                self.parent_class_names = []

        return DataClassLines.create(
            self.class_name,
            self.parent_class_names,
            self.fields,
            self.field_name_order,
            self.is_frozen,
        )


def create_class_lines(lines: list[str]) -> ClassLines:
    is_dataclass = lines[0].startswith("@dataclass")

    # Get the lines that are the class description, including the name and parent classes.
    desc_start = 1 if is_dataclass else 0
    desc_end = desc_start
    # Find the first line that has ":", as the class description may be split over multiple lines if there
    # are multiple/long parent class names.
    while desc_end < len(lines) and ":" not in lines[desc_end]:
        desc_end += 1
    class_description = "".join(
        line.strip("\n") for line in lines[desc_start : desc_end + 1]
    )

    # Get the class name
    match = None
    if class_description.startswith("class"):
        match = re.match("class ([^\\(:]*)", class_description)
    elif " = " in class_description:
        # Match type aliasing, e.g. TClass = str
        match = re.match("(\\S+) =", lines[0])
    if not match:
        msg = f"Could not determine class name for: {''.join(lines)}."
        raise AssertionError(msg)
    class_name = match.groups()[0]

    if not is_dataclass:
        return ClassLines(lines, class_name)

    # Handle case where dataclass is just a rename of another dataclass. We don't need to do anything with
    # these, so just pass them.
    if "pass" in lines[desc_end + 1] and ":" not in lines[desc_end + 1]:
        return ClassLines(lines, class_name)

    is_frozen = "frozen=True" in lines[0]

    # Get parent class names
    parent_class_names = []
    match = re.match(f"class {class_name}\\((.*)\\):", class_description)
    parent_class_names = (
        [name.strip() for name in match.groups()[0].split(",")] if match else []
    )

    # Get fields of the dataclass
    fields: dict[str, DataclassField] = {}
    field_name_order = []
    field_contents = ""
    for line in lines[desc_end + 1 :]:
        if ":" in line and field_contents:
            field = DataclassField.create(field_contents)
            fields[field.name] = field
            field_name_order.append(field.name)
            field_contents = line
        else:
            field_contents += line

    field = DataclassField.create(field_contents)
    fields[field.name] = field
    field_name_order.append(field.name)

    return DataClassLines.create(
        name=class_name,
        parent_class_names=parent_class_names,
        fields=fields,
        field_name_order=field_name_order,
        is_frozen=is_frozen,
    )


class ModelClassEditor:
    """
    Iterates over a file of generated models and rewrites it with modifications, including:

    - Adding manifest to base model
    - Factoring out models found in shared/models
    - Fixing issues with dataclass models that cause issues with python (e.g. dataclass with a required
            field can not inherit from a dataclass with an optional field)
    - Combining some dataclasses to reduce combinatorial explosions. Note that this reduces accuracy at the
            cost of readability. We let the schema enforce correctness in these cases.
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
        self, class_name: str, classes: dict[str, ClassLines]
    ) -> list[str] | None:
        class_lines = classes[class_name]

        # A dataclass with required fields can not inherit from a dataclass with an optional field
        if (
            isinstance(class_lines, DataClassLines)
            and class_lines.has_required_fields()
        ):
            for parent_class_name in class_lines.parent_class_names:
                parent_class = classes[parent_class_name]
                if (
                    isinstance(parent_class, DataClassLines)
                    and parent_class.has_optional_fields()
                ):
                    class_lines = class_lines.merge_parent(parent_class)

        # Add manifest to base Model class.
        if class_lines.class_name == "Model" and "manifest" not in "".join(
            class_lines.lines
        ):
            class_lines.lines.append(f'    manifest: str = "{self.manifest}"\n')
        return class_lines.lines

    def _get_class_lines(
        self, file: io.TextIOBase, existing_lines: list[str] | None = None
    ) -> ClassLines | None:
        # Reads lines for the next class and returns as a ClassLines object.
        lines: list[str] = existing_lines or []
        started = False
        while True:
            line = file.readline()
            # Skip empty lines at the start, return when we hit a newline after the class.
            if line == "\n":
                if started:
                    return create_class_lines(lines)
                else:
                    continue
            # End of file, return the class if we've read one in on this run.
            if not line:
                return create_class_lines(lines) if started else None
            started = True
            lines.append(line)

    def _find_substitutions(
        self, classes: dict[str, ClassLines], class_groups: dict[str, set[str]]
    ) -> dict[str, str]:
        substitutions: dict[str, str] = {}

        for class_group in class_groups.values():
            sorted_class_names = sorted(class_group)
            for i in range(len(sorted_class_names) - 1):
                class1 = classes[sorted_class_names[i]]
                if not isinstance(class1, DataClassLines):
                    continue
                for j in range(i + 1, len(sorted_class_names)):
                    class2 = classes[sorted_class_names[j]]
                    if not isinstance(class2, DataClassLines):
                        continue
                    # If classes are equal or similar enough to merge, substitute.
                    if class1 == class2:
                        substitutions[class2.class_name] = class1.class_name
                    elif class1.should_merge(class2):
                        classes[class1.class_name] = class1.merge_similar(class2)
                        substitutions[class2.class_name] = class1.class_name

        return substitutions

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
            for module, imports in self.imports_to_add.items():
                new_contents.append(
                    f"from {SHARED_FOLDER_MODULE}.{module} import {', '.join(sorted(imports))}\n"
                )
        else:
            new_contents = new_contents[:-2]

        # Parse classes
        classes_in_order = []
        classes: dict[str, ClassLines] = {}
        class_groups: defaultdict[str, set[str]] = defaultdict(set)
        while True:
            class_lines = self._get_class_lines(f, existing_lines)
            existing_lines = []
            if not class_lines:
                break
            classes_in_order.append(class_lines.class_name)
            classes[class_lines.class_name] = class_lines
            class_groups[class_lines.base_class_name].add(class_lines.class_name)

        # If there are identical/similar classes with numerical suffixes, remove them.
        substitutions = self._find_substitutions(classes, class_groups)

        # Build the new file contents before we do substitutions and look for unused classes.
        for class_name in classes_in_order:
            if class_name in self.classes_to_skip or class_name in substitutions:
                continue
            updated_lines = self._handle_class_lines(class_name, classes)
            if updated_lines:
                new_contents.extend(["\n", "\n", *updated_lines])
        new = "".join(new_contents)

        # Do substitutions
        for class_to_remove in sorted(substitutions.keys(), reverse=True):
            new = re.sub(
                f"{class_to_remove}([^0-9])",
                rf"{substitutions[class_to_remove]}\g<1>",
                new,
            )

        # Check for classes that are no longer used
        unused_classes: set[str] = set()
        for class_name in classes:
            if class_name == "Model":
                continue
            if not re.search(rf"(?<!class )(?<!\w){class_name}(?!\w)(?! = )", new):
                unused_classes.add(class_name)

        # If we changed anything, run through again to look for iterative removals
        if unused_classes or substitutions:
            self.classes_to_skip = unused_classes
            self.imports_to_add = {}
            return self.modify_file(new)

        return new


def modify_file(model_path: Path, schema_path: Path) -> None:
    classes_to_skip, imports_to_add = get_shared_schema_info(schema_path)
    manifest = get_manifest_from_schema_path(schema_path)

    editor = ModelClassEditor(manifest, classes_to_skip, imports_to_add)

    with open(model_path) as f:
        contents = f.read()

    with open(model_path, "w") as f:
        f.write(editor.modify_file(contents))
