import os
from typing import Any, cast
import unittest
from unittest.mock import patch

from allotropy.parsers.utils.json import JsonData


class TestJsonData(unittest.TestCase):
    def setUp(self) -> None:
        # Create sample data for testing
        self.test_data = {
            "string_value": "test",
            "integer_value": 42,
            "float_value": 3.14,
            "boolean_value": True,
            "null_value": None,
            "string_percentage": "25%",
            "nested": {"key1": "value1", "key2": 2},
            "array": [1, 2, 3],
            "object_array": [{"id": 1, "name": "item1"}, {"id": 2, "name": "item2"}],
        }
        self.json_data = JsonData(self.test_data)

    def test_get_primitive_types(self) -> None:
        # Test retrieving different primitive types
        self.assertEqual(self.json_data.get(str, "string_value"), "test")
        self.assertEqual(self.json_data.get(int, "integer_value"), 42)
        self.assertEqual(self.json_data.get(float, "float_value"), 3.14)
        self.assertEqual(self.json_data.get(bool, "boolean_value"), True)

    def test_get_with_default(self) -> None:
        # Test retrieving with default values
        self.assertEqual(self.json_data.get(str, "non_existent", "default"), "default")
        self.assertEqual(self.json_data.get(int, "non_existent", 100), 100)

        # Test when type doesn't match
        self.assertIsNone(self.json_data.get(int, "string_value"))
        self.assertEqual(self.json_data.get(int, "string_value", 999), 999)

    def test_get_with_key_iterable(self) -> None:
        # Test using multiple keys (first found wins)
        self.assertEqual(self.json_data.get(int, ["non_existent", "integer_value"]), 42)
        self.assertEqual(
            self.json_data.get(
                str, ["non_existent", "also_non_existent", "string_value"]
            ),
            "test",
        )

        # Test when none of the keys exist
        self.assertIsNone(self.json_data.get(str, ["key1", "key2", "key3"]))

    def test_get_with_percentage(self) -> None:
        # Test percentage handling
        self.assertEqual(self.json_data.get(float, "string_percentage"), 25.0)

    def test_bool_conversion(self) -> None:
        # Test boolean conversion
        bool_data = JsonData(
            {
                "true_string": "true",
                "false_string": "false",
                "yes_string": "yes",
                "no_string": "no",
                "one_string": "1",
                "zero_string": "0",
            }
        )

        self.assertTrue(bool_data.get(bool, "true_string"))
        self.assertTrue(bool_data.get(bool, "yes_string"))
        self.assertTrue(bool_data.get(bool, "one_string"))

        self.assertFalse(bool_data.get(bool, "false_string"))
        self.assertFalse(bool_data.get(bool, "no_string"))
        self.assertFalse(bool_data.get(bool, "zero_string"))

    def test_nested_access(self) -> None:
        # Test accessing nested values
        nested_value = self.json_data.get_nested(str, ["nested", "key1"])
        self.assertEqual(nested_value, "value1")

        # Test with default value
        non_existent = self.json_data.get_nested(
            str, ["nested", "non_existent"], "default"
        )
        self.assertEqual(non_existent, "default")

        # Test with invalid path
        invalid_path = self.json_data.get_nested(str, ["invalid", "path"], "fallback")
        self.assertEqual(invalid_path, "fallback")

    def test_getitem(self) -> None:
        # Test dictionary-like access with []
        self.assertEqual(self.json_data[str, "string_value"], "test")

        # Test with error message
        with self.assertRaises(Exception) as context:
            self.json_data[str, "non_existent", "Error message"]
        self.assertTrue("Error message" in str(context.exception))

    def test_mark_read(self) -> None:
        # Test marking keys as read
        self.json_data.mark_read("string_value")
        self.assertIn("string_value", self.json_data.read_keys)

        # Test marking multiple keys
        self.json_data.mark_read({"integer_value", "float_value"})
        self.assertIn("integer_value", self.json_data.read_keys)
        self.assertIn("float_value", self.json_data.read_keys)

    def test_has_key(self) -> None:
        # Test key existence check
        self.assertTrue(self.json_data.has_key("string_value"))
        self.assertFalse(self.json_data.has_key("non_existent"))

    def test_get_unread(self) -> None:
        # Test getting unread keys
        self.json_data.get(str, "string_value")  # Mark as read

        unread = self.json_data.get_unread()
        self.assertNotIn("string_value", unread)
        self.assertIn("integer_value", unread)

        # Test with regex
        self.json_data.get(int, "integer_value")  # Mark as read
        float_unread = self.json_data.get_unread("float.*")
        self.assertEqual(list(float_unread.keys()), ["float_value"])

        # Test with skip
        all_except_boolean = self.json_data.get_unread(skip={"boolean_value"})
        self.assertNotIn("boolean_value", all_except_boolean)
        self.assertIn(
            "boolean_value", self.json_data.read_keys
        )  # Skip should mark as read

    def test_get_custom_keys(self) -> None:
        # Test getting custom keys
        custom_value = self.json_data.get_custom_keys("string.*")
        # The get_custom_keys method converts percentage strings to float values
        self.assertEqual(
            custom_value, {"string_value": "test", "string_percentage": 25.0}
        )

        # Test with no matches
        empty = self.json_data.get_custom_keys("xyz.*")
        self.assertEqual(empty, {})

    def test_filter_none_values(self) -> None:
        # Test that None values are filtered out when using ValidateRawMode.NOT_NONE
        value = self.json_data.get(str, "null_value", validate=JsonData.NOT_NONE)
        self.assertIsNone(value)

    @patch.dict(os.environ, {"WARN_UNUSED_KEYS": "1"})
    def test_destructor_warning(self) -> None:
        # Test warning on unused keys when object goes out of scope
        with self.assertWarns(Warning):
            # Create JsonData without reading all keys, then let it go out of scope
            JsonData({"test": "value"})

    def test_complex_data_types(self) -> None:
        # The JsonData.get() method is designed for primitive types
        # Complex types should be accessed via .data directly

        # Test array
        array_data = cast(list[int], self.json_data.data.get("array"))
        self.assertIsInstance(array_data, list)
        self.assertEqual(array_data, [1, 2, 3])

        # Test nested object
        nested_data = cast(dict[str, Any], self.json_data.data.get("nested"))
        self.assertIsInstance(nested_data, dict)
        self.assertEqual(nested_data, {"key1": "value1", "key2": 2})

        # Test object array
        object_array = cast(
            list[dict[str, Any]], self.json_data.data.get("object_array")
        )
        self.assertIsInstance(object_array, list)
        self.assertEqual(len(object_array), 2)
        self.assertEqual(object_array[0]["id"], 1)


if __name__ == "__main__":
    unittest.main()
