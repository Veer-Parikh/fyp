# backend/app/utils.py
from typing import Dict, Any
import math

# tweakable risk weights
ZAP_SEV = {"High": 9.0, "Medium": 5.0, "Low": 2.0, "Info": 0.5}
PORT_RISK = {21: 6.0, 22: 4.0, 23: 7.0, 80: 2.0, 443: 1.0, 3306: 6.0, 3389: 7.0}

def compute_risk(nmap_result: Dict[str, Any], zap_result: Dict[str, Any]) -> float:
    """
    Compute a normalized risk score between 0 and 10.
    - uses counts from ZAP and open ports in Nmap
    - result is rounded to 2 decimals
    """
    score = 0.0
    try:
        counts = zap_result.get("summary", {}).get("counts", {})
        for k, v in counts.items():
            weight = ZAP_SEV.get(k, 1.0)
            score += weight * v
    except Exception:
        pass

    try:
        for host in nmap_result.get("hosts", []):
            for p in host.get("ports", []):
                if p.get("state") == "open":
                    score += PORT_RISK.get(p.get("port", 0), 1.0)
    except Exception:
        pass

    # Normalize: soft cap using log to avoid extreme values dominating
    normalized_raw = score / 10.0
    normalized = max(0.0, min(10.0, normalized_raw))
    return round(normalized, 2)
