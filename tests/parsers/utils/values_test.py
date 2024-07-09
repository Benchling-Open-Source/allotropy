from __future__ import annotations

from xml.etree import ElementTree

import pytest

from allotropy.exceptions import AllotropeConversionError
from allotropy.parsers.utils.values import (
    assert_not_none,
    get_attrib_from_xml,
    get_val_from_xml,
    get_val_from_xml_or_none,
    natural_sort_key,
    try_float,
    try_float_or_none,
    try_int,
    try_int_or_none,
)


def test_assert_not_none() -> None:
    x = 3
    assert assert_not_none(x) == x


def test_assert_not_none_fails() -> None:
    with pytest.raises(Exception, match="^Expected non-null value.$"):
        assert_not_none(None)


def test_assert_not_none_fails_with_message() -> None:
    with pytest.raises(Exception, match="^param_name was None$"):
        assert_not_none(None, msg="param_name was None")


def test_assert_not_none_fails_with_name() -> None:
    with pytest.raises(Exception, match="^Expected non-null value for param_name.$"):
        assert_not_none(None, "param_name")


def test_assert_not_none_fails_with_message_and_name() -> None:
    with pytest.raises(Exception, match="^param_name was None$"):
        assert_not_none(None, "param_name", "param_name was None")


@pytest.mark.short
@pytest.mark.parametrize(
    "key,expected",
    [
        ("", []),
        ("a", ["a"]),
        ("1", ["         1"]),
        ("a1b2c", ["a", "         1", "b", "         2", "c"]),
    ],
)
def test_natural_sort_key(key: str, expected: list[str]) -> None:
    assert natural_sort_key(key) == expected


def _try_float(value: str) -> float:
    return try_float(value, "param")


def test_try_float() -> None:
    assert _try_float("1.0") == 1.0


@pytest.mark.short
@pytest.mark.parametrize(
    "value,expected_regex",
    [
        (None, "Expected non-null value for param."),
        ("a", "Invalid float string: 'a'."),
    ],
)
def test_try_float_fails(value: str, expected_regex: str) -> None:
    with pytest.raises(AllotropeConversionError, match=expected_regex):
        _try_float(value)


@pytest.mark.short
@pytest.mark.parametrize(
    "value,expected",
    [
        (None, None),
        ("", None),
        ("1", 1),
        ("1.1", 1.1),
    ],
)
def test_try_float_or_none(value: str | None, expected: int | None) -> None:
    assert try_float_or_none(value) == expected


def _try_int(value: str | None) -> int:
    return try_int(value, "param")


def test_try_int() -> None:
    assert _try_int("1") == 1


@pytest.mark.short
@pytest.mark.parametrize(
    "value,expected_regex",
    [
        (None, "Expected non-null value for param."),
        ("a", "Invalid integer string: 'a'."),
    ],
)
def test_try_int_fails(value: str | None, expected_regex: str) -> None:
    with pytest.raises(AllotropeConversionError, match=expected_regex):
        _try_int(value)


@pytest.mark.short
@pytest.mark.parametrize(
    "value,expected",
    [
        (None, None),
        ("", None),
        ("1", 1),
        ("1.1", None),
    ],
)
def test_try_int_or_none(value: str | None, expected: float | None) -> None:
    assert try_int_or_none(value) == expected


@pytest.mark.short
@pytest.mark.parametrize(
    "tag_name,expected_output_val",
    [
        (("RunConditions", "RP1Gain"), "2198"),
        (("MachineInfo", "SerialNumber"), "LX12345678912"),
        (("RunProtocolDocumentName", None), "qux_15PLEX_ASSAY"),
    ],
)
def test_get_val_from_xml(tag_name: tuple[str, str], expected_output_val: str) -> None:
    xml_string = """<Well RowNo="1" ColNo="1" WellNo="1">
        <RunProtocolDocumentName>qux_15PLEX_ASSAY</RunProtocolDocumentName>
            <RunConditions>
                <PlatformTemp Unit="°C">23.56</PlatformTemp>
                <RP1Gain>2198</RP1Gain>
            </RunConditions>
            <MachineInfo>
                <SerialNumber>LX12345678912</SerialNumber>
                <XYPlatformSerialNumber>LXY07068104</XYPlatformSerialNumber>
            </MachineInfo>
    </Well>"""
    test_xml = ElementTree.fromstring(xml_string)  # noqa: S314
    assert (
        get_val_from_xml(
            xml_object=test_xml, tag_name=tag_name[0], tag_name_2=tag_name[1]
        )
        == expected_output_val
    )


@pytest.mark.short
def test_get_val_raise_error() -> None:
    xml_string = """<Well RowNo="1" ColNo="1" WellNo="1">
        <RunProtocolDocumentName>qux_15PLEX_ASSAY</RunProtocolDocumentName>
            <RunConditions>
                <PlatformTemp Unit="°C">23.56</PlatformTemp>
                <RP1Gain>2198</RP1Gain>
            </RunConditions>
            <TotalEvents>717</TotalEvents>
    </Well>"""
    test_xml = ElementTree.fromstring(xml_string)  # noqa: S314
    with pytest.raises(
        AllotropeConversionError, match="Unable to find 'SerialNumber' from xml."
    ):
        get_val_from_xml(test_xml, "SerialNumber")


@pytest.mark.short
@pytest.mark.parametrize(
    "inputs,expected_output_val",
    [
        (("RunConditions", "Unit", "FlowRate"), "µl/min"),
        (("RunSettings", "BeadCount", "StopReadingCriteria"), "25"),
    ],
)
def test_get_attrib_from_xml(
    inputs: tuple[str, str, str], expected_output_val: str
) -> None:
    xml_string = """
    <Well RowNo="4" ColNo="11" WellNo="47">
            <RunConditions>
                <PlatformTemp Unit="°C">24.43</PlatformTemp>
                <FlowRate Unit="µl/min">60</FlowRate>
            </RunConditions>
            <RunSettings>
                <SampleVolume Unit="µl">50</SampleVolume>
                <StopReadingCriteria BeadCount="25" BeadCountIn="0">Each selected region</StopReadingCriteria>
            </RunSettings>
    </Well>"""
    test_xml = ElementTree.fromstring(xml_string)  # noqa: S314
    assert (
        get_attrib_from_xml(
            xml_object=test_xml,
            tag_name=inputs[0],
            attrib_name=inputs[1],
            tag_name_2=inputs[2],
        )
        == expected_output_val
    )


def test_get_attrib_from_xml_raise_error() -> None:
    xml_string = """
    <Well RowNo="4" ColNo="11" WellNo="47">
            <RunSettings>
                <SampleVolume Unit="µl">50</SampleVolume>
                <StopReadingCriteria BeadCount="25" BeadCountIn="0">Each selected region</StopReadingCriteria>
            </RunSettings>
    </Well>"""
    test_xml = ElementTree.fromstring(xml_string)  # noqa: S314
    with pytest.raises(
        AllotropeConversionError,
        match="Unable to find 'SerialNumber' in {'BeadCount': '25', 'BeadCountIn': '0'}",
    ):
        get_attrib_from_xml(
            test_xml, "RunSettings", "SerialNumber", "StopReadingCriteria"
        )


def test_get_val_from_xml_or_none() -> None:
    xml_string = """
    <Well RowNo="4" ColNo="11" WellNo="47">
            <RunSettings>
                <SampleVolume Unit="µl">50</SampleVolume>
                <StopReadingCriteria BeadCount="25" BeadCountIn="0">Each selected region</StopReadingCriteria>
            </RunSettings>
    </Well>"""
    test_xml = ElementTree.fromstring(xml_string)  # noqa: S314
    assert (
        get_val_from_xml_or_none(
            xml_object=test_xml, tag_name="RunSettings", tag_name_2="DilutionFactor"
        )
        is None
    )
