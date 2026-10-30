#!/usr/bin/env python3
"""Repo-local build tooling. Invoked BY PATH, never installed, never a distribution."""
import sys

from pipeline.pipeline import main

if __name__ == "__main__":
    sys.exit(main())
