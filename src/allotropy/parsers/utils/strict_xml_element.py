from __future__ import annotations

import os
import re
import traceback
import warnings
from xml.etree import ElementTree

# xml fromstring is vulnerable so defusedxml version is used instead
from defusedxml.ElementTree import fromstring

from allotropy.parsers.utils.values import assert_not_none, try_float_or_none


class StrictXmlElement:
    @classmethod
    def create_from_bytes(cls, data: bytes) -> StrictXmlElement:
        return StrictXmlElement(fromstring(data))

    def __init__(
        self, element: ElementTree.Element, namespaces: dict[str, str] | None = None
    ):
        self.element = element
        self.namespaces = namespaces or {}
        self.read_keys: set[str] = set()
        self.errored = False
        self.creation_stack = traceback.extract_stack()

    def __del__(self) -> None:
        if self.errored:
            return
        # NOTE: this will be turned on by default when all callers have been updated to pass the warning.
        # Only consider attributes as available keys, not child elements
        attribute_keys = set()

        # Add attributes with "attr:" prefix
        for attr_name in self.element.attrib.keys():
            attribute_keys.add(f"attr:{attr_name}")

            # Also check if this is a namespaced attribute and add the ns_attr version
            for namespace_key, namespace_uri in self.namespaces.items():
                if attr_name.startswith(f"{{{namespace_uri}}}"):
                    field_name = attr_name.replace(f"{{{namespace_uri}}}", "")
                    attribute_keys.add(f"ns_attr:{namespace_key}:{field_name}")

        # Filter out attributes that have been read in either form (attr: or ns_attr:)
        unread_keys = set()
        for key in attribute_keys:
            if key.startswith("attr:"):
                attr_name = key[5:]  # Remove "attr:" prefix

                # Check if this is a namespaced attribute that has been read via ns_attr
                is_namespaced_and_read = False
                for namespace_key, namespace_uri in self.namespaces.items():
                    if attr_name.startswith(f"{{{namespace_uri}}}"):
                        field_name = attr_name.replace(f"{{{namespace_uri}}}", "")
                        ns_attr_key = f"ns_attr:{namespace_key}:{field_name}"
                        if ns_attr_key in self.read_keys:
                            is_namespaced_and_read = True
                            break

                # Only consider unread if it hasn't been read via namespaced access and not directly read
                if key not in self.read_keys and not is_namespaced_and_read:
                    unread_keys.add(key)

            elif key.startswith("ns_attr:"):
                # Parse "ns_attr:namespace:field"
                parts = key.split(":", 2)
                if len(parts) == 3:
                    namespace_key, field = parts[1], parts[2]
                    if namespace_key in self.namespaces:
                        namespace_uri = self.namespaces[namespace_key]
                        full_attr_key = f"attr:{{{namespace_uri}}}{field}"

                        # Only consider unread if neither the ns_attr nor the full URI version has been read
                        if (
                            key not in self.read_keys
                            and full_attr_key not in self.read_keys
                        ):
                            unread_keys.add(key)

        # Only warn if we've read at least one key but haven't read all keys
        # This avoids warnings for elements that were never accessed at all
        if unread_keys and self.read_keys:
            if os.getenv("WARN_UNUSED_KEYS"):
                # Find the creation point in the stack (skip the StrictXmlElement.__init__ frame)
                creation_point = None
                for frame in reversed(self.creation_stack):
                    if (
                        frame.name != "__init__"
                        or "strict_xml_element.py" not in frame.filename
                    ):
                        creation_point = (
                            f"{frame.filename}:{frame.lineno} in {frame.name}"
                        )
                        break

                creation_info = (
                    f" (created at {creation_point})" if creation_point else ""
                )

                warnings.warn(
                    f"StrictXmlElement went out of scope without reading all keys{creation_info}, unread: {sorted(unread_keys)}.",
                    stacklevel=2,
                )

    def _get_all_available_keys(self) -> set[str]:
        """Get all available keys (attributes and child elements) from the XML element."""
        keys = set()

        # Add attributes with "attr:" prefix
        for attr_name in self.element.attrib.keys():
            keys.add(f"attr:{attr_name}")

            # Also check if this is a namespaced attribute and add the ns_attr version
            for namespace_key, namespace_uri in self.namespaces.items():
                if attr_name.startswith(f"{{{namespace_uri}}}"):
                    field_name = attr_name.replace(f"{{{namespace_uri}}}", "")
                    keys.add(f"ns_attr:{namespace_key}:{field_name}")

        # Add child elements with "element:" prefix
        child_names = set()
        for child in self.element:
            if child.tag not in child_names:
                keys.add(f"element:{child.tag}")
                child_names.add(child.tag)

        # Add text content if present
        if self.element.text and self.element.text.strip():
            keys.add("text:")

        return keys

    def _get_matching_keys(self, key_or_keys: str | set[str]) -> set[str]:
        """Get keys that match the given pattern(s)."""
        all_keys = self._get_all_available_keys()

        # Normalize keys by adding appropriate prefixes if they don't have them
        normalized_keys = set()
        for regex_key in key_or_keys if isinstance(key_or_keys, set) else {key_or_keys}:
            # If the key doesn't have a prefix and it's a simple attribute name,
            # automatically add the "attr:" prefix
            if not any(
                regex_key.startswith(prefix)
                for prefix in ["attr:", "ns_attr:", "element:", "text:"]
            ):
                # Check if this matches any actual attribute name (including namespaced ones)
                attr_key = f"attr:{regex_key}"
                matches_found = False

                # Check for exact match
                if any(
                    k for k in all_keys if k == attr_key or re.fullmatch(attr_key, k)
                ):
                    normalized_keys.add(attr_key)
                    matches_found = True

                # Check for namespaced matches (e.g., "schemaLocation" should match "attr:{namespace}schemaLocation")
                for key in all_keys:
                    if key.startswith("attr:"):
                        attr_name = key[5:]  # Remove "attr:" prefix
                        # Check if the attribute name ends with our regex_key (for namespaced attributes)
                        if (
                            attr_name.endswith(regex_key)
                            and "{" in attr_name
                            and "}" in attr_name
                        ):
                            # This is a namespaced attribute that ends with our key
                            normalized_keys.add(key)
                            matches_found = True

                if not matches_found:
                    # Keep the original key for other types of matches
                    normalized_keys.add(regex_key)
            else:
                normalized_keys.add(regex_key)

        return {
            matched
            for regex_key in normalized_keys
            for matched in [
                k for k in all_keys if k == regex_key or re.fullmatch(regex_key, k)
            ]
        }

    def mark_read(self, key_or_keys: str | set[str]) -> None:
        """Mark specified keys as read."""
        self.read_keys |= self._get_matching_keys(key_or_keys)

    def mark_all_as_read(self) -> None:
        """Mark all available keys as read to avoid warnings."""
        self.read_keys = self._get_all_available_keys()

    def get_unread(
        self, regex: str | None = None, skip: set[str] | None = None
    ) -> dict[str, str | None]:
        """
        Get unread attributes from this element.

        Args:
            regex: Optional regex pattern to filter keys
            skip: Set of keys to skip

        Returns a dictionary with clean attribute names (prefixes removed):
        - attribute names without "attr:" prefix
        - namespaced attribute names without "ns_attr:" prefix
        """
        # Get only attribute keys, not child elements or text
        attribute_keys = set()

        # Add attributes with "attr:" prefix
        for attr_name in self.element.attrib.keys():
            attribute_keys.add(f"attr:{attr_name}")

            # Also check if this is a namespaced attribute and add the ns_attr version
            for namespace_key, namespace_uri in self.namespaces.items():
                if attr_name.startswith(f"{{{namespace_uri}}}"):
                    field_name = attr_name.replace(f"{{{namespace_uri}}}", "")
                    attribute_keys.add(f"ns_attr:{namespace_key}:{field_name}")

        skip_keys = self._get_matching_keys(skip) if skip else set()
        # Mark explicitly skipped keys as "read"
        self.read_keys |= skip_keys

        matching_keys = (
            {k for k in attribute_keys if regex and re.fullmatch(regex, k)}
            if regex
            else attribute_keys
        )

        unread_keys = {}
        processed_attrs = set()  # Track which attributes we've already processed

        for key in matching_keys - self.read_keys:
            if key.startswith("attr:"):
                attr_name = key[5:]  # Remove "attr:" prefix

                # Check if this is a namespaced attribute that has been read via ns_attr
                is_namespaced_and_read = False
                namespace_form_key = None
                for namespace_key, namespace_uri in self.namespaces.items():
                    if attr_name.startswith(f"{{{namespace_uri}}}"):
                        field_name = attr_name.replace(f"{{{namespace_uri}}}", "")
                        ns_attr_key = f"ns_attr:{namespace_key}:{field_name}"
                        namespace_form_key = f"{namespace_key}:{field_name}"
                        # Check if this attribute was read via namespaced access
                        if ns_attr_key in self.read_keys:
                            is_namespaced_and_read = True
                            break

                # Only include if it hasn't been read via namespaced access and we haven't processed this attribute yet
                if not is_namespaced_and_read and attr_name not in processed_attrs:
                    # If there's a namespace form available, prefer that over the full URI form
                    if (
                        namespace_form_key
                        and f"ns_attr:{namespace_key}:{field_name}" in matching_keys
                    ):
                        # Skip this full URI form - we'll process the namespace form instead
                        pass
                    else:
                        # Convert full URI to namespace prefix format if possible
                        clean_key = attr_name
                        for ns_key, ns_uri in self.namespaces.items():
                            if attr_name.startswith(f"{{{ns_uri}}}"):
                                field_name = attr_name.replace(f"{{{ns_uri}}}", "")
                                # Check if this is XMLSchema-instance namespace by looking for 'xsi' key
                                if ns_key == "xsi":
                                    clean_key = field_name
                                else:
                                    clean_key = f"{ns_key}:{field_name}"
                                break
                        unread_keys[clean_key] = self.element.get(attr_name)
                        processed_attrs.add(attr_name)

            elif key.startswith("ns_attr:"):
                # Parse "ns_attr:namespace:field"
                parts = key.split(":", 2)
                if len(parts) == 3:
                    namespace_key, field = parts[1], parts[2]
                    if namespace_key in self.namespaces:
                        namespace_uri = self.namespaces[namespace_key]
                        full_attr_name = f"{{{namespace_uri}}}{field}"
                        full_attr_key = f"attr:{full_attr_name}"

                        # Only include if neither the ns_attr nor the full URI version has been read
                        # and we haven't processed this attribute yet
                        if (
                            key not in self.read_keys
                            and full_attr_key not in self.read_keys
                            and full_attr_name not in processed_attrs
                        ):
                            clean_key = (
                                f"{namespace_key}:{field}"  # Use namespace:field as key
                            )
                            unread_keys[clean_key] = self.element.get(
                                f"{{{namespace_uri}}}{field}"
                            )
                            processed_attrs.add(full_attr_name)

        # Mark these keys as read now that we've accessed them
        if unread_keys:
            # We need to mark the actual keys we found as read, not the clean keys
            keys_to_mark = {
                key
                for key in matching_keys - self.read_keys
                if key.startswith(("attr:", "ns_attr:"))
            }
            self.read_keys |= keys_to_mark

        return unread_keys

    def find_or_none(self, name: str) -> StrictXmlElement | None:
        self.read_keys.add(f"element:{name}")
        element = self.element.find(name, self.namespaces)
        return (
            StrictXmlElement(element, self.namespaces) if element is not None else None
        )

    def find(self, name: str) -> StrictXmlElement:
        try:
            return assert_not_none(
                self.find_or_none(name),
                msg=f"Unable to find '{name}' in xml file contents",
            )
        except Exception:
            self.errored = True
            raise

    def recursive_find_or_none(self, names: list[str]) -> StrictXmlElement | None:
        if len(names) == 0:
            return self
        name, *sub_names = names
        if element := self.find_or_none(name):
            return element.recursive_find_or_none(sub_names)
        return None

    def recursive_find(self, names: list[str]) -> StrictXmlElement:
        if len(names) == 0:
            return self
        name, *sub_names = names
        return self.find(name).recursive_find(sub_names)

    def findall(self, name: str) -> list[StrictXmlElement]:
        self.read_keys.add(f"element:{name}")
        return [
            StrictXmlElement(element, self.namespaces)
            for element in self.element.findall(name, self.namespaces)
        ]

    def get_attr_or_none(self, name: str) -> str | None:
        self.read_keys.add(f"attr:{name}")
        value = self.element.get(name)
        return None if value is None else str(value)

    def get_attr(self, name: str) -> str:
        try:
            return assert_not_none(
                self.get_attr_or_none(name),
                msg=f"Unable to find '{name}' in xml file contents",
            )
        except Exception:
            self.errored = True
            raise

    def parse_text_or_none(self) -> StrictXmlElement | None:
        if (text := self.get_text_or_none()) is None:
            return None
        try:
            return StrictXmlElement(fromstring(text), self.namespaces)
        except ElementTree.ParseError:
            return None

    def parse_text(self, name: str) -> StrictXmlElement:
        try:
            return assert_not_none(
                self.parse_text_or_none(),
                msg=f"Unable to parse text from xml tag '{name}' as valid xml content",
            )
        except Exception:
            self.errored = True
            raise

    def get_text_or_none(self) -> str | None:
        if self.element.text is not None:
            self.read_keys.add("text:")
        return self.element.text

    def get_text(self, name: str) -> str:
        try:
            return assert_not_none(
                self.get_text_or_none(),
                msg=f"Unable to find valid string from xml tag '{name}'",
            )
        except Exception:
            self.errored = True
            raise

    def get_float_or_none(self) -> float | None:
        return try_float_or_none(self.get_text_or_none())

    def get_float(self, name: str) -> float:
        try:
            return assert_not_none(self.get_float_or_none(), name)
        except Exception:
            self.errored = True
            raise

    def get_sub_float_or_none(self, name: str) -> float | None:
        if element := self.find_or_none(name):
            return element.get_float_or_none()
        return None

    def get_sub_text_or_none(self, name: str) -> str | None:
        if element := self.find_or_none(name):
            return element.get_text_or_none()
        return None

    # namespace-specific methods
    def get_namespaced_attr_or_none(self, namespace_key: str, field: str) -> str | None:
        self.read_keys.add(f"ns_attr:{namespace_key}:{field}")
        if namespace_key not in self.namespaces:
            return None
        return self.element.get(f"{{{self.namespaces.get(namespace_key)}}}{field}")

    def get_namespaced_attr(self, namespace_key: str, field: str) -> str:
        try:
            return assert_not_none(
                self.get_namespaced_attr_or_none(namespace_key, field),
                msg=f"Unable to find '{namespace_key}:{field}' in xml file contents",
            )
        except Exception:
            self.errored = True
            raise
