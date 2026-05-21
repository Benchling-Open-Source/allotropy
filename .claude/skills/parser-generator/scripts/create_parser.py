#!/usr/bin/env python3
# type: ignore
"""
Creates a new Allotropy parser with complete file structure.
Usage: python create_parser.py <parser_name> <display_name> [--schema SCHEMA_PATH] [--example EXAMPLE_FILE]
"""
from pathlib import Path
import sys


def create_parser_init(parser_name: str) -> str:
    """Generate __init__.py content."""
    class_name = (
        "".join(word.capitalize() for word in parser_name.split("_")) + "Parser"
    )
    return f'''"""Allotropy parser for {parser_name.replace('_', ' ').title()}."""

from allotropy.parsers.{parser_name}.{parser_name}_parser import {class_name}

__all__ = ["{class_name}"]
'''


def create_parser_file(
    parser_name: str, display_name: str, schema_path: str, extension: str
) -> str:
    """Generate parser.py content."""
    class_name = (
        "".join(word.capitalize() for word in parser_name.split("_")) + "Parser"
    )

    # Extract schema details from path
    # Expected format: adm/technique/ORG/YEAR/MONTH/technique
    path_parts = schema_path.split("/")
    path_parts[1] if len(path_parts) > 1 else "plate_reader"

    return f'''"""Parser for {display_name}."""

from allotropy.allotrope.models.{schema_path.replace('/', '.')} import Model
from allotropy.allotrope.schema_mappers.{schema_path.replace('/', '.')} import (
    Data,
    Mapper,
)
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.release_state import ReleaseState
from allotropy.parsers.vendor_parser import VendorParser

from allotropy.parsers.{parser_name}.{parser_name}_reader import {class_name}Reader
from allotropy.parsers.{parser_name}.{parser_name}_structure import (
    create_metadata,
    create_measurement_groups,
)


class {class_name}(VendorParser[Data, Model]):
    """Parser for {display_name} files."""

    DISPLAY_NAME = "{display_name}"
    RELEASE_STATE = ReleaseState.WORKING_DRAFT
    SUPPORTED_EXTENSIONS = "{extension}"
    SCHEMA_MAPPER = Mapper

    def create_data(self, named_file_contents: NamedFileContents) -> Data:
        """Create Data object from input file."""
        reader = {class_name}Reader(named_file_contents)

        return Data(
            create_metadata(reader.header, named_file_contents.original_file_path),
            create_measurement_groups(reader.measurements),
        )
'''


def create_reader_file(parser_name: str, extension: str) -> str:
    """Generate reader.py content."""
    class_name = (
        "".join(word.capitalize() for word in parser_name.split("_")) + "Reader"
    )

    if extension == "xlsx":
        reader_content = '''"""Reader for {display_name} Excel files."""

from typing import Any, Dict, List
import pandas as pd

from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.utils.pandas import read_excel


class {class_name}:
    """Reads and parses {display_name} Excel files."""

    def __init__(self, named_file_contents: NamedFileContents) -> None:
        """Initialize reader with file contents."""
        # Read the Excel file
        df = read_excel(
            named_file_contents.contents,
            header=None,
            sheet_name=0,  # Or specify sheet name
        )

        # Parse header section
        self.header = self._parse_header(df)

        # Parse measurements section
        self.measurements = self._parse_measurements(df)

    def _parse_header(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Parse header/metadata section."""
        header = {{}}

        # TODO: Extract metadata from appropriate rows
        # Example:
        # header["instrument_model"] = df.iloc[0, 1]
        # header["run_date"] = df.iloc[1, 1]

        return header

    def _parse_measurements(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Parse measurement data."""
        measurements = []

        # TODO: Find data section and parse
        # Example:
        # data_start_row = 10  # Adjust based on file format
        # data = df.iloc[data_start_row:].reset_index(drop=True)
        # data.columns = df.iloc[data_start_row - 1]  # Use row above as headers

        return measurements
'''
    else:
        reader_content = '''"""Reader for {display_name} text files."""

from typing import Any, Dict, List

from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.lines_reader import LinesReader


class {class_name}:
    """Reads and parses {display_name} text files."""

    def __init__(self, named_file_contents: NamedFileContents) -> None:
        """Initialize reader with file contents."""
        reader = LinesReader(named_file_contents.contents)

        # Parse header section
        self.header = self._parse_header(reader)

        # Parse measurements section
        self.measurements = self._parse_measurements(reader)

    def _parse_header(self, reader: LinesReader) -> Dict[str, Any]:
        """Parse header/metadata section."""
        header = {{}}

        # TODO: Extract metadata from lines
        # Example:
        # for line in reader.pop_until_empty():
        #     if ":" in line:
        #         key, value = line.split(":", 1)
        #         header[key.strip()] = value.strip()

        return header

    def _parse_measurements(self, reader: LinesReader) -> List[Dict[str, Any]]:
        """Parse measurement data."""
        measurements = []

        # TODO: Parse data section
        # Example:
        # headers = reader.pop().split("\\t")
        # for line in reader.lines:
        #     values = line.split("\\t")
        #     measurement = dict(zip(headers, values))
        #     measurements.append(measurement)

        return measurements
'''

    return reader_content.format(
        display_name=parser_name.replace("_", " ").title(), class_name=class_name
    )


def create_structure_file(parser_name: str) -> str:
    """Generate structure.py content."""
    return f'''"""Data structures for {parser_name.replace('_', ' ').title()} parser."""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from allotropy.allotrope.schema_mappers.adm.plate_reader.rec._2024._06.plate_reader import (
    Measurement,
    MeasurementGroup,
    MeasurementType,
    Metadata,
)
from allotropy.parsers.constants import NOT_APPLICABLE
from allotropy.parsers.utils.pandas import SeriesData
from allotropy.parsers.utils.uuids import random_uuid_str


def create_metadata(header: Dict[str, Any], file_path: Optional[Path]) -> Metadata:
    """Create Metadata object from header data."""
    return Metadata(
        device_identifier=header.get("instrument_id", NOT_APPLICABLE),
        model_number=header.get("model", NOT_APPLICABLE),
        software_name=header.get("software", NOT_APPLICABLE),
        unc_path=str(file_path) if file_path else NOT_APPLICABLE,
        data_system_instance_id=NOT_APPLICABLE,
    )


def create_measurement_groups(
    measurements_data: List[Dict[str, Any]]
) -> List[MeasurementGroup]:
    """Create MeasurementGroup objects from measurement data."""
    measurements = []

    for data in measurements_data:
        measurement = Measurement(
            identifier=random_uuid_str(),
            type_=MeasurementType.UNKNOWN,  # TODO: Set appropriate type
            sample_identifier=data.get("sample_id", NOT_APPLICABLE),
            # TODO: Add more measurement fields
        )
        measurements.append(measurement)

    # Group measurements as needed
    return [
        MeasurementGroup(
            measurements=measurements,
        )
    ]
'''


def create_test_file(parser_name: str) -> str:
    """Generate test file content."""
    return f'''"""Tests for {parser_name.replace('_', ' ').title()} parser."""

from allotropy.testing.utils import run_allotropy


def test_to_allotrope_{parser_name}() -> None:
    """Test parsing of example {parser_name.replace('_', ' ')} file."""
    test_file = "tests/parsers/{parser_name}/testdata/example.xlsx"
    expected_file = "tests/parsers/{parser_name}/testdata/example.json"
    run_allotropy(test_file, expected_file)
'''


def main():
    """Main function to create parser structure."""
    if len(sys.argv) < 3:
        print(
            "Usage: python create_parser.py <parser_name> <display_name> [--schema SCHEMA_PATH] [--example EXAMPLE_FILE]"
        )
        print("\nExample:")
        print(
            '  python create_parser.py beckman_pharmspec "Beckman Coulter PharmSpec" --schema adm/plate_reader/BENCHLING/2024/06/plate_reader'
        )
        sys.exit(1)

    parser_name = sys.argv[1].lower().replace(" ", "_").replace("-", "_")
    display_name = sys.argv[2]

    # Parse optional arguments
    schema_path = "adm/plate_reader/BENCHLING/2024/06/plate_reader"  # Default
    example_file = None
    extension = "xlsx"  # Default

    i = 3
    while i < len(sys.argv):
        if sys.argv[i] == "--schema" and i + 1 < len(sys.argv):
            schema_path = sys.argv[i + 1]
            i += 2
        elif sys.argv[i] == "--example" and i + 1 < len(sys.argv):
            example_file = Path(sys.argv[i + 1])
            extension = example_file.suffix[1:] if example_file.suffix else "xlsx"
            i += 2
        else:
            i += 1

    # Find repository root
    current = Path.cwd()
    repo_root = None
    for parent in [current, *list(current.parents)]:
        if (parent / "src" / "allotropy").exists():
            repo_root = parent
            break

    if not repo_root:
        print("Error: Must run from within allotropy repository")
        sys.exit(1)

    # Create parser directory structure
    parser_dir = repo_root / "src" / "allotropy" / "parsers" / parser_name
    test_dir = repo_root / "tests" / "parsers" / parser_name
    testdata_dir = test_dir / "testdata"

    # Check if parser already exists
    if parser_dir.exists():
        print(f"Error: Parser '{parser_name}' already exists at {parser_dir}")
        sys.exit(1)

    # Create directories
    parser_dir.mkdir(parents=True)
    test_dir.mkdir(parents=True)
    testdata_dir.mkdir(parents=True)

    # Create parser files
    files_created = []

    # __init__.py
    init_file = parser_dir / "__init__.py"
    init_file.write_text(create_parser_init(parser_name))
    files_created.append(init_file)

    # parser.py
    parser_file = parser_dir / f"{parser_name}_parser.py"
    parser_file.write_text(
        create_parser_file(parser_name, display_name, schema_path, extension)
    )
    files_created.append(parser_file)

    # reader.py
    reader_file = parser_dir / f"{parser_name}_reader.py"
    reader_file.write_text(create_reader_file(parser_name, extension))
    files_created.append(reader_file)

    # structure.py
    structure_file = parser_dir / f"{parser_name}_structure.py"
    structure_file.write_text(create_structure_file(parser_name))
    files_created.append(structure_file)

    # Test file
    test_file = test_dir / f"test_{parser_name}_parser.py"
    test_file.write_text(create_test_file(parser_name))
    files_created.append(test_file)

    # Test __init__.py
    test_init = test_dir / "__init__.py"
    test_init.write_text("")
    files_created.append(test_init)

    # Copy example file if provided
    if example_file and example_file.exists():
        import shutil

        dest_file = testdata_dir / f"example.{extension}"
        shutil.copy(example_file, dest_file)
        files_created.append(dest_file)

    # Print summary
    print(f"\n✅ Successfully created parser: {parser_name}")
    print(f"   Display name: {display_name}")
    print(f"   Schema: {schema_path}")
    print(f"   Extension: {extension}")

    print("\n📁 Files created:")
    for file in files_created:
        print(f"   - {file.relative_to(repo_root)}")

    print("\n📝 Next steps:")
    print(f"1. Edit {parser_name}_reader.py to implement file parsing")
    print(f"2. Edit {parser_name}_structure.py to map data to schema")
    print(f"3. Add test data to {testdata_dir}")
    print(f"4. Run tests: hatch run test:pytest tests/parsers/{parser_name}/")
    print("5. Register parser in src/allotropy/parser_factory.py")
    print("6. Update README.md with parser information")


if __name__ == "__main__":
    main()
