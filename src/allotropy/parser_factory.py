from datetime import timezone
from enum import Enum
from typing import Optional, Union

from allotropy.allotrope.allotrope import AllotropeConversionError
from allotropy.parsers.agilent_gen5.agilent_gen5_parser import AgilentGen5Parser
from allotropy.parsers.appbio_quantstudio.appbio_quantstudio_parser import (
    AppBioQuantStudioParser,
)
from allotropy.parsers.beckman_vi_cell_blu.vi_cell_blu_parser import ViCellBluParser
from allotropy.parsers.beckman_vi_cell_xr.vi_cell_xr_parser import ViCellXRParser
from allotropy.parsers.moldev_softmax_pro.softmax_pro_parser import SoftmaxproParser
from allotropy.parsers.novabio_flex2.novabio_flex2_parser import NovaBioFlexParser
from allotropy.parsers.perkin_elmer_envision.elmer_envision_parser import (
    ElmerEnvisionParser,
)
from allotropy.parsers.roche_cedex_bioht.cedex_bioht_parser import CedexBiohtParser
from allotropy.parsers.utils.timestamp_parser import TimestampParser
from allotropy.parsers.vendor_parser import VendorParser


class Vendor(Enum):
    AGILENT_GEN5 = "AGILENT_GEN5"
    APPBIO_QUANTSTUDIO = "APPBIO_QUANTSTUDIO"
    BECKMAN_VI_CELL_BLU = "BECKMAN_VI_CELL_BLU"
    BECKMAN_VI_CELL_XR = "BECKMAN_VI_CELL_XR"
    MOLDEV_SOFTMAX_PRO = "MOLDEV_SOFTMAX_PRO"
    NOVABIO_FLEX2 = "NOVABIO_FLEX2"
    PERKIN_ELMER_ENVISION = "PERKIN_ELMER_ENVISION"
    ROCHE_CEDEX_BIOHT = "ROCHE_CEDEX_BIOHT"


VendorType = Union[Vendor, str]


_VENDOR_TO_PARSER: dict[Vendor, type[VendorParser]] = {
    Vendor.AGILENT_GEN5: AgilentGen5Parser,
    Vendor.APPBIO_QUANTSTUDIO: AppBioQuantStudioParser,
    Vendor.BECKMAN_VI_CELL_BLU: ViCellBluParser,
    Vendor.BECKMAN_VI_CELL_XR: ViCellXRParser,
    Vendor.NOVABIO_FLEX2: NovaBioFlexParser,
    Vendor.MOLDEV_SOFTMAX_PRO: SoftmaxproParser,
    Vendor.PERKIN_ELMER_ENVISION: ElmerEnvisionParser,
    Vendor.ROCHE_CEDEX_BIOHT: CedexBiohtParser,
}


class ParserFactory:
    def __init__(self) -> None:
        pass

    def create(
        self, vendor_type: VendorType, default_timezone: Optional[timezone] = None
    ) -> VendorParser:
        try:
            timestamp_parser = TimestampParser(default_timezone)
            return _VENDOR_TO_PARSER[Vendor(vendor_type)](timestamp_parser)
        except (ValueError, KeyError) as e:
            error = f"Failed to create parser, unregistered vendor: {vendor_type}"
            raise AllotropeConversionError(error) from e


def get_parser(
    vendor_type: VendorType, default_timezone: Optional[timezone] = None
) -> VendorParser:
    return PARSER_FACTORY.create(vendor_type, default_timezone=default_timezone)


PARSER_FACTORY: ParserFactory = ParserFactory()
