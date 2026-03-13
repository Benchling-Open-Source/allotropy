#!/usr/bin/env python3
"""
Script to optimize large test files by creating minimal versions.
This replaces the original files directly.
"""

from pathlib import Path
import shutil
import xml.etree.ElementTree as ET


def create_minimal_biorad_xml(filepath: Path) -> bool:
    """Create minimal version of Biorad Bioplex XML file."""
    try:
        # Parse the XML
        tree = ET.parse(filepath)
        root = tree.getroot()

        # Find all well elements and keep only first 8
        namespaces = {"ns": "http://www.bio-rad.com/schemas/SRBXExtended/v1.0"}
        wells = root.findall(".//ns:Well", namespaces)

        if len(wells) > 8:
            # Remove excess wells
            parent_map = {c: p for p in tree.iter() for c in p}
            for well in wells[8:]:
                parent = parent_map.get(well)
                if parent is not None:
                    parent.remove(well)

        # Save back to original location
        tree.write(filepath, encoding="utf-8", xml_declaration=True)
        print(f"  ✓ Optimized XML: {len(wells)} → 8 wells")
        return True
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False


def create_minimal_quantstudio_txt(
    filepath: Path, max_wells: int = 8, max_cycles: int = 3
) -> bool:
    """Create minimal version of AppBio QuantStudio TXT file."""
    try:
        with open(filepath, encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()

        # Find section boundaries
        sections = {}
        current_section = None
        section_start = 0

        for i, line in enumerate(lines):
            if line.startswith("["):
                if current_section:
                    sections[current_section] = (section_start, i)
                current_section = line.strip()
                section_start = i

        if current_section:
            sections[current_section] = (section_start, len(lines))

        # Create minimal version
        minimal_lines = []

        # Keep header (everything before first section)
        first_section_start = (
            min(start for start, _ in sections.values()) if sections else len(lines)
        )
        minimal_lines.extend(lines[:first_section_start])

        # Process each section
        for section_name, (start, end) in sections.items():
            minimal_lines.append(lines[start])  # Section header

            if section_name == "[Sample Setup]" and start + 1 < end:
                # Keep header and first max_wells*2 lines (2 targets per well)
                minimal_lines.append(lines[start + 1])  # Column headers
                well_count = 0
                for line in lines[start + 2 : end]:
                    if well_count < max_wells * 2:
                        minimal_lines.append(line)
                        well_count += 1

            elif section_name in [
                "[Raw Data]",
                "[Amplification Data]",
                "[Multicomponent Data]",
            ]:
                if start + 1 < end:
                    minimal_lines.append(lines[start + 1])  # Column headers
                    # Keep first few cycles for first few wells
                    data_count = 0
                    for line in lines[start + 2 : end]:
                        parts = line.split("\t")
                        if len(parts) >= 2:
                            try:
                                cycle = int(parts[0])
                                well = int(parts[1])
                                if cycle <= max_cycles and well <= max_wells:
                                    minimal_lines.append(line)
                                    data_count += 1
                            except (ValueError, IndexError):
                                pass

            elif section_name == "[Results]" and start + 1 < end:
                # Keep header and first max_wells results
                minimal_lines.append(lines[start + 1])  # Column headers
                result_count = 0
                for line in lines[start + 2 : end]:
                    if result_count < max_wells * 2:  # 2 targets per well
                        minimal_lines.append(line)
                        result_count += 1

        # Save back to original location
        with open(filepath, "w", encoding="utf-8") as f:
            f.writelines(minimal_lines)

        original_lines = len(lines)
        new_lines = len(minimal_lines)
        print(
            f"  ✓ Optimized TXT: {original_lines} → {new_lines} lines ({100*(1-new_lines/original_lines):.1f}% reduction)"
        )
        return True

    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False


def optimize_xlsx_file(filepath: Path) -> bool:
    """For XLSX files, we can't easily minimize them, so just report."""
    size_mb = filepath.stat().st_size / (1024 * 1024)
    print(f"  ⚠ XLSX file ({size_mb:.1f}MB) - requires manual optimization")
    return False


def main():
    """Main function to optimize test files."""

    # Files to optimize in this batch
    files_to_optimize = [
        (
            "tests/parsers/biorad_bioplex_manager/testdata/bio-rad_bio-plex_manager_example_01.xml",
            "xml",
        ),
        (
            "tests/parsers/appbio_quantstudio/testdata/appbio_quantstudio_example01.txt",
            "txt",
        ),
    ]

    print("=" * 60)
    print("OPTIMIZING TEST FILES - BATCH 1")
    print("=" * 60)
    print()

    success_count = 0

    for filepath, file_type in files_to_optimize:
        full_path = Path(filepath)
        if not full_path.exists():
            print(f"✗ File not found: {filepath}")
            continue

        size_mb = full_path.stat().st_size / (1024 * 1024)
        print(f"\n{full_path.name} ({size_mb:.1f}MB)")

        # Create backup
        backup_path = full_path.with_suffix(full_path.suffix + ".backup")
        shutil.copy2(full_path, backup_path)

        # Optimize based on file type
        if file_type == "xml" and "biorad" in filepath:
            if create_minimal_biorad_xml(full_path):
                success_count += 1
        elif file_type == "txt" and "quantstudio" in filepath:
            if create_minimal_quantstudio_txt(full_path):
                success_count += 1
        elif file_type == "xlsx":
            optimize_xlsx_file(full_path)

        # Check new size
        if full_path.exists():
            new_size_mb = full_path.stat().st_size / (1024 * 1024)
            if new_size_mb < size_mb:
                reduction = 100 * (1 - new_size_mb / size_mb)
                print(
                    f"  Size: {size_mb:.1f}MB → {new_size_mb:.1f}MB ({reduction:.1f}% reduction)"
                )

    print(f"\n✅ Successfully optimized {success_count} files")

    # Remove corresponding JSON output files so they get regenerated
    json_files_to_remove = [
        "tests/parsers/biorad_bioplex_manager/testdata/bio-rad_bio-plex_manager_example_01.json",
        "tests/parsers/appbio_quantstudio/testdata/appbio_quantstudio_example01.json",
    ]

    print("\nRemoving JSON output files for regeneration...")
    for json_file in json_files_to_remove:
        json_path = Path(json_file)
        if json_path.exists():
            json_path.unlink()
            print(f"  ✓ Removed {json_path.name}")

    print("\n" + "=" * 60)
    print("Next steps:")
    print("1. Run tests to regenerate output files")
    print("2. Verify all tests pass")
    print("3. Remove backup files if successful")
    print("=" * 60)


if __name__ == "__main__":
    main()
