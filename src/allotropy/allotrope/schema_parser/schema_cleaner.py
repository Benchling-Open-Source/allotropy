import copy
from typing import Any


class SchemaCleaner:
    def __init__(self, schema: dict[str, Any]):
        self.schema = schema

    def _clean(self, schema: dict[str, Any]) -> dict[str, Any]:
        cleaned = {}
        for key, value in schema.items():
            if isinstance(value, dict):
                cleaned[key] = self._clean(value)
            elif key == "allOf" and len(value) == 1:
                # datamodel-codegen cannot handle single-value allOf entries.
                assert isinstance(value[0], dict), "Unhandled case, non-dict value inside allOf"
                for nested_key, nested_value in self._clean(value[0]).items():
                    cleaned[nested_key] = nested_value
            else:
                cleaned[key] = value

        return cleaned

    def clean(self) -> dict[str, Any]:
        return self._clean(self.schema)
