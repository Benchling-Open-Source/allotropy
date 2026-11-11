"""Allotropy test data package.

This package provides access to real-world instrument file examples and their
expected ASM (Allotrope Simple Model) outputs for testing purposes.
"""

from allotropy_testdata.__about__ import __version__
from allotropy_testdata.registry import (
    get_data_dir,
    get_file,
    get_input_files,
    get_output_files,
    get_test_files,
    get_vendor_dir,
    list_vendors,
)

__all__ = [
    "__version__",
    "get_data_dir",
    "get_file",
    "get_input_files",
    "get_output_files",
    "get_test_files",
    "get_vendor_dir",
    "list_vendors",
]
