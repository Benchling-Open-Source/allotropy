#!/usr/bin/env python3
"""Build both allotropy and allotropy-testdata packages.

The two distributions are versioned independently.
"""

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
    # Wheel only: an sdist would not contain the test data.
    run_command(["hatch", "build", "--clean", "-t", "wheel"], ROOT / "testdata")

    print("\n✅ Successfully built both packages!")
    for dist_dir in (ROOT / "dist", ROOT / "testdata" / "dist"):
        for artifact in sorted(dist_dir.glob("*")):
            print(f"  - {artifact} ({artifact.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
