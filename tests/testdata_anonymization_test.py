"""Guards against customer identifiers leaking into test data (see "Test Data" in CLAUDE.md).

Test data is usually derived from real customer exports. This catches the identifier
shapes that survive manual anonymization most often: corporate domains in UNC paths,
email addresses, and Office document properties that name the file's author or tenant.
"""

from collections.abc import Iterator
from pathlib import Path
import re
import zipfile

TESTS_DIR = Path(__file__).parent
MAX_SCANNED_FILE_SIZE = 10_000_000

UNC_HOST = re.compile(rb"\\{2,}([A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+)\\")
EMAIL = re.compile(
    rb"[A-Za-z0-9._%+-]+@([A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,})"
)
SENSITIVITY_LABEL = re.compile(rb'name="MSIP_Label_[^"]*"')
PLACEHOLDER_DOMAIN = re.compile(rb"(^|\.)example\.(com|net|org)$", re.IGNORECASE)


def _testdata_files() -> Iterator[Path]:
    for path in sorted(TESTS_DIR.rglob("*")):
        if path.is_file() and "testdata" in path.relative_to(TESTS_DIR).parts:
            yield path


def _raw_contents(path: Path) -> list[bytes]:
    if zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as archive:
            return [
                archive.read(name)
                for name in archive.namelist()
                if name.startswith("docProps/")
            ]
    if path.stat().st_size > MAX_SCANNED_FILE_SIZE:
        return []
    return [path.read_bytes()]


def _scannable_contents(path: Path) -> list[bytes]:
    # Dropping NUL bytes lets the same patterns match UTF-16 encoded content.
    return [content.replace(b"\x00", b"") for content in _raw_contents(path)]


def _find_identifiers(content: bytes) -> list[str]:
    found = [
        match.group(0).decode(errors="replace")
        for pattern in (UNC_HOST, EMAIL)
        for match in pattern.finditer(content)
        if not PLACEHOLDER_DOMAIN.search(match.group(1))
    ]
    found.extend(
        match.group(0).decode() for match in SENSITIVITY_LABEL.finditer(content)
    )
    return found


def test_testdata_contains_no_customer_identifiers() -> None:
    violations = {
        str(path.relative_to(TESTS_DIR)): sorted(set(identifiers))
        for path in _testdata_files()
        if (
            identifiers := [
                identifier
                for content in _scannable_contents(path)
                for identifier in _find_identifiers(content)
            ]
        )
    }

    assert not violations, (
        "Test data contains identifiers that look customer-specific. Replace them "
        "with placeholders such as example.net (see 'Test Data' in CLAUDE.md): "
        f"{violations}"
    )
