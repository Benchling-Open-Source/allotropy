import xml.etree.ElementTree as Et

from allotropy.exceptions import (
    AllotropeConversionError,
    AllotropyParserError,
    get_key_or_error,
)
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.biorad_bioplex_manager import constants


class BioradBioplexReader:
    def __init__(self, named_file_contents: NamedFileContents) -> None:
        contents = named_file_contents.contents.read()
        try:
            xml_tree = Et.ElementTree(Et.fromstring(contents))  # noqa: S314
            self.root = xml_tree.getroot()
            self.children = {child.tag: child for child in self.root}
        except Et.ParseError as err:
            # Return all expected tags if XML parsing fails
            msg = "Error parsing xml"
            raise AllotropyParserError(msg) from err

        self._validate()

    def _validate(self) -> None:
        missing_tags = [
            tag for tag in constants.EXPECTED_TAGS if tag not in self.children
        ]
        if missing_tags:
            msg = f"Missing expected tags in xml: {missing_tags}"
            raise AllotropeConversionError(msg)

    def __getitem__(self, child_tag: str) -> Et.Element:
        return get_key_or_error("child tag of root", child_tag, self.children)

    def get_attribute(self, child_tag: str, attribute: str) -> str:
        try:
            return self[child_tag].attrib[attribute]
        except KeyError as e:
            msg = f"Unable to find '{attribute}' in {self[child_tag].attrib}"
            raise AllotropeConversionError(msg) from e
