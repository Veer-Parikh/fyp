import subprocess
import xmltodict
from urllib.parse import urlparse
from typing import Dict, Any, List
import logging

logger = logging.getLogger("nmap-scanner")
logger.setLevel(logging.INFO)

def clean_target(target: str) -> str:
    parsed = urlparse(target)
    return parsed.hostname or target

def _parse_ports_nmap(parsed) -> List[Dict[str, Any]]:
    ports_output = []
    try:
        ports = parsed["nmaprun"]["host"]["ports"].get("port", [])
        if isinstance(ports, dict):
            ports = [ports]

        for p in ports:
            ports_output.append({
                "port": int(p["@portid"]),
                "protocol": p["@protocol"],
                "state": p["state"]["@state"],
                "service": p.get("service", {}).get("@name", "")
            })
    except Exception:
        pass
    return ports_output

def run_nmap_scan(target: str, mode: str = "fast") -> Dict[str, Any]:
    hostname = clean_target(target)

    # Choose arguments depending on mode
    if mode == "fast":
        args = ["nmap", "-T4", "-F", "-Pn", hostname]
    elif mode == "deep":
        args = ["nmap", "-T4", "-A", "-p-", "-Pn", hostname]
    else:
        args = ["nmap", "-sT", "-Pn", hostname]

    try:
        result = subprocess.run(
            args + ["-oX", "-"],       # XML output
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=180                # avoids freeze
        )

        xml_data = result.stdout
        parsed = xmltodict.parse(xml_data)

        hosts_out = [{
            "host": hostname,
            "state": parsed["nmaprun"]["host"]["status"]["@state"],
            "ports": _parse_ports_nmap(parsed)
        }]

        print("Nmap scan completed for", hostname)

        return {
            "status": "success",
            "tool": "nmap",
            "arguments": " ".join(args),
            "scanned_target": hostname,
            "hosts": hosts_out,
            "raw_xml": xml_data
        }

    except subprocess.TimeoutExpired:
        return {
            "status": "error",
            "tool": "nmap",
            "message": "Nmap timed out (deep scan takes too long)",
            "scanned_target": hostname
        }

    except Exception as e:
        logger.exception("Nmap scan failed")
        return {
            "status": "error",
            "tool": "nmap",
            "message": str(e),
            "scanned_target": hostname
        }

# # backend/app/nmap_scanner.py
# import nmap
# from urllib.parse import urlparse

# def clean_target(target: str) -> str:
#     parsed = urlparse(target)
#     return parsed.hostname or target

# def run_nmap_scan(target: str, mode: str = "fast"):
#     hostname = clean_target(target)
#     scanner = nmap.PortScanner()
#     if mode == "fast":
#         args = "-T4 -F -Pn"
#     elif mode == "deep":
#         args = "-T4 -A -p- -Pn"
#     else:
#         args = "-sT -Pn"

#     try:
#         raw = scanner.scan(hosts=hostname, arguments=args)
#         hosts_out = []
#         for host in scanner.all_hosts():
#             info = scanner[host]
#             state = info.get("status", {}).get("state", "unknown")
#             host_info = {
#                 "host": host,
#                 "hostname": info.hostname() or "",
#                 "state": state,
#                 "ports": []
#             }
#             tcp = info.get("tcp", {}) or {}
#             for port_str, pinfo in tcp.items():
#                 host_info["ports"].append({
#                     "port": int(port_str),
#                     "state": pinfo.get("state", ""),
#                     "service": pinfo.get("name", ""),
#                     "product": pinfo.get("product", ""),
#                     "version": pinfo.get("version", ""),
#                     "extrainfo": pinfo.get("extrainfo", "")
#                 })
#             hosts_out.append(host_info)

#         return {"status": "success", "tool": "nmap", "arguments": args, "scanned_target": hostname, "hosts": hosts_out, "raw": raw}

#     except Exception as e:
#         return {"status": "error", "tool": "nmap", "message": str(e), "scanned_target": hostname}
