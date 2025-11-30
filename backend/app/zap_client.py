# backend/app/zap_client.py
import time
import logging
from zapv2 import ZAPv2

logger = logging.getLogger("zap-client")
logger.setLevel(logging.INFO)

ZAP_PROXY = "http://127.0.0.1:8090"
ZAP_API_KEY = None  # Optional

zap = ZAPv2(
    apikey=ZAP_API_KEY,
    proxies={"http": ZAP_PROXY, "https": ZAP_PROXY}
)

# ---------------------------------------------------------
# SAFE HELPERS — PROTECT FROM HANGS
# ---------------------------------------------------------

def _wait_for_spider(spider_id, timeout=60):
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
# MAIN — FAST / NORMAL / EXTREME
# ---------------------------------------------------------

def run_zap_scan(target: str, mode="fast", crawler_urls=None):
    logger.info(f"Starting ZAP scan mode={mode} for {target}")

    # Feed crawler URLs first (optional)
    if crawler_urls:
        for u in crawler_urls:
            try:
                zap.urlopen(u)
            except:
                pass

    # 1. Spider
    spider_id = zap.spider.scan(target)
    spider_status = _wait_for_spider(spider_id)

    logger.info(f"Spider finished: {spider_status}")

    # FAST MODE → STOP
    if mode == "fast":
        alerts = zap.core.alerts(baseurl=target)
        return {
            "mode": "fast",
            "spider_status": spider_status,
            "alerts": alerts,
            "summary": _summarize(alerts),
        }

    # 2. PASSIVE SCAN
    passive_status = _wait_for_passive()
    logger.info(f"Passive scan finished: {passive_status}")

    if mode == "normal":
        alerts = zap.core.alerts(baseurl=target)
        return {
            "mode": "normal",
            "spider_status": spider_status,
            "passive_status": passive_status,
            "alerts": alerts,
            "summary": _summarize(alerts),
        }

    # 3. EXTREME MODE → Active Scan
    ascan_id = zap.ascan.scan(target)
    active_status = _wait_for_active(ascan_id)

    logger.info(f"Active scan finished: {active_status}")

    alerts = zap.core.alerts(baseurl=target)
    return {
        "mode": "extreme",
        "spider_status": spider_status,
        "passive_status": passive_status,
        "active_status": active_status,
        "alerts": alerts,
        "summary": _summarize(alerts),
    }

# ---------------------------------------------------------
# SUMMARY
# ---------------------------------------------------------

def _summarize(alerts):
    counts = {"High": 0, "Medium": 0, "Low": 0, "Info": 0}
    for a in alerts:
        risk = a.get("risk", "Info")
        counts[risk] = counts.get(risk, 0) + 1
    return {"total": sum(counts.values()), "counts": counts}
