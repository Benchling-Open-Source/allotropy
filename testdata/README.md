# allotropy-testdata

Test data files for the [allotropy](https://github.com/Benchling-Open-Source/allotropy) package.

This package contains real-world instrument file examples and their expected ASM (Allotrope Simple Model) outputs, enabling users to:
- Write integration tests against allotropy's output format
- Test allotropy flows end-to-end using real instrument files
- Validate custom parsers against known-good outputs

## Installation

### As optional extra (recommended)
```bash
pip install allotropy[testdata]
```

### Standalone
```bash
pip install allotropy-testdata
```

## Usage

```python
from allotropy_testdata import get_test_files, get_input_files, list_vendors

# List all available vendors
vendors = list_vendors()
# ['appbio_quantstudio', 'agilent_gen5', 'beckman_vi_cell_blu', ...]

# Get all test files for a vendor (returns dict of input -> output path)
test_files = get_test_files("appbio_quantstudio")
# {
#   PosixPath('.../example01.txt'): PosixPath('.../example01.json'),
#   PosixPath('.../example02.txt'): PosixPath('.../example02.json'),
#   ...
# }

# Get only input files
inputs = get_input_files("appbio_quantstudio")
# [PosixPath('.../example01.txt'), PosixPath('.../example02.txt'), ...]

# Get only output files
from allotropy_testdata import get_output_files
outputs = get_output_files("appbio_quantstudio")
# [PosixPath('.../example01.json'), PosixPath('.../example02.json'), ...]

# Get a specific file
from allotropy_testdata import get_file
input_file = get_file("appbio_quantstudio", "appbio_quantstudio_example01.txt")
```

## Versioning

This package is versioned in lockstep with the main allotropy package. Version `0.1.116` of allotropy-testdata contains test files that correspond to allotropy `0.1.116`.

## Size Warning

This package is significantly larger (~600MB) than the main allotropy package due to containing binary and data files. It is intended as an optional dependency for testing purposes.

## License

MIT License - see the main [allotropy repository](https://github.com/Benchling-Open-Source/allotropy) for details.
