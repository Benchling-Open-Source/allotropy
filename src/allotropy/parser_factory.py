from datetime import tzinfo
from enum import Enum

from allotropy.parsers.agilent_gen5.agilent_gen5_parser import AgilentGen5Parser
from allotropy.parsers.agilent_gen5_image.agilent_gen5_image_parser import (
    AgilentGen5ImageParser,
)
from allotropy.parsers.appbio_absolute_q.appbio_absolute_q_parser import (
    AppbioAbsoluteQParser,
)
from allotropy.parsers.appbio_quantstudio.appbio_quantstudio_parser import (
    AppBioQuantStudioParser,
)
from allotropy.parsers.appbio_quantstudio_designandanalysis.appbio_quantstudio_designandanalysis_parser import (
    AppBioQuantStudioDesignandanalysisParser,
)
from allotropy.parsers.beckman_pharmspec.beckman_pharmspec_parser import PharmSpecParser
from allotropy.parsers.beckman_vi_cell_blu.vi_cell_blu_parser import ViCellBluParser
from allotropy.parsers.beckman_vi_cell_xr.vi_cell_xr_parser import ViCellXRParser
from allotropy.parsers.biorad_bioplex_manager.biorad_bioplex_manager_parser import (
    BioradBioplexParser,
)
from allotropy.parsers.chemometec_nucleoview.nucleoview_parser import (
    ChemometecNucleoviewParser,
)
from allotropy.parsers.ctl_immunospot.ctl_immunospot_parser import CtlImmunospotParser
from allotropy.parsers.example_weyland_yutani.example_weyland_yutani_parser import (
    ExampleWeylandYutaniParser,
)
from allotropy.parsers.luminex_xponent.luminex_xponent_parser import (
    LuminexXponentParser,
)
from allotropy.parsers.methodical_mind.methodical_mind_parser import (
    MethodicalMindParser,
)
from allotropy.parsers.moldev_softmax_pro.softmax_pro_parser import SoftmaxproParser
from allotropy.parsers.novabio_flex2.novabio_flex2_parser import NovaBioFlexParser
from allotropy.parsers.perkin_elmer_envision.perkin_elmer_envision_parser import (
    PerkinElmerEnvisionParser,
)
from allotropy.parsers.qiacuity_dpcr.qiacuity_dpcr_parser import QiacuitydPCRParser
from allotropy.parsers.release_state import ReleaseState
from allotropy.parsers.revvity_kaleido.kaleido_parser import KaleidoParser
from allotropy.parsers.roche_cedex_bioht.roche_cedex_bioht_parser import (
    RocheCedexBiohtParser,
)
from allotropy.parsers.thermo_fisher_nanodrop_eight.nanodrop_eight_parser import (
    NanodropEightParser,
)
from allotropy.parsers.unchained_labs_lunatic.unchained_labs_lunatic_parser import (
    UnchainedLabsLunaticParser,
)
from allotropy.parsers.utils.timestamp_parser import TimestampParser
from allotropy.parsers.vendor_parser import VendorParser


class Vendor(Enum):
    AGILENT_GEN5 = "AGILENT_GEN5"
    AGILENT_GEN5_IMAGE = "AGILENT_GEN5_IMAGE"
    APPBIO_ABSOLUTE_Q = "APPBIO_ABSOLUTE_Q"
    APPBIO_QUANTSTUDIO = "APPBIO_QUANTSTUDIO"
    APPBIO_QUANTSTUDIO_DESIGNANDANALYSIS = "APPBIO_QUANTSTUDIO_DESIGNANDANALYSIS"
    BECKMAN_PHARMSPEC = "BECKMAN_PHARMSPEC"
    BECKMAN_VI_CELL_BLU = "BECKMAN_VI_CELL_BLU"
    BECKMAN_VI_CELL_XR = "BECKMAN_VI_CELL_XR"
    BIORAD_BIOPLEX = "BIORAD_BIOPLEX"
    CHEMOMETEC_NUCLEOVIEW = "CHEMOMETEC_NUCLEOVIEW"
    CTL_IMMUNOSPOT = "CTL_IMMUNOSPOT"
    EXAMPLE_WEYLAND_YUTANI = "EXAMPLE_WEYLAND_YUTANI"
    LUMINEX_XPONENT = "LUMINEX_XPONENT"
    METHODICAL_MIND = "METHODICAL_MIND"
    MOLDEV_SOFTMAX_PRO = "MOLDEV_SOFTMAX_PRO"
    NOVABIO_FLEX2 = "NOVABIO_FLEX2"
    PERKIN_ELMER_ENVISION = "PERKIN_ELMER_ENVISION"
    QIACUITY_DPCR = "QIACUITY_DPCR"
    REVVITY_KALEIDO = "REVVITY_KALEIDO"
    ROCHE_CEDEX_BIOHT = "ROCHE_CEDEX_BIOHT"
    THERMO_FISHER_NANODROP_EIGHT = "THERMO_FISHER_NANODROP_EIGHT"
    UNCHAINED_LABS_LUNATIC = "UNCHAINED_LABS_LUNATIC"

    @property
    def display_name(self) -> str:
        return self.get_parser().display_name

    @property
    def release_state(self) -> ReleaseState:
        return self.get_parser().release_state

    def get_parser(self, default_timezone: tzinfo | None = None) -> VendorParser:
        timestamp_parser = TimestampParser(default_timezone)
        return _VENDOR_TO_PARSER[self](timestamp_parser)


_VENDOR_TO_PARSER: dict[Vendor, type[VendorParser]] = {
    Vendor.AGILENT_GEN5: AgilentGen5Parser,
    Vendor.AGILENT_GEN5_IMAGE: AgilentGen5ImageParser,
    Vendor.APPBIO_ABSOLUTE_Q: AppbioAbsoluteQParser,
    Vendor.APPBIO_QUANTSTUDIO: AppBioQuantStudioParser,
    Vendor.APPBIO_QUANTSTUDIO_DESIGNANDANALYSIS: AppBioQuantStudioDesignandanalysisParser,
    Vendor.BECKMAN_PHARMSPEC: PharmSpecParser,
    Vendor.BECKMAN_VI_CELL_BLU: ViCellBluParser,
    Vendor.BECKMAN_VI_CELL_XR: ViCellXRParser,
    Vendor.BIORAD_BIOPLEX: BioradBioplexParser,
    Vendor.CHEMOMETEC_NUCLEOVIEW: ChemometecNucleoviewParser,
    Vendor.CTL_IMMUNOSPOT: CtlImmunospotParser,
    Vendor.EXAMPLE_WEYLAND_YUTANI: ExampleWeylandYutaniParser,
    Vendor.LUMINEX_XPONENT: LuminexXponentParser,
    Vendor.METHODICAL_MIND: MethodicalMindParser,
    Vendor.MOLDEV_SOFTMAX_PRO: SoftmaxproParser,
    Vendor.NOVABIO_FLEX2: NovaBioFlexParser,
    Vendor.PERKIN_ELMER_ENVISION: PerkinElmerEnvisionParser,
    Vendor.QIACUITY_DPCR: QiacuitydPCRParser,
    Vendor.REVVITY_KALEIDO: KaleidoParser,
    Vendor.ROCHE_CEDEX_BIOHT: RocheCedexBiohtParser,
    Vendor.THERMO_FISHER_NANODROP_EIGHT: NanodropEightParser,
    Vendor.UNCHAINED_LABS_LUNATIC: UnchainedLabsLunaticParser,
}
