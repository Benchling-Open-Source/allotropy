#!/usr/bin/env python3
from pathlib import Path

from allotropy.allotrope.schema_parser.generate_schemas import generate_schemas

ROOT_DIR = Path(__file__).parent.parent


if __name__ == "__main__":
    generate_schemas(ROOT_DIR)
