import pytest

from allotropy.allotrope.models.shared.definitions.definitions import TDatacubeData
from allotropy.exceptions import AllotropeConversionError


def test_data_cube_data() -> None:
    cube = TDatacubeData(
        dimensions=[["A", "B"]],
        measures=[[1.0, None]],
    )
    assert cube.dimensions == [["A", "B"]]
    assert cube.measures == [[1.0, None]]

    cube = TDatacubeData(
        dimensions=[[1.0, 2.0]],
        points=[[True, False]],
    )
    assert cube.dimensions == [[1.0, 2.0]]
    assert cube.points == [[True, False]]


def test_data_cube_data_oneof_post_init() -> None:
    with pytest.raises(
        AllotropeConversionError,
        match="Exactly one of measures or points must be set on a datacube.",
    ):
        TDatacubeData(dimensions=[["A", "B"]])

    with pytest.raises(
        AllotropeConversionError,
        match="Exactly one of measures or points must be set on a datacube.",
    ):
        TDatacubeData(dimensions=[["A", "B"]], measures=[], points=[])


def test_data_cube_data_oneof_post_init_empty_list_ok() -> None:
    cube = TDatacubeData(dimensions=[["A", "B"]], measures=[])
    assert cube.measures == []
    assert cube.points is None

    cube = TDatacubeData(dimensions=[["A", "B"]], points=[])
    assert cube.measures is None
    assert cube.points == []
