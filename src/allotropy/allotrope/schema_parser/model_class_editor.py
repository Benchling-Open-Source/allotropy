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

SCHEMA_DIR_PATH = "src/allotropy/allotrope/schemas"
SHARED_FOLDER_MODULE = "allotropy.allotrope.models.shared"


def _values_equal(value1: Any, value2: Any) -> bool:
    if isinstance(value1, dict):
        return isinstance(value2, dict) and _schemas_equal(value1, value2)
    elif isinstance(value1, list):
        return (
            isinstance(value2, list)
            and len(value1) == len(value2)
            and all(_values_equal(v1, v2) for v1, v2 in zip(value1, value2))
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


def _parse_field_types(type_string: str) -> set[str]:
    # Parses a set of types from a dataclass field type specification, e.g.
    #   key: Union[str, int] -> {int, str}
    #
    # Combined duplicated values recursively. These can happen due to class substitutions, e.g.
    #   item: Union[Type, Type1], where Type1 gets replaced with Type becomes:
    #   item: Union[Type, Type] -> {Type}
    if "[" not in type_string:
        return {type_string}

    identifier, inner = type_string.split("[", 1)
    inner = inner[:-1]

    # Return Unioned values as a set of deduped types
    if identifier == "Union":
        types = set()
        for inner_ in inner.split(","):
            if not inner_:
                continue
            types |= _parse_field_types(inner_)
        return types

    if identifier.lower() in ("list", "set", "tuple"):
        # Special handling for type specifications with lowercase (typedef) identifiers, which
        # can specify a list of types without a union. e.g.
        #     List[Union[str, int]] == list[str, int]
        # Handle this by inserting a Union and reparsing
        if not inner.lower().startswith("union["):
            inner = f"Union[{inner}]"
        types = _parse_field_types(inner)
    elif identifier in ("dict", "Dict", "Mapping"):
        # NOTE: assumes that key_type is always one value. Generated code hasn't done something else yet.
        key_type, value_types = inner.split(",", 1)
        return {f"{identifier}[{key_type},{','.join(_parse_field_types(value_types))}]"}
    else:
        types = _parse_field_types(inner)

    if len(types) > 1:
        types_string = f"Union[{','.join(sorted(types))}]"
    else:
        types_string = next(iter(types))
    return {f"{identifier}[{types_string}]"}


@dataclass
class DataclassField:
    """Represents a dataclass field."""

    name: str
    is_required: bool
    default_value: Optional[str]
    field_types: set[str]

    @staticmethod
    def create(contents: str) -> DataclassField:
        name, content = re.sub(r"\s", "", contents).split(":", maxsplit=1)
        type_string, default_value = (
            content.split("=") if "=" in content else (content, None)
        )
        if not type_string:
            msg = "This is impossible but type checker is dumb"
            raise AssertionError(msg)
        is_required = True
        if type_string.startswith("Optional["):
            is_required = False
            type_string = type_string[9:-1]
        types = _parse_field_types(type_string)

        return DataclassField(name, is_required, default_value, types)

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

    def can_merge(self, other: DataclassField) -> bool:
        return (
            self.name == other.name
            and self.is_required == other.is_required
            and self.default_value == other.default_value
        )

    def merge(self, other: DataclassField) -> DataclassField:
        if not self.can_merge(other):
            msg = f"Can not merge incompatible fields {self} and {other}"
            raise AssertionError(msg)
        return DataclassField(
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
        field_name_order: Optional[list[str]] = None,
        is_frozen: Optional[bool] = False,  # noqa: FBT002
    ) -> DataClassLines:
        # Recreate lines with no whitespace from parsed values
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
        if not set(self.parent_class_names) == set(other.parent_class_names):
            return False
        # There must be some overlapping fields with the same values
        if not any(
            self.fields[name].contents == other.fields[name].contents
            for name in self.fields.keys() & other.fields.keys()
        ):
            return False
        # Fields unique to one class must be optional.
        all_fields = self.fields | other.fields
        if any(
            all_fields[name].is_required
            for name in self.fields.keys() ^ other.fields.keys()
        ):
            return False
        # Shared fields must agree on whether they are required
        if not all(
            self.fields[name].can_merge(other.fields[name])
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
                self.field_name_order.append(field_name)

        # Merge fields by combining types into a single union.
        for field_name in self.fields.keys() & other.fields.keys():
            if self.fields[field_name].contents == other.fields[field_name].contents:
                continue
            self.fields[field_name] = self.fields[field_name].merge(
                other.fields[field_name]
            )

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
    ) -> Optional[list[str]]:
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


def modify_file(model_path: str, schema_path: str) -> None:
    classes_to_skip, imports_to_add = get_shared_schema_info(schema_path)
    manifest = get_manifest_from_schema_path(schema_path)

    editor = ModelClassEditor(manifest, classes_to_skip, imports_to_add)

    with open(model_path) as f:
        contents = f.read()

    with open(model_path, "w") as f:
        f.write(editor.modify_file(contents))
