"""Quantity value lifecycle manager.

Tracks TQuantityValue{Unit} thin subclasses — maps unit strings to class
names, records new classes for generate.py to append to the shared module.
"""

from __future__ import annotations

# Base type names for quantity value variants (case-sensitive prefixes).
QV_BASE_NAMES = ("tQuantityValue", "tNullableQuantityValue")


def is_quantity_value_variant(def_name: str) -> bool:
    """Return True if *def_name* is a pre-composed QV variant (not the base type)."""
    return any(def_name.startswith(base) and def_name != base for base in QV_BASE_NAMES)


class QuantityValueManager:
    """Tracks and manages TQuantityValue{Unit} thin subclasses.

    Centralizes the logic for resolving quantity value types, checking
    whether they already exist in the shared module, and recording new
    ones that need to be appended.

    Tracking uses a single authoritative map from unit_string to class name.
    A derived ``_known_names`` set provides fast name-based lookup.
    """

    def __init__(
        self,
        unit_descriptive_names: dict[str, str] | None = None,
    ) -> None:
        # unit_string → class name.  Single source of truth.
        self._unit_to_class: dict[str, str] = {}
        # unit const → descriptive name from shared units (e.g., "degC" → "DegreeCelsius").
        self._descriptive: dict[str, str] = dict(unit_descriptive_names or {})
        # Derived: set of all known class names (for fast membership checks).
        self._known_names: set[str] = set()
        self.new_classes: list[tuple[str, str]] = []

    @property
    def known_class_names(self) -> set[str]:
        """All known TQuantityValue class names (existing + newly created)."""
        return self._known_names

    @property
    def all_classes(self) -> dict[str, str]:
        """Complete mapping of unit_string → class_name."""
        return dict(self._unit_to_class)

    def get_or_create(self, unit_const: str) -> str:
        """Return the class name for *unit_const*, recording it as new if needed."""
        existing = self._unit_to_class.get(unit_const)
        if existing is not None:
            return existing
        class_name = self._build_class_name(unit_const)
        if class_name not in self._known_names:
            self._unit_to_class[unit_const] = class_name
            self._known_names.add(class_name)
            self.new_classes.append((class_name, unit_const))
        return class_name

    def _build_class_name(self, unit_const: str) -> str:
        """Build a TQuantityValue class name using descriptive unit names."""
        descriptive = self._descriptive.get(unit_const)
        if not descriptive:
            msg = (
                f"No descriptive name for unit {unit_const!r}. "
                "Add it to _MANUAL_UNITS in generate.py or ensure it appears "
                "in a cached schema's $asm.unit-iri."
            )
            raise ValueError(msg)
        return "TQuantityValue" + descriptive
