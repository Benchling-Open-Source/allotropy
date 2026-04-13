"""Tests for allotropy.schema_gen.naming — URL and name transformations."""

from __future__ import annotations

from pathlib import Path

import pytest

from allotropy.schema_gen.naming import (
    allotrope_url_to_gitlab_raw,
    allotrope_url_to_relative_path,
    def_name_to_class_name,
    gitlab_blob_to_raw,
    normalize_schema_url,
    parse_ref,
    property_name_to_class_name,
    property_name_to_python,
    quantity_value_class_name,
    schema_url_to_cache_path,
    schema_url_to_model_file,
    schema_url_to_module_path,
    unit_symbol_to_class_name,
)

BASE = "http://purl.allotrope.org/json-schemas/"
CORE_URL = f"{BASE}adm/core/REC/2024/09/core.schema"
QPCR_URL = f"{BASE}adm/pcr/REC/2024/09/qpcr.schema"
UNITS_URL = f"{BASE}qudt/REC/2024/09/units.schema"


# ---------------------------------------------------------------------------
# URL parsing
# ---------------------------------------------------------------------------


class TestAllotropeUrlToRelativePath:
    def test_standard_url(self) -> None:
        assert (
            allotrope_url_to_relative_path(CORE_URL)
            == "adm/core/REC/2024/09/core.schema"
        )

    def test_technique_url(self) -> None:
        assert (
            allotrope_url_to_relative_path(QPCR_URL)
            == "adm/pcr/REC/2024/09/qpcr.schema"
        )

    def test_units_url(self) -> None:
        assert (
            allotrope_url_to_relative_path(UNITS_URL) == "qudt/REC/2024/09/units.schema"
        )

    def test_non_allotrope_url_raises(self) -> None:
        with pytest.raises(ValueError, match="Not an Allotrope URL"):
            allotrope_url_to_relative_path("https://example.com/schema")


class TestAllotropeUrlToGitlabRaw:
    def test_adds_json_extension(self) -> None:
        result = allotrope_url_to_gitlab_raw(CORE_URL)
        assert result.endswith("/core.schema.json")
        assert "/-/raw/main/" in result

    def test_preserves_existing_json(self) -> None:
        result = allotrope_url_to_gitlab_raw(CORE_URL + ".json")
        assert result.endswith("/core.schema.json")
        assert not result.endswith(".json.json")


class TestGitlabBlobToRaw:
    def test_converts_blob_to_raw(self) -> None:
        blob = "https://gitlab.com/allotrope-public/asm/-/blob/main/json-schemas/foo"
        result = gitlab_blob_to_raw(blob)
        assert "/-/raw/main/" in result
        assert "/-/blob/" not in result


class TestNormalizeSchemaUrl:
    def test_allotrope_url_passthrough(self) -> None:
        assert normalize_schema_url(CORE_URL) == CORE_URL

    def test_strips_json_extension(self) -> None:
        assert normalize_schema_url(CORE_URL + ".json") == CORE_URL

    def test_strips_fragment(self) -> None:
        assert normalize_schema_url(CORE_URL + "#/$defs/foo") == CORE_URL

    def test_gitlab_raw_url(self) -> None:
        raw = "https://gitlab.com/allotrope-public/asm/-/raw/main/json-schemas/adm/core/REC/2024/09/core.schema.json"
        assert normalize_schema_url(raw) == CORE_URL

    def test_unknown_url_raises(self) -> None:
        with pytest.raises(ValueError, match="Cannot normalize"):
            normalize_schema_url("https://example.com/unknown")


class TestParseRef:
    def test_local_ref(self) -> None:
        schema_url, def_name = parse_ref("#/$defs/tStringValue")
        assert schema_url is None
        assert def_name == "tStringValue"

    def test_external_ref(self) -> None:
        ref = f"{CORE_URL}#/$defs/tStringValue"
        schema_url, def_name = parse_ref(ref)
        assert schema_url == CORE_URL
        assert def_name == "tStringValue"

    def test_json_pointer_decoding(self) -> None:
        # ~1 decodes to /
        ref = f"{UNITS_URL}#/$defs/pg~1mL"
        schema_url, def_name = parse_ref(ref)
        assert schema_url == UNITS_URL
        assert def_name == "pg/mL"

    def test_whole_schema_ref(self) -> None:
        schema_url, def_name = parse_ref(CORE_URL)
        assert schema_url == CORE_URL
        assert def_name is None

    def test_url_encoded_fragment(self) -> None:
        ref = f"{UNITS_URL}#/$defs/pg%2FmL"
        schema_url, def_name = parse_ref(ref)
        assert schema_url == UNITS_URL
        assert def_name == "pg/mL"


# ---------------------------------------------------------------------------
# Path mapping
# ---------------------------------------------------------------------------


class TestSchemaUrlToCachePath:
    def test_maps_to_json_file(self) -> None:
        path = schema_url_to_cache_path(CORE_URL, Path("/cache"))
        assert path == Path("/cache/adm/core/REC/2024/09/core.schema.json")

    def test_preserves_existing_json(self) -> None:
        path = schema_url_to_cache_path(CORE_URL + ".json", Path("/cache"))
        assert str(path).endswith("core.schema.json")
        assert not str(path).endswith(".json.json")


class TestSchemaUrlToModulePath:
    def test_core_module(self) -> None:
        assert schema_url_to_module_path(CORE_URL) == "adm.core.rec._2024._09.core"

    def test_technique_module(self) -> None:
        assert schema_url_to_module_path(QPCR_URL) == "adm.pcr.rec._2024._09.qpcr"

    def test_units_module(self) -> None:
        assert schema_url_to_module_path(UNITS_URL) == "qudt.rec._2024._09.units"

    def test_hyphenated_schema(self) -> None:
        url = f"{BASE}adm/cell-counting/REC/2024/09/cell-counting.schema"
        assert (
            schema_url_to_module_path(url)
            == "adm.cell_counting.rec._2024._09.cell_counting"
        )


class TestSchemaUrlToModelFile:
    def test_core_file(self) -> None:
        path = schema_url_to_model_file(CORE_URL, Path("/models"))
        assert path == Path("/models/adm/core/rec/_2024/_09/core.py")

    def test_hyphenated_technique(self) -> None:
        url = f"{BASE}adm/cell-counting/REC/2024/09/cell-counting.schema"
        path = schema_url_to_model_file(url, Path("/models"))
        assert path == Path("/models/adm/cell_counting/rec/_2024/_09/cell_counting.py")


# ---------------------------------------------------------------------------
# Name conversions
# ---------------------------------------------------------------------------


class TestPropertyNameToPython:
    def test_space_separated(self) -> None:
        assert (
            property_name_to_python("device system document")
            == "device_system_document"
        )

    def test_dollar_prefix(self) -> None:
        assert property_name_to_python("$asm.manifest") == "field_asm_manifest"

    def test_at_type(self) -> None:
        assert property_name_to_python("@type") == "field_type"

    def test_at_index(self) -> None:
        assert property_name_to_python("@index") == "field_index"

    def test_at_id(self) -> None:
        assert property_name_to_python("@id") == "field_id"

    def test_camel_case(self) -> None:
        assert property_name_to_python("minInclusive") == "min_inclusive"

    def test_field_component_datatype(self) -> None:
        assert (
            property_name_to_python("fieldComponentDatatype")
            == "field_component_datatype"
        )

    def test_hyphenated(self) -> None:
        assert property_name_to_python("cube-structure") == "cube_structure"

    def test_ph(self) -> None:
        assert property_name_to_python("pH") == "p_h"

    def test_pco2(self) -> None:
        assert property_name_to_python("pCO2") == "p_co2"

    def test_parenthesized_qualifier(self) -> None:
        result = property_name_to_python("cycle threshold result (qPCR)")
        assert result == "cycle_threshold_result__q_pcr_"

    def test_leading_digit(self) -> None:
        result = property_name_to_python("95% confidence interval")
        assert result.startswith("_")

    def test_asm_fill_value(self) -> None:
        assert property_name_to_python("$asm.fill-value") == "field_asm_fill_value"


class TestDefNameToClassName:
    def test_camel_case(self) -> None:
        assert def_name_to_class_name("tStringValue") == "TStringValue"

    def test_preserves_case_pattern(self) -> None:
        assert (
            def_name_to_class_name("measurementDocumentItems")
            == "MeasurementDocumentItems"
        )

    def test_space_separated(self) -> None:
        assert (
            def_name_to_class_name("device system document") == "DeviceSystemDocument"
        )

    def test_single_char(self) -> None:
        assert def_name_to_class_name("t") == "T"

    def test_lowercase_camel(self) -> None:
        assert def_name_to_class_name("cFillValueBoolean") == "CFillValueBoolean"


class TestPropertyNameToClassName:
    def test_space_separated(self) -> None:
        assert (
            property_name_to_class_name("device system document")
            == "DeviceSystemDocument"
        )

    def test_hyphenated(self) -> None:
        assert property_name_to_class_name("sample-role-type") == "SampleRoleType"

    def test_underscored(self) -> None:
        assert property_name_to_class_name("sample_role_type") == "SampleRoleType"


class TestUnitSymbolToClassName:
    def test_simple_unit(self) -> None:
        assert unit_symbol_to_class_name("mAU") == "MAU"

    def test_nanometer(self) -> None:
        assert unit_symbol_to_class_name("nm") == "Nm"

    def test_per_unit(self) -> None:
        assert unit_symbol_to_class_name("pg/mL") == "PgPermL"

    def test_unitless(self) -> None:
        assert unit_symbol_to_class_name("(unitless)") == "Unitless"

    def test_hash(self) -> None:
        assert unit_symbol_to_class_name("#") == "NumberSign"

    def test_percent(self) -> None:
        assert unit_symbol_to_class_name("%") == "Percent"

    def test_degree_celsius(self) -> None:
        assert unit_symbol_to_class_name("degC") == "DegC"

    def test_micro_sign(self) -> None:
        assert unit_symbol_to_class_name("µm") == "Microm"

    def test_greek_mu(self) -> None:
        assert unit_symbol_to_class_name("μL") == "MicroL"

    def test_dot_unit(self) -> None:
        assert unit_symbol_to_class_name("mAU.s") == "MAUDots"

    def test_caret_unit(self) -> None:
        assert unit_symbol_to_class_name("mm^2") == "MmSq"

    def test_per_molar_per_second(self) -> None:
        assert unit_symbol_to_class_name("M-1s-1") == "M1s1"

    def test_leading_digit(self) -> None:
        result = unit_symbol_to_class_name("10^6 cells/mL")
        assert result[0].isalpha()

    def test_number_per_microliter(self) -> None:
        assert unit_symbol_to_class_name("#/μL") == "NumPerMicroL"


class TestQuantityValueClassName:
    def test_mau(self) -> None:
        assert quantity_value_class_name("mAU") == "TQuantityValueMAU"

    def test_nm(self) -> None:
        assert quantity_value_class_name("nm") == "TQuantityValueNm"

    def test_unitless(self) -> None:
        assert quantity_value_class_name("(unitless)") == "TQuantityValueUnitless"
