import pytest

from allotropy.allotrope.models.shared.definitions.definitions import TDatacubeData


def test_data_cube_data() -> None:
    cube = TDatacubeData(
        dimensions=[["A", "B"]],
        measures=[[1.0, None]],
    )
    assert cube.dimensions == [["A", "B"]]
    assert cube.measures == [[1.0, None]]


def test_data_cube_data_invalid_when_measures_and_points_missing() -> None:
    with pytest.raises(ValueError):
        TDatacubeData(dimensions=[["A", "B"]])


def test_data_cube_data_valid_when_points_or_measures_are_empty() -> None:
    cube = TDatacubeData(dimensions=[["A", "B"]], measures=[])
    assert cube.measures == []
    assert cube.points is None

    cube = TDatacubeData(dimensions=[["A", "B"]], points=[])
    assert cube.measures is None
    assert cube.points == []
