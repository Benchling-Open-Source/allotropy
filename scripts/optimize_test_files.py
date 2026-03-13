#!/usr/bin/env python3
"""
Script to identify and create minimal versions of large test files
to reduce test execution time.
"""

import json
import os
from pathlib import Path
import shutil
from typing import List, Dict, Any

def get_file_size_mb(filepath: Path) -> float:
    """Get file size in MB."""
    return filepath.stat().st_size / (1024 * 1024)

def find_large_test_files(test_dir: Path, min_size_kb: int = 500) -> List[Path]:
    """Find all test files larger than min_size_kb."""
    large_files = []
    for filepath in test_dir.rglob("*"):
        if filepath.is_file() and filepath.stat().st_size > min_size_kb * 1024:
            # Skip already minimized files
            if "_minimal" not in filepath.name and "_optimized" not in filepath.name:
                large_files.append(filepath)
    return sorted(large_files, key=lambda x: x.stat().st_size, reverse=True)

def create_minimal_json(filepath: Path, max_items: int = 8) -> bool:
    """Create a minimal version of a JSON test file."""
    try:
        with open(filepath, 'r') as f:
            data = json.load(f)

        modified = False

        # Common patterns in allotropy JSON files
        patterns = [
            # Plate reader patterns
            ('plate reader aggregate document', 'plate reader document'),
            # qPCR patterns
            ('qpcr aggregate document', 'qpcr document'),
            ('qPCR raw data aggregate document', 'qPCR raw data document'),
            # Multi-analyte patterns
            ('multi analyte profiling aggregate document', 'multi analyte profiling document'),
            # ELISA patterns
            ('ELISA aggregate document', 'ELISA document'),
            # Imaging patterns
            ('imaging aggregate document', 'imaging document'),
        ]

        for outer_key, inner_key in patterns:
            if outer_key in data and inner_key in data[outer_key]:
                docs = data[outer_key][inner_key]
                if isinstance(docs, list) and len(docs) > max_items:
                    # Reduce to max_items documents
                    data[outer_key][inner_key] = docs[:max_items]
                    modified = True
                    print(f"  Reduced {inner_key} from {len(docs)} to {max_items}")

                # Also check for nested measurement documents
                for doc in data[outer_key][inner_key][:max_items]:
                    if isinstance(doc, dict) and 'measurement aggregate document' in doc:
                        measurements = doc['measurement aggregate document'].get('measurement document', [])
                        if len(measurements) > max_items:
                            doc['measurement aggregate document']['measurement document'] = measurements[:max_items]
                            modified = True
                            print(f"  Reduced measurements from {len(measurements)} to {max_items}")

                    # Check for analyte documents
                    if isinstance(doc, dict) and 'analyte aggregate document' in doc:
                        analytes = doc['analyte aggregate document'].get('analyte document', [])
                        if len(analytes) > max_items:
                            doc['analyte aggregate document']['analyte document'] = analytes[:max_items]
                            modified = True
                            print(f"  Reduced analytes from {len(analytes)} to {max_items}")

        if modified:
            # Save minimal version
            minimal_path = filepath.parent / f"{filepath.stem}_minimal{filepath.suffix}"
            with open(minimal_path, 'w') as f:
                json.dump(data, f, indent=2)
            return True

    except Exception as e:
        print(f"  Error processing JSON: {e}")

    return False

def create_minimal_txt(filepath: Path, max_wells: int = 8, max_cycles: int = 3) -> bool:
    """Create a minimal version of a TXT test file (for AppBio QuantStudio)."""
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()

        # Find section boundaries
        sections = {}
        current_section = None
        section_start = 0

        for i, line in enumerate(lines):
            if line.startswith('['):
                if current_section:
                    sections[current_section] = (section_start, i)
                current_section = line.strip()
                section_start = i

        if current_section:
            sections[current_section] = (section_start, len(lines))

        if not sections:
            return False

        # Create minimal version
        minimal_lines = []

        # Keep header (everything before first section)
        first_section_start = min(start for start, _ in sections.values())
        minimal_lines.extend(lines[:first_section_start])

        # Process each section
        for section_name, (start, end) in sections.items():
            minimal_lines.append(lines[start])  # Section header

            if section_name == '[Sample Setup]':
                # Keep header and first max_wells*2 lines (2 targets per well)
                if start + 1 < end:
                    minimal_lines.append(lines[start + 1])  # Column headers
                    well_lines = lines[start + 2:min(start + 2 + max_wells * 2, end)]
                    minimal_lines.extend(well_lines)

            elif section_name in ['[Raw Data]', '[Amplification Data]', '[Multicomponent Data]']:
                # Keep header and first max_cycles for first max_wells
                if start + 1 < end:
                    minimal_lines.append(lines[start + 1])  # Column headers
                    for line in lines[start + 2:end]:
                        parts = line.split('\t')
                        if len(parts) >= 2 and parts[0].isdigit() and parts[1].isdigit():
                            cycle = int(parts[0])
                            well = int(parts[1])
                            if cycle <= max_cycles and well <= max_wells:
                                minimal_lines.append(line)

            elif section_name == '[Results]':
                # Keep header and first max_wells lines
                if start + 1 < end:
                    minimal_lines.append(lines[start + 1])  # Column headers
                    result_lines = lines[start + 2:min(start + 2 + max_wells, end)]
                    minimal_lines.extend(result_lines)

            else:
                # For unknown sections, keep first few lines
                section_lines = lines[start + 1:min(start + 11, end)]
                minimal_lines.extend(section_lines)

        # Save minimal version
        minimal_path = filepath.parent / f"{filepath.stem}_minimal{filepath.suffix}"
        with open(minimal_path, 'w') as f:
            f.writelines(minimal_lines)

        return True

    except Exception as e:
        print(f"  Error processing TXT: {e}")

    return False

def main():
    """Main function to optimize test files."""
    # Find allotropy test directory
    test_dir = Path("/Users/nathan.stender/allotropy/tests")

    if not test_dir.exists():
        print(f"Test directory not found: {test_dir}")
        return

    print("Finding large test files...")
    large_files = find_large_test_files(test_dir, min_size_kb=500)

    print(f"\nFound {len(large_files)} large test files")
    print("\nCreating minimal versions...")

    success_count = 0
    for filepath in large_files[:20]:  # Process top 20 largest files
        size_mb = get_file_size_mb(filepath)
        print(f"\n{filepath.name} ({size_mb:.1f} MB)")

        if filepath.suffix == '.json':
            if create_minimal_json(filepath):
                success_count += 1
                print(f"  ✓ Created minimal JSON")
        elif filepath.suffix == '.txt':
            if create_minimal_txt(filepath):
                success_count += 1
                print(f"  ✓ Created minimal TXT")
        else:
            print(f"  ⚠ Unsupported file type: {filepath.suffix}")

    print(f"\n✅ Successfully created {success_count} minimal test files")
    print("\nNext steps:")
    print("1. Update test files to use minimal versions where appropriate")
    print("2. Verify all tests still pass with minimal files")
    print("3. Remove or archive original large files if no longer needed")

if __name__ == "__main__":
    main()