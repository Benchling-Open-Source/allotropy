#!/usr/bin/env python3
"""Build both allotropy and allotropy-testdata packages."""

from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).parent.parent


def run_command(cmd: list[str], cwd: Path) -> None:
    """Run a command and exit on failure."""
    print(f"\n{'='*60}")
    print(f"Running: {' '.join(cmd)}")
    print(f"In: {cwd}")
    print(f"{'='*60}\n")

    result = subprocess.run(cmd, cwd=cwd, check=False)  # noqa: S603
    if result.returncode != 0:
        print(f"\n❌ Command failed: {' '.join(cmd)}", file=sys.stderr)
        sys.exit(1)


def main() -> None:
    """Build both packages."""
    print("Building allotropy packages...")

    # Build main allotropy package
    print("\n📦 Building allotropy...")
    run_command(["hatch", "build", "--clean"], ROOT)

    # Build allotropy-testdata package
    print("\n📦 Building allotropy-testdata...")
    run_command(["hatch", "build", "--clean"], ROOT / "testdata")

    print("\n✅ Successfully built both packages!")
    print(f"\nBoth packages built to: {ROOT / 'dist'}")
    print("  - allotropy-0.1.116-py3-none-any.whl")
    print("  - allotropy_testdata-0.1.116-py3-none-any.whl")


if __name__ == "__main__":
    main()
