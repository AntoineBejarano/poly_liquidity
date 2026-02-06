"""
Utilities for Gamma API (Polymarket) compatibility.

- parse_clob_token_ids: robust parsing of clobTokenIds (string/list/dict).
  Contract: primary always string|null; selection_hint one of primary_yes|single|multi|none.
"""
from typing import Any, Dict, List, Optional, Literal
import json
import logging

logger = logging.getLogger(__name__)

SelectionHint = Literal["primary_yes", "single", "multi", "none"]


def parse_clob_token_ids(raw: Any) -> Dict[str, Any]:
    """
    Parse clobTokenIds from Gamma market payload.
    
    Gamma OpenAPI: clobTokenIds is string (may be JSON). Can be:
    - string: JSON of list [id1, id2] or dict {"YES": id1, "NO": id2}
    - list: [id1, id2] — NO assumption list[0]=YES; treat as tokens without semantics
    - dict: {"YES": id1, "NO": id2} — keys case-insensitive
    
    Contract:
    - primary: string | null — token to use for metrics per policy
    - selection_hint: "primary_yes" | "single" | "multi" | "none"
    - primary_yes, primary_no: only if inferrable from dict with YES/NO keys
    - clob_token_ids_all: when list (no semantics)
    - clob_token_ids_by_key: when dict
    """
    result: Dict[str, Any] = {
        "primary_yes": None,
        "primary_no": None,
        "clob_token_ids_all": None,
        "clob_token_ids_by_key": None,
        "selection_hint": "none",
        "primary": None,
    }
    
    if raw is None:
        return result
    
    # Parse string (may be JSON)
    if isinstance(raw, str):
        raw = raw.strip()
        if not raw:
            return result
        if raw.startswith("[") or raw.startswith("{"):
            try:
                raw = json.loads(raw)
            except json.JSONDecodeError:
                logger.debug("Could not parse clobTokenIds string as JSON: %s", raw[:50])
                return result
        else:
            return result
    
    # List: expose as clob_token_ids_all, no YES/NO semantics
    if isinstance(raw, list):
        ids = [str(x) for x in raw if x is not None and str(x).strip()]
        result["clob_token_ids_all"] = ids
        if len(ids) == 0:
            result["selection_hint"] = "none"
        elif len(ids) == 1:
            result["selection_hint"] = "single"
            result["primary"] = ids[0]
        else:
            result["selection_hint"] = "multi"
            # Optional: use first token for sampling (front shows badge "Multi (sampled)")
            result["primary"] = ids[0]
        return result
    
    # Dict: try to infer YES/NO
    if isinstance(raw, dict):
        by_key: Dict[str, str] = {}
        for k, v in raw.items():
            if v is not None and str(v).strip():
                by_key[str(k)] = str(v)
        result["clob_token_ids_by_key"] = by_key if by_key else None
        
        # Case-insensitive YES/NO lookup
        yes_val = None
        no_val = None
        for k, v in by_key.items():
            k_upper = k.upper()
            if k_upper == "YES":
                yes_val = v
            elif k_upper == "NO":
                no_val = v
        
        if yes_val is not None or no_val is not None:
            result["primary_yes"] = yes_val
            result["primary_no"] = no_val
            if yes_val:
                result["selection_hint"] = "primary_yes"
                result["primary"] = yes_val
            else:
                # Tiene estructura YES/NO (aunque solo NO); hint=primary_yes, primary=NO
                result["selection_hint"] = "primary_yes"
                result["primary"] = no_val
        elif len(by_key) == 1:
            result["selection_hint"] = "single"
            result["primary"] = list(by_key.values())[0]
        elif len(by_key) >= 2:
            result["selection_hint"] = "multi"
            result["primary"] = list(by_key.values())[0]
        return result
    
    return result
