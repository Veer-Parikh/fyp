import subprocess
import xmltodict
from urllib.parse import urlparse
from typing import Dict, Any, List
import logging
import shlex
import json

logger = logging.getLogger("nmap-scanner")
logger.setLevel(logging.INFO)


def clean_target(target: str) -> str:
    parsed = urlparse(target)
    return parsed.hostname or target


def _extract_host_address(host_node):
    """
    Extract best IP or hostname from <address> nodes.
    Nmap sometimes gives multiple records.
    """
    try:
        addr = host_node.get("address")
        if isinstance(addr, dict):
            return addr.get("@addr", "")
        if isinstance(addr, list):
            for a in addr:
                if a.get("@addr"):
                    return a["@addr"]
    except:
        pass
    return ""


def _extract_hostname(host_node):
    """Extract visible hostname (reverse DNS) if any."""
    try:
        h = host_node.get("hostnames", {}).get("hostname", [])

        if isinstance(h, dict):  # single
            return h.get("@name", "")

        if isinstance(h, list) and len(h) > 0:
            return h[0].get("@name", "")
    except:
        pass
    return ""


def _extract_ports(host_node):
    """Return ports in FIXED report-friendly format."""
    ports_out = []
    try:
        ports = host_node.get("ports", {}).get("port", [])

        if isinstance(ports, dict):
            ports = [ports]

        for p in ports:
            ports_out.append({
                "port": int(p.get("@portid", 0)),
                "protocol": p.get("@protocol", ""),
                "state": p.get("state", {}).get("@state", ""),
                "service": p.get("service", {}).get("@name", "")
            })
    except Exception as e:
        logger.error("Port parse error: %s", e)
    return ports_out

def detect_firewall(nmap_xml) -> str:
    """
    Detects common firewall/WAF signatures from Nmap output.
    Returns string message.
    """
    raw = json.dumps(nmap_xml).lower()

    waf_rules = {
        "cloudflare": ["cloudflare", "cf-ray"],
        "akamai": ["akamai", "akamaiGHost".lower()],
        "imperva": ["incapsula", "imperva"],
        "azure": ["azure-frontdoor"],
        "sucuri": ["sucuri"],
        "f5": ["big-ip", "f5"],
        "mod_security": ["mod_security", "modsecurity"],
    }

    for waf, sigs in waf_rules.items():
        if any(sig in raw for sig in sigs):
            return f"Detected Web Firewall: {waf}"

    return "No firewall signatures detected"


def run_nmap_scan(target: str, mode: str = "fast") -> Dict[str, Any]:
    hostname = clean_target(target)

    # ---------------------------
    # SCAN MODES
    # ---------------------------
    if mode == "fast":
        args = "-T4 -F -Pn -oX -"

    elif mode == "deep":
        # moderate depth scan
        args = "-T4 -sV -O -Pn -p 1-5000 -oX -"

    elif mode == "extreme":
        # full, aggressive
        args = "-T4 -A -p- -Pn -oX -"

    else:
        args = "-T4 -F -Pn -oX -"

    cmd = f"nmap {args} {hostname}"
    logger.info("Running Nmap cmd: %s", cmd)

    try:
        result = subprocess.run(
            shlex.split(cmd),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=300
        )

        if result.returncode != 0:
            return {
                "tool": "nmap",
                "mode": mode,
                "arguments": args,
                "target": hostname,
                "hosts": [],
                "error": "nmap_failed",
                "stderr": result.stderr,
            }

        xml = xmltodict.parse(result.stdout)

        # --------------------------------
        # EXTRACT HOSTS SAFELY
        # --------------------------------
        host_nodes = xml.get("nmaprun", {}).get("host", [])
        if isinstance(host_nodes, dict):
            host_nodes = [host_nodes]

        hosts_out = []
        for h in host_nodes:
            state = h.get("status", {}).get("@state", "unknown")

            hosts_out.append({
                "host": _extract_host_address(h),
                "hostname": _extract_hostname(h),
                "state": state,
                "ports": _extract_ports(h),
            })

        logger.info(f"Nmap ({mode}) scan complete → {len(hosts_out)} hosts")
        waf = detect_firewall(xml)

        return {
            "tool": "nmap",
            "mode": mode,
            "arguments": args,
            "target": hostname,
            "hosts": hosts_out,
            "xml_raw": xml,
            "waf_detection": waf,
        }

    except subprocess.TimeoutExpired:
        return {
            "tool": "nmap",
            "mode": mode,
            "target": hostname,
            "hosts": [],
            "error": "timeout"
        }

    except Exception as e:
        logger.exception("Nmap scan failed")
        return {
            "tool": "nmap",
            "mode": mode,
            "target": hostname,
            "hosts": [],
            "error": str(e)
        }
