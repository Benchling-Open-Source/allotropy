#!/usr/bin/env python3
"""Optimize test files - Batch 1"""

import os
from pathlib import Path


def optimize_quantstudio_txt(filepath: str) -> None:
    """Optimize AppBio QuantStudio TXT file."""
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()
    
    print(f"Original: {len(lines)} lines")
    
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
    max_wells = 8
    max_cycles = 3
    
    for section, (start, end) in sections.items():
        output.append(lines[start])  # Section header
        
        if section == '[Sample Setup]':
            # Keep header + first 16 rows (8 wells, possibly 2 targets each)
            if start + 1 < end:
                output.append(lines[start + 1])  # Headers
                for i in range(start + 2, min(start + 18, end)):
                    output.append(lines[i])
                    
        elif section in ['[Raw Data]', '[Amplification Data]', '[Multicomponent Data]']:
            if start + 1 < end:
                output.append(lines[start + 1])  # Headers
                # Keep first 3 cycles for first 8 wells
                count = 0
                for i in range(start + 2, end):
                    if count >= max_wells * max_cycles:
                        break
                    line = lines[i]
                    if '\t' in line:
                        parts = line.split('\t')
                        try:
                            if section == '[Raw Data]':
                                # Format: Well, Well Position, Cycle, ...
                                well = int(parts[0]) if parts[0].replace('.','').isdigit() else 999
                                cycle = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else 999
                            else:
                                # Format: Well, Cycle, ...
                                well = int(parts[0]) if parts[0].replace('.','').isdigit() else 999
                                cycle = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 999
                            
                            if well <= max_wells and cycle <= max_cycles:
                                output.append(line)
                                count += 1
                        except (ValueError, IndexError):
                            pass
                            
        elif section == '[Results]':
            # Keep header + first 16 rows
            if start + 1 < end:
                output.append(lines[start + 1])  # Headers
                for i in range(start + 2, min(start + 18, end)):
                    output.append(lines[i])
        
        elif section == '[Melt Curve Raw Data]':
            # Skip this section for optimization
            if start + 1 < end:
                output.append(lines[start + 1])  # Just headers
    
    # Write optimized file
    with open(filepath, 'w', encoding='utf-8') as f:
        f.writelines(output)
    
    print(f"Optimized: {len(output)} lines ({100*(1-len(output)/len(lines)):.1f}% reduction)")


def optimize_biorad_xml(filepath: str) -> None:
    """Optimize Biorad Bioplex XML file."""
    with open(filepath, 'r') as f:
        lines = f.readlines()
    
    print(f"Original: {len(lines)} lines")
    
    output = []
    in_wells = False
    well_count = 0
    skip_lines = False
    
    for line in lines:
        if '<Wells>' in line:
            in_wells = True
            output.append(line)
        elif '</Wells>' in line:
            in_wells = False
            output.append(line)
        elif in_wells:
            if '<Well ' in line and 'WellNo=' in line:
                well_count += 1
                skip_lines = (well_count > 8)
            
            if not skip_lines:
                output.append(line)
            
            if '</Well>' in line:
                skip_lines = False
        else:
            output.append(line)
    
    # Write optimized file
    with open(filepath, 'w') as f:
        f.writelines(output)
    
    print(f"Optimized: {len(output)} lines, kept {min(well_count, 8)}/{well_count} wells")


# Main
files = [
    ('tests/parsers/appbio_quantstudio/testdata/appbio_quantstudio_example01.txt', optimize_quantstudio_txt),
    ('tests/parsers/biorad_bioplex_manager/testdata/bio-rad_bio-plex_manager_example_01.xml', optimize_biorad_xml),
]

print("Optimizing Batch 1 files...")
print("=" * 60)

for filepath, optimizer in files:
    path = Path(filepath)
    size_before = path.stat().st_size / (1024 * 1024)
    print(f"\n{path.name} ({size_before:.1f}MB)")
    
    optimizer(filepath)
    
    size_after = path.stat().st_size / (1024 * 1024)
    print(f"Size: {size_before:.1f}MB → {size_after:.1f}MB ({100*(1-size_after/size_before):.1f}% reduction)")

# Remove JSON outputs for regeneration
json_files = [
    'tests/parsers/appbio_quantstudio/testdata/appbio_quantstudio_example01.json',
    'tests/parsers/biorad_bioplex_manager/testdata/bio-rad_bio-plex_manager_example_01.json',
]

print("\n" + "=" * 60)
print("Removing JSON outputs for regeneration...")
for json_file in json_files:
    if Path(json_file).exists():
        os.unlink(json_file)
        print(f"  ✓ {Path(json_file).name}")

print("\nBatch 1 optimization complete!")
