#!/usr/bin/env python3
"""
Analyzes an input file to infer structure and suggest appropriate Allotrope schema.
Usage: python analyze_file.py <file_path>
"""
import sys
from pathlib import Path
import pandas as pd
from typing import Any, Dict, List, Optional

def analyze_excel_file(file_path: Path) -> Dict[str, Any]:
    """Analyze Excel file structure."""
    try:
        # Try to read Excel file (try calamine first, fall back to openpyxl)
        try:
            df = pd.read_excel(file_path, header=None, engine="calamine")
        except:
            df = pd.read_excel(file_path, header=None, engine="openpyxl")

        analysis: Dict[str, Any] = {
            "format": "excel",
            "shape": df.shape,
            "columns": df.shape[1],
            "rows": df.shape[0],
            "has_headers": False,
            "potential_sections": [],
            "measurement_indicators": [],
            "suggested_schema": None
        }

        # Check for headers (first row contains mostly strings)
        if df.iloc[0].dtype == 'object':
            analysis["has_headers"] = True

        # Look for measurement type indicators
        content_str = df.to_string().lower()

        # Schema detection based on keywords
        indicators = {
            "plate-reader": ["absorbance", "fluorescence", "luminescence", "well", "plate", "od", "optical density"],
            "pcr": ["ct", "cq", "cycle", "amplification", "melt", "target", "threshold"],
            "solution-analyzer": ["ph", "osmolality", "particle", "size", "distribution", "conductivity"],
            "cell-counting": ["viability", "cell density", "cell count", "live cells", "dead cells", "total cells"],
            "spectrophotometry": ["wavelength", "spectrum", "absorbance", "transmittance", "nm"],
            "electrophoresis": ["lane", "band", "migration", "gel", "ladder"],
            "liquid-chromatography": ["retention time", "peak", "chromatogram", "area", "height"],
            "binding-affinity": ["ka", "kd", "kon", "koff", "resonance", "binding", "affinity"],
            "flow-cytometry": ["fsc", "ssc", "fluorescence", "population", "gating"],
        }

        detected_schemas = []
        for schema, keywords in indicators.items():
            matches = sum(1 for kw in keywords if kw in content_str)
            if matches > 0:
                detected_schemas.append((schema, matches))
                analysis["measurement_indicators"].extend([kw for kw in keywords if kw in content_str])

        # Sort by number of matches
        if detected_schemas:
            detected_schemas.sort(key=lambda x: x[1], reverse=True)
            analysis["suggested_schema"] = detected_schemas[0][0]
            analysis["all_matches"] = detected_schemas

        # Check for sheet names if Excel
        try:
            try:
                xl = pd.ExcelFile(file_path, engine="calamine")
            except:
                xl = pd.ExcelFile(file_path, engine="openpyxl")
            analysis["sheet_names"] = xl.sheet_names
        except:
            pass

        return analysis

    except Exception as e:
        return {"format": "excel", "error": str(e)}


def analyze_text_file(file_path: Path) -> Dict[str, Any]:
    """Analyze text file structure."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        lines = content.split('\n')

        analysis: Dict[str, Any] = {
            "format": "text",
            "lines": len(lines),
            "has_sections": False,
            "section_markers": [],
            "delimiter": None,
            "measurement_indicators": [],
            "suggested_schema": None
        }

        # Check for section markers
        for line in lines[:50]:  # Check first 50 lines
            if line.strip().startswith('[') and line.strip().endswith(']'):
                analysis["has_sections"] = True
                analysis["section_markers"].append(line.strip())

        # Detect delimiter
        if '\t' in content:
            analysis["delimiter"] = "tab"
        elif ',' in content:
            analysis["delimiter"] = "comma"

        # Schema detection (same as Excel)
        content_lower = content.lower()
        indicators = {
            "plate-reader": ["absorbance", "fluorescence", "luminescence", "well", "plate", "od", "optical density"],
            "pcr": ["ct", "cq", "cycle", "amplification", "melt", "target", "threshold"],
            "solution-analyzer": ["ph", "osmolality", "particle", "size", "distribution", "conductivity"],
            "cell-counting": ["viability", "cell density", "cell count", "live cells", "dead cells"],
            "spectrophotometry": ["wavelength", "spectrum", "absorbance", "transmittance", "nm"],
            "binding-affinity": ["ka", "kd", "kon", "koff", "resonance", "binding", "affinity"],
        }

        detected_schemas = []
        for schema, keywords in indicators.items():
            matches = sum(1 for kw in keywords if kw in content_lower)
            if matches > 0:
                detected_schemas.append((schema, matches))
                analysis["measurement_indicators"].extend([kw for kw in keywords if kw in content_lower])

        if detected_schemas:
            detected_schemas.sort(key=lambda x: x[1], reverse=True)
            analysis["suggested_schema"] = detected_schemas[0][0]
            analysis["all_matches"] = detected_schemas

        return analysis

    except Exception as e:
        return {"format": "text", "error": str(e)}


def main():
    if len(sys.argv) < 2:
        print("Usage: python analyze_file.py <file_path>")
        print("\nThis script analyzes an input file to suggest the appropriate Allotrope schema.")
        sys.exit(1)

    file_path = Path(sys.argv[1])

    if not file_path.exists():
        print(f"Error: File not found: {file_path}")
        sys.exit(1)

    # Determine file type and analyze
    if file_path.suffix.lower() in ['.xlsx', '.xls']:
        analysis = analyze_excel_file(file_path)
    elif file_path.suffix.lower() in ['.txt', '.csv', '.tsv']:
        analysis = analyze_text_file(file_path)
    else:
        print(f"Unsupported file format: {file_path.suffix}")
        print("Supported formats: .xlsx, .xls, .txt, .csv, .tsv")
        sys.exit(1)

    # Print results
    print("\n" + "="*60)
    print(f"FILE ANALYSIS: {file_path.name}")
    print("="*60)

    for key, value in analysis.items():
        if key == "all_matches":
            print(f"\n{key.upper()}:")
            for schema, count in value:
                print(f"  - {schema}: {count} indicators")
        elif key == "sheet_names" and value:
            print(f"\nSHEET NAMES:")
            for sheet in value:
                print(f"  - {sheet}")
        elif key == "measurement_indicators" and value:
            print(f"\nMEASUREMENT INDICATORS FOUND:")
            unique_indicators = list(set(value))[:10]  # Limit to first 10 unique
            for item in unique_indicators:
                print(f"  - {item}")
        elif key == "section_markers" and value:
            print(f"\nSECTION MARKERS:")
            for item in value[:10]:  # Limit to first 10
                print(f"  - {item}")
        elif key not in ["all_matches", "measurement_indicators", "section_markers", "sheet_names"]:
            print(f"{key}: {value}")

    print("\n" + "="*60)
    if analysis.get("suggested_schema"):
        print(f"✅ RECOMMENDED SCHEMA: {analysis['suggested_schema']}")
        print(f"\nNext steps:")
        print(f"1. Run 'python .claude/skills/parser-generator/scripts/list_schemas.py {analysis['suggested_schema']}' for more details")
        print(f"2. Review existing parsers in src/allotropy/parsers/ for similar instruments")
        print(f"3. Run 'python scripts/create_parser.py' to generate the parser")
    else:
        print("⚠️  Could not determine schema - manual selection required")
        print(f"\nRun 'python .claude/skills/parser-generator/scripts/list_schemas.py' to see all available schemas")
    print("="*60 + "\n")


if __name__ == "__main__":
    main()