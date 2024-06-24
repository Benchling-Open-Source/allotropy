from allotropy.allotrope.schema_parser.generate_schemas import generate_schemas


def test_generate_schemas_runs_to_completion() -> None:
    models_changed = generate_schemas(dry_run=True)
    assert (
        not models_changed
    ), f"Expected no models files to have changed by generate-schemas script, found changes in: {models_changed}.\nPlease run 'hatch run scripts:generate-schemas' and validate the changes."
