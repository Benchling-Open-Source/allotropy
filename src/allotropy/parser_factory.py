from collections import defaultdict
from datetime import tzinfo
from enum import Enum
from pathlib import Path
from typing import Any

from allotropy.allotrope.schema_parser.path_util import ROOT_DIR
from allotropy.parsers.agilent_gen5.agilent_gen5_parser import AgilentGen5Parser
from allotropy.parsers.agilent_gen5_image.agilent_gen5_image_parser import (
    AgilentGen5ImageParser,
)
from allotropy.parsers.agilent_openlab_cds.agilent_openlab_cds_parser import (
    AgilentOpenLabCDSParser,
)
from allotropy.parsers.agilent_tapestation_analysis.agilent_tapestation_analysis_parser import (
    AgilentTapestationAnalysisParser,
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
from allotropy.parsers.bd_biosciences_facsdiva.bd_biosciences_facsdiva_parser import (
    BDFACSDivaParser,
)
from allotropy.parsers.beckman_coulter_biomek.beckman_coulter_biomek_parser import (
    BeckmanCoulterBiomekParser,
)
from allotropy.parsers.beckman_echo_plate_reformat.beckman_echo_plate_reformat_parser import (
    BeckmanEchoPlateReformatParser,
)
from allotropy.parsers.beckman_pharmspec.beckman_pharmspec_parser import PharmSpecParser
from allotropy.parsers.beckman_vi_cell_blu.vi_cell_blu_parser import ViCellBluParser
from allotropy.parsers.beckman_vi_cell_xr.vi_cell_xr_parser import ViCellXRParser
from allotropy.parsers.benchling_chromeleon.benchling_chromeleon_parser import (
    BenchlingChromeleonParser,
)
from allotropy.parsers.benchling_empower.benchling_empower_parser import (
    BenchlingEmpowerParser,
)
from allotropy.parsers.biorad_bioplex_manager.biorad_bioplex_manager_parser import (
    BioradBioplexParser,
)
from allotropy.parsers.bmg_labtech_smart_control.bmg_labtech_smart_control_parser import (
    BmgLabtechSmartControlParser,
)
from allotropy.parsers.bmg_mars.bmg_mars_parser import BmgMarsParser
from allotropy.parsers.cfxmaestro.cfxmaestro_parser import CfxmaestroParser
from allotropy.parsers.chemometec_nc_view.chemometec_nc_view_parser import (
    ChemometecNcViewParser,
)
from allotropy.parsers.chemometec_nucleoview.nucleoview_parser import (
    ChemometecNucleoviewParser,
)
from allotropy.parsers.ctl_immunospot.ctl_immunospot_parser import CtlImmunospotParser
from allotropy.parsers.cytiva_biacore_t200_control.cytiva_biacore_t200_control_parser import (
    CytivaBiacoreT200ControlParser,
)
from allotropy.parsers.cytiva_unicorn.cytiva_unicorn_parser import CytivaUnicornParser
from allotropy.parsers.example_weyland_yutani.example_weyland_yutani_parser import (
    ExampleWeylandYutaniParser,
)
from allotropy.parsers.flowjo.flowjo_parser import FlowjoParser
from allotropy.parsers.luminex_xponent.luminex_xponent_parser import (
    LuminexXponentParser,
)
from allotropy.parsers.mabtech_apex.mabtech_apex_parser import MabtechApexParser
from allotropy.parsers.methodical_mind.methodical_mind_parser import (
    MethodicalMindParser,
)
from allotropy.parsers.moldev_softmax_pro.softmax_pro_parser import SoftmaxproParser
from allotropy.parsers.msd_workbench.msd_workbench_parser import MSDWorkbenchParser
from allotropy.parsers.novabio_flex2.novabio_flex2_parser import NovaBioFlexParser
from allotropy.parsers.perkin_elmer_envision.perkin_elmer_envision_parser import (
    PerkinElmerEnvisionParser,
)
from allotropy.parsers.qiacuity_dpcr.qiacuity_dpcr_parser import QiacuitydPCRParser
from allotropy.parsers.release_state import ReleaseState
from allotropy.parsers.revvity_kaleido.kaleido_parser import KaleidoParser
from allotropy.parsers.revvity_matrix.revvity_matrix_parser import (
    RevvityMatrixParser,
)
from allotropy.parsers.roche_cedex_bioht.roche_cedex_bioht_parser import (
    RocheCedexBiohtParser,
)
from allotropy.parsers.roche_cedex_hires.roche_cedex_hires_parser import (
    RocheCedexHiResParser,
)
from allotropy.parsers.tecan_magellan.tecan_magellan_parser import TecanMagellanParser
from allotropy.parsers.thermo_fisher_genesys30.thermo_fisher_genesys30_parser import (
    ThermoFisherGenesys30Parser,
)
from allotropy.parsers.thermo_fisher_genesys_on_board.thermo_fisher_genesys_on_board_parser import (
    ThermoFisherGenesysOnBoardParser,
)
from allotropy.parsers.thermo_fisher_nanodrop_8000.nanodrop_8000_parser import (
    Nanodrop8000Parser,
)
from allotropy.parsers.thermo_fisher_nanodrop_eight.nanodrop_eight_parser import (
    NanodropEightParser,
)
from allotropy.parsers.thermo_fisher_nanodrop_one.thermo_fisher_nanodrop_one_parser import (
    ThermoFisherNanodropOneParser,
)
from allotropy.parsers.thermo_fisher_qubit4.thermo_fisher_qubit4_parser import (
    ThermoFisherQubit4Parser,
)
from allotropy.parsers.thermo_fisher_qubit_flex.thermo_fisher_qubit_flex_parser import (
    ThermoFisherQubitFlexParser,
)
from allotropy.parsers.thermo_fisher_visionlite.thermo_fisher_visionlite_parser import (
    ThermoFisherVisionliteParser,
)
from allotropy.parsers.thermo_skanit.thermo_skanit_parser import ThermoSkanItParser
from allotropy.parsers.unchained_labs_lunatic.unchained_labs_lunatic_parser import (
    UnchainedLabsLunaticParser,
)
from allotropy.parsers.utils.timestamp_parser import TimestampParser
from allotropy.parsers.vendor_parser import VendorParser


class Vendor(Enum):
    AGILENT_GEN5 = "AGILENT_GEN5"
    AGILENT_GEN5_IMAGE = "AGILENT_GEN5_IMAGE"
    AGILENT_OPENLAB_CDS = "AGILENT_OPENLAB_CDS"
    AGILENT_TAPESTATION_ANALYSIS = "AGILENT_TAPESTATION_ANALYSIS"
    APPBIO_ABSOLUTE_Q = "APPBIO_ABSOLUTE_Q"
    APPBIO_QUANTSTUDIO = "APPBIO_QUANTSTUDIO"
    APPBIO_QUANTSTUDIO_DESIGNANDANALYSIS = "APPBIO_QUANTSTUDIO_DESIGNANDANALYSIS"
    BENCHLING_EMPOWER = "BENCHLING_EMPOWER"
    BECKMAN_COULTER_BIOMEK = "BECKMAN_COULTER_BIOMEK"
    BECKMAN_ECHO_PLATE_REFORMAT = "BECKMAN_ECHO_PLATE_REFORMAT"
    BMG_LABTECH_SMART_CONTROL = "BMG_LABTECH_SMART_CONTROL"
    BMG_MARS = "BMG_MARS"
    BECKMAN_PHARMSPEC = "BECKMAN_PHARMSPEC"
    BECKMAN_VI_CELL_BLU = "BECKMAN_VI_CELL_BLU"
    BECKMAN_VI_CELL_XR = "BECKMAN_VI_CELL_XR"
    BD_BIOSCIENCES_FACSDIVA = "BD_BIOSCIENCES_FACSDIVA"
    BIORAD_BIOPLEX = "BIORAD_BIOPLEX"
    CFXMAESTRO = "CFXMAESTRO"
    CHEMOMETEC_NC_VIEW = "CHEMOMETEC_NC_VIEW"
    CHEMOMETEC_NUCLEOVIEW = "CHEMOMETEC_NUCLEOVIEW"
    CTL_IMMUNOSPOT = "CTL_IMMUNOSPOT"
    CYTIVA_BIACORE_T200_CONTROL = "CYTIVA_BIACORE_T200_CONTROL"
    CYTIVA_UNICORN = "CYTIVA_UNICORN"
    EXAMPLE_WEYLAND_YUTANI = "EXAMPLE_WEYLAND_YUTANI"
    FLOWJO = "FLOWJO"
    LUMINEX_XPONENT = "LUMINEX_XPONENT"
    MABTECH_APEX = "MABTECH_APEX"
    METHODICAL_MIND = "METHODICAL_MIND"
    MOLDEV_SOFTMAX_PRO = "MOLDEV_SOFTMAX_PRO"
    MSD_WORKBENCH = "MSD_WORKBENCH"
    REVVITY_MATRIX = "REVVITY_MATRIX"
    NOVABIO_FLEX2 = "NOVABIO_FLEX2"
    PERKIN_ELMER_ENVISION = "PERKIN_ELMER_ENVISION"
    QIACUITY_DPCR = "QIACUITY_DPCR"
    REVVITY_KALEIDO = "REVVITY_KALEIDO"
    ROCHE_CEDEX_BIOHT = "ROCHE_CEDEX_BIOHT"
    ROCHE_CEDEX_HIRES = "ROCHE_CEDEX_HIRES"
    TECAN_MAGELLAN = "TECAN_MAGELLAN"
    BENCHLING_CHROMELEON = "BENCHLING_CHROMELEON"
    THERMO_FISHER_GENESYS30 = "THERMO_FISHER_GENESYS30"
    THERMO_FISHER_GENESYS_ON_BOARD = "THERMO_FISHER_GENESYS_ON_BOARD"
    THERMO_FISHER_NANODROP_8000 = "THERMO_FISHER_NANODROP_8000"
    THERMO_FISHER_NANODROP_EIGHT = "THERMO_FISHER_NANODROP_EIGHT"
    THERMO_FISHER_NANODROP_ONE = "THERMO_FISHER_NANODROP_ONE"
    THERMO_FISHER_QUBIT4 = "THERMO_FISHER_QUBIT4"
    THERMO_FISHER_QUBIT_FLEX = "THERMO_FISHER_QUBIT_FLEX"
    THERMO_FISHER_VISIONLITE = "THERMO_FISHER_VISIONLITE"
    THERMO_SKANIT = "THERMO_SKANIT"
    UNCHAINED_LABS_LUNATIC = "UNCHAINED_LABS_LUNATIC"

    @property
    def display_name(self) -> str:
        return self.get_parser().DISPLAY_NAME

    @property
    def release_state(self) -> ReleaseState:
        return self.get_parser().RELEASE_STATE

    @property
    def supported_extensions(self) -> list[str]:
        return [
            ext.strip().lower()
            for ext in self.get_parser().SUPPORTED_EXTENSIONS.split(",")
        ]

    @property
    def asm_versions(self) -> list[str]:
        # NOTE: this is a list because soon parsers will support multiple schemas as they are upgraded.
        manifests = [
            Path(manifest) for manifest in [self.get_parser()._get_mapper().MANIFEST]
        ]
        return ["/".join(manifest.parts[-4:-1]).split(".")[0] for manifest in manifests]

    @property
    def technique(self) -> str:
        techniques = [
            Path(manifest).stem
            for manifest in [self.get_parser()._get_mapper().MANIFEST]
        ]
        if not all(tech == techniques[0] for tech in techniques):
            msg = f"Parser {self} supports multiple technique types, if this is expected please update logic."
            raise AssertionError(msg)
        technique = techniques[0].replace("-", " ").title()
        return {
            "Dpcr": "dPCR",
            "Qpcr": "qPCR",
        }.get(technique, technique)

    def get_parser(
        self, default_timezone: tzinfo | None = None
    ) -> VendorParser[Any, Any]:
        timestamp_parser = TimestampParser(default_timezone)
        return _VENDOR_TO_PARSER[self](timestamp_parser)


_VENDOR_TO_PARSER: dict[Vendor, type[VendorParser[Any, Any]]] = {
    Vendor.AGILENT_GEN5: AgilentGen5Parser,
    Vendor.AGILENT_GEN5_IMAGE: AgilentGen5ImageParser,
    Vendor.AGILENT_OPENLAB_CDS: AgilentOpenLabCDSParser,
    Vendor.AGILENT_TAPESTATION_ANALYSIS: AgilentTapestationAnalysisParser,
    Vendor.APPBIO_ABSOLUTE_Q: AppbioAbsoluteQParser,
    Vendor.APPBIO_QUANTSTUDIO: AppBioQuantStudioParser,
    Vendor.APPBIO_QUANTSTUDIO_DESIGNANDANALYSIS: AppBioQuantStudioDesignandanalysisParser,
    Vendor.BECKMAN_COULTER_BIOMEK: BeckmanCoulterBiomekParser,
    Vendor.BECKMAN_ECHO_PLATE_REFORMAT: BeckmanEchoPlateReformatParser,
    Vendor.BECKMAN_PHARMSPEC: PharmSpecParser,
    Vendor.BECKMAN_VI_CELL_BLU: ViCellBluParser,
    Vendor.BECKMAN_VI_CELL_XR: ViCellXRParser,
    Vendor.BENCHLING_EMPOWER: BenchlingEmpowerParser,
    Vendor.BIORAD_BIOPLEX: BioradBioplexParser,
    Vendor.BMG_LABTECH_SMART_CONTROL: BmgLabtechSmartControlParser,
    Vendor.BMG_MARS: BmgMarsParser,
    Vendor.CFXMAESTRO: CfxmaestroParser,
    Vendor.CHEMOMETEC_NC_VIEW: ChemometecNcViewParser,
    Vendor.CHEMOMETEC_NUCLEOVIEW: ChemometecNucleoviewParser,
    Vendor.CTL_IMMUNOSPOT: CtlImmunospotParser,
    Vendor.CYTIVA_BIACORE_T200_CONTROL: CytivaBiacoreT200ControlParser,
    Vendor.CYTIVA_UNICORN: CytivaUnicornParser,
    Vendor.EXAMPLE_WEYLAND_YUTANI: ExampleWeylandYutaniParser,
    Vendor.FLOWJO: FlowjoParser,
    Vendor.BD_BIOSCIENCES_FACSDIVA: BDFACSDivaParser,
    Vendor.LUMINEX_XPONENT: LuminexXponentParser,
    Vendor.MABTECH_APEX: MabtechApexParser,
    Vendor.METHODICAL_MIND: MethodicalMindParser,
    Vendor.MOLDEV_SOFTMAX_PRO: SoftmaxproParser,
    Vendor.MSD_WORKBENCH: MSDWorkbenchParser,
    Vendor.REVVITY_MATRIX: RevvityMatrixParser,
    Vendor.NOVABIO_FLEX2: NovaBioFlexParser,
    Vendor.PERKIN_ELMER_ENVISION: PerkinElmerEnvisionParser,
    Vendor.QIACUITY_DPCR: QiacuitydPCRParser,
    Vendor.REVVITY_KALEIDO: KaleidoParser,
    Vendor.ROCHE_CEDEX_BIOHT: RocheCedexBiohtParser,
    Vendor.ROCHE_CEDEX_HIRES: RocheCedexHiResParser,
    Vendor.TECAN_MAGELLAN: TecanMagellanParser,
    Vendor.BENCHLING_CHROMELEON: BenchlingChromeleonParser,
    Vendor.THERMO_FISHER_GENESYS30: ThermoFisherGenesys30Parser,
    Vendor.THERMO_FISHER_GENESYS_ON_BOARD: ThermoFisherGenesysOnBoardParser,
    Vendor.THERMO_FISHER_NANODROP_8000: Nanodrop8000Parser,
    Vendor.THERMO_FISHER_NANODROP_EIGHT: NanodropEightParser,
    Vendor.THERMO_FISHER_NANODROP_ONE: ThermoFisherNanodropOneParser,
    Vendor.THERMO_FISHER_QUBIT4: ThermoFisherQubit4Parser,
    Vendor.THERMO_FISHER_QUBIT_FLEX: ThermoFisherQubitFlexParser,
    Vendor.THERMO_FISHER_VISIONLITE: ThermoFisherVisionliteParser,
    Vendor.THERMO_SKANIT: ThermoSkanItParser,
    Vendor.UNCHAINED_LABS_LUNATIC: UnchainedLabsLunaticParser,
}


def get_table_contents() -> str:
    contents = """The parsers follow maturation levels of: Recommended, Candidate Release, Working Draft.

* Recommended - "General Availability" - the parser has good coverage of input formats, and exports the majority of data from source files.
** Note that while we judge release status based on observed use cases, it is still a judgement call - it is still possible that we miss some cases.
** If you have an example case for an instrument that is not supported or discover a bug, please https://github.com/Benchling-Open-Source/allotropy/issues[open an issue] with sample data and will work to add support!
* Candidate Release - "Limited Availability" - the parser exports correct data for supported cases, but may be missing some functionality, including:
** May not handle all possible input formats from the target instrument software (because they have not been seen before).
** May not export all available data from the input, either because it cannot be supported yet by ASM, or because we have not determined how to add it.
** Increased likelihood of bugs due to lack of "bake time" for discovering issues.
* Working Draft - "Beta" - in development, not ready for production use:
** May be missing enough sample data for us to be confident about correctness of parser
** May be in-progress, with signifcant known TODO work

'''
"""
    table_data: defaultdict[str, list[Vendor]] = defaultdict(list)

    for vendor in Vendor:
        if "example" in str(vendor).lower():
            continue
        table_data[vendor.technique].append(vendor)

    contents += '[cols="4*^.^"]\n'
    contents += "|===\n"
    contents += (
        "|Instrument Category|Instrument Software|Release Status|Exported ASM Schema\n"
    )
    for technique in sorted(table_data):
        vendors = table_data[technique]
        contents += f".{len(vendors)}+|{technique}|{vendors[0].display_name}|{vendors[0].release_state}|{vendors[0].asm_versions[0]}\n"
        for vendor in vendors[1:]:
            contents += f"|{vendor.display_name}|{vendor.release_state}|{vendor.asm_versions[0]}\n"
    contents += "|==="

    return contents


def update_supported_instruments() -> None:
    with open(Path(ROOT_DIR, "SUPPORTED_INSTRUMENT_SOFTWARE.adoc"), "w") as f:
        f.write(get_table_contents())
