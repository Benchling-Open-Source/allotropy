from pathlib import Path

from allotropy.allotrope.schema_parser.generate_schemas import generate_schemas


def test_generate_schemas_runs_to_completion() -> None:
    root_dir = Path(__file__).parent.parent.parent.parent
    models_changed = generate_schemas(root_dir, dry_run=True)
    assert (
        not models_changed
    ), f"Expected no models files to have changed by generate-schemas script, found changes in: {models_changed}.\nPlease run 'hatch run scripts:generate-schemas' and validate the changes."
