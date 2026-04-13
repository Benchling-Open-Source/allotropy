"""Tests for allotropy.schema_gen.serializer — dataclass ↔ JSON dict roundtrip."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from allotropy.schema_gen.serializer import from_dict, to_dict

# ---------------------------------------------------------------------------
# Test fixtures — simple dataclasses
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


# ---------------------------------------------------------------------------
# to_dict
# ---------------------------------------------------------------------------


class TestToDict:
    def test_simple_model(self) -> None:
        obj = SimpleModel(name="test", value=42)
        result = to_dict(obj)
        assert result == {"name": "test", "value": 42}

    def test_omits_none_optional(self) -> None:
        obj = SimpleModel(name="test", value=42, description=None)
        result = to_dict(obj)
        assert "description" not in result

    def test_includes_none_required(self) -> None:
        # Required fields (no default) keep None values
        @dataclass(frozen=True, kw_only=True)
        class RequiredNone:
            value: int | None  # No default — required

        obj = RequiredNone(value=None)
        result = to_dict(obj)
        assert result == {"value": None}

    def test_json_name_metadata(self) -> None:
        obj = ModelWithJsonName(field_asm_manifest="http://test")
        result = to_dict(obj)
        assert "$asm.manifest" in result
        assert result["$asm.manifest"] == "http://test"

    def test_trivial_name_mapping(self) -> None:
        obj = ModelWithJsonName(field_asm_manifest="http://test", device_type="reader")
        result = to_dict(obj)
        assert "device type" in result  # Underscore → space fallback
        assert result["device type"] == "reader"

    def test_nested_dataclass(self) -> None:
        obj = NestedParent(name="parent", child=NestedChild(child_value="hello"))
        result = to_dict(obj)
        assert result["name"] == "parent"
        assert result["child"]["child value"] == "hello"

    def test_list_of_dataclasses(self) -> None:
        obj = ModelWithList(
            items=[NestedChild(child_value="a"), NestedChild(child_value="b")]
        )
        result = to_dict(obj)
        assert len(result["items"]) == 2
        assert result["items"][0]["child value"] == "a"
        assert result["items"][1]["child value"] == "b"

    def test_enum_serializes_as_value(self) -> None:
        obj = ModelWithEnum(role=SampleRole.standard)
        result = to_dict(obj)
        assert result["role"] == "standard"

    def test_hyphen_json_name(self) -> None:
        obj = ModelWithHyphen(cube_structure="test")
        result = to_dict(obj)
        assert "cube-structure" in result

    def test_at_type_json_name(self) -> None:
        obj = ModelWithAtType(field_type="test_type", value="hello")
        result = to_dict(obj)
        assert "@type" in result
        assert result["@type"] == "test_type"

    def test_none_passthrough(self) -> None:
        assert to_dict(None) is None

    def test_primitive_passthrough(self) -> None:
        assert to_dict(42) == 42
        assert to_dict("hello") == "hello"
        assert to_dict(3.14) == 3.14
        assert to_dict(True) is True  # noqa: FBT003

    def test_dict_passthrough(self) -> None:
        result = to_dict({"a": 1, "b": 2})
        assert result == {"a": 1, "b": 2}


# ---------------------------------------------------------------------------
# from_dict
# ---------------------------------------------------------------------------


class TestFromDict:
    def test_simple_model(self) -> None:
        data = {"name": "test", "value": 42}
        result = from_dict(data, SimpleModel)
        assert result.name == "test"
        assert result.value == 42

    def test_with_optional_field(self) -> None:
        data = {"name": "test", "value": 42, "description": "hello"}
        result = from_dict(data, SimpleModel)
        assert result.description == "hello"

    def test_missing_optional_uses_default(self) -> None:
        data = {"name": "test", "value": 42}
        result = from_dict(data, SimpleModel)
        assert result.description is None

    def test_json_name_mapping(self) -> None:
        data = {"$asm.manifest": "http://test"}
        result = from_dict(data, ModelWithJsonName)
        assert result.field_asm_manifest == "http://test"

    def test_trivial_name_mapping(self) -> None:
        data = {"$asm.manifest": "http://test", "device type": "reader"}
        result = from_dict(data, ModelWithJsonName)
        assert result.device_type == "reader"

    def test_non_dataclass_passthrough(self) -> None:
        result = from_dict("hello", str)
        assert result == "hello"

    def test_extra_keys_ignored(self) -> None:
        data = {"name": "test", "value": 42, "unknown_field": "ignored"}
        result = from_dict(data, SimpleModel)
        assert result.name == "test"


# ---------------------------------------------------------------------------
# Roundtrip
# ---------------------------------------------------------------------------


class TestRoundtrip:
    def test_simple_roundtrip(self) -> None:
        obj = SimpleModel(name="test", value=42, description="hello")
        result = from_dict(to_dict(obj), SimpleModel)
        assert result == obj

    def test_nested_roundtrip(self) -> None:
        obj = NestedParent(name="parent", child=NestedChild(child_value="hello"))
        result = from_dict(to_dict(obj), NestedParent)
        assert result == obj

    def test_list_roundtrip(self) -> None:
        obj = ModelWithList(
            items=[NestedChild(child_value="a"), NestedChild(child_value="b")],
            name="test",
        )
        result = from_dict(to_dict(obj), ModelWithList)
        assert result == obj

    def test_json_name_roundtrip(self) -> None:
        obj = ModelWithJsonName(field_asm_manifest="http://test", device_type="reader")
        result = from_dict(to_dict(obj), ModelWithJsonName)
        assert result == obj

    def test_enum_roundtrip(self) -> None:
        obj = ModelWithEnum(role=SampleRole.blank, name="test")
        result = from_dict(to_dict(obj), ModelWithEnum)
        assert result == obj

    def test_hyphen_name_roundtrip(self) -> None:
        obj = ModelWithHyphen(cube_structure="test")
        result = from_dict(to_dict(obj), ModelWithHyphen)
        assert result == obj

    def test_at_type_roundtrip(self) -> None:
        obj = ModelWithAtType(field_type="test_type", value="hello")
        result = from_dict(to_dict(obj), ModelWithAtType)
        assert result == obj


# ---------------------------------------------------------------------------
# Real model integration
# ---------------------------------------------------------------------------


class TestRealModelSerialization:
    """Tests using actual generated model classes to verify serialization works
    end-to-end with the codegen output."""

    def test_quantity_value_serialization(self) -> None:
        from allotropy.allotrope.models.shared.definitions.definitions import (
            TQuantityValue,
        )

        obj = TQuantityValue(value=42.0, unit="mAU")
        result = to_dict(obj)
        assert result["value"] == 42.0
        assert result["unit"] == "mAU"
        # has_statistic_datum_role is optional, should be omitted when None
        assert "has statistic datum role" not in result

    def test_quantity_value_subclass_serialization(self) -> None:
        from allotropy.allotrope.models.shared.definitions.quantity_values import (
            TQuantityValueDegC,
        )

        obj = TQuantityValueDegC(value=37.0)
        result = to_dict(obj)
        assert result["value"] == 37.0
        assert result["unit"] == "degC"

    def test_datacube_structure_hyphen_name(self) -> None:
        from allotropy.allotrope.models.shared.definitions.definitions import (
            TDatacube,
            TDatacubeStructure,
        )

        structure = TDatacubeStructure(dimensions=[], measures=[])
        cube = TDatacube(cube_structure=structure)
        result = to_dict(cube)
        assert "cube-structure" in result

    def test_statistic_datum_role_enum(self) -> None:
        from allotropy.allotrope.models.shared.definitions.definitions import (
            TStatisticDatumRole,
        )

        result = to_dict(TStatisticDatumRole.arithmetic_mean_role)
        assert result == "arithmetic mean role"

    def test_invalid_json_float_enum(self) -> None:
        from allotropy.allotrope.models.shared.definitions.definitions import (
            InvalidJsonFloat,
        )

        result = to_dict(InvalidJsonFloat.NaN)
        assert result == "NaN"


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    def test_empty_list(self) -> None:
        obj = ModelWithList(items=[])
        result = to_dict(obj)
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
        result = to_dict(obj)
        assert result["child"]["child"]["value"] == "deep"
