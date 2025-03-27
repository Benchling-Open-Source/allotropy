from allotropy.calcdocs.extractor import Element, Extractor
from allotropy.parsers.appbio_quantstudio_designandanalysis.structure.generic.structure import (
    WellItem,
)


class AppbioQuantstudioDAExtractor(Extractor[WellItem]):
    @classmethod
    def to_element(cls, well_item: WellItem) -> Element:
        return Element(
            uuid=well_item.uuid,
            data={
                "uuid": well_item.uuid,
                "identifier": well_item.identifier,
                "target_dna_description": well_item.target_dna_description,
                "sample_identifier": well_item.sample_identifier,
                "reporter_dye_setting": well_item.reporter_dye_setting,
                "well_location_identifier": well_item.well_location_identifier,
                "quencher_dye_setting": well_item.quencher_dye_setting,
                "sample_role_type": (
                    well_item.sample_role_type.value
                    if well_item.sample_role_type is not None
                    else None
                ),
                "cycle_threshold_value_setting": well_item.result.cycle_threshold_value_setting,
                "cycle_threshold_result": well_item.result.cycle_threshold_result,
                "automatic_cycle_threshold_enabled_setting": well_item.result.automatic_cycle_threshold_enabled_setting,
                "automatic_baseline_determination_enabled_setting": well_item.result.automatic_baseline_determination_enabled_setting,
                "normalized_reporter_result": well_item.result.normalized_reporter_result,
                "baseline_corrected_reporter_result": well_item.result.baseline_corrected_reporter_result,
                "baseline_determination_start_cycle_setting": well_item.result.baseline_determination_start_cycle_setting,
                "baseline_determination_end_cycle_setting": well_item.result.baseline_determination_end_cycle_setting,
                "genotyping_determination_result": well_item.result.genotyping_determination_result,
                "genotyping_determination_method_setting": well_item.result.genotyping_determination_method_setting,
                "quantity": well_item.result.quantity,
                "quantity_mean": well_item.result.quantity_mean,
                "quantity_sd": well_item.result.quantity_sd,
                "ct_mean": well_item.result.ct_mean,
                "eq_ct_mean": well_item.result.eq_ct_mean,
                "adj_eq_ct_mean": well_item.result.adj_eq_ct_mean,
                "ct_sd": well_item.result.ct_sd,
                "ct_se": well_item.result.ct_se,
                "delta_ct_mean": well_item.result.delta_ct_mean,
                "delta_ct_se": well_item.result.delta_ct_se,
                "delta_ct_sd": well_item.result.delta_ct_sd,
                "delta_delta_ct": well_item.result.delta_delta_ct,
                "rq": well_item.result.rq,
                "rq_min": well_item.result.rq_min,
                "rq_max": well_item.result.rq_max,
                "rn_mean": well_item.result.rn_mean,
                "rn_sd": well_item.result.rn_sd,
                "y_intercept": well_item.result.y_intercept,
                "r_squared": well_item.result.r_squared,
                "slope": well_item.result.slope,
                "efficiency": well_item.result.efficiency,
                "amp_score": well_item.result.amp_score,
                "cq_conf": well_item.result.cq_conf,
            },
        )
