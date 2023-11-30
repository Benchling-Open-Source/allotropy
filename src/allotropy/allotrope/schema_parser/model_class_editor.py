from collections import defaultdict
from dataclasses import dataclass
import io
import json
import os
from pathlib import Path
import re
from typing import Optional

from allotropy.allotrope.schema_parser.schema_model import (
    get_all_schema_components,
    get_schema_definitions_mapping,
)
from allotropy.exceptions import AllotropeConversionError

SCHEMA_DIR_PATH = "src/allotropy/allotrope/schemas"
SHARED_FOLDER_MODULE = "allotropy.allotrope.models.shared"


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
            if schema_model.schema == component_schema:
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


@dataclass
class ClassLines:
    """Represents a set of lines defining a class."""

    lines: list[str]

    @property
    def class_name(self) -> str:
        match = None
        if self.lines[0].startswith("@dataclass"):
            match = re.match("class ([^\\(:]*)", self.lines[1])
        elif self.lines[0].startswith("class"):
            match = re.match("class ([^\\(:]*)", self.lines[0])
        elif " = " in self.lines[0]:
            match = re.match("(\\S+) =", self.lines[0])
        if not match:
            error = f"Could not determine class name for: {''.join(self.lines)}."
            raise AllotropeConversionError(error)
        return match.groups()[0]


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

    def _handle_class_lines(self, class_lines: ClassLines) -> Optional[list[str]]:
        # Given a ClassLines object, returns the lines to add to the file.
        if class_lines.class_name in self.classes_to_skip:
            return None
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
                    return ClassLines(lines)
                else:
                    continue
            # End of file, return the class if we've read one in on this run.
            if not line:
                return ClassLines(lines) if started else None
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
        all_classes: set[str] = set()
        while True:
            class_lines = self._get_class_lines(f, existing_lines)
            existing_lines = []
            if not class_lines:
                break
            updated_lines = self._handle_class_lines(class_lines)
            if updated_lines:
                new_contents.extend(["\n", "\n", *updated_lines])
                all_classes.add(class_lines.class_name)

        # If there are any unused classes, remove them.
        new = "".join(new_contents)
        classes_to_remove: set[str] = set()
        for class_name in all_classes:
            if class_name == "Model":
                continue
            if not re.search(rf"(?<!class )(?<!\w){class_name}(?!\w)(?! = )", new):
                classes_to_remove.add(class_name)

        if classes_to_remove:
            self.classes_to_skip.update(classes_to_remove)
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
