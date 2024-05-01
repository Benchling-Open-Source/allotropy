from io import StringIO

from allotropy.allotrope.schema_parser.model_class_editor import (
    _parse_types,
    ClassLines,
    Field,
    get_manifest_from_schema_path,
    ModelClassEditor,
)


def test_parse_types() -> None:
    assert _parse_types("str") == {"str"}
    assert _parse_types("Union[str,int]") == {"int", "str"}
    assert _parse_types("Union[str,str,str]") == {"str"}
    assert _parse_types("Union[List[str],int]") == {"int", "List[str]"}
    assert _parse_types("List[Union[str,str,str]]") == {"List[str]"}
    assert _parse_types("list[str,str,str]") == {"list[str]"}
    assert _parse_types("tuple[str,int]") == {"tuple[int,str]"}
    assert _parse_types("set[int,int]") == {"set[int]"}
    assert _parse_types("dict[str,Any]") == {"dict[str,Any]"}
    assert _parse_types("dict[str,list[str,str]]") == {"dict[str,list[str]]"}
    assert _parse_types("dict[Union[int,float],str]") == {"dict[Union[int,float],str]"}
    assert _parse_types("List[Union[Type1,Type2,Type3,]]") == {
        "List[Type1,Type2,Type3]"
    }


def lines_from_multistring(lines: str) -> list[str]:
    return list(StringIO(lines.strip("\n") + "\n").readlines())


def test_get_manifest_from_schema_path() -> None:
    schema_path = "src/allotropy/allotrope/schemas/cell_counting/BENCHLING/2023/09/cell-counting.json"
    expected = "http://purl.allotrope.org/manifests/cell_counting/BENCHLING/2023/09/cell-counting.manifest"
    assert get_manifest_from_schema_path(schema_path) == expected


def test_modify_file_removes_skipped_and_unused_classes() -> None:
    classes_to_skip = {"ClassA"}
    imports_to_add = {"definitions": {"Thing1", "Thing2"}}
    editor = ModelClassEditor("fake_manifest", classes_to_skip, imports_to_add)

    model_file_contents = """
import json
from typing import Union


@dataclass(frozen=True)
class ClassA:
    key: str
    value: str


@dataclass(frozen=True)
class ClassB:
    key: str
    value: str


@dataclass(frozen=True)
class UnusedClass:
    value: int


@dataclass(frozen=True)
class Model:
    key: str
    value: str
    b_thing: ClassB
"""

    expected = """
import json
from typing import Union

from allotropy.allotrope.models.shared.definitions import Thing1, Thing2


@dataclass(frozen=True)
class ClassB:
    key: str
    value: str


@dataclass(frozen=True)
class Model:
    key: str
    value: str
    b_thing: ClassB
    manifest: str=\"fake_manifest\"
"""
    assert editor.modify_file(model_file_contents) == expected


def test_class_lines_dataclass_parent_classes() -> None:
    lines = lines_from_multistring(
        """
@dataclass(frozen=True)
class ClassA:
    key: str
    value: str
"""
    )
    class_lines = ClassLines.create(lines)

    assert class_lines.class_name == "ClassA"
    assert class_lines.is_dataclass
    assert class_lines.parent_class_names == []

    lines = lines_from_multistring(
        """
@dataclass(frozen=True)
class ClassB(ClassA):
    key: str
    value: str
"""
    )

    class_lines = ClassLines.create(lines)

    assert class_lines.class_name == "ClassB"
    assert class_lines.is_dataclass
    assert class_lines.parent_class_names == ["ClassA"]

    lines = lines_from_multistring(
        """
@dataclass(frozen=True)
class ClassB(ClassA, ClassC):
    key: str
    value: str
"""
    )

    class_lines = ClassLines.create(lines)

    assert class_lines.class_name == "ClassB"
    assert class_lines.is_dataclass
    assert class_lines.parent_class_names == ["ClassA", "ClassC"]

    lines = lines_from_multistring(
        """
@dataclass(frozen=True)
class ClassB(
    ClassA,
    ClassC
):
    key: str
    value: str
"""
    )

    class_lines = ClassLines.create(lines)

    assert class_lines.class_name == "ClassB"
    assert class_lines.is_dataclass
    assert class_lines.parent_class_names == ["ClassA", "ClassC"]


def test_class_lines_dataclass_field_parsing() -> None:
    lines = lines_from_multistring(
        """
@dataclass
class Test:
    key: str
    value: str
"""
    )
    class_lines = ClassLines.create(lines)

    assert class_lines.has_required_fields()
    assert not class_lines.has_optional_fields()
    assert class_lines.fields == {
        "key": Field("key", is_required=True, default_value=None, field_types={"str"}),
        "value": Field(
            "value", is_required=True, default_value=None, field_types={"str"}
        ),
    }

    lines = lines_from_multistring(
        """
@dataclass
class Test:
    key: Optional[str]
    value: Optional[str]="something"
    int_value:Optional[int]=1
"""
    )
    class_lines = ClassLines.create(lines)

    assert not class_lines.has_required_fields()
    assert class_lines.has_optional_fields()
    assert class_lines.fields == {
        "key": Field("key", is_required=False, default_value=None, field_types={"str"}),
        "value": Field(
            "value", is_required=False, default_value='"something"', field_types={"str"}
        ),
        "int_value": Field(
            "int_value", is_required=False, default_value="1", field_types={"int"}
        ),
    }

    lines = lines_from_multistring(
        """
@dataclass
class Test:
    key: str
    item: Union[
        Item1,
        str
    ]
    value: Optional[
        str
    ]
    other_key: Optional[str]=None
"""
    )

    class_lines = ClassLines.create(lines)
    assert class_lines.has_required_fields()
    assert class_lines.has_optional_fields()
    assert class_lines.fields == {
        "key": Field("key", is_required=True, default_value=None, field_types={"str"}),
        "item": Field(
            "item", is_required=True, default_value=None, field_types={"Item1", "str"}
        ),
        "value": Field(
            "value", is_required=False, default_value=None, field_types={"str"}
        ),
        "other_key": Field(
            "other_key", is_required=False, default_value="None", field_types={"str"}
        ),
    }


def test_class_lines_merge_parent_class() -> None:
    lines = lines_from_multistring(
        """
@dataclass
class ClassA:
    a_required: str
    a_optional: Optional[str]
"""
    )
    parent_class = ClassLines.create(lines)

    lines = lines_from_multistring(
        """
@dataclass
class ClassB(ClassA):
    b_required: str
    b_optional: Optional[str]
"""
    )
    child_class = ClassLines.create(lines)

    result = child_class.merge_parent_class(parent_class)

    assert result.lines == lines_from_multistring(
        """
@dataclass
class ClassB:
    b_required: str
    a_required: str
    b_optional: Optional[str]
    a_optional: Optional[str]
"""
    )


def test_class_lines_merge_parent_class_multiple() -> None:
    lines = lines_from_multistring(
        """
@dataclass
class ClassA:
    a_required: str
    a_optional: Optional[str]
"""
    )
    parent_class = ClassLines.create(lines)

    lines = lines_from_multistring(
        """
@dataclass
class ClassB(ClassA, ClassC):
    b_required: str
    b_optional: Optional[
        str
    ]
"""
    )
    child_class = ClassLines.create(lines)

    result = child_class.merge_parent_class(parent_class)

    assert result.lines == lines_from_multistring(
        """
@dataclass
class ClassB(ClassC):
    b_required: str
    a_required: str
    b_optional: Optional[str]
    a_optional: Optional[str]
"""
    )


def test_class_lines_dataclass_has_identical_contents() -> None:
    lines = ClassLines.create(
        lines_from_multistring(
            """
@dataclass(frozen=True)
class Item:
    key: Union[str, int]
"""
        )
    )

    other_lines = ClassLines.create(
        lines_from_multistring(
            """
@dataclass(frozen=True)
class Item1:
    key: Union[
        str,
        int
    ]
"""
        )
    )

    assert lines.has_identical_contents(other_lines)


def test_class_lines_typedef_has_identical_contents() -> None:
    lines = ClassLines.create(
        lines_from_multistring(
            """
TDateTimeStampValue1 = Union[str, TDateTimeStampValue2]
"""
        )
    )

    other_lines = ClassLines.create(
        lines_from_multistring(
            """
TDateTimeStampValue = Union[str, TDateTimeStampValue3]
"""
        )
    )

    assert not lines.has_identical_contents(other_lines)

    lines = ClassLines.create(
        lines_from_multistring(
            """
TDateTimeStampValue1 = Union[str, TDateTimeStampValue2]
"""
        )
    )

    other_lines = ClassLines.create(
        lines_from_multistring(
            """
TDateTimeStampValue = Union[str, TDateTimeStampValue2]
"""
        )
    )

    assert lines.has_identical_contents(other_lines)


def test_class_lines_dataclass_has_similar_contents() -> None:
    lines = ClassLines.create(
        lines_from_multistring(
            """
@dataclass(frozen=True)
class Item:
    key: str
    special: Optional[int]
"""
        )
    )

    other_lines = ClassLines.create(
        lines_from_multistring(
            """
@dataclass(frozen=True)
class Item1:
    key: str
    other_special: Optional[int]
"""
        )
    )
    assert lines.has_similar_contents(other_lines)

    # Extra required key will not match
    other_lines_extra_required_key = ClassLines.create(
        lines_from_multistring(
            """
@dataclass(frozen=True)
class Item1:
    key: str
    other_special: int
"""
        )
    )
    assert not lines.has_similar_contents(other_lines_extra_required_key)

    # Missing required key will not match
    other_lines_missing_required_key = ClassLines.create(
        lines_from_multistring(
            """
@dataclass(frozen=True)
class Item1:
    other_special: Optional[int]
"""
        )
    )
    assert not lines.has_similar_contents(other_lines_missing_required_key)

    # Shared key that does not agree on optional/required will not match
    other_lines_non_matching_shared_key = ClassLines.create(
        lines_from_multistring(
            """
@dataclass(frozen=True)
class Item1:
    key: Optional[str]
"""
        )
    )
    assert not lines.has_similar_contents(other_lines_non_matching_shared_key)


def test_class_lines_merge_similar_class() -> None:
    lines = ClassLines.create(
        lines_from_multistring(
            """
@dataclass(frozen=True)
class Item:
    key: str
    other_key: str
    special: Optional[int]
"""
        )
    )

    other_lines = ClassLines.create(
        lines_from_multistring(
            """
@dataclass(frozen=True)
class Item1:
    key: str
    other_key: Union[
        int,
        float,
    ]
    other_special: Optional[str]
"""
        )
    )

    result = lines.merge_similar_class(other_lines)
    assert result.lines == lines_from_multistring(
        """
@dataclass(frozen=True)
class Item:
    key: str
    other_key: Union[float,int,str]
    special: Optional[int]
    other_special: Optional[str]
"""
    )


def test_class_lines_merge_similar_class_with_lists() -> None:
    lines = ClassLines.create(
        lines_from_multistring(
            """
@dataclass(frozen=True)
class Item:
    key: list[str]
"""
        )
    )

    other_lines = ClassLines.create(
        lines_from_multistring(
            """
@dataclass(frozen=True)
class Item1:
    key: list[int]
"""
        )
    )

    result = lines.merge_similar_class(other_lines)
    assert result.lines == lines_from_multistring(
        """
@dataclass(frozen=True)
class Item:
    key: Union[list[int],list[str]]
"""
    )


def test_modify_file_handles_merging_parent_classes_and_removing_unused_parents() -> None:
    classes_to_skip = set()
    imports_to_add = {}
    editor = ModelClassEditor("fake_manifest", classes_to_skip, imports_to_add)

    model_file_contents = """
import json
from typing import Union


@dataclass(frozen=True)
class OptionalFieldParentClass:
    optional_parent: Optional[str]


@dataclass(frozen=True)
class RequiredFieldChildClass(OptionalFieldParentClass):
    required_child: str


@dataclass(frozen=True)
class Model:
    key: str
    value: str
    b_thing: RequiredFieldChildClass
"""

    expected = """
import json
from typing import Union


@dataclass(frozen=True)
class RequiredFieldChildClass:
    required_child: str
    optional_parent: Optional[str]


@dataclass(frozen=True)
class Model:
    key: str
    value: str
    b_thing: RequiredFieldChildClass
    manifest: str=\"fake_manifest\"
"""
    assert editor.modify_file(model_file_contents) == expected


def test_modify_file_handles_does_not_merge_parent_classes_when_not_required() -> None:
    classes_to_skip = set()
    imports_to_add = {}
    editor = ModelClassEditor("fake_manifest", classes_to_skip, imports_to_add)

    model_file_contents = """
import json
from typing import Union


@dataclass(frozen=True)
class RequiredFieldParentClass:
    required_parent: str


@dataclass(frozen=True)
class OptionalFieldParentClass:
    optional_parent: Optional[str]


@dataclass(frozen=True)
class RequiredFieldChildClassUsingRequiredParent(RequiredFieldParentClass):
    required_child: str


@dataclass(frozen=True)
class RequiredFieldChildUsingOptionalParent(OptionalFieldParentClass):
    required_child: str


@dataclass(frozen=True)
class OptionalFieldChildClass(OptionalFieldParentClass):
    optional_child: Optional[str]


@dataclass(frozen=True)
class Model:
    key: str
    thing1: RequiredFieldChildClassUsingRequiredParent
    thing2: RequiredFieldChildUsingOptionalParent
    thing3: OptionalFieldChildClass
"""

    expected = """
import json
from typing import Union


@dataclass(frozen=True)
class RequiredFieldParentClass:
    required_parent: str


@dataclass(frozen=True)
class OptionalFieldParentClass:
    optional_parent: Optional[str]


@dataclass(frozen=True)
class RequiredFieldChildClassUsingRequiredParent(RequiredFieldParentClass):
    required_child: str


@dataclass(frozen=True)
class RequiredFieldChildUsingOptionalParent:
    required_child: str
    optional_parent: Optional[str]


@dataclass(frozen=True)
class OptionalFieldChildClass(OptionalFieldParentClass):
    optional_child: Optional[str]


@dataclass(frozen=True)
class Model:
    key: str
    thing1: RequiredFieldChildClassUsingRequiredParent
    thing2: RequiredFieldChildUsingOptionalParent
    thing3: OptionalFieldChildClass
    manifest: str = \"fake_manifest\"
"""
    assert editor.modify_file(model_file_contents) == expected


def test_modify_file_removes_identical_classes() -> None:
    classes_to_skip = set()
    imports_to_add = {}
    editor = ModelClassEditor("fake_manifest", classes_to_skip, imports_to_add)

    model_file_contents = """
import json


@dataclass(frozen=True)
class Item:
    key: str


@dataclass(frozen=True)
class Item1:
    key: str


@dataclass(frozen=True)
class Item2:
    key: str


@dataclass(frozen=True)
class Item12:
    value: str


@dataclass(frozen=True)
class ParentItem:
    item: Item1
    other_item: Optional[Item2]


@dataclass(frozen=True)
class Model:
    item: Item
    thing: ParentItem
    other_item: Optional[Item12]
"""

    expected = """
import json


@dataclass(frozen=True)
class Item:
    key: str


@dataclass(frozen=True)
class Item12:
    value: str


@dataclass(frozen=True)
class ParentItem:
    item: Item
    other_item: Optional[Item]


@dataclass(frozen=True)
class Model:
    item: Item
    thing: ParentItem
    manifest: str=\"fake_manifest\"
    other_item: Optional[Item12]
"""

    result = editor.modify_file(model_file_contents)
    # assert editor.modify_file(model_file_contents) == expected
    assert result == expected


def test_modify_file_merges_similar_classes() -> None:
    classes_to_skip = set()
    imports_to_add = {}
    editor = ModelClassEditor("fake_manifest", classes_to_skip, imports_to_add)

    model_file_contents = """
import json


@dataclass(frozen=True)
class Item:
    key: str
    disagree: int


@dataclass(frozen=True)
class Item1:
    key: str
    disagree: str
    extra_key: Optional[str]="test"


@dataclass(frozen=True)
class Item2:
    key: str
    disagree: str
    extra_key: str


@dataclass(frozen=True)
class Model:
    item: Item
    item1: Item1
    item2: Item2
"""

    expected = """
import json


@dataclass(frozen=True)
class Item:
    key: str
    disagree: Union[int,str]
    extra_key: Optional[str]="test"


@dataclass(frozen=True)
class Item2:
    key: str
    disagree: str
    extra_key: str


@dataclass(frozen=True)
class Model:
    item: Item
    item1: Item
    item2: Item2
    manifest: str=\"fake_manifest\"
"""
    assert editor.modify_file(model_file_contents) == expected
