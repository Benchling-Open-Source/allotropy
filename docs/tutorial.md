# Tutorial

This brief tutorial introduces the key ideas in this project
and shows how to extend this package to handle a new kind of device.
We assume you know how to create a virtual environment for Python,
how to define a class,
and how to run tests using `pytest`.

**Note:**
please follow the instructions in `CONTRIBUTING.md` in the root folder of this project
*before* beginning this tutorial.

## What is Allotropy?

`allotropy` is an open source Python package for converting laboratory instrument data
into [Allotrope Simple Model][allotrope] (ASM) format,
i.e.,
to take the (often messy) output of laboratory tools
and turn it into something that is well structured and has a well-defined semantics
so that other pieces of software can use it.

ASM is a complex format,
but that complexity is necessary to represent the wide variety of inputs it must handle.
For example,
some plate readers produce several readings per well,
so the format needs a way to represent a one-to-many relationship.
Similarly,
other devices might include timestamps,
sample numbers,
operator IDs,
and other information,
so ASM as a whole has to accommodate these
even for devices that don't generate that information.

`allotropy` represents the structures defined by ASM as Python classes
that can be converted to and from JSON.
It does not convert those nested structures into flat formats
like Pandas dataframes
because different applications will want to extract different pieces of information
from the overall representation.
However,
producing dataframes and other representations is straightforward,
and is covered in this tutorial.

## A Simple Input File

The input files for this tutorial come from an old Weyland-Yutani plate reader,
which produces CSV files like this:

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

-   One line with the device model number (Weyland-Yutani 470) and serial number (1251),
    all in one column.
-   Another line with the word `Recorded` in the first column
    and an ISO-formatted timestamp in the second column.
-   A "blank" line.
    Note that this line, and all others,
    actually contains enough commas to delimit five columns
    even if values are absent.
-   Five lines of plate data.
    The first line has a blank followed by column titles A-D;
    the remaining four rows have row numbers followed by readings.

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

This file has a different machine serial number (1384 instead of 1251),
but more importantly,
the plate readings are followed by another "blank" line consisting of nothing but commas
and then a checksum of the readings.
Unfortunately,
the documentation available to us does not specify how this checksum is calculated.

## Defining Files

After forking the [`allotropy` repository][allotropy_repo]
and creating a new branch for our work,
we make a new directory `./src/allotropy/parsers/example_weyland_yutani/` for our work
and create three files in that directory:

-   `example_weyland_yutani_structure.py` defines the classes
    that represent the data we pull from our CSV files.
-   `example_weyland_yutani_parser.py` contains code to read CSV files
    and produce objects of those classes.
-   an empty `__init__.py` file identifies this directory as a sub-package to Python.

## Representing Data

`example_weyland_yutani_structure.py` defines five classes
to represent various parts and levels of our data.
All of these classes use the `@dataclass` decorator from the Python standard library,
and all are "frozen",
i.e.,
instances cannot be modified after they are created.
For example,
the class that represent basic assay information is defined as:

```python
from dataclasses import dataclass
from typing import Optional

PROTOCOL_ID = "Weyland Yutani Example"
ASSAY_ID = "Example Assay"

@dataclass(frozen=True)
class BasicAssayInfo:
    protocol_id: str
    assay_id: str
    checksum: Optional[str]

    @staticmethod
    def create(bottom: Optional[pd.DataFrame]) -> BasicAssayInfo:
        checksum = (
            None
            if (bottom is None) or (bottom.iloc[0, 0] != "Checksum")
            else str(bottom.iloc[0, 1])
        )
        return BasicAssayInfo(
            protocol_id=PROTOCOL_ID,
            assay_id=ASSAY_ID,
            checksum=checksum,
        )
```

From top to bottom, this class defines:

-   Constants for the protocol ID and assay ID.
    (Real code would probably allow both to be variables taken from the data.)

-   The `BasicAssayInfo` dataclass with three fields:
    the protocol ID, the assay ID, and a checksum.
    As in all Python dataclasses,
    these are defined as class-level variables with type annotations;
    the checksum is marked as optional.

-   A static method called `create` that can take a Pandas dataframe as input
    and that produces an instance of `BasicAssayInfo`.
    The dataframe argument may have the value `None`
    if a checksum footer isn't present in the input data,
    so the parameter `bottom` is defined as `Optional[pd.DataFrame]`.
    The `create` method does a conditional check
    and defines `checksum` to be `None` or a value taken from the data if it's available,
    then constructs the `BasicAssayInfo` instance and returns it.

The other four classes in this file have a similar structure.
They are:

-   `Instrument`: capture information about the particular machine
    used to collect this data.
-   `Result`: store a single well reading as a triple of column, row, and reading.
-   `Plate`: store a collection of `Result` objects for a single plate.
-   `Data`: store a list of plates,
    the number of wells in each plate,
    and one instance each of `BasicAssayInfo` and `Instrument`.

The structure of these classes illustrates the point made earlier
that we sometimes need fields that aren't strictly necessary in one particular case
in order to conform with the needs of more complex cases.
For example,
`Plate` has two fields called `result` and `number`.
Quite sensibly,
the former holds a list of one `Result` object per well.
The latter always holds the value 0,
because the Weyland-Yutani reader only handles one plate at a time.
We probably wouldn't bother to record this value
if this was the only machine we were working with,
but since our data structures need to be able to represent multi-plate readers,
we need this field for compatibility.

## The Parser

The parser that turns CSV files into instances of the classes described above
is a class called `ExampleWeylandYutaniParser`
that lives in `example_weyland_yutani_parser.py`.
This class is derived from the generic `VendorParser` class
and *must* define a single method called `to_allotrope`
that takes a `NamedFileContents` objects as input
and produces an instance of (something derived from) `Model` as a result:

```python
class ExampleWeylandYutaniParser(VendorParser):
    def to_allotrope(self, named_file_contents: NamedFileContents) -> Model:
        raw_contents = named_file_contents.contents
        reader = CsvReader(raw_contents)
        return self._get_model(Data.create(reader))
```

After pulling the raw textual content out of the file object,
`to_allotrope` wraps it with an instance of  `CsvReader`.
This helper class,
which is defined by `allotropy`,
provides methods for inspecting and disassembling files that
may or may not be readable by Python's own `csv` module—as anyone
who has worked with the output of laboratory equipment can testify,
many vendors have very idiosyncratic interpretations of "comma-separated values".

The bulk of the work in this class is done by the `_get_model` method,
which looks like this:

```python
    def _get_model(self, data: Data) -> Model:
        if data.number_of_wells is None:
            msg = "Unable to determine the number of wells in the plate."
            raise AllotropeConversionError(msg)

        return Model(
            measurement_aggregate_document=MeasurementAggregateDocument(
                measurement_identifier=str(uuid.uuid4()),
                measurement_time=self._get_measurement_time(data),
                analytical_method_identifier=data.basic_assay_info.protocol_id,
                experimental_data_identifier=data.basic_assay_info.assay_id,
                container_type=ContainerType.well_plate,
                plate_well_count=TQuantityValueNumber(value=data.number_of_wells),
                device_system_document=DeviceSystemDocument(
                    model_number=data.instrument.serial_number,
                    device_identifier=data.instrument.nickname,
                ),
                measurement_document=self._get_measurement_document(data),
            )
        )
```

The first part of this method looks at the `Data` object
defined in `example_weyland_yutani_structure.py`
to make sure that the plate actually has some wells,
and if not,
raises an `AllotropeConversionError` exception.
Please use this exception for *all* parsing and data conversion errors
rather than (for example) raw Python `assert` statements
so that client applications can catch problems reliably.

The second part of `_get_model` constructs an instance of
the `allotropy` class `Model`,
which for our data is just a wrapper around another `allotropy` class
called `MeasurementAggregateDocument`.
Again,
this extra level of wrapping wouldn't be necessary
if we were only supporting one kind of machine with one kind of output,
but a `Model` can contain other information to support other kinds of hardware.
The various objects that `MeasurementAggregateDocument` depends on,
such as `ContainerType` and `DeviceSystemDocument`,
are also defined by `allotropy`;
in practice,
the easiest way to navigate them
is to copy and modify an existing parser.

## Making the Parser Available

Once our classes and parser are defined,
we add entries to `src/allotropy/parser_factory.py`
to make them available to users of the package:

1.  Import `ExampleWeylandYutaniParser`.
    We don't need to import the dataclasses it depends on,
    since client code will always access these by field name.

2.  Add an entry `EXAMPLE_WEYLAND_YUTANI` to the `Vendor` enumeration
    to uniquely identify this kind of parser.

3.  Add a similar entry to the `_VENDOR_TO_PARSER` lookup table
    to translate this enumeration element into the appropriate class.

## Testing

Tests for this new code go in `tests/parsers/example_weyland_yutani/`.
To write these,
we create two input CSV files,
which we put in the `testdata` directory below our tests directory.
We then use the script `csv-as-json`
to convert these CSV files to JSON,
inspect the JSON to make sure it's correct,
and save it in the same `testdata` directory:

```
hatch run scripts:csv-as-json --infile tests/parsers/example_weyland_yutani/testdata/Weyland_Yutani_simple_correct.csv --vendor EXAMPLE_WEYLAND_YUTANI --outfile tests/parsers/example_weyland_yutani/testdata/Weyland_Yutani_simple_correct.json
```

Our tests then compare the generated JSON against the saved files.

If we make changes to our parser, we may need to update the results of the test file.
We can do this via the script above, but we can also set `write_actual_to_expected_on_fail=True`
in the test function `validate_contents` to overwrite the contents of the file.

More complex parsers may require tests against helper methods,
and will probably have many more input-output pairs to check.

## Exercises

We have left the keyword `TODO` in a few places in the Weyland-Yutani example
to serve as thought exercises
and as examples of potential extensions to the base parser for handling more complex files.
We hope you will work through them,
but please do not submit fixes:
we would like other people to be able to work through them too.
Improvements or extensions to this tutorial,
on the other hand,
are very welcome,
and should be submitted as pull requests in the usual way.

[allotrope]: https://www.allotrope.org/product-overview
[allotropy_repo]: https://github.com/Benchling-Open-Source/allotropy
