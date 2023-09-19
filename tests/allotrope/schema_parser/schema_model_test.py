from allotropy.allotrope.schema_parser.schema_model import (
    get_all_schema_components,
    snake_to_upper_camel,
)


def test_snake_to_upper_camel() -> None:
    assert "SampleDocument" == snake_to_upper_camel("sample document", " ")


def test_get_all_schema_components() -> None:
    schema = {
        "type": "object",
        "properties": {
            "prop1": {"type": "string"},
            "nested_prop": {
                "type": "object",
                "properties": {
                    "nested_prop2": {"type": "string"},
                },
            },
        },
    }

    assert {
        "prop1": {"type": "string"},
        "nested_prop": {
            "type": "object",
            "properties": {
                "nested_prop2": {"type": "string"},
            },
        },
        "nested_prop2": {"type": "string"},
    } == get_all_schema_components(schema)


def test_get_all_schema_components_list() -> None:
    schema = {
        "type": "array",
        "items": {"type": "object", "properties": {"prop1": {"type": "string"}}},
    }

    assert {"prop1": {"type": "string"}} == get_all_schema_components(schema)


def test_get_all_schema_components_all_of() -> None:
    schema = {
        "type": "array",
        "items": {
            "allOf": [
                {
                    "type": "object",
                    "properties": {
                        "allOf prop1": {
                            "type": "object",
                            "properties": {"value": {"type": "number"}},
                        },
                        "allOf prop2": {"type": "boolean"},
                    },
                },
                {
                    "properties": {
                        "allOf prop3": {"type": "string"},
                    }
                },
            ]
        },
        "minItems": 0,
    }

    assert {
        "allOf prop1": {
            "type": "object",
            "properties": {"value": {"type": "number"}},
        },
        "value": {"type": "number"},
        "allOf prop2": {"type": "boolean"},
        "allOf prop3": {"type": "string"},
    } == get_all_schema_components(schema)


def test_get_all_schema_components_one_of() -> None:
    schema = {
        "type": "object",
        "properties": {
            "oneOf prop": {
                "oneOf": [
                    {"type": "string"},
                    {
                        "type": "object",
                        "properties": {
                            "value": {"type": "string"},
                        },
                    },
                    {
                        "type": "object",
                        "properties": {
                            "other": {"type": "string"},
                        },
                    },
                ],
            },
        },
    }

    assert {
        "oneOf prop item": {
            "type": "object",
            "properties": {
                "value": {"type": "string"},
            },
        },
        "value": {"type": "string"},
        "oneOf prop item1": {
            "type": "object",
            "properties": {
                "other": {"type": "string"},
            },
        },
        "other": {"type": "string"},
    } == get_all_schema_components(schema)
