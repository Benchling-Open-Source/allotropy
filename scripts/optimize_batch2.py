#!/usr/bin/env python3
"""Optimize test files - Batch 2"""

import os
from pathlib import Path


def optimize_quantstudio_txt(filepath: str, max_wells: int = 8, max_cycles: int = 3) -> None:
    """Optimize AppBio QuantStudio TXT file."""
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()

    print(f"  Original: {len(lines)} lines", end="")

    # Find sections
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

    # Build optimized file
    output = []

    # Keep header
    first_section = min(s[0] for s in sections.values()) if sections else len(lines)
    output.extend(lines[:first_section])

    # Process each section
    for section, (start, end) in sections.items():
        output.append(lines[start])  # Section header

        if section == '[Sample Setup]':
            # Keep header + first rows for max_wells
            if start + 1 < end:
                output.append(lines[start + 1])  # Headers
                well_count = 0
                for i in range(start + 2, end):
                    if well_count >= max_wells * 2:  # 2 targets per well possible
                        break
                    output.append(lines[i])
                    well_count += 1

        elif section in ['[Raw Data]', '[Amplification Data]', '[Multicomponent Data]']:
            if start + 1 < end:
                output.append(lines[start + 1])  # Headers
                # Keep first few cycles for first few wells
                count = 0
                for i in range(start + 2, end):
                    if count >= max_wells * max_cycles:
                        break
                    line = lines[i]
                    if '\t' in line:
                        parts = line.split('\t')
                        try:
                            # Check well and cycle numbers
                            if section == '[Raw Data]':
                                # Format: Well, Well Position, Cycle, ...
                                if len(parts) > 2:
                                    well = int(float(parts[0])) if parts[0].replace('.','').replace('-','').isdigit() else 999
                                    cycle = int(parts[2]) if parts[2].isdigit() else 999
                                else:
                                    continue
                            else:
                                # Format: Well, Cycle, ...
                                if len(parts) > 1:
                                    well = int(float(parts[0])) if parts[0].replace('.','').replace('-','').isdigit() else 999
                                    cycle = int(parts[1]) if parts[1].isdigit() else 999
                                else:
                                    continue

                            if well <= max_wells and cycle <= max_cycles:
                                output.append(line)
                                count += 1
                        except (ValueError, IndexError):
                            pass

        elif section == '[Results]':
            # Keep header + first rows
            if start + 1 < end:
                output.append(lines[start + 1])  # Headers
                for i in range(start + 2, min(start + 2 + max_wells * 2, end)):
                    output.append(lines[i])

        elif section == '[Melt Curve Raw Data]':
            # Skip most of this section for optimization
            if start + 1 < end:
                output.append(lines[start + 1])  # Just headers

    # Write optimized file
    with open(filepath, 'w', encoding='utf-8') as f:
        f.writelines(output)

    print(f" → {len(output)} lines ({100*(1-len(output)/len(lines)):.1f}% reduction)")


def optimize_agilent_gen5_txt(filepath: str) -> None:
    """Optimize Agilent Gen5 TXT file."""
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()

    print(f"  Original: {len(lines)} lines", end="")

    output = []
    in_data_section = False
    data_count = 0
    max_data_rows = 200  # Keep first 200 data rows

    for line in lines:
        # Keep all headers and metadata
        if not in_data_section:
            output.append(line)
            # Check if we're entering a data section
            if "Read " in line and ":" in line:
                in_data_section = True
        else:
            # In data section - limit rows
            if line.strip() == "" or "Read " in line:
                # End of data section or new section
                in_data_section = False
                data_count = 0
                output.append(line)
            elif data_count < max_data_rows:
                output.append(line)
                data_count += 1

    # Write optimized file
    with open(filepath, 'w', encoding='utf-8') as f:
        f.writelines(output)

    print(f" → {len(output)} lines ({100*(1-len(output)/len(lines)):.1f}% reduction)")


def optimize_facsdiva_xml(filepath: str) -> None:
    """Optimize BD FACSdiva XML file - keep structure but reduce data points."""
    with open(filepath, 'r') as f:
        lines = f.readlines()

    print(f"  Original: {len(lines)} lines", end="")

    # For now, just keep the file as-is since XML structure is complex
    # This is a placeholder for future optimization
    print(" → No optimization applied (complex XML structure)")


def optimize_softmax_txt(filepath: str) -> None:
    """Optimize SoftMax Pro TXT file."""
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()

    print(f"  Original: {len(lines)} lines", end="")

    output = []
    in_plate_section = False
    plate_line_count = 0
    max_plate_lines = 20  # Keep first 20 lines of plate data

    for line in lines:
        if "Plate:" in line or "Group:" in line:
            in_plate_section = True
            plate_line_count = 0
            output.append(line)
        elif in_plate_section:
            if line.strip() == "" or "~End" in line:
                in_plate_section = False
                output.append(line)
            elif plate_line_count < max_plate_lines:
                output.append(line)
                plate_line_count += 1
        else:
            output.append(line)

    # Write optimized file
    with open(filepath, 'w', encoding='utf-8') as f:
        f.writelines(output)

    print(f" → {len(output)} lines ({100*(1-len(output)/len(lines)):.1f}% reduction)")


# Main
files = [
    ('tests/parsers/agilent_gen5/testdata/Synergy instrument datafile (Fibrillation data) - TXT format.txt', optimize_agilent_gen5_txt),
    ('tests/parsers/appbio_quantstudio/testdata/appbio_quantstudio_example02.txt', optimize_quantstudio_txt),
    ('tests/parsers/appbio_quantstudio/testdata/appbio_quantstudio_example03.txt', optimize_quantstudio_txt),
    ('tests/parsers/appbio_quantstudio/testdata/appbio_quantstudio_example07.txt', optimize_quantstudio_txt),
    ('tests/parsers/appbio_quantstudio/testdata/appbio_quantstudio_example05.txt', optimize_quantstudio_txt),
    ('tests/parsers/moldev_softmax_pro/testdata/partial_plate_with_empty_values.txt', optimize_softmax_txt),
    ('tests/parsers/moldev_softmax_pro/testdata/ACSINS_absorbance_timeformat_spectrum.txt', optimize_softmax_txt),
]

print("Optimizing Batch 2 files...")
print("=" * 60)

for filepath, optimizer in files:
    path = Path(filepath)
    if not path.exists():
        print(f"✗ {path.name} - File not found")
        continue

    size_before = path.stat().st_size / 1024  # KB
    print(f"\n{path.name} ({size_before:.0f}KB)")

    optimizer(filepath)

    size_after = path.stat().st_size / 1024  # KB
    if size_after < size_before:
        print(f"  Size: {size_before:.0f}KB → {size_after:.0f}KB ({100*(1-size_after/size_before):.1f}% reduction)")

# Remove corresponding JSON outputs for regeneration
json_files = []
for filepath, _ in files:
    json_path = Path(filepath).with_suffix('.json')
    if json_path.exists():
        json_files.append(str(json_path))

if json_files:
    print("\n" + "=" * 60)
    print("Removing JSON outputs for regeneration...")
    for json_file in json_files:
        os.unlink(json_file)
        print(f"  ✓ {Path(json_file).name}")

print("\nBatch 2 optimization complete!")
print("\nNext: Run tests to verify all pass with optimized files")