from allotropy.parsers.cytiva_biacore_t200_evaluation.cytiva_biacore_t200_evaluation_data_creator import (
    _extract_kinetic_parameter_error,
)
from allotropy.parsers.cytiva_biacore_t200_evaluation.cytiva_biacore_t200_evaluation_structure import (
    CalculatedValue,
    FitQuality,
    KineticResult,
    Parameter,
)


def test_extract_kinetic_parameter_error_does_not_mix_kd_and_kd_constant() -> None:
    # Kinetics fit: "kd" is the dissociation rate, the calculated "Kd_M" has no error.
    kinetics = KineticResult(
        fit_quality=FitQuality(None, None),
        parameters=[
            Parameter("ka", 1.0e5, 1585.25, "M-1s-1"),
            Parameter("kd", 2.8e-3, 6.06e-6, "s-1"),
        ],
        calculated=[CalculatedValue("Kd_M", 5.0e-9, "M")],
    )
    assert _extract_kinetic_parameter_error(kinetics, ["kd", "koff"]) == 6.06e-6
    assert _extract_kinetic_parameter_error(kinetics, ["KD", "Kd_M"]) is None

    # Affinity fit: only the dissociation constant "KD" is reported, with its error.
    affinity = KineticResult(
        fit_quality=FitQuality(None, None),
        parameters=[Parameter("rmax", 100.0, 1.46, "RU")],
        calculated=[CalculatedValue("KD", 1.0e-6, "M", 3.63e-7)],
    )
    assert _extract_kinetic_parameter_error(affinity, ["KD", "Kd_M"]) == 3.63e-7
    assert _extract_kinetic_parameter_error(affinity, ["kd", "koff"]) is None
