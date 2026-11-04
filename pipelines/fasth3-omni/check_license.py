#!/usr/bin/env python3
"""Gate FastH3 batch scripts on explicit license acceptance."""
from __future__ import annotations

import os
import sys

MSG = """
FastH3 / MiniMax-H3 requires the MiniMax H3 Community License (not Apache-2.0).
Read: pipelines/fasth3-omni/LICENSE_NOTICE.md

If you accept responsibility for territory, commercial use, and NOTICE requirements:
  export ACCEPT_MINIMAX_H3_LICENSE=1
"""


def require_acceptance() -> None:
    if os.environ.get("ACCEPT_MINIMAX_H3_LICENSE", "").strip() not in ("1", "true", "yes"):
        sys.exit(MSG.strip())


if __name__ == "__main__":
    require_acceptance()
    print("ok — ACCEPT_MINIMAX_H3_LICENSE is set")
