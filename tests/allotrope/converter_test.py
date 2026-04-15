from __future__ import annotations

import importlib
from dataclasses import dataclass, field, fields, make_dataclass
from enum import Enum
from pathlib import Path

import pytest

from allotropy.allotrope.converter import (
    add_custom_information_document,
    structure,
    unstructure,
)
from allotropy.schema_gen.naming import default_json_name
from allotropy.allotrope.models.adm.pcr.benchling._2023._09.qpcr import (
    DataProcessingDocument,
    ProcessedDataDocumentItem,
)
from allotropy.allotrope.models.shared.definitions.definitions import (
    FieldComponentDatatype,
    TDatacube,
    TDatacubeComponent,
    TDatacubeData,
    TDatacubeStructure,
)
from allotropy.allotrope.models.shared.definitions.quantity_values import (
    TQuantityValueUnitless,
)

# ---------------------------------------------------------------------------
# Test fixtures — simple dataclasses for unit tests
# ---------------------------------------------------------------------------


@dataclass(frozen=True, kw_only=True)
class SimpleModel:
    name: str
    value: int
    description: str | None = None


@dataclass(frozen=True, kw_only=True)
class ModelWithJsonName:
    field_asm_manifest: str = field(metadata={"json_name": "$asm.manifest"})
    device_type: str | None = None  # No json_name needed (trivial mapping)


@dataclass(frozen=True, kw_only=True)
class NestedChild:
    child_value: str


@dataclass(frozen=True, kw_only=True)
class NestedParent:
    name: str
    child: NestedChild | None = None


@dataclass(frozen=True, kw_only=True)
class ModelWithList:
    items: list[NestedChild]
    name: str | None = None


class SampleRole(Enum):
    standard = "standard"
    blank = "blank"
    control = "control"


@dataclass(frozen=True, kw_only=True)
class ModelWithEnum:
    role: SampleRole
    name: str | None = None


@dataclass(frozen=True, kw_only=True)
class ModelWithHyphen:
    cube_structure: str | None = field(
        default=None, metadata={"json_name": "cube-structure"}
    )


@dataclass(frozen=True, kw_only=True)
class ModelWithAtType:
    field_type: str | None = field(default=None, metadata={"json_name": "@type"})
    value: str | None = None


# Union test fixtures — must be module-level for get_type_hints to resolve
# string annotations from `from __future__ import annotations`.


@dataclass
class UnionD1:
    x: int


@dataclass
class UnionD2:
    y: int


@dataclass
class HasUnionOfListBoth:
    z: list[UnionD1] | list[UnionD2] | UnionD2 | None = None


@dataclass
class HasUnionOfListSingle:
    z: list[UnionD2] | UnionD2 | None = None


# ---------------------------------------------------------------------------
# unstructure
# ---------------------------------------------------------------------------


class TestUnstructure:
    def test_simple_model(self) -> None:
        obj = SimpleModel(name="test", value=42)
        result = unstructure(obj)
        assert result == {"name": "test", "value": 42}

    def test_omits_none_optional(self) -> None:
        obj = SimpleModel(name="test", value=42, description=None)
        result = unstructure(obj)
        assert "description" not in result

    def test_includes_none_required(self) -> None:
        @dataclass(frozen=True, kw_only=True)
        class RequiredNone:
            value: int | None  # No default — required

        obj = RequiredNone(value=None)
        result = unstructure(obj)
        assert result == {"value": None}

    def test_json_name_metadata(self) -> None:
        obj = ModelWithJsonName(field_asm_manifest="http://test")
        result = unstructure(obj)
        assert "$asm.manifest" in result
        assert result["$asm.manifest"] == "http://test"

    def test_trivial_name_mapping(self) -> None:
        obj = ModelWithJsonName(field_asm_manifest="http://test", device_type="reader")
        result = unstructure(obj)
        assert "device type" in result  # Underscore → space fallback
        assert result["device type"] == "reader"

    def test_nested_dataclass(self) -> None:
        obj = NestedParent(name="parent", child=NestedChild(child_value="hello"))
        result = unstructure(obj)
        assert result["name"] == "parent"
        assert result["child"]["child value"] == "hello"

    def test_list_of_dataclasses(self) -> None:
        obj = ModelWithList(
            items=[NestedChild(child_value="a"), NestedChild(child_value="b")]
        )
        result = unstructure(obj)
        assert len(result["items"]) == 2
        assert result["items"][0]["child value"] == "a"
        assert result["items"][1]["child value"] == "b"

    def test_enum_serializes_as_value(self) -> None:
        obj = ModelWithEnum(role=SampleRole.standard)
        result = unstructure(obj)
        assert result["role"] == "standard"

    def test_hyphen_json_name(self) -> None:
        obj = ModelWithHyphen(cube_structure="test")
        result = unstructure(obj)
        assert "cube-structure" in result

    def test_at_type_json_name(self) -> None:
        obj = ModelWithAtType(field_type="test_type", value="hello")
        result = unstructure(obj)
        assert "@type" in result
        assert result["@type"] == "test_type"

    def test_none_passthrough(self) -> None:
        assert unstructure(None) is None

    def test_primitive_passthrough(self) -> None:
        assert unstructure(42) == 42
        assert unstructure("hello") == "hello"
        assert unstructure(3.14) == 3.14
        assert unstructure(True) is True  # noqa: FBT003

    def test_dict_passthrough(self) -> None:
        result = unstructure({"a": 1, "b": 2})
        assert result == {"a": 1, "b": 2}


# ---------------------------------------------------------------------------
# structure
# ---------------------------------------------------------------------------


class TestStructure:
    def test_simple_model(self) -> None:
        data = {"name": "test", "value": 42}
        result = structure(data, SimpleModel)
        assert result.name == "test"
        assert result.value == 42

    def test_with_optional_field(self) -> None:
        data = {"name": "test", "value": 42, "description": "hello"}
        result = structure(data, SimpleModel)
        assert result.description == "hello"

    def test_missing_optional_uses_default(self) -> None:
        data = {"name": "test", "value": 42}
        result = structure(data, SimpleModel)
        assert result.description is None

    def test_json_name_mapping(self) -> None:
        data = {"$asm.manifest": "http://test"}
        result = structure(data, ModelWithJsonName)
        assert result.field_asm_manifest == "http://test"

    def test_trivial_name_mapping(self) -> None:
        data = {"$asm.manifest": "http://test", "device type": "reader"}
        result = structure(data, ModelWithJsonName)
        assert result.device_type == "reader"

    def test_non_dataclass_passthrough(self) -> None:
        result = structure("hello", str)
        assert result == "hello"

    def test_extra_keys_ignored(self) -> None:
        data = {"name": "test", "value": 42, "unknown_field": "ignored"}
        result = structure(data, SimpleModel)
        assert result.name == "test"


# ---------------------------------------------------------------------------
# Roundtrip
# ---------------------------------------------------------------------------


class TestRoundtrip:
    def test_simple_roundtrip(self) -> None:
        obj = SimpleModel(name="test", value=42, description="hello")
        assert structure(unstructure(obj), SimpleModel) == obj

    def test_nested_roundtrip(self) -> None:
        obj = NestedParent(name="parent", child=NestedChild(child_value="hello"))
        assert structure(unstructure(obj), NestedParent) == obj

    def test_list_roundtrip(self) -> None:
        obj = ModelWithList(
            items=[NestedChild(child_value="a"), NestedChild(child_value="b")],
            name="test",
        )
        assert structure(unstructure(obj), ModelWithList) == obj

    def test_json_name_roundtrip(self) -> None:
        obj = ModelWithJsonName(field_asm_manifest="http://test", device_type="reader")
        assert structure(unstructure(obj), ModelWithJsonName) == obj

    def test_enum_roundtrip(self) -> None:
        obj = ModelWithEnum(role=SampleRole.blank, name="test")
        assert structure(unstructure(obj), ModelWithEnum) == obj

    def test_hyphen_name_roundtrip(self) -> None:
        obj = ModelWithHyphen(cube_structure="test")
        assert structure(unstructure(obj), ModelWithHyphen) == obj

    def test_at_type_roundtrip(self) -> None:
        obj = ModelWithAtType(field_type="test_type", value="hello")
        assert structure(unstructure(obj), ModelWithAtType) == obj


# ---------------------------------------------------------------------------
# Real model integration
# ---------------------------------------------------------------------------


class TestRealModelSerialization:
    """Tests using actual generated model classes to verify serialization works
    end-to-end with the codegen output."""

    def test_data_cube(self) -> None:
        data_cube = TDatacube(
            cube_structure=TDatacubeStructure(
                dimensions=[
                    TDatacubeComponent(
                        field_componentDatatype=FieldComponentDatatype("double"),
                        concept="elapsed time",
                        unit="s",
                    ),
                    TDatacubeComponent(
                        field_componentDatatype=FieldComponentDatatype("int"),
                        concept="wavelength",
                        unit=None,
                    ),
                ],
                measures=[
                    TDatacubeComponent(
                        field_componentDatatype=FieldComponentDatatype("double"),
                        concept="fluorescence",
                        unit="RFU",
                    )
                ],
            ),
            data=TDatacubeData(
                dimensions=[[1.1, 2.2, 3.3], [1.0, 2.0, 3.0]],
                measures=[[4.0, 5.0, None]],
            ),
        )
        asm_dict = unstructure(data_cube)
        assert asm_dict == {
            "cube-structure": {
                "dimensions": [
                    {
                        "@componentDatatype": "double",
                        "concept": "elapsed time",
                        "unit": "s",
                    },
                    {"@componentDatatype": "int", "concept": "wavelength"},
                ],
                "measures": [
                    {
                        "@componentDatatype": "double",
                        "concept": "fluorescence",
                        "unit": "RFU",
                    }
                ],
            },
            "data": {
                "dimensions": [[1.1, 2.2, 3.3], [1.0, 2.0, 3.0]],
                "measures": [[4.0, 5.0, None]],
            },
        }
        assert structure(asm_dict, TDatacube) == data_cube

    def test_quantity_value_serialization(self) -> None:
        from allotropy.allotrope.models.shared.definitions.definitions import (
            TQuantityValue,
        )

        obj = TQuantityValue(value=42.0, unit="mAU")
        result = unstructure(obj)
        assert result["value"] == 42.0
        assert result["unit"] == "mAU"
        # has_statistic_datum_role is optional, should be omitted when None
        assert "has statistic datum role" not in result

    def test_quantity_value_subclass_serialization(self) -> None:
        from allotropy.allotrope.models.shared.definitions.quantity_values import (
            TQuantityValueDegreeCelsius,
        )

        obj = TQuantityValueDegreeCelsius(value=37.0)
        result = unstructure(obj)
        assert result["value"] == 37.0
        assert result["unit"] == "degC"

    def test_datacube_structure_hyphen_name(self) -> None:
        cube_structure = TDatacubeStructure(dimensions=[], measures=[])
        cube = TDatacube(cube_structure=cube_structure)
        result = unstructure(cube)
        assert "cube-structure" in result

    def test_statistic_datum_role_enum(self) -> None:
        from allotropy.allotrope.models.shared.definitions.definitions import (
            TStatisticDatumRole,
        )

        result = unstructure(TStatisticDatumRole.arithmetic_mean_role)
        assert result == "arithmetic mean role"

    def test_invalid_json_float_enum(self) -> None:
        from allotropy.allotrope.models.shared.definitions.definitions import (
            InvalidJsonFloat,
        )

        result = unstructure(InvalidJsonFloat.NaN)
        assert result == "NaN"


# ---------------------------------------------------------------------------
# Custom information document
# ---------------------------------------------------------------------------


class TestCustomInformationDocument:
    def test_roundtrip(self) -> None:
        item = add_custom_information_document(
            ProcessedDataDocumentItem(
                cycle_threshold_result=TQuantityValueUnitless(value=2.0),
                data_processing_document=DataProcessingDocument(
                    cycle_threshold_value_setting=TQuantityValueUnitless(value=1.0),
                ),
            ),
            {
                "extra key": "Value",
                "$w.e\\ir:[d]-k'e~y/(v^a=l@ue)°#": "Other value",
            },
        )

        assert item.custom_information_document.extra_key == "Value"  # type: ignore
        assert item.custom_information_document._DOLLAR_w_POINT_e_BSLASH_ir_COLON__OBRACKET_d_CBRACKET__DASH_k_QUOTE_e_TILDE_y_SLASH__OPAREN_v_CARET_a_EQUALS_l_AT_ue_CPAREN__DEG__NUMBER_ == "Other value"  # type: ignore
        asm_dict = unstructure(item)
        assert asm_dict == {
            "cycle threshold result": {"value": 2.0, "unit": "(unitless)"},
            "data processing document": {
                "cycle threshold value setting": {
                    "value": 1.0,
                    "unit": "(unitless)",
                },
            },
            "custom information document": {
                "extra key": "Value",
                "$w.e\\ir:[d]-k'e~y/(v^a=l@ue)°#": "Other value",
            },
        }
        assert structure(asm_dict, ProcessedDataDocumentItem) == item

    def test_nested_list_preserved(self) -> None:
        """Nested lists (e.g. data cube arrays) should pass through unchanged."""
        from allotropy.allotrope.converter import (
            structure_custom_information_document,
            _unstructure_custom_information_document,
        )

        doc = {"dimensions": [[1, 2, 3], [4, 5, 6]], "label": "cube"}
        structured = structure_custom_information_document(doc, "test")
        result = _unstructure_custom_information_document(structured)
        assert result == doc


# ---------------------------------------------------------------------------
# Dynamic dataclass handling
# ---------------------------------------------------------------------------


class TestDynamicDataclass:
    def test_optional_none_omitted(self) -> None:
        test_data_class = make_dataclass(
            "test_data_class",
            [
                ("sample_id", str),
                ("volume", int),
                ("scientist", str | None, field(default=None)),  # type: ignore
            ],
        )
        test_class = test_data_class(sample_id="abc", volume=5, scientist=None)
        asm_dict = unstructure(test_class)
        assert asm_dict == {
            "sample id": "abc",
            "volume": 5,
        }
        assert structure(asm_dict, test_data_class) == test_class

    def test_required_none_preserved(self) -> None:
        test_data_class = make_dataclass(
            "test_data_class",
            [("sample_id", str), ("volume", int), ("scientist", str | None)],  # type: ignore
        )
        test_class = test_data_class(sample_id="abc", volume=5, scientist=None)
        asm_dict = unstructure(test_class)
        assert asm_dict == {
            "sample id": "abc",
            "volume": 5,
            "scientist": None,
        }
        assert structure(asm_dict, test_data_class) == test_class


# ---------------------------------------------------------------------------
# Union handling
# ---------------------------------------------------------------------------


class TestUnionOfLists:
    def test_list_of_first_variant(self) -> None:
        obj = HasUnionOfListBoth(z=[UnionD1(1), UnionD1(2)])
        obj_dict = unstructure(obj)
        assert obj_dict == {"z": [{"x": 1}, {"x": 2}]}
        assert structure(obj_dict, HasUnionOfListBoth) == obj

    def test_list_of_second_variant(self) -> None:
        obj = HasUnionOfListBoth(z=[UnionD2(1)])
        obj_dict = unstructure(obj)
        assert obj_dict == {"z": [{"y": 1}]}
        assert structure(obj_dict, HasUnionOfListBoth) == obj

    def test_single_variant(self) -> None:
        obj = HasUnionOfListSingle(z=UnionD2(1))
        obj_dict = unstructure(obj)
        assert obj_dict == {"z": {"y": 1}}
        assert structure(obj_dict, HasUnionOfListSingle) == obj

    def test_none_variant(self) -> None:
        obj = HasUnionOfListSingle(z=None)
        obj_dict = unstructure(obj)
        assert obj_dict == {}
        assert structure(obj_dict, HasUnionOfListSingle) == obj


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    def test_empty_list(self) -> None:
        obj = ModelWithList(items=[])
        result = unstructure(obj)
        assert result["items"] == []

    def test_deeply_nested(self) -> None:
        @dataclass(frozen=True, kw_only=True)
        class Level3:
            value: str

        @dataclass(frozen=True, kw_only=True)
        class Level2:
            child: Level3

        @dataclass(frozen=True, kw_only=True)
        class Level1:
            child: Level2

        obj = Level1(child=Level2(child=Level3(value="deep")))
        result = unstructure(obj)
        assert result["child"]["child"]["value"] == "deep"


# ---------------------------------------------------------------------------
# json_name contract: codegen metadata ↔ converter fallback must agree
# ---------------------------------------------------------------------------


def _discover_generated_modules() -> list[str]:
    """Find all model modules marked as generated by schema_gen."""
    models_dir = Path("src/allotropy/allotrope/models/adm")
    modules = []
    for f in sorted(models_dir.rglob("*.py")):
        if f.name == "__init__.py":
            continue
        content = f.read_text()
        if "# generated by allotropy.schema_gen" in content:
            rel = f.relative_to(Path("src"))
            modules.append(str(rel).replace("/", ".").replace(".py", ""))
    return modules


def _collect_dataclasses(module_name: str) -> list[type]:
    """Import a module and return all dataclass types defined in it.

    Returns an empty list if the module cannot be imported (e.g. missing
    quantity value types that haven't been generated yet).
    """
    from dataclasses import is_dataclass

    try:
        mod = importlib.import_module(module_name)
    except (ImportError, ModuleNotFoundError):
        return []
    result = []
    for name in dir(mod):
        obj = getattr(mod, name)
        if isinstance(obj, type) and is_dataclass(obj) and obj.__module__ == module_name:
            result.append(obj)
    return result


class TestJsonNameContract:
    """Verify the json_name contract between codegen and converter.

    For every field in every generated dataclass:
    - If json_name metadata is present, it must differ from the default
      fallback (otherwise the metadata is redundant).
    - If json_name metadata is absent, the default fallback must produce
      a valid JSON key (no Python-only artifacts like leading underscores).
    """

    def test_json_name_metadata_only_when_needed(self) -> None:
        """Fields with json_name metadata should need it (non-trivial mapping)."""
        redundant: list[str] = []
        for module_name in _discover_generated_modules():
            for cls in _collect_dataclasses(module_name):
                for f in fields(cls):
                    json_name = f.metadata.get("json_name")
                    if json_name is not None:
                        fallback = default_json_name(f.name)
                        if json_name == fallback:
                            redundant.append(
                                f"{cls.__name__}.{f.name}: json_name={json_name!r} "
                                f"== default fallback"
                            )
        assert not redundant, (
            f"Found {len(redundant)} fields with redundant json_name metadata "
            f"(metadata matches fallback):\n" + "\n".join(redundant[:20])
        )

    def test_no_field_produces_empty_json_key(self) -> None:
        """Every field must map to a non-empty JSON key."""
        empty_keys: list[str] = []
        for module_name in _discover_generated_modules():
            for cls in _collect_dataclasses(module_name):
                for f in fields(cls):
                    json_name = f.metadata.get("json_name", default_json_name(f.name))
                    if not json_name or not json_name.strip():
                        empty_keys.append(f"{cls.__name__}.{f.name}")
        assert not empty_keys, f"Fields with empty JSON keys: {empty_keys}"
