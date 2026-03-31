#!/usr/bin/env python3
"""
Lists available Allotrope schemas by scanning the local allotropy repository.
Usage: python list_schemas.py [filter] [--verbose]
"""
from collections import defaultdict
import os
from pathlib import Path
import sys

# Fallback descriptions for common schema types
SCHEMA_DESCRIPTIONS = {
    "plate-reader": "Microplate readers measuring absorbance, fluorescence, luminescence in wells",
    "plate_reader": "Microplate readers measuring absorbance, fluorescence, luminescence in wells",
    "pcr": "PCR instruments (qPCR and dPCR) measuring amplification cycles and targets",
    "qpcr": "Quantitative PCR (qPCR) measuring real-time amplification",
    "dpcr": "Digital PCR (dPCR) measuring absolute quantification",
    "solution-analyzer": "Instruments analyzing solution properties (pH, osmolality, particle size)",
    "solution_analyzer": "Instruments analyzing solution properties (pH, osmolality, particle size)",
    "cell-counting": "Cell counters measuring viability, density, and cell populations",
    "cell_counting": "Cell counters measuring viability, density, and cell populations",
    "spectrophotometry": "Spectrophotometers measuring absorbance/transmittance across wavelengths",
    "electrophoresis": "Electrophoresis systems analyzing DNA/RNA/protein separation",
    "liquid-chromatography": "Liquid chromatography systems measuring compound separation and peaks",
    "liquid_chromatography": "Liquid chromatography systems measuring compound separation and peaks",
    "multi-analyte-profiling": "Multi-analyte detection platforms (e.g., Luminex)",
    "multi_analyte_profiling": "Multi-analyte detection platforms (e.g., Luminex)",
    "binding-affinity": "Surface plasmon resonance and binding affinity analyzers",
    "binding_affinity": "Surface plasmon resonance and binding affinity analyzers",
    "binding-affinity-analyzer": "Surface plasmon resonance and binding affinity analyzers",
    "binding_affinity_analyzer": "Surface plasmon resonance and binding affinity analyzers",
    "flow-cytometry": "Flow cytometers analyzing cell populations and markers",
    "flow_cytometry": "Flow cytometers analyzing cell populations and markers",
    "mass_spectrometry": "Mass spectrometers analyzing molecular mass and structure",
}


def find_allotropy_repo() -> Path | None:
    """Find the allotropy repository in the environment."""
    # Check if we're in the allotropy repo
    current = Path.cwd()
    for parent in [current, *list(current.parents)]:
        if (parent / "src" / "allotropy" / "allotrope" / "schemas").exists():
            return parent

    # Check environment variable
    if allotropy_path := os.getenv("ALLOTROPY_PATH"):
        path = Path(allotropy_path)
        if path.exists():
            return path

    return None


def scan_schemas(allotropy_path: Path) -> dict[str, list[dict[str, str]]]:
    """Scan the allotropy repository for available schemas."""
    schemas_dir = allotropy_path / "src" / "allotropy" / "allotrope" / "schemas" / "adm"

    if not schemas_dir.exists():
        print(f"Error: Schema directory not found: {schemas_dir}")
        sys.exit(1)

    # Group schemas by technique
    schemas: dict[str, list[dict[str, str]]] = defaultdict(list)

    for technique_dir in sorted(schemas_dir.iterdir()):
        if not technique_dir.is_dir():
            continue

        technique_name = technique_dir.name

        # Scan for schema files
        for schema_file in technique_dir.rglob("*.schema.json"):
            # Build relative path from schemas/adm/
            rel_path = schema_file.relative_to(schemas_dir)
            # Remove .schema.json extension
            schema_path = str(rel_path).replace(".schema.json", "")

            # Try to get the version info from path
            path_parts = schema_path.split("/")
            version_info = ""
            if len(path_parts) >= 4:
                # Format: technique/ORG/YEAR/MONTH
                version_info = f"{path_parts[1]}/{path_parts[2]}/{path_parts[3]}"

            schemas[technique_name].append(
                {
                    "path": f"adm/{schema_path}",
                    "version": version_info,
                    "file": str(schema_file),
                }
            )

    return dict(schemas)


def find_parsers_using_schema(allotropy_path: Path, technique_name: str) -> list[str]:
    """Find parsers that might use a specific schema technique."""
    parsers_dir = allotropy_path / "src" / "allotropy" / "parsers"
    matching_parsers = []

    if not parsers_dir.exists():
        return matching_parsers

    # Look for parsers that import from this schema technique
    for parser_dir in parsers_dir.iterdir():
        if not parser_dir.is_dir() or parser_dir.name.startswith("_"):
            continue

        # Check if parser file exists
        parser_file = parser_dir / f"{parser_dir.name}_parser.py"
        if parser_file.exists():
            try:
                with open(parser_file) as f:
                    content = f.read()
                    # Check for imports from the schema
                    if (
                        f"adm.{technique_name}" in content
                        or f"adm/{technique_name}" in content
                    ):
                        matching_parsers.append(parser_dir.name)
            except Exception:
                pass  # noqa: S110

    return matching_parsers


def list_schemas(
    allotropy_path: Path, filter_term: str | None = None, verbose: bool = False
) -> None:
    """List all available schemas from the local repository."""
    print("\n" + "=" * 80)
    print("AVAILABLE ALLOTROPE SCHEMAS")
    print(f"Repository: {allotropy_path}")
    print("=" * 80 + "\n")

    schemas = scan_schemas(allotropy_path)

    if not schemas:
        print("No schemas found in repository.")
        return

    total_count = 0
    for technique_name in sorted(schemas.keys()):
        if filter_term and filter_term.lower() not in technique_name.lower():
            continue

        schema_list = sorted(schemas[technique_name], key=lambda x: x["path"])
        total_count += len(schema_list)

        print(f"📋 {technique_name.upper()}")

        # Show description if available
        description = SCHEMA_DESCRIPTIONS.get(technique_name)
        if description:
            print(f"   {description}")

        print(f"\n   Available schema paths ({len(schema_list)} version(s)):")
        for schema_info in schema_list:
            if verbose:
                print(f"     - {schema_info['path']}")
                print(f"       Version: {schema_info['version']}")
            else:
                print(f"     - {schema_info['path']}")

        # Find example parsers
        matching_parsers = find_parsers_using_schema(allotropy_path, technique_name)
        if matching_parsers:
            print("\n   📁 Example parsers using this schema:")
            for parser in matching_parsers[:5]:  # Limit to 5
                print(f"     - {parser}")

        print("\n" + "-" * 80 + "\n")

    if not filter_term:
        print(f"Total schemas found: {total_count}")
        print("\nUse a filter to see specific schemas: python list_schemas.py <filter>")
        print("Use --verbose for more details: python list_schemas.py --verbose")


def main() -> None:
    # Parse arguments
    args = sys.argv[1:]
    filter_term = None
    verbose = False

    for arg in args:
        if arg in ["--verbose", "-v"]:
            verbose = True
        elif not arg.startswith("-"):
            filter_term = arg

    # Find allotropy repository
    allotropy_path = find_allotropy_repo()

    if not allotropy_path:
        print("Error: Could not find allotropy repository.")
        print("\nPlease run this script from within the allotropy repository,")
        print("or set ALLOTROPY_PATH environment variable:")
        print("  export ALLOTROPY_PATH=/path/to/allotropy")
        sys.exit(1)

    list_schemas(allotropy_path, filter_term, verbose)


if __name__ == "__main__":
    main()
