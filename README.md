# Introduction
Welcome to `allotropy` -- a Python library for converting instrument data into Allotrope Simple Model (ASM).

The objective of this library is to read text or Excel based instrument software output and return a JSON representation that conforms to the published ASM schema. The code in this library does not convert from proprietary/binary output formats and so has no need to interact with any of the specific vendor softwares.

If you aren't familiar with Allotrope, we suggest you start by reading the [Allotrope Product Overview](https://www.allotrope.org/product-overview).

We have chosen to have this library output ASM since JSON is easy to read and consume in most modern systems and can be checked by humans without any special tools needed. All of the published open source ASMs can be found in the [ASM Gitlab repository](https://gitlab.com/allotrope-public/asm).

We currently have parser support for the following instruments:
  - Agilent Gen5
  - Applied Bio QuantStudio
  - Beckman Vi-Cell BLU
  - Beckman Vi-Cell XR
  - MolDev SoftMax Pro
  - NovaBio Flex2
  - PerkinElmer Envision
  - Roche Cedex BioHT

This code is published under the permissive MIT license because we believe that standardized instrument data is a benefit for everyone in science.

# Usage

Convert a file to an ASM dictionary:

```sh
from allotropy.parser_factory import VendorType
from allotropy.to_allotrope import allotrope_from_file

asm_schema = allotrope_from_file("filepath.txt", Vendor.MOLDEV_SOFTMAX_PRO)
```

or, convert any IO:

```sh
from allotropy.parser_factory import VendorType
from allotropy.to_allotrope import allotrope_from_io

with open("filename.txt") as f:
    asm_schema = allotrope_from_io(f, Vendor.MOLDEV_SOFTMAX_PRO)

bytes_io = BytesIO(file_stream)
asm_schema = allotrope_from_io(bytes_io, Vendor.MOLDEV_SOFTMAX_PRO)
```

# Specific setup and build instructions

`.gitignore`: used standard GitHub Python template and added their recommended JetBrains lines


### Setup

Install Hatch: https://hatch.pypa.io/latest/
Install python: https://www.python.org/downloads/

Add pre-push checks to your repo:
```sh
hatch run scripts:setup-pre-push
```

#### Dependencies

To add requirements used by the library, update `dependencies` in `pyproject.toml`:
- For project dependencies, update `dependencies` under `[project]`.
- For script dependencies, update `dependencies` under `[tool.hatch.envs.default]`.
- For lint dependencies, update `dependencies` under `[tool.hatch.envs.lint]`.
- For test dependencies, update `dependencies` under `[tool.hatch.envs.test]`.

### Useful Hatch commands
```sh
hatch env show
```

Run all lint:
```sh
hatch run lint:all
```

Auto-fix all possible lint issues:
```sh
hatch run lint:fix
```

Run all tests:
```sh
hatch run test:test
```

Run all tests with coverage:
```sh
hatch run test:cov
```

### Publish

To publish a new version, update the version in `src/allotropy/__about__.py` and run:

```sh
hatch build
hatch publish
```
