import xml.etree.ElementTree as Et

from allotropy.exceptions import (
    AllotropeConversionError,
    AllotropyParserError,
    get_key_or_error,
)
from allotropy.named_file_contents import NamedFileContents
from allotropy.parsers.biorad_bioplex_manager import constants
from allotropy.parsers.utils.strict_xml_element import StrictXmlElement


class BioradBioplexReader:
    def __init__(self, named_file_contents: NamedFileContents) -> None:
        contents = named_file_contents.contents.read()
        # Ensure contents is bytes for StrictXmlElement.create_from_bytes()
        if isinstance(contents, str):
            contents = contents.encode("utf-8")
        try:
            self.root = StrictXmlElement.create_from_bytes(contents)
            # Create a mapping of child tags to StrictXmlElement objects
            self.children = {}
            for child_tag in constants.EXPECTED_TAGS:
                child_element = self.root.find_or_none(child_tag)
                if child_element is not None:
                    self.children[child_tag] = child_element
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

    def __getitem__(self, child_tag: str) -> StrictXmlElement:
        return get_key_or_error("child tag of root", child_tag, self.children)

    def get_attribute(self, child_tag: str, attribute: str) -> str:
        try:
            return self[child_tag].get_attr(attribute)
        except Exception as e:
            msg = f"Unable to find '{attribute}' in {self[child_tag].element.attrib}"
            raise AllotropeConversionError(msg) from e
