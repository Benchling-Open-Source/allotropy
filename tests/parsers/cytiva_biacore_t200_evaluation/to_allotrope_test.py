from pathlib import Path
from typing import Any
from unittest.mock import patch

from allotropy.parser_factory import Vendor

# Import the original functions before patching to avoid recursion
from allotropy.parsers.cytiva_biacore_t200_evaluation.cytiva_biacore_t200_evaluation_data_creator import (
    _get_sensorgram_datacube as _original_get_sensorgram_datacube,
    create_measurement_groups as _original_create_measurement_groups,
)
from tests.to_allotrope_test import ParserTest


def _reduce_sensorgram_for_testing(
    sensorgram_df: Any, *, cycle: Any, flow_cell: Any
) -> Any:
    """
    Patched version of _get_sensorgram_datacube that reduces data for testing.
    """
    # Reduce the dataframe to 6 points if it's larger
    max_points = 6
    if sensorgram_df is not None and len(sensorgram_df) > max_points:
        # Take evenly spaced points to maintain time distribution
        step = len(sensorgram_df) // max_points
        indices = [i * step for i in range(max_points)]
        sensorgram_df = sensorgram_df.iloc[indices].reset_index(drop=True)

    # Call the original function with the reduced dataframe
    return _original_get_sensorgram_datacube(
        sensorgram_df, cycle=cycle, flow_cell=flow_cell
    )


def _reduce_cycles_for_testing(data: Any) -> Any:
    """
    Patched version of create_measurement_groups that reduces cycles for testing.
    """
    # Limit to first 4 cycles for testing
    max_cycles = 4
    if hasattr(data, "cycle_data") and len(data.cycle_data) > max_cycles:
        # Import the Data class to create a new instance
        from allotropy.parsers.cytiva_biacore_t200_evaluation.cytiva_biacore_t200_evaluation_structure import (
            Data,
        )

        # Create a new Data instance with reduced cycles
        reduced_data = Data(
            run_metadata=data.run_metadata,
            chip_data=data.chip_data,
            system_information=data.system_information,
            total_cycles=max_cycles,
            cycle_data=data.cycle_data[:max_cycles],
            dip=data.dip,
            kinetic_analysis=data.kinetic_analysis,
            sample_data=data.sample_data,
            application_template_details=data.application_template_details,
        )
        data = reduced_data

    # Call the original function with the reduced data
    return _original_create_measurement_groups(data)


class TestParser(ParserTest):
    VENDOR = Vendor.CYTIVA_BIACORE_T200_EVALUATION

    @patch(
        "allotropy.parsers.cytiva_biacore_t200_evaluation.cytiva_biacore_t200_evaluation_data_creator.create_measurement_groups",
        side_effect=_reduce_cycles_for_testing,
    )
    @patch(
        "allotropy.parsers.cytiva_biacore_t200_evaluation.cytiva_biacore_t200_evaluation_data_creator._get_sensorgram_datacube",
        side_effect=_reduce_sensorgram_for_testing,
    )
    def test_positive_cases(
        self,
        _mock_sensorgram: Any,
        _mock_cycles: Any,
        test_file_path: Path,
        *,
        overwrite: bool,
        warn_unread_keys: bool,
    ) -> None:
        """Override the test method with cycle and sensorgram data reduction patches."""
        return super().test_positive_cases(
            test_file_path, overwrite=overwrite, warn_unread_keys=warn_unread_keys
        )
