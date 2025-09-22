# backend/hd_config.py
"""Module: backend/hd_config.py
Contract: Pure env reader for HD integration; never exposes secret values; no runtime imports.
Determinism: Pure, no IO/network; stable field ordering and output formatting.
Version: v1
"""
from __future__ import annotations
import os
from typing import Dict

REQUIRED = ("HD_API_KEY","HD_GEOCODE_KEY")
OPTIONAL = ("HD_SERVICE_TOKEN",)

def get_hd_config(check_optional: bool=False) -> Dict[str, object]:
    keys = [*REQUIRED, *OPTIONAL]
    vars_view = {k: ("set" if (os.getenv(k) not in (None, "")) else "unset") for k in keys}
    missing = [k for k in REQUIRED if vars_view[k]=="unset"]
    status = "OK (hd_config)" if not missing else f"OK (hd_config WARN: missing={','.join(missing)})"
    return {"status": status, "vars": vars_view}

