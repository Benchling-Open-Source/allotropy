\*Allotrope® is a registered trademark of the Allotrope Foundation; no affiliation with the Allotrope Foundation is claimed or implied.

# Introduction
Welcome to `allotropy` -- a Python library by Benchling for converting instrument data into the Allotrope Simple Model (ASM).

View the list of instrument software currently supported in [SUPPORTED_INSTRUMENT_SOFTWARE](https://github.com/Benchling-Open-Source/allotropy/blob/main/SUPPORTED_INSTRUMENT_SOFTWARE.adoc).

The objective of this library is to read text or Excel based instrument software output and return a JSON representation that conforms to the published ASM schema. Note that some schemas do not yet match the published ASM schema, in these cases the CHANGE_NOTES.md file included alongside the schema details the differences and proposed changes to ASM or the library schema. The code in this library does not convert from proprietary/binary output formats and so has no need to interact with any of the specific vendor softwares.

If you aren't familiar with Allotrope, we suggest you start by reading the [Allotrope Product Overview](https://www.allotrope.org/product-overview).

We have chosen to have this library output ASM since JSON is easy to read and consume in most modern systems and can be checked by humans without any special tools needed. All of the published open source ASMs can be found in the [ASM Gitlab repository](https://gitlab.com/allotrope-public/asm).

This code is published under the permissive MIT license because we believe that standardized instrument data is a benefit for everyone in science.

# Contributing
We welcome community contributions to this library and we hope that together we can expand the coverage of ASM-ready data for everyone. If you are interested, please read our [contribution guidelines](CONTRIBUTING.md).


# Usage

Convert a file to an ASM dictionary:

```sh
from allotropy.parser_factory import Vendor
from allotropy.to_allotrope import allotrope_from_file

asm_dict = allotrope_from_file("filepath.txt", Vendor.MOLDEV_SOFTMAX_PRO)
```

or, convert any IO:

```sh
from allotropy.parser_factory import Vendor
from allotropy.to_allotrope import allotrope_from_io

with open("filename.txt") as f:
    asm_dict = allotrope_from_io(f, Vendor.MOLDEV_SOFTMAX_PRO)

bytes_io = BytesIO(file_stream)
asm_dict = allotrope_from_io(bytes_io, Vendor.MOLDEV_SOFTMAX_PRO)
```

# Specific setup and build instructions

`.gitignore`: used standard GitHub Python template and added their recommended JetBrains lines


### Setup

Install Hatch: https://hatch.pypa.io/latest/
Install Python: https://www.python.org/downloads/
This library supports Python 3.10 or higher. Hatch will install a matching version of Python (defined in `pyproject.toml`) when it sets up your environment.

Tell git to use .githooks:
```sh
git config core.hooksPath .githooks
```

#### Dependencies

To add requirements used by the library, update `dependencies` in `pyproject.toml`:
- For project dependencies, update `dependencies` under `[project]`.
- For script dependencies, update `dependencies` under `[tool.hatch.envs.default]`.
- For lint dependencies, update `dependencies` under `[tool.hatch.envs.lint]`.
- For test dependencies, update `dependencies` under `[tool.hatch.envs.test]`.

### Useful Hatch commands
List all environments:
```sh
hatch env show
```

Run all lint:
```sh
hatch run lint:all
```

Auto-fix all possible lint issues:
```sh
hatch run fix
```

Run all tests in the default python enviroment (currently: 3.11.9)
```sh
hatch run test
```

Run all tests against all supported python versions (currently 3.10-3.12)
Note: this is checked against in CI - your change must pass this to merge.
```sh
hatch run test_all:test
```

Run against a specific python version (useful for debugging if a test is failing in one environment)
```sh
hatch run test_all.py3.12:test
```

Run a specific test file (replace the filepath with your own):
```sh
hatch run test tests/allotrope/allotrope_test.py
```

Run all tests with coverage:
```sh
hatch run test:cov
```

Spawn a shell within an environment for development:
```sh
hatch shell
```

### Publish

NOTE: only package admins can publish allotropy.

To publish a new version:

```sh
hatch run scripts:update-version
```

Merge the resulting PR, and then run on `main`:
```
hatch build
hatch publish
```
