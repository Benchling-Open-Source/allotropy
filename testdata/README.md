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

## What is included

Only the contents of `tests/parsers/*/testdata/` are packaged (no test code). Files larger than 10 MB are excluded to keep the wheel within PyPI's size limit. The excluded files are:

- `cytiva_biacore_t200_evaluation`: `biacore_evaluation_module_example.bme` (232 MB), `biacore_evaluation_module_example3.bme` (141 MB), `biacore_evaluation_module_example4.bme` (78 MB)
- `cytiva_biacore_insight`: `Insight evaluaiton software kinetics and affinity.json`
- `appbio_quantstudio_designandanalysis`: four large negative-case files under `testdata/invalid/`

Because of this, a few inputs available in the repository are missing from the package. Get them from the [repository](https://github.com/Benchling-Open-Source/allotropy) if needed.

## File pairing

`get_test_files` follows the convention of allotropy's own parser tests:

- Files are found recursively under a vendor's `testdata/` folder.
- The expected output of `<dir>/x.ext` is `<dir>/x.json`.
- Parsers with JSON input keep inputs in an `input/` folder; `<dir>/input/x.json` is paired with `<dir>/output/x.json`.
- A `.rslt` folder is a single input.
- Paths containing `error`, `exclude` or `invalid` are negative cases. They are not returned as inputs but can be read with `get_file("vendor", "errors/name.ext")`.

## Versioning

`allotropy-testdata` is versioned independently of allotropy. Its version starts at the allotropy version it was first released with and is bumped (in `testdata/src/allotropy_testdata/__about__.py`) only when test data changes. The `testdata` extra of allotropy requires `allotropy-testdata >= <version>`, so raise that minimum when a release of allotropy depends on newer data.

Release with `scripts/build_all.py` and `scripts/publish_all.py` (publishing is interactive). Only a wheel is built for allotropy-testdata, since an sdist would not contain the data.

## Size

The wheel is about 54 MB. It is intended as an optional dependency for testing purposes.

## License

MIT License - see the main [allotropy repository](https://github.com/Benchling-Open-Source/allotropy) for details.
