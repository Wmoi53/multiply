"""Enable ``python -m backtest ...``."""

from __future__ import annotations

import sys

from .report import main

if __name__ == "__main__":
    sys.exit(main())
