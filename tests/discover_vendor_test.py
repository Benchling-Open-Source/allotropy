from pathlib import Path

import pytest

from allotropy.parser_factory import Vendor
from allotropy.to_allotrope import vendor_from_file

TESTS_DIR = Path(__file__).parent / "parsers"

DIR_TO_VENDOR: dict[str, Vendor] = {
    "biorad_bioplex_manager": Vendor.BIORAD_BIOPLEX,
    "unchained_labs_lunatic_stunner": Vendor.UNCHAINED_LABS_LUNATIC,
}

INDISTINGUISHABLE: dict[Vendor, set[Vendor]] = {
    Vendor.AGILENT_GEN5: {Vendor.AGILENT_GEN5, Vendor.AGILENT_GEN5_IMAGE},
    Vendor.AGILENT_GEN5_IMAGE: {Vendor.AGILENT_GEN5, Vendor.AGILENT_GEN5_IMAGE},
    Vendor.APPBIO_QUANTSTUDIO: {
        Vendor.APPBIO_QUANTSTUDIO,
        Vendor.APPBIO_QUANTSTUDIO_DESIGNANDANALYSIS,
    },
    Vendor.APPBIO_QUANTSTUDIO_DESIGNANDANALYSIS: {
        Vendor.APPBIO_QUANTSTUDIO,
        Vendor.APPBIO_QUANTSTUDIO_DESIGNANDANALYSIS,
    },
    Vendor.LUMINEX_XPONENT: {Vendor.LUMINEX_XPONENT, Vendor.LUMINEX_INTELLIFLEX},
    Vendor.LUMINEX_INTELLIFLEX: {Vendor.LUMINEX_XPONENT, Vendor.LUMINEX_INTELLIFLEX},
    Vendor.THERMO_FISHER_VISIONLITE: {
        Vendor.THERMO_FISHER_VISIONLITE,
        Vendor.THERMO_FISHER_GENESYS_ON_BOARD,
    },
    Vendor.THERMO_FISHER_GENESYS_ON_BOARD: {
        Vendor.THERMO_FISHER_VISIONLITE,
        Vendor.THERMO_FISHER_GENESYS_ON_BOARD,
    },
    Vendor.BECKMAN_ECHO_CHERRY_PICK: {
        Vendor.BECKMAN_ECHO_CHERRY_PICK,
        Vendor.BECKMAN_ECHO_PLATE_REFORMAT,
    },
    Vendor.BECKMAN_ECHO_PLATE_REFORMAT: {
        Vendor.BECKMAN_ECHO_CHERRY_PICK,
        Vendor.BECKMAN_ECHO_PLATE_REFORMAT,
    },
    Vendor.MSD_WORKBENCH: {
        Vendor.MSD_WORKBENCH,
        Vendor.METHODICAL_MIND,
    },
    Vendor.METHODICAL_MIND: {
        Vendor.MSD_WORKBENCH,
        Vendor.METHODICAL_MIND,
    },
}

EXCLUDE_KEYWORDS = {"error", "exclude", "invalid"}

SKIP_DIRS = {"utils", "example_weyland_yutani"}


def _expected_vendor(dir_name: str) -> Vendor:
    if dir_name in DIR_TO_VENDOR:
        return DIR_TO_VENDOR[dir_name]
    return Vendor[dir_name.upper()]


def _is_valid_testcase(path: Path) -> bool:
    if not path.is_file():
        return False
    if str(path.stem).startswith("."):
        return False
    if "__pycache__" in str(path):
        return False
    if path.suffix.lower() in (".pyc", ".py", ".json", ".parquet"):
        return False
    if path.parts[-2] == "input":
        return True
    return all(keyword not in str(path).lower() for keyword in EXCLUDE_KEYWORDS)


def _get_discovery_test_cases() -> list[tuple[str, Path, Vendor]]:
    cases = []
    for vendor_dir in sorted(TESTS_DIR.iterdir()):
        if not vendor_dir.is_dir() or vendor_dir.name in SKIP_DIRS:
            continue
        testdata_dir = vendor_dir / "testdata"
        if not testdata_dir.exists():
            continue
        expected = _expected_vendor(vendor_dir.name)
        for path in sorted(testdata_dir.rglob("*")):
            if _is_valid_testcase(path):
                test_id = f"{vendor_dir.name}/{path.relative_to(testdata_dir)}"
                cases.append((test_id, path, expected))
    return cases


@pytest.mark.parametrize(
    ("test_id", "test_file", "expected_vendor"),
    _get_discovery_test_cases(),
    ids=lambda x: x if isinstance(x, str) else "",
)
def test_discover_vendor(
    test_id: str, test_file: Path, expected_vendor: Vendor
) -> None:
    result = vendor_from_file(str(test_file))
    if expected_vendor in INDISTINGUISHABLE:
        assert (
            result in INDISTINGUISHABLE[expected_vendor]
        ), f"For {test_id}: expected one of {INDISTINGUISHABLE[expected_vendor]}, got {result}"
    else:
        assert (
            result == expected_vendor
        ), f"For {test_id}: expected {expected_vendor}, got {result}"
