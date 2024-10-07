# Tutorial

This brief tutorial introduces the key ideas in this project and shows how to extend this package to handle a
new kind of device. We assume you know how to create a virtual environment for Python, how to define a class,
and how to run tests using `pytest`.

**Note:**
please follow the instructions in `CONTRIBUTING.md` in the root folder of this project
*before* beginning this tutorial.

## What is Allotropy?

`allotropy` is an open source Python package for converting laboratory instrument data into
[Allotrope Simple Model][allotrope] (ASM) format, i.e., to take the (often messy) output of laboratory tools
and turn it into something that is well structured and has a well-defined semantics so that other pieces of
software can use it.

ASM is a complex format, but that complexity is necessary to represent the wide variety of inputs it must handle.
For example, some plate readers produce several readings per well, so the format needs a way to represent a
one-to-many relationship.

Similarly, other devices might include timestamps, sample numbers, operator IDs, and other information,
so ASM as a whole has to accommodate these even for devices that don't generate that information.

`allotropy` represents the structures defined by ASM as Python classes that can be converted to and from JSON.
It does not convert those nested structures into flat formats like Pandas dataframes because different
applications will want to extract different pieces of information from the overall representation.
However, producing dataframes and other representations is straightforward, and is covered in this tutorial.

## A Simple Input File

The input files for this tutorial come from an old Weyland-Yutani plate reader, which produces CSV files like this:

```csv
Weyland-Yutani 470 1251,,,,
Recorded,2023-10-23:17:54:48,,,
,,,,
,A,B,C,D
1,4.87,3.45,0.92,4.71
2,3.29,0.99,0.76,3.30
3,2.93,0.57,3.52,3.73
4,1.94,4.46,2.25,4.05
```

Line by line,
the structure of this file is:

-   One line with the device model number (Weyland-Yutani 470) and serial number (1251), all in one column.
-   Another line with the word `Recorded` in the first column and an ISO-formatted timestamp in the second column.
-   A "blank" line. Note that this line, and all others, actually contains enough commas to delimit five columns
    even if values are absent.
-   Five lines of plate data. The first line has a blank followed by column titles A-D; the remaining four
    rows have row numbers followed by readings.

If the operator pushes the right buttons,
the Weyland-Yutani 470 can also produce files like this:

```csv
Weyland-Yutani 470 1384,,,,
Recorded,2023-10-26:11:15:40,,,
,,,,
,A,B,C,D
1,3.61,1.45,2.23,3.08
2,4.10,4.58,3.60,1.67
3,3.27,1.40,4.99,2.47
4,2.78,0.72,4.00,0.49
,,,,
Checksum,b855,,,
```

This file has a different machine serial number (1384 instead of 1251), but more importantly, the plate
readings are followed by another "blank" line consisting of nothing but commas and then a checksum of the readings.
Unfortunately, the documentation available to us does not specify how this checksum is calculated.

## Defining Files

After forking the [`allotropy` repository][allotropy_repo]
and creating a new branch for our work,
we make a new parser by running `hatch run scripts:create-parser "example wayland yutani" "09/plate-reader"`

This will create 4 files in the directory `src/parsers/example_wayland_yutani`

- `example_weyland_yutani_reader.py` contains a reader class to parse the input file.
- `example_weyland_yutani_structure.py` defines functions that convert the raw data from our CSV files into
dataclasses that the schema mapper can use to produce ASM.
- `example_weyland_yutani_parser.py` contains code to read CSV file and produce objects of those classes.
- `constants.py` contains constants specific to these classes.
- an empty `__init__.py` file identifies this directory as a sub-package to Python.

It will also create a corresponding test directory: `tests/parsers/example_wayland_yutani`

- `to_allotrope_test.py` is a base test that will automatically run a test case for every file in `testdata`
- `testdata/` is a directory for example test data
-  an empty `__init__.py` file identifies this directory as a sub-package to Python.

## Representing Data

`example_weyland_yutani_structure.py` defines five classes to represent various parts and levels of our data.
All of these classes use the `@dataclass` decorator from the Python standard library, and all are "frozen",
i.e., instances cannot be modified after they are created. For example, the class that represent basic assay
information is defined as:

```python
from dataclasses import dataclass


@dataclass(frozen=True)
class BasicAssayInfo:
    protocol_id: str
    assay_id: str
    checksum: str | None

    @staticmethod
    def create(bottom: pd.DataFrame | None) -> BasicAssayInfo:
        checksum = (
            None
            if (bottom is None) or (bottom.iloc[0, 0] != "Checksum")
            else str(bottom.iloc[0, 1])
        )
        return BasicAssayInfo(
            # NOTE: in real code these values would be read from data
            protocol_id=constants.PROTOCOL_ID,
            assay_id=constants.ASSAY_ID,
            checksum=checksum,
        )

```

From top to bottom, this class defines:

-   The `BasicAssayInfo` dataclass with three fields: the protocol ID, the assay ID, and a checksum.
    As in all Python dataclasses, these are defined as class-level variables with type annotations;
    the checksum is marked as optional.

-   A static method called `create` that can take a Pandas dataframe as input and that produces an instance of `BasicAssayInfo`.
    The dataframe argument may have the value `None` if a checksum footer isn't present in the input data,
    so the parameter `bottom` is defined as `pd.DataFrame | None`. The `create` method does a conditional check
    and defines `checksum` to be `None` or a value taken from the data if it's available, then constructs the
    `BasicAssayInfo` instance and returns it.

The other four classes in this file have a similar structure.
They are:

-   `Instrument`: capture information about the particular machine used to collect this data.
-   `Result`: store a single well reading as a triple of column, row, and reading.
-   `Plate`: store a collection of `Result` objects for a single plate.

The structure of these classes illustrates the point made earlier that we sometimes need fields that aren't
strictly necessary in one particular case in order to conform with the needs of more complex cases.
For example, `Plate` has two fields called `result` and `number`. Quite sensibly, the former holds a list of
one `Result` object per well. The latter always holds the value 0, because the Weyland-Yutani reader only
handles one plate at a time. We probably wouldn't bother to record this value if this was the only machine we
were working with, but since our data structures need to be able to represent multi-plate readers, we need
this field for compatibility.

Finally, we define two functions `create_metadata` and `create_measurement_group`, which take the dataclasses
above and use them to populate dataclasses that correspond to the structure of the ASM schema. When writing
a new parser, you should familiarize yourself with the `SchemaMapper` of the schema that your parser will
populate. This will give you and idea of the data will be extracting from the file.

## The Parser

The parser that turns CSV files into instances of the classes described above is a class called `ExampleWeylandYutaniParser`
that lives in `example_weyland_yutani_parser.py`. This class is derived from the generic `VendorParser` class
and *must* define set `DISPLAY_NAME`, `RELEASE_STATE`, and `SCHEMA_MAPPER` and implement a single method called
`create_data` that takes a `NamedFileContents` objects as input and produces an instance of (something derived from) `Data` as a result:

```python
class ExampleWeylandYutaniParser(VendorParser[Data, Model]):
    DISPLAY_NAME = DISPLAY_NAME
    RELEASE_STATE = ReleaseState.WORKING_DRAFT
    SCHEMA_MAPPER = Mapper

    def create_data(self, named_file_contents: NamedFileContents) -> Model:
        reader = ExampleWeylandYutaniReader(named_file_contents)
        basic_assay_info = BasicAssayInfo.create(reader.bottom)
        instrument = Instrument.create()
        plates = Plate.create(reader.middle)

        if plates[0].number_of_wells is None:
            msg = "Unable to determine the number of wells in the plate."
            raise AllotropeConversionError(msg)

        return Data(
            create_metadata(instrument, named_file_contents.original_file_name),
            [create_measurement_group(plate, basic_assay_info) for plate in plates],
        )
```

`Parser.create_data` uses a `Reader` class to extract raw data out of the input file, which in this case is a CSV.
The `Reader` class makes use of `CsvReader`, a helper class which is defined by `allotropy`.
`CsvReader` provides methods for inspecting and disassembling files that may or may not be readable by
Python's own `csv` module — as anyone who has worked with the output of laboratory equipment can testify,
many vendors have very idiosyncratic interpretations of "comma-separated values".

After parsing the raw data, the method checks to make sure that the plate actually has some wells, and if not,
raises an `AllotropeConversionError` exception. Please use this exception for *all* errors caused by bad input
data, rather than (for example) raw Python `assert` statements so that client applications can catch problems
reliably.

Note that after the call to `create_data`, the base `VendorParser` uses the `SchemaMapper` class to produce
the corresponding `Model`, which can then be serialized into ASM json.

## Making the Parser Available

Once our classes and parser are defined, we add entries to `src/allotropy/parser_factory.py`
to make them available to users of the package:
(NOTE: this will be done automatically if using `hatch run scripts:create-parser`)

1.  Import `ExampleWeylandYutaniParser`.
    We don't need to import the dataclasses it depends on, since client code will always access these by field name.

2.  Add an entry `EXAMPLE_WEYLAND_YUTANI` to the `Vendor` enumeration to uniquely identify this kind of parser.

3.  Add a similar entry to the `_VENDOR_TO_PARSER` lookup table to translate this enumeration element into the appropriate class.

## Testing

Tests for this new code go in `tests/parsers/example_weyland_yutani/`.
To write these, we create two input CSV files, which we put in the `testdata` directory below our tests directory.

The `ParserTest` test included in the generated `to_allotrope_test.py` discovers every file in `testdata` and
tests against if by:

1. Calling the parser specified by VENDOR on the file
2. Comparing the output against expected output, contained in a file with the same name but a `json` extension.

Note: the test runs against every file in the corresponding testdata/ folder by default, but you can use
`--filter` to select specific cases to run, and `--exclude` to skip cases, and files with "error", "exclude" or "invalid"
in their names will automatically be skipped.

We can automatically generate the expected output by running `to_allotrope_test.py` without the corresponding
expected output file:

```
hatch run test tests/parsers/example_weyland_yutani/to_allotrope_test.py
```

The test will detect the missing expected output file and create it (if the parser runs successfully!)

It is important to then inspect the output JSON to make sure it's correct.

Once created, the runs of the test in the future will compare the output of the parser against the expected
output file.

If we make changes to our parser, we may need to update the results of the test file.
We can do this by passing `--overwrite` while running the test.
The test will fail if the contents do not match, but it will then update the contents of the expected
output file, and will pass on further runs.

More complex parsers may require tests against helper methods, and will probably have many more input-output pairs to check.

## Exercises

We have left the keyword `TODO(tutorial)` in a few places in the Weyland-Yutani example to serve as thought
exercises and as examples of potential extensions to the base parser for handling more complex files.
We hope you will work through them, but please do not submit fixes: we would like other people to be able to
work through them too.

Improvements or extensions to this tutorial, on the other hand, are very welcome, and should be submitted as
pull requests in the usual way.

[allotrope]: https://www.allotrope.org/product-overview
[allotropy_repo]: https://github.com/Benchling-Open-Source/allotropy
