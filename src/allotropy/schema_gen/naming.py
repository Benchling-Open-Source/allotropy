"""Name transformation utilities for schema-to-model generation.

Handles mapping between:
- Allotrope schema URLs and local file paths
- JSON Schema property names and Python identifiers
- Schema definition names and Python class names
"""

from __future__ import annotations

from pathlib import Path
import re
from urllib.parse import unquote

# Base URL prefix for all Allotrope JSON schemas
ALLOTROPE_URL_PREFIX = "http://purl.allotrope.org/json-schemas/"

# GitLab raw content base URL
GITLAB_RAW_BASE = "https://gitlab.com/allotrope-public/asm/-/raw/main/json-schemas/"

# Substring that identifies a units schema URL (as opposed to core/hierarchy/technique)
UNITS_SCHEMA_MARKER = "units.schema"

# Default output directories (relative to project root)
DEFAULT_SCHEMA_CACHE_DIR = Path("src/allotropy/allotrope/schemas")
DEFAULT_MODEL_OUTPUT_DIR = Path("src/allotropy/allotrope/models")

# Pre-compiled regex patterns
_RE_GITLAB_URL = re.compile(r"https?://gitlab\.com/.+?/json-schemas/(.+?)(?:\.json)?$")
_RE_DEFS_FRAGMENT = re.compile(r"/?\$defs/(.+)$")
_RE_SCHEMA_SUFFIX = re.compile(r"\.schema(\.json)?$")
_RE_SEPARATOR = re.compile(r"[\s.\-/~^]+")
_RE_NON_IDENTIFIER = re.compile(r"[^a-zA-Z0-9_]")
_RE_CAMEL_BOUNDARY = re.compile(r"([a-z0-9])([A-Z])")
_RE_WORD_SPLIT = re.compile(r"[\s\-_]+")
_RE_NON_ALNUM = re.compile(r"[^a-zA-Z0-9]")


def allotrope_url_to_relative_path(url: str) -> str:
    """Extract the relative path from an Allotrope schema URL.

    Example:
        "http://purl.allotrope.org/json-schemas/adm/core/REC/2024/06/core.schema"
        → "adm/core/REC/2024/06/core.schema"
    """
    if url.startswith(ALLOTROPE_URL_PREFIX):
        return url[len(ALLOTROPE_URL_PREFIX) :]
    msg = f"Not an Allotrope URL: {url}"
    raise ValueError(msg)


def allotrope_url_to_gitlab_raw(url: str) -> str:
    """Convert an Allotrope schema URL to a GitLab raw download URL.

    Example:
        "http://purl.allotrope.org/json-schemas/adm/core/REC/2024/06/core.schema"
        → "https://gitlab.com/allotrope-public/asm/-/raw/main/json-schemas/adm/core/REC/2024/06/core.schema.json"
    """
    rel_path = allotrope_url_to_relative_path(url)
    # Remote files have .json extension, but the URLs omit it
    if not rel_path.endswith(".json"):
        rel_path += ".json"
    return GITLAB_RAW_BASE + rel_path


def gitlab_blob_to_raw(url: str) -> str:
    """Convert a GitLab blob URL to a raw download URL.

    Example:
        "https://gitlab.com/allotrope-public/asm/-/blob/main/json-schemas/adm/..."
        → "https://gitlab.com/allotrope-public/asm/-/raw/main/json-schemas/adm/..."
    """
    return url.replace("/-/blob/", "/-/raw/")


def normalize_schema_url(url: str) -> str:
    """Normalize any schema URL to an Allotrope canonical URL (without fragment).

    Handles:
    - Allotrope URLs (already canonical)
    - GitLab blob/raw URLs (extract relative path)
    - URLs with fragments (strip #/$defs/...)
    """
    # Strip fragment
    url = url.split("#")[0]

    # Strip query string
    url = url.split("?")[0]

    if url.startswith(ALLOTROPE_URL_PREFIX):
        # Already canonical, strip .json if present
        return url.removesuffix(".json")

    if "json-schemas/" in url:
        # Only accept URLs hosted on gitlab.com (not substrings like evil.com/gitlab.com)
        match = _RE_GITLAB_URL.match(url)
        if match:
            return ALLOTROPE_URL_PREFIX + match.group(1)

    msg = f"Cannot normalize URL: {url}"
    raise ValueError(msg)


def _decode_json_pointer(pointer: str) -> str:
    """Decode JSON Pointer escapes (RFC 6901).

    ~1 → /
    ~0 → ~

    Order matters: ~1 must be decoded before ~0, otherwise "~01" would
    incorrectly become "~1" (via ~0→~) then "/" (via ~1→/) instead of "~1".
    """
    return pointer.replace("~1", "/").replace("~0", "~")


def parse_ref(ref: str) -> tuple[str | None, str | None]:
    """Parse a $ref string into (schema_url, definition_path).

    Returns:
        (schema_url, def_path) where either may be None.
        The def_path is decoded from JSON Pointer encoding.

    Examples:
        "#/$defs/tStringValue" → (None, "tStringValue")
        "http://.../core.schema#/$defs/tStringValue" → ("http://.../core.schema", "tStringValue")
        "http://.../units.schema#/$defs/pg~1mL" → ("http://.../units.schema", "pg/mL")
        "http://.../manifest.schema" → ("http://.../manifest.schema", None)
    """
    if "#" in ref:
        schema_part, fragment = ref.split("#", 1)
        # URL-decode the fragment first (RFC 3986), then apply JSON Pointer decoding
        fragment = unquote(fragment)
        # Extract definition name from fragment like /$defs/tStringValue
        def_match = _RE_DEFS_FRAGMENT.match(fragment)
        def_name = _decode_json_pointer(def_match.group(1)) if def_match else None
        schema_url = normalize_schema_url(schema_part) if schema_part else None
        return schema_url, def_name
    # No fragment - reference to a whole schema
    return normalize_schema_url(ref), None


def schema_url_to_cache_path(
    url: str, cache_dir: Path = DEFAULT_SCHEMA_CACHE_DIR
) -> Path:
    """Map a canonical schema URL to a local cache file path.

    Example:
        "http://.../adm/core/REC/2024/06/core.schema"
        → cache_dir / "adm/core/REC/2024/06/core.schema.json"
    """
    rel_path = allotrope_url_to_relative_path(url)
    if not rel_path.endswith(".json"):
        rel_path += ".json"
    return Path(cache_dir, rel_path)


def schema_url_to_module_path(url: str) -> str:
    """Map a canonical schema URL to a Python module path (relative to models).

    Example:
        "http://.../adm/core/REC/2024/06/core.schema"
        → "adm.core.rec._2024._06.core"
    """
    rel_path = allotrope_url_to_relative_path(url)
    # Remove .schema suffix
    rel_path = _RE_SCHEMA_SUFFIX.sub("", rel_path)
    # Convert path separators to dots, make Python-safe
    parts = rel_path.split("/")
    python_parts = [_path_component_to_python(p) for p in parts]
    return ".".join(python_parts)


def schema_url_to_model_file(
    url: str, output_dir: Path = DEFAULT_MODEL_OUTPUT_DIR
) -> Path:
    """Map a canonical schema URL to the output Python file path.

    Example:
        "http://.../adm/core/REC/2024/06/core.schema"
        → output_dir / "adm/core/rec/_2024/_06/core.py"
    """
    rel_path = allotrope_url_to_relative_path(url)
    # Remove .schema suffix
    rel_path = _RE_SCHEMA_SUFFIX.sub("", rel_path)
    parts = rel_path.split("/")
    python_parts = [_path_component_to_python(p) for p in parts]
    file_path = Path(output_dir, *python_parts[:-1], python_parts[-1] + ".py")
    return file_path


def _path_component_to_python(component: str) -> str:
    """Convert a path component to a valid Python identifier.

    - Lowercase
    - Replace hyphens with underscores
    - Prefix digits with underscore
    """
    result = component.lower().replace("-", "_")
    if result and result[0].isdigit():
        result = "_" + result
    return result


def property_name_to_python(name: str) -> str:
    """Convert a JSON property name to a Python attribute name (snake_case).

    Examples:
        "device system document" → "device_system_document"
        "$asm.manifest" → "field_asm_manifest"
        "@index" → "field_index"
        "@type" → "field_type"
        "minInclusive" → "min_inclusive"
        "fieldComponentDatatype" → "field_component_datatype"
    """
    # $- and @-prefixed properties get "field_" prefix (datamodel-codegen convention)
    special_prefix = name.startswith("@") or name.startswith("$")

    # Strip leading $ or @
    name = name.lstrip("$@")

    if special_prefix:
        name = "field_" + name

    # Replace dots, spaces, hyphens with underscores (collapse consecutive)
    result = _RE_SEPARATOR.sub("_", name)
    # Replace parentheses with individual underscores (not collapsed with whitespace)
    result = result.replace("(", "_").replace(")", "_")
    # Remove any remaining non-alphanumeric chars (except underscore)
    result = _RE_NON_IDENTIFIER.sub("", result)
    # Insert underscores at camelCase boundaries (e.g. minInclusive → min_Inclusive)
    result = _RE_CAMEL_BOUNDARY.sub(r"\1_\2", result)
    # Ensure snake_case
    result = result.lower()
    # Don't start with a digit
    if result and result[0].isdigit():
        result = "_" + result
    return result


def def_name_to_class_name(name: str) -> str:
    """Convert a JSON Schema $defs name to a Python class name.

    Preserves existing CamelCase (e.g., tStringValue → TStringValue).
    Converts space/hyphen separated to PascalCase.

    Examples:
        "tStringValue" → "TStringValue"
        "measurementDocumentItems" → "MeasurementDocumentItems"
        "device system document" → "DeviceSystemDocument"
        "cFillValueBoolean" → "CFillValueBoolean"
    """
    # If it's already camelCase/PascalCase (no spaces/hyphens), just capitalize first letter
    if " " not in name and "-" not in name:
        return name[0].upper() + name[1:] if name else name

    # Otherwise convert from space/hyphen separated
    words = _RE_WORD_SPLIT.split(name)
    return "".join(w[0].upper() + w[1:] for w in words if w)


def property_name_to_class_name(name: str) -> str:
    """Convert a JSON property name to a Python class name (PascalCase).

    Examples:
        "device system document" → "DeviceSystemDocument"
        "measurement document" → "MeasurementDocument"
        "scan position setting (plate reader)" → "ScanPositionSettingPlateReader"
        "@componentDatatype" → "ComponentDatatype"
    """
    # Strip @ and $ prefixes (schema metadata markers)
    name = name.lstrip("@$")
    # Strip parentheses before splitting (they appear in names like
    # "scan position setting (plate reader)")
    name = name.replace("(", " ").replace(")", " ")
    words = _RE_WORD_SPLIT.split(name)
    result = "".join(w[0].upper() + w[1:] for w in words if w)
    # If stripping @ left a camelCase name, ensure first letter is uppercase
    return result[0].upper() + result[1:] if result else result


def unit_symbol_to_class_name(symbol: str) -> str:
    """Convert a QUDT unit symbol to a Python class name.

    Handles special characters in QUDT unit symbols:
        "mAU" → "MAU"
        "nm" → "Nm"
        "pg/mL" → "PgPerML"
        "(unitless)" → "Unitless"
        "#" → "NumberSign"
        '"' → "InchQuote"
        "2θ" → "TwoTheta"
    """
    # Handle common special symbols first
    special_map = {
        '"': "InchQuote",
        "#": "NumberSign",
        "'": "ArcMinuteQuote",
    }
    if symbol in special_map:
        return special_map[symbol]

    cleaned = symbol
    # Replace known multi-char patterns
    cleaned = cleaned.replace("~1", "/")
    cleaned = cleaned.replace("^2", "Sq")
    cleaned = cleaned.replace("^3", "Cu")
    cleaned = cleaned.replace("^", "")
    cleaned = cleaned.replace("(", "").replace(")", "")
    cleaned = cleaned.replace("/", "Per")
    cleaned = cleaned.replace("·", "Dot")
    cleaned = cleaned.replace("°", "Deg")
    cleaned = cleaned.replace("θ", "Theta")
    # Both Unicode codepoints for micro: U+03BC GREEK SMALL LETTER MU (μ)
    # and U+00B5 MICRO SIGN (µ). Schema data uses both interchangeably.
    cleaned = cleaned.replace("μ", "Micro")
    cleaned = cleaned.replace("µ", "Micro")
    cleaned = cleaned.replace("\u2212", "")  # MINUS SIGN (U+2212)
    cleaned = cleaned.replace(".", "Dot")
    cleaned = cleaned.replace(" ", "")
    cleaned = cleaned.replace("%", "Percent")
    cleaned = cleaned.replace("'", "")
    cleaned = cleaned.replace("#", "Num")
    # Remove any remaining non-alphanumeric chars
    cleaned = _RE_NON_ALNUM.sub("", cleaned)
    # Ensure starts with a letter
    if cleaned and cleaned[0].isdigit():
        digit_names = {
            "0": "Zero",
            "1": "One",
            "2": "Two",
            "3": "Three",
            "4": "Four",
            "5": "Five",
            "6": "Six",
            "7": "Seven",
            "8": "Eight",
            "9": "Nine",
        }
        cleaned = digit_names.get(cleaned[0], "N") + cleaned[1:]
    # Capitalize first letter
    if cleaned and cleaned[0].islower():
        cleaned = cleaned[0].upper() + cleaned[1:]
    if not cleaned:
        cleaned = "Unknown"
    return cleaned


def default_json_name(python_name: str) -> str:
    """Derive the default JSON property name from a Python field name.

    The convention is that underscores map to spaces.  When the actual
    JSON name differs from this default (e.g. hyphens, camelCase, ``$``
    or ``@`` prefixes), the codegen emits explicit ``json_name`` metadata.
    The converter (structure/unstructure) uses the same fallback so the two stay in sync.
    """
    return python_name.replace("_", " ")
