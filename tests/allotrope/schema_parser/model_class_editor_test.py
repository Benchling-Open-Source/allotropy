from io import StringIO

from allotropy.allotrope.schema_parser.model_class_editor import (
    _is_or_union,
    _parse_field_types,
    _split_types,
    _to_or_union,
    _union_to_or,
    ClassLines,
    create_class_lines,
    DataclassField,
    DataClassLines,
    ModelClassEditor,
)


def lines_from_multistring(lines: str) -> list[str]:
    return list(StringIO(lines.strip("\n") + "\n").readlines())


def class_lines_from_multistring(lines: str) -> ClassLines:
    return create_class_lines(lines_from_multistring(lines))


def data_class_lines_from_multistring(lines: str) -> DataClassLines:
    class_lines = create_class_lines(lines_from_multistring(lines))
    assert isinstance(class_lines, DataClassLines)
    return class_lines


def validate_lines_against_multistring(class_lines: ClassLines, lines: str) -> None:
    assert class_lines == class_lines_from_multistring(lines)


def test__to_or_union() -> None:
    assert _to_or_union({"str"}) == "str"
    assert _to_or_union({"str", "int"}) == "int|str"
    assert _to_or_union({"str", "None", "int"}) == "int|str|None"


def test__is_or_union() -> None:
    assert not _is_or_union("int")
    assert _is_or_union("int|float")
    assert not _is_or_union("list[int,float]")
    assert _is_or_union("str|dict[int,float]")
    assert _is_or_union("list[str,int]|str")
    assert not _is_or_union("dict[float|int,str]")


def test__split_types() -> None:
    assert _split_types("int", ",")[0] == {"int"}
    assert _split_types("int,str", ",")[0] == {"int", "str"}
    assert _split_types("int|str", "|")[0] == {"int", "str"}
    assert _split_types("list[int,float]|str", "|")[0] == {"list[int,float]", "str"}
    assert _split_types("list[int|float],str", ",")[0] == {"list[int|float]", "str"}
    # When an unmatched closing bracket is found, returns types up to the bracket, and index of the bracket.
    assert _split_types("int,float]|str", ",") == ({"int", "float"}, 9)
    assert _split_types("int,list[float]]|str", ",") == ({"int", "list[float]"}, 15)


def test__union_to_or() -> None:
    assert _union_to_or("int") == "int"
    assert _union_to_or("Union[int,str]") == "int|str"
    assert _union_to_or("Union[Union[int,float],str]") == "str|float|int"
    assert _union_to_or("Union[list[int,float],str]") == "list[int,float]|str"
    assert _union_to_or("list[Union[int,float]]") == "list[float|int]"
    assert (
        _union_to_or("Union[dict[str,int],dict[int,float]]")
        == "dict[int,float]|dict[str,int]"
    )


def test__parse_field_types() -> None:
    assert _parse_field_types("str") == {"str"}
    assert _parse_field_types("Union[str,int]") == {"int", "str"}
    assert _parse_field_types("Union[str,str,str]") == {"str"}
    assert _parse_field_types("Union[List[str],int]") == {"int", "List[str]"}
    assert _parse_field_types("List[Union[str,str,str]]") == {"List[str]"}
    assert _parse_field_types("list[str,str,str]") == {"list[str]"}
    assert _parse_field_types("tuple[str,int]") == {"tuple[int|str]"}
    assert _parse_field_types("set[int,int]") == {"set[int]"}
    assert _parse_field_types("dict[str,Any]") == {"dict[str,Any]"}
    assert _parse_field_types("dict[Union[int,str],Optional[float]]") == {
        "dict[int|str,float|None]"
    }
    assert _parse_field_types("dict[int|str,float|None]") == {
        "dict[int|str,float|None]"
    }
    assert _parse_field_types("dict[str,list[str,str]]") == {"dict[str,list[str]]"}
    assert _parse_field_types("dict[Union[int,float],str]") == {"dict[float|int,str]"}
    assert _parse_field_types("List[Union[Type1,Type2,Type3,]]") == {
        "List[Type1|Type2|Type3]"
    }
    assert _parse_field_types("str|int") == {"int", "str"}
    assert _parse_field_types("str|None") == {"str", "None"}
    assert _parse_field_types("list[str|int]") == {"list[int|str]"}
    assert _parse_field_types("list[str,dict[str,int],float,None]") == {
        "list[dict[str,int]|float|str|None]"
    }


def test__modify_file_removes_skipped_and_unused_classes() -> None:
    classes_to_skip = {"ClassA"}
    imports_to_add = {"definitions": {"Thing1", "Thing2"}}
    editor = ModelClassEditor(
        "fake_manifest", classes_to_skip, imports_to_add, schema_name="dummy_name"
    )

    model_file_contents = """
import json
from typing import Union


@dataclass(frozen=True,kw_only=True)
class ClassA:
    key: str
    value: str


@dataclass(frozen=True,kw_only=True)
class ClassB:
    key: str
    value: str


@dataclass(frozen=True,kw_only=True)
class UnusedClass:
    value: int


@dataclass(frozen=True,kw_only=True)
class Model:
    key: str
    value: str
    b_thing: ClassB
"""

    expected = """
import json
from typing import Union

from allotropy.allotrope.models.shared.definitions import Thing1, Thing2


@dataclass(frozen=True,kw_only=True)
class ClassB:
    key: str
    value: str


@dataclass(frozen=True,kw_only=True)
class Model:
    key: str
    value: str
    b_thing: ClassB
    manifest: str=\"fake_manifest\"
"""
    assert editor.modify_file(model_file_contents) == expected


def test__class_lines_dataclass_parent_classes() -> None:
    class_lines = class_lines_from_multistring(
        """
@dataclass(frozen=True,kw_only=True)
class ClassA:
    key: str
    value: str
"""
    )
    assert class_lines.class_name == "ClassA"
    assert isinstance(class_lines, DataClassLines)
    assert class_lines.parent_class_names == []

    class_lines = class_lines_from_multistring(
        """
@dataclass(frozen=True,kw_only=True)
class ClassB(ClassA):
    key: str
    value: str
"""
    )
    assert class_lines.class_name == "ClassB"
    assert isinstance(class_lines, DataClassLines)
    assert class_lines.parent_class_names == ["ClassA"]

    class_lines = class_lines_from_multistring(
        """
@dataclass(frozen=True,kw_only=True)
class ClassB(ClassA, ClassC):
    key: str
    value: str
"""
    )
    assert class_lines.class_name == "ClassB"
    assert isinstance(class_lines, DataClassLines)
    assert class_lines.parent_class_names == ["ClassA", "ClassC"]

    class_lines = class_lines_from_multistring(
        """
@dataclass(frozen=True,kw_only=True)
class ClassB(
    ClassA,
    ClassC
):
    key: str
    value: str
"""
    )
    assert class_lines.class_name == "ClassB"
    assert isinstance(class_lines, DataClassLines)
    assert class_lines.parent_class_names == ["ClassA", "ClassC"]


def test__class_lines_dataclass_field_parsing() -> None:
    class_lines = data_class_lines_from_multistring(
        """
@dataclass(kw_only=True)
class Test:
    key: str
    value: str
"""
    )
    assert class_lines.has_required_fields()
    assert not class_lines.has_optional_fields()
    assert class_lines.fields == {
        "key": DataclassField("key", default_value=None, field_types={"str"}),
        "value": DataclassField("value", default_value=None, field_types={"str"}),
    }

    class_lines = data_class_lines_from_multistring(
        """
@dataclass(kw_only=True)
class Test:
    key: str|None
    value: str|None="something"
    int_value:Optional[int]=1
"""
    )
    assert not class_lines.has_required_fields()
    assert class_lines.has_optional_fields()
    assert class_lines.fields == {
        "key": DataclassField("key", default_value=None, field_types={"str", "None"}),
        "value": DataclassField(
            "value", default_value='"something"', field_types={"str", "None"}
        ),
        "int_value": DataclassField(
            "int_value", default_value="1", field_types={"int", "None"}
        ),
    }

    class_lines = data_class_lines_from_multistring(
        """
@dataclass(kw_only=True)
class Test:
    key: str
    item: Union[
        Item1,
        str
    ]
    value: Optional[
        str
    ]
    other_key: str|None=None
"""
    )
    assert class_lines.has_required_fields()
    assert class_lines.has_optional_fields()
    assert class_lines.fields == {
        "key": DataclassField("key", default_value=None, field_types={"str"}),
        "item": DataclassField(
            "item", default_value=None, field_types={"Item1", "str"}
        ),
        "value": DataclassField(
            "value", default_value=None, field_types={"str", "None"}
        ),
        "other_key": DataclassField(
            "other_key", default_value="None", field_types={"str", "None"}
        ),
    }


def test__class_lines_bar_union() -> None:
    class_lines = data_class_lines_from_multistring(
        """
@dataclass(kw_only=True)
class Test:
    key: str | int
    value: str | None
"""
    )
    assert class_lines.has_required_fields()
    assert class_lines.has_optional_fields()
    assert class_lines.fields == {
        "key": DataclassField("key", default_value=None, field_types={"str", "int"}),
        "value": DataclassField(
            "value", default_value=None, field_types={"str", "None"}
        ),
    }


def test__class_lines_merge_parent() -> None:
    parent_class = data_class_lines_from_multistring(
        """
@dataclass(kw_only=True)
class ClassA:
    a_required: str
    a_optional: str|None
"""
    )
    child_class = data_class_lines_from_multistring(
        """
@dataclass(kw_only=True)
class ClassB(ClassA):
    b_required: str
    b_optional: str|None
"""
    )

    validate_lines_against_multistring(
        child_class.merge_parent(parent_class),
        """
@dataclass(kw_only=True)
class ClassB:
    b_required: str
    a_required: str
    b_optional: str|None
    a_optional: str|None
""",
    )


def test__class_lines_merge_parent_multiple() -> None:
    parent_class = data_class_lines_from_multistring(
        """
@dataclass(kw_only=True)
class ClassA:
    a_required: str
    a_optional: str|None
"""
    )
    child_class = data_class_lines_from_multistring(
        """
@dataclass(kw_only=True)
class ClassB(ClassA, ClassC):
    b_required: str
    b_optional: Optional[
        str
    ]
"""
    )
    validate_lines_against_multistring(
        child_class.merge_parent(parent_class),
        """
@dataclass(kw_only=True)
class ClassB(ClassC):
    b_required: str
    a_required: str
    b_optional: str|None
    a_optional: str|None
""",
    )


def test__class_lines_dataclass_eq() -> None:
    class_lines = data_class_lines_from_multistring(
        """
@dataclass(frozen=True,kw_only=True)
class Item:
    key: Union[str, int]
"""
    )

    other_lines = data_class_lines_from_multistring(
        """
@dataclass(frozen=True,kw_only=True)
class Item1:
    key: Union[
        str,
        int
    ]
"""
    )
    assert class_lines == other_lines


def test__class_lines_typedef_eq() -> None:
    lines = class_lines_from_multistring(
        """
TDateTimeStampValue1 = Union[str, TDateTimeStampValue2]
"""
    )
    other_lines = class_lines_from_multistring(
        """
TDateTimeStampValue = Union[str, TDateTimeStampValue3]
"""
    )
    assert lines != other_lines

    lines = class_lines_from_multistring(
        """
TDateTimeStampValue1 = Union[str, TDateTimeStampValue2]
"""
    )
    other_lines = class_lines_from_multistring(
        """
TDateTimeStampValue = Union[str, TDateTimeStampValue2]
"""
    )
    assert lines == other_lines


def test__class_lines_dataclass_should_merge() -> None:
    lines = data_class_lines_from_multistring(
        """
@dataclass(frozen=True,kw_only=True)
class Item:
    key: str
    special: Optional[int]
"""
    )
    other_lines = data_class_lines_from_multistring(
        """
@dataclass(frozen=True,kw_only=True)
class Item1:
    key: str
    other_special: Optional[int]
"""
    )
    assert lines.should_merge(other_lines)

    # Extra required key will be added as optional
    other_lines_extra_required_key = data_class_lines_from_multistring(
        """
@dataclass(frozen=True,kw_only=True)
class Item1:
    key: str
    other_special: int
"""
    )
    assert lines.should_merge(other_lines_extra_required_key)

    other_lines_missing_required_key = data_class_lines_from_multistring(
        """
@dataclass(frozen=True,kw_only=True)
class Item1:
    other_special: Optional[int]
"""
    )
    assert lines.should_merge(other_lines_missing_required_key)

    other_lines_non_matching_shared_key = data_class_lines_from_multistring(
        """
@dataclass(frozen=True,kw_only=True)
class Item1:
    key: str|None
"""
    )
    assert lines.should_merge(other_lines_non_matching_shared_key)


def test__class_lines_dataclass_should_not_merge() -> None:
    lines = data_class_lines_from_multistring(
        """
@dataclass(frozen=True,kw_only=True)
class Item(Base1):
    key: str
"""
    )

    # Different base classes should not merge.
    other_lines = data_class_lines_from_multistring(
        """
@dataclass(frozen=True,kw_only=True)
class Item1(Base2):
    key: str
"""
    )
    assert not lines.should_merge(other_lines)


def test__class_lines_merge_similar() -> None:
    lines = data_class_lines_from_multistring(
        """
@dataclass(frozen=True,kw_only=True)
class Item:
    key: str
    other_key: str
    special: Optional[int]
"""
    )

    other_lines = data_class_lines_from_multistring(
        """
@dataclass(frozen=True,kw_only=True)
class Item1:
    key: str
    other_key: Union[
        int,
        float,
    ]
    other_special: str|None
"""
    )

    validate_lines_against_multistring(
        lines.merge_similar(other_lines),
        """
@dataclass(frozen=True,kw_only=True)
class Item:
    key: str
    other_key: Union[float,int,str]
    special: Optional[int]=None
    other_special: str|None=None
""",
    )


def test__class_lines_merge_similar_with_lists() -> None:
    lines = data_class_lines_from_multistring(
        """
@dataclass(frozen=True,kw_only=True)
class Item:
    key: list[str]
"""
    )

    other_lines = data_class_lines_from_multistring(
        """
@dataclass(frozen=True,kw_only=True)
class Item1:
    key: list[int]
"""
    )

    validate_lines_against_multistring(
        lines.merge_similar(other_lines),
        """
@dataclass(frozen=True,kw_only=True)
class Item:
    key: Union[list[int],list[str]]
""",
    )


def test__modify_file_handles_merging_parent_classes_and_removing_unused_parents() -> (
    None
):
    editor = ModelClassEditor(
        "fake_manifest",
        classes_to_skip=set(),
        imports_to_add={},
        schema_name="dummy_name",
    )

    model_file_contents = """
import json
from typing import Union


@dataclass(frozen=True,kw_only=True)
class OptionalFieldParentClass:
    optional_parent: str|None


@dataclass(frozen=True,kw_only=True)
class RequiredFieldChildClass(OptionalFieldParentClass):
    required_child: str


@dataclass(frozen=True,kw_only=True)
class Model:
    key: str
    value: str
    b_thing: RequiredFieldChildClass
"""

    expected = """
import json
from typing import Union


@dataclass(frozen=True,kw_only=True)
class RequiredFieldChildClass:
    required_child: str
    optional_parent: str|None


@dataclass(frozen=True,kw_only=True)
class Model:
    key: str
    value: str
    b_thing: RequiredFieldChildClass
    manifest: str=\"fake_manifest\"
"""
    assert editor.modify_file(model_file_contents) == expected


def test__modify_file_handles_does_not_merge_parents_when_not_required() -> None:
    editor = ModelClassEditor(
        "fake_manifest",
        classes_to_skip=set(),
        imports_to_add={},
        schema_name="dummy_name",
    )

    model_file_contents = """
import json
from typing import Union


@dataclass(frozen=True,kw_only=True)
class RequiredFieldParentClass:
    required_parent: str


@dataclass(frozen=True,kw_only=True)
class OptionalFieldParentClass:
    optional_parent: str|None


@dataclass(frozen=True,kw_only=True)
class RequiredFieldChildClassUsingRequiredParent(RequiredFieldParentClass):
    required_child: str


@dataclass(frozen=True,kw_only=True)
class RequiredFieldChildUsingOptionalParent(OptionalFieldParentClass):
    required_child: str


@dataclass(frozen=True,kw_only=True)
class OptionalFieldChildClass(OptionalFieldParentClass):
    optional_child: str|None


@dataclass(frozen=True,kw_only=True)
class Model:
    key: str
    thing1: RequiredFieldChildClassUsingRequiredParent
    thing2: RequiredFieldChildUsingOptionalParent
    thing3: OptionalFieldChildClass
"""

    expected = """
import json
from typing import Union


@dataclass(frozen=True,kw_only=True)
class RequiredFieldParentClass:
    required_parent: str


@dataclass(frozen=True,kw_only=True)
class OptionalFieldParentClass:
    optional_parent: str|None


@dataclass(frozen=True,kw_only=True)
class RequiredFieldChildClassUsingRequiredParent(RequiredFieldParentClass):
    required_child: str


@dataclass(frozen=True,kw_only=True)
class RequiredFieldChildUsingOptionalParent:
    required_child: str
    optional_parent: str|None


@dataclass(frozen=True,kw_only=True)
class OptionalFieldChildClass(OptionalFieldParentClass):
    optional_child: str|None


@dataclass(frozen=True,kw_only=True)
class Model:
    key: str
    thing1: RequiredFieldChildClassUsingRequiredParent
    thing2: RequiredFieldChildUsingOptionalParent
    thing3: OptionalFieldChildClass
    manifest: str = \"fake_manifest\"
"""
    assert editor.modify_file(model_file_contents) == expected


def test__modify_file_removes_identical_classes() -> None:
    editor = ModelClassEditor(
        "fake_manifest",
        classes_to_skip=set(),
        imports_to_add={},
        schema_name="dummy_name",
    )

    model_file_contents = """
import json


@dataclass(frozen=True,kw_only=True)
class Item:
    key: str


@dataclass(frozen=True,kw_only=True)
class Item1:
    key: str


@dataclass(frozen=True,kw_only=True)
class Item2:
    key: str


@dataclass(frozen=True,kw_only=True)
class Item12:
    value: str


@dataclass(frozen=True,kw_only=True)
class ParentItem:
    item: Item1
    other_item: Item2|None


@dataclass(frozen=True,kw_only=True)
class Model:
    item: Item
    thing: ParentItem
    other_item: Item12|None
"""

    expected = """
import json


@dataclass(frozen=True,kw_only=True)
class Item:
    key: str|None=None
    value: str|None=None


@dataclass(frozen=True,kw_only=True)
class ParentItem:
    item: Item
    other_item: Item|None


@dataclass(frozen=True,kw_only=True)
class Model:
    item: Item
    thing: ParentItem
    manifest: str=\"fake_manifest\"
    other_item: Item|None
"""
    assert editor.modify_file(model_file_contents) == expected


def test__modify_file_merges_similar_classes() -> None:
    editor = ModelClassEditor(
        "fake_manifest",
        classes_to_skip=set(),
        imports_to_add={},
        schema_name="dummy_name",
    )

    model_file_contents = """
import json


@dataclass(frozen=True,kw_only=True)
class Item:
    key: str
    disagree: int


@dataclass(frozen=True,kw_only=True)
class Item1:
    key: str
    disagree: str
    extra_key: str|None="test"


@dataclass(frozen=True,kw_only=True)
class Item2:
    key: str
    disagree: str
    extra_key: str


@dataclass(frozen=True,kw_only=True)
class Model:
    item: Item
    item1: Item1
    item2: Item2
"""

    expected = """
import json


@dataclass(frozen=True,kw_only=True)
class Item:
    key: str
    disagree: int|str
    extra_key: str|None=None


@dataclass(frozen=True,kw_only=True)
class Model:
    item: Item
    item1: Item
    item2: Item
    manifest: str=\"fake_manifest\"
"""
    assert editor.modify_file(model_file_contents) == expected
