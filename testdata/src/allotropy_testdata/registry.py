"""File registry and lookup for allotropy test data."""

from pathlib import Path

# Get the data directory - check both installed package location and local repo location
_PACKAGE_DIR = Path(__file__).parent
_INSTALLED_DATA_DIR = _PACKAGE_DIR / "data" / "parsers"
_LOCAL_DATA_DIR = _PACKAGE_DIR.parent.parent.parent / "tests" / "parsers"

# Use installed location if it exists, otherwise fall back to local repo
if _INSTALLED_DATA_DIR.exists():
    _DATA_DIR = _INSTALLED_DATA_DIR
elif _LOCAL_DATA_DIR.exists():
    _DATA_DIR = _LOCAL_DATA_DIR
else:
    msg = f"Could not find test data at {_INSTALLED_DATA_DIR} or {_LOCAL_DATA_DIR}"
    raise RuntimeError(msg)


def get_data_dir() -> Path:
    """Get the root data directory containing all vendor test files.

    Returns:
        Path to the parsers directory containing vendor subdirectories
    """
    return _DATA_DIR


def list_vendors() -> list[str]:
    """List all available vendor names that have test data.

    Returns:
        Sorted list of vendor names (e.g., ['appbio_quantstudio', 'agilent_gen5', ...])
    """
    if not _DATA_DIR.exists():
        return []

    vendors = [
        d.name
        for d in _DATA_DIR.iterdir()
        if d.is_dir() and (d / "testdata").exists() and not d.name.startswith("_")
    ]
    return sorted(vendors)


def get_vendor_dir(vendor: str) -> Path:
    """Get the testdata directory for a vendor.

    Args:
        vendor: Vendor name (e.g., 'appbio_quantstudio')

    Returns:
        Path to the vendor's testdata directory

    Raises:
        ValueError: If vendor not found
    """
    vendor_dir = _DATA_DIR / vendor / "testdata"
    if not vendor_dir.exists():
        available = ", ".join(list_vendors())
        msg = f"Vendor '{vendor}' not found. Available vendors: {available}"
        raise ValueError(msg)
    return vendor_dir


_EXCLUDED_KEYWORDS = ("error", "exclude", "invalid")
_FOLDER_INPUT_SUFFIXES = (".rslt",)
_JSON_INPUT_DIR = "input"
_JSON_OUTPUT_DIR = "output"


def _is_input_file(vendor_dir: Path, path: Path) -> bool:
    relative = path.relative_to(vendor_dir)
    if any(part.startswith(".") or part == "__pycache__" for part in relative.parts):
        return False
    if any(keyword in relative.as_posix().lower() for keyword in _EXCLUDED_KEYWORDS):
        return False
    if path.is_dir():
        return path.suffix in _FOLDER_INPUT_SUFFIXES
    if any(parent.suffix in _FOLDER_INPUT_SUFFIXES for parent in relative.parents):
        return False
    # Parsers with JSON input keep inputs in an input/ folder, so .json is only an
    # output elsewhere.
    if relative.parent.name == _JSON_INPUT_DIR:
        return True
    return path.suffix.lower() not in (".json", ".parquet", ".py", ".pyc")


def _expected_output_path(path: Path) -> Path:
    if path.parent.name == _JSON_INPUT_DIR:
        return (path.parent.parent / _JSON_OUTPUT_DIR / path.name).with_suffix(".json")
    return path.with_suffix(".json")


def get_input_files(vendor: str) -> list[Path]:
    """Get all positive-case input files for a vendor.

    Mirrors allotropy's own parser tests: files are found recursively, JSON files
    are inputs only when they live in an ``input/`` folder, ``.rslt`` folders are
    inputs as a whole, and paths containing "error", "exclude" or "invalid" are
    negative-case files that are not returned (use ``get_file`` to access them).

    Args:
        vendor: Vendor name (e.g., 'appbio_quantstudio')

    Returns:
        List of paths to input files (sorted)
    """
    vendor_dir = get_vendor_dir(vendor)
    return sorted(
        path for path in vendor_dir.rglob("*") if _is_input_file(vendor_dir, path)
    )


def get_output_files(vendor: str) -> list[Path]:
    """Get the expected ASM JSON output for each input file of a vendor.

    Args:
        vendor: Vendor name (e.g., 'appbio_quantstudio')

    Returns:
        List of paths to expected output .json files (sorted)
    """
    return sorted(get_test_files(vendor).values())


def get_test_files(vendor: str) -> dict[Path, Path]:
    """Get all input/output file pairs for a vendor.

    The expected output of ``<dir>/x.ext`` is ``<dir>/x.json``. For parsers with
    JSON input, ``<dir>/input/x.json`` is paired with ``<dir>/output/x.json``.
    Inputs without an existing expected output are omitted.

    Args:
        vendor: Vendor name (e.g., 'appbio_quantstudio')

    Returns:
        Dictionary mapping input file paths to output file paths
    """
    pairs: dict[Path, Path] = {}
    for input_file in get_input_files(vendor):
        output_file = _expected_output_path(input_file)
        if output_file.is_file():
            pairs[input_file] = output_file
    return pairs


def get_file(vendor: str, filename: str) -> Path:
    """Get a specific file by name for a vendor.

    Args:
        vendor: Vendor name (e.g., 'appbio_quantstudio')
        filename: File name (e.g., 'example01.txt' or 'example01.json')

    Returns:
        Path to the requested file

    Raises:
        ValueError: If vendor not found
        FileNotFoundError: If file not found in vendor testdata directory
    """
    vendor_dir = get_vendor_dir(vendor)
    file_path = vendor_dir / filename

    if not file_path.exists():
        msg = f"File '{filename}' not found in vendor '{vendor}' testdata directory"
        raise FileNotFoundError(msg)

    return file_path
