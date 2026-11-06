# Allotropy Parser Generator Skill

This Claude skill helps you generate complete Allotropy instrument parsers from example input files. It analyzes file structure, auto-detects appropriate Allotrope schemas, and generates fully functional parser code.

## Installation

This skill is already installed in the `.claude/skills/parser-generator/` directory.

## Usage with Claude

When working with Claude in this repository, you can invoke the parser generator skill by saying:

- "Use the parser-generator skill to create a new parser"
- "Analyze this file and suggest a schema" (with a file path)
- "Generate a parser for [instrument name]"
- "/parser-generator" (if configured as a slash command)

## Manual Usage

You can also run the scripts directly:

### 1. Analyze an Input File

```bash
python .claude/skills/parser-generator/scripts/analyze_file.py <path_to_file>
```

This will analyze the file and suggest an appropriate schema based on the content.

### 2. List Available Schemas

```bash
# List all schemas
python .claude/skills/parser-generator/scripts/list_schemas.py

# Filter schemas
python .claude/skills/parser-generator/scripts/list_schemas.py plate

# Verbose output with paths
python .claude/skills/parser-generator/scripts/list_schemas.py --verbose
```

### 3. Generate a Parser

```bash
python .claude/skills/parser-generator/scripts/create_parser.py \
  <parser_name> \
  "<Display Name>" \
  --schema <schema_path> \
  --example <example_file>
```

Example:
```bash
python .claude/skills/parser-generator/scripts/create_parser.py \
  beckman_pharmspec \
  "Beckman Coulter PharmSpec" \
  --schema adm/plate_reader/BENCHLING/2024/06/plate_reader \
  --example ~/Downloads/pharmspec_data.xlsx
```

## Generated Files

The skill creates a complete parser structure:

```
src/allotropy/parsers/{parser_name}/
├── __init__.py                    # Module exports
├── {parser_name}_parser.py        # Main parser class
├── {parser_name}_reader.py        # File reading logic
└── {parser_name}_structure.py     # Data structures

tests/parsers/{parser_name}/
├── __init__.py
├── test_{parser_name}_parser.py   # Test file
└── testdata/
    └── example.xlsx               # Test data
```

## Workflow

1. **Analyze** your example file to detect the schema
2. **List** available schemas if you need to override
3. **Generate** the parser with the create script
4. **Implement** the TODO sections in the generated code
5. **Test** the parser with your example data
6. **Register** the parser in `parser_factory.py`

## Supported File Formats

- Excel files (.xlsx, .xls)
- CSV files (.csv)
- Tab-delimited files (.txt, .tsv)
- Text files with sections

## Schema Detection

The skill detects schemas based on keywords in the file:

- **plate-reader**: absorbance, fluorescence, luminescence, well, plate
- **pcr**: ct, cq, cycle, amplification, target
- **cell-counting**: viability, cell count, density
- **spectrophotometry**: wavelength, spectrum, nm
- **solution-analyzer**: pH, osmolality, particle size
- **binding-affinity**: ka, kd, kon, koff, resonance

## Tips

- Always start with `analyze_file.py` to understand your input format
- Look at similar existing parsers for patterns
- Use the existing utility functions in `allotropy.parsers.utils`
- Test with real data files early and often
- Start with `WORKING_DRAFT` release state

## Troubleshooting

- **Schema not detected**: Manually specify with `list_schemas.py`
- **Parser already exists**: Choose a different name or delete existing
- **Import errors**: Make sure you're in the allotropy repository
- **Test failures**: Check that your Data structure matches the schema