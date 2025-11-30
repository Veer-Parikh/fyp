# backend/app/nmap_scanner.py
import subprocess
import xmltodict
from urllib.parse import urlparse
from typing import Dict, Any, List
import logging
import shlex

logger = logging.getLogger("nmap-scanner")
logger.setLevel(logging.INFO)


def clean_target(target: str) -> str:
    parsed = urlparse(target)
    return parsed.hostname or target


def _parse_ports_from_host(host_node: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Given a single host node (xmltodict structure), return list of ports.
    """
    ports_out = []
    try:
        ports_block = host_node.get("ports", {}) or {}
        ports = ports_block.get("port", [])

        if isinstance(ports, dict):
            ports = [ports]

        for p in ports:
            # defensive access
            portid = int(p.get("@portid", 0))
            proto = p.get("@protocol", "")
            state = p.get("state", {}).get("@state", "unknown")
            service = p.get("service", {}).get("@name", "")

            ports_out.append({
                "port": portid,
                "protocol": proto,
                "state": state,
                "service": service
            })
    except Exception as e:
        logger.debug("Error parsing ports from host node: %s", e)
    return ports_out


def run_nmap_scan(target: str, mode: str = "fast") -> Dict[str, Any]:
    """
    Run Nmap and return structured data compatible with report_generator:
      {
        "tool": "nmap",
        "mode": "<fast|deep|extreme>",
        "arguments": "<nmap args>",
        "target": "<hostname>",
        "hosts": [
            {
               "host": "1.2.3.4",
               "hostname": "example.com",
               "state": "up",
               "ports": [ {port, protocol, state, service}, ... ]
            },
            ...
        ],
        "xml_raw": {...}
      }
    """
    hostname = clean_target(target)

    if mode == "fast":
        args = "-T4 -F -Pn -oX -"
    elif mode == "deep":
        args = "-T4 -sV -O -Pn -p 1-5000 -oX -"
    elif mode == "extreme":
        args = "-T4 -A -p- -Pn -oX -"
    else:
        args = "-T4 -F -Pn -oX -"

    cmd = f"nmap {args} {hostname}"
    logger.info("Running Nmap cmd: %s", cmd)
git
    try:
        result = subprocess.run(
            shlex.split(cmd),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=300  # set a generous timeout; tune as needed
        )

        # if nmap itself failed, return the stderr for debugging
        if result.returncode != 0:
            logger.error("Nmap returned non-zero exit code: %s", result.stderr)
            return {
                "tool": "nmap",
                "mode": mode,
                "arguments": args,
                "target": hostname,
                "hosts": [],
                "error": "nmap_failed",
                "stderr": result.stderr,
                "stdout": result.stdout,
            }

        # parse XML
        parsed_xml = xmltodict.parse(result.stdout)

        # get host nodes (handle single-host or list)
        hosts_node = parsed_xml.get("nmaprun", {}).get("host", [])
        if isinstance(hosts_node, dict):
            hosts_node = [hosts_node]

        hosts_out: List[Dict[str, Any]] = []
        for h in hosts_node:
            # address could be under 'address' (dict) or list - handle both
            addr_node = h.get("address", {})
            ip = ""
            if isinstance(addr_node, list):
                # pick the first addr that has @addr
                for a in addr_node:
                    if a.get("@addr"):
                        ip = a.get("@addr")
                        break
            elif isinstance(addr_node, dict):
                ip = addr_node.get("@addr", "")

            # hostname if available
            hostname_node = h.get("hostnames", {}) or {}
            hostnames = hostname_node.get("hostname", [])
            hostname_text = ""
            if isinstance(hostnames, dict):
                hostname_text = hostnames.get("@name", "")
            elif isinstance(hostnames, list) and len(hostnames) > 0:
                # pick the first
                hostname_text = hostnames[0].get("@name", "")

            state = h.get("status", {}).get("@state", "unknown")
            ports = _parse_ports_from_host(h)

            hosts_out.append({
                "host": ip or hostname,
                "hostname": hostname_text,
                "state": state,
                "ports": ports
            })

        logger.info("Nmap (%s) scan completed for %s; hosts found: %d", mode, hostname, len(hosts_out))

        return {
            "tool": "nmap",
            "mode": mode,
            "arguments": args,
            "target": hostname,
            "hosts": hosts_out,
            "xml_raw": parsed_xml
        }

    except subprocess.TimeoutExpired:
        logger.exception("Nmap timed out")
        return {
            "tool": "nmap",
            "mode": mode,
            "target": hostname,
            "hosts": [],
            "error": "nmap_timeout"
        }
    except Exception as e:
        logger.exception("Nmap scan failed: %s", e)
        return {
            "tool": "nmap",
            "mode": mode,
            "target": hostname,
            "hosts": [],
            "error": str(e)
        }
