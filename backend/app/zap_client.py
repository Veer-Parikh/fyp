# backend/app/zap_client.py
import time
import logging
from zapv2 import ZAPv2

logger = logging.getLogger("zap-client")
logger.setLevel(logging.INFO)

ZAP_API_KEY = "changeme_if_you_use_auth"     # Optional
ZAP_PROXY = "http://127.0.0.1:8090"          # Your local ZAP

zap = ZAPv2(apikey=ZAP_API_KEY, proxies={"http": ZAP_PROXY, "https": ZAP_PROXY})

# ---------------------------------------------------------
# SAFE HELPERS — TIMEOUT PROTECTED (prevents hangs forever)
# ---------------------------------------------------------

def _wait_for_spider(spider_id, timeout=60):
    """ Wait for spider with timeout. """
    start = time.time()
    while True:
        try:
            progress = int(zap.spider.status(spider_id))
        except:
            progress = 0

        if progress >= 100:
            return "ok"

        if time.time() - start > timeout:
            return f"timeout_after_{timeout}s (stuck={progress}%)"

        time.sleep(1)


def _wait_for_passive(timeout=60):
    """ Wait for passive scan queue to drain. """
    start = time.time()
    while True:
        try:
            remaining = int(zap.pscan.records_to_scan)
        except:
            remaining = 0

        if remaining == 0:
            return "ok"

        if time.time() - start > timeout:
            return f"timeout_after_{timeout}s (remaining={remaining})"

        time.sleep(1)


def _wait_for_active(scan_id, timeout=180):
    """ Wait for active scan to complete. """
    start = time.time()
    while True:
        try:
            progress = int(zap.ascan.status(scan_id))
        except:
            progress = 0

        if progress >= 100:
            return "ok"

        if time.time() - start > timeout:
            return f"timeout_after_{timeout}s (stuck={progress}%)"

        time.sleep(2)


# ---------------------------------------------------------
# MAIN FUNCTION — FAST, NORMAL, DEEP (no-hang implementation)
# ---------------------------------------------------------

def run_zap_scan(target: str, spider_only: bool = True, mode: str = "fast"):
    """
    FAST  → Spider only (1–3 sec)
    NORMAL → Spider + Passive (adds ~2-10 sec)
    DEEP  → Spider + Passive + Active Scan (max 3 min, timeout-safe)
    """
    logger.info(f"Starting ZAP scan mode={mode} for {target}")

    # ------------------
    # 1. Spider
    # ------------------
    spider_id = zap.spider.scan(target)
    spider_status = _wait_for_spider(spider_id)

    logger.info(f"Spider finished: {spider_status}")

    # ------------------
    # FAST MODE: STOP HERE
    # ------------------
    if mode == "fast" or spider_only:
        alerts = zap.core.alerts(baseurl=target)
        return {
            "mode": "fast",
            "spider_status": spider_status,
            "alerts": alerts,
            "summary": _summarize(alerts),
        }

    # ------------------
    # 2. PASSIVE SCAN WAIT (NORMAL)
    # ------------------
    passive_status = _wait_for_passive()
    logger.info(f"Passive scan status: {passive_status}")

    if mode == "normal":
        alerts = zap.core.alerts(baseurl=target)
        return {
            "mode": "normal",
            "spider_status": spider_status,
            "passive_status": passive_status,
            "alerts": alerts,
            "summary": _summarize(alerts),
        }

    # ------------------
    # 3. ACTIVE SCAN (DEEP MODE)
    # ------------------
    scan_id = zap.ascan.scan(target)
    active_status = _wait_for_active(scan_id)

    logger.info(f"Active scan status: {active_status}")

    alerts = zap.core.alerts(baseurl=target)

    return {
        "mode": "deep",
        "spider_status": spider_status,
        "passive_status": passive_status,
        "active_status": active_status,
        "alerts": alerts,
        "summary": _summarize(alerts),
    }


# ---------------------------------------------------------
# Summary helper
# ---------------------------------------------------------
def _summarize(alerts):
    """ Summarize ZAP alerts into counts. """
    counts = {"High": 0, "Medium": 0, "Low": 0, "Info": 0}
    for a in alerts:
        counts[a.get("risk", "Info")] = counts.get(a.get("risk"), 0) + 1

    return {
        "total": sum(counts.values()),
        "counts": counts
    }
