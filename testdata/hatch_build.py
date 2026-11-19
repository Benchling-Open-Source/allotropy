"""Build hook that bundles allotropy's parser test data into the wheel."""

from pathlib import Path
from typing import Any

from hatchling.builders.hooks.plugin.interface import BuildHookInterface

MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024
DATA_PACKAGE_PATH = "allotropy_testdata/data/parsers"


class AllotropyTestDataBuildHook(BuildHookInterface):
    """Force-includes tests/parsers/*/testdata/** except files above the size limit."""

    PLUGIN_NAME = "custom"

    def initialize(
        self,
        version: str,  # noqa: ARG002
        build_data: dict[str, Any],
    ) -> None:
        parsers_dir = Path(self.root).parent / "tests" / "parsers"
        if not parsers_dir.is_dir():
            msg = f"Test data directory not found: {parsers_dir}"
            raise FileNotFoundError(msg)

        excluded = []
        for path in sorted(parsers_dir.glob("*/testdata/**/*")):
            if not path.is_file() or path.name.startswith("."):
                continue
            relative = path.relative_to(parsers_dir)
            if path.stat().st_size > MAX_FILE_SIZE_BYTES:
                excluded.append(relative.as_posix())
                continue
            build_data["force_include"][
                str(path)
            ] = f"{DATA_PACKAGE_PATH}/{relative.as_posix()}"

        for name in excluded:
            self.app.display_info(f"Excluded (over size limit): {name}")
