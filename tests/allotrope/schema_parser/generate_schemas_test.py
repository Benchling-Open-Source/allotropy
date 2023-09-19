from pathlib import Path

from allotropy.allotrope.schema_parser.generate_schemas import generate_schemas


def test_generate_schemas_runs_to_completion() -> None:
    root_dir = Path(__file__).parent.parent.parent.parent
    assert generate_schemas(root_dir) == 7
