#!/usr/bin/env python3
"""Publish both allotropy and allotropy-testdata packages to PyPI."""

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
    """Publish both packages."""
    # Get any additional args (like --repo for test PyPI)
    extra_args = sys.argv[1:]

    print("Publishing allotropy packages...")
    print("⚠️  Make sure you've built both packages first with build_all.py")

    response = input("\nContinue with publish? (yes/no): ")
    if response.lower() not in ("yes", "y"):
        print("Aborted.")
        sys.exit(0)

    # Publish main allotropy package
    print("\n📤 Publishing allotropy...")
    run_command(["hatch", "publish", *extra_args], ROOT)

    # Publish allotropy-testdata package
    print("\n📤 Publishing allotropy-testdata...")
    run_command(["hatch", "publish", *extra_args], ROOT / "testdata")

    print("\n✅ Successfully published both packages!")


if __name__ == "__main__":
    main()
