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


def get_input_files(vendor: str) -> list[Path]:
    """Get all input files for a vendor.

    Args:
        vendor: Vendor name (e.g., 'appbio_quantstudio')

    Returns:
        List of paths to input files (sorted by name)
    """
    vendor_dir = get_vendor_dir(vendor)

    # Get all files that are not .json (outputs are .json)
    input_files = [
        f
        for f in vendor_dir.iterdir()
        if f.is_file() and f.suffix != ".json" and not f.name.startswith(".")
    ]
    return sorted(input_files)


def get_output_files(vendor: str) -> list[Path]:
    """Get all output files (expected ASM JSON) for a vendor.

    Args:
        vendor: Vendor name (e.g., 'appbio_quantstudio')

    Returns:
        List of paths to output .json files (sorted by name)
    """
    vendor_dir = get_vendor_dir(vendor)

    # Outputs are always .json files
    output_files = [
        f
        for f in vendor_dir.iterdir()
        if f.is_file() and f.suffix == ".json" and not f.name.startswith(".")
    ]
    return sorted(output_files)


def get_test_files(vendor: str) -> dict[Path, Path]:
    """Get all input/output file pairs for a vendor.

    Matches input files to their corresponding output .json files by stem name.
    For example: 'example01.txt' -> 'example01.json'

    Args:
        vendor: Vendor name (e.g., 'appbio_quantstudio')

    Returns:
        Dictionary mapping input file paths to output file paths
    """
    input_files = get_input_files(vendor)
    output_files = get_output_files(vendor)

    # Create a map of stem -> output file
    output_map = {f.stem: f for f in output_files}

    # Match inputs to outputs by stem
    test_pairs: dict[Path, Path] = {}
    for input_file in input_files:
        output_file = output_map.get(input_file.stem)
        if output_file:
            test_pairs[input_file] = output_file

    return test_pairs


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
