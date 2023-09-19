from allotropy.allotrope.schema_parser.model_class_editor import (
    get_manifest_from_schema_path,
    ModelClassEditor,
)


def test_get_manifest_from_schema_path() -> None:
    schema_path = "src/allotropy/allotrope/schemas/cell_counter/BENCHLING/2023/09/cell-counter.json"
    expected = "http://purl.allotrope.org/manifests/cell_counter/BENCHLING/2023/09/cell-counter.manifest"
    assert get_manifest_from_schema_path(schema_path) == expected


def test_modify_file() -> None:
    classes_to_skip = {"ClassA"}
    imports_to_add = {"definitions": {"Thing1", "Thing2"}}
    editor = ModelClassEditor("fake_manifest", classes_to_skip, imports_to_add)

    model_file_contents = """
import json
from typing import Union


@dataclass
class ClassA:
    key: str
    value: str


@dataclass
class ClassB:
    key: str
    value: str


@dataclass
class UnusedClass:
    value: int


@dataclass
class Model:
    key: str
    value: str
    b_thing: ClassB
"""

    expected = """
import json
from typing import Union

from allotropy.allotrope.models.shared.definitions import Thing1, Thing2


@dataclass
class ClassB:
    key: str
    value: str


@dataclass
class Model:
    key: str
    value: str
    b_thing: ClassB
    manifest: str = \"fake_manifest\"
"""
    assert editor.modify_file(model_file_contents) == expected
