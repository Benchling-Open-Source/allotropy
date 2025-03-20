from allotropy.parsers.methodical_mind.methodical_mind_reader import (
    _extract_spot_legend_spots,
)


def test_extract_spot_legend() -> None:
    lines = [
        "line1  :   value1",
        "line2  :   value2",
    ]
    updated_lines, spots = _extract_spot_legend_spots(lines)
    assert updated_lines == lines
    assert not spots

    lines = [
        "line1  :   value1",
        "Spot     :	   <>",
        "Legend   :	<1>   <8>",
        "          	   <>",
        "          	<>   <>",
        "          	   <>",
        "          	<3>   <10>",
        "          	   <>",
        "line2  :   value2",
    ]
    updated_lines, spots = _extract_spot_legend_spots(lines)
    assert updated_lines == [
        "line1  :   value1",
        "line2  :   value2",
    ]
    assert spots == [1, 3, 8, 10]
