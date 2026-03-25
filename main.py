#!/usr/bin/env python3
"""兼容入口：python main.py ..."""

from pubmed_reporter.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
