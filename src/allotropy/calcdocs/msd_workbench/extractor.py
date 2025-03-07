from allotropy.calcdocs.extractor import Element, Extractor
from allotropy.parsers.msd_workbench.calculdated_data_structure import (
    CalculatedDataMeasurementStructure,
)


class MsdWorkbenchExtractor(Extractor[CalculatedDataMeasurementStructure]):
    @classmethod
    def to_element(
        cls, calc_data_structure: CalculatedDataMeasurementStructure
    ) -> Element:
        return Element(
            uuid=calc_data_structure.measurement.identifier,
            data={
                "type_": calc_data_structure.measurement.type_.value,
                "uuid": calc_data_structure.measurement.identifier,
                "luminescence": calc_data_structure.measurement.luminescence,
                "sample_identifier": calc_data_structure.measurement.sample_identifier,
                "location_identifier": calc_data_structure.measurement.location_identifier,
                "well_location_identifier": calc_data_structure.measurement.well_location_identifier,
                "well_plate_identifier": calc_data_structure.measurement.well_plate_identifier,
                "device_type": calc_data_structure.measurement.device_type,
                "detection_type": calc_data_structure.measurement.detection_type,
                "mass_concentration": calc_data_structure.measurement.mass_concentration,
                "sample_role_type": calc_data_structure.measurement.sample_role_type.value
                if calc_data_structure.measurement.sample_role_type
                else None,
                "assay_identifier": calc_data_structure.measurement.measurement_custom_info.get(
                    "assay identifier"
                )
                if calc_data_structure.measurement.measurement_custom_info
                else None,
                "adjusted_signal": calc_data_structure.adjusted_signal,
                "mean": calc_data_structure.mean,
                "adj_sig_mean": calc_data_structure.adj_sig_mean,
                "fit_statistic_rsquared": calc_data_structure.fit_statistic_rsquared,
                "cv": calc_data_structure.cv,
                "percent_recovery": calc_data_structure.percent_recovery,
                "percent_recovery_mean": calc_data_structure.percent_recovery_mean,
                "calc_concentration": calc_data_structure.calc_concentration,
                "calc_conc_mean": calc_data_structure.calc_conc_mean,
            },
        )
