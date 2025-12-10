# backend/app/attack_graph.py

from typing import Dict, Any, List, Tuple
import networkx as nx  # pip install networkx


def build_attack_graph(
    nmap: Dict[str, Any],
    zap: Dict[str, Any],
    crawler: Dict[str, Any],
) -> nx.DiGraph:
    """
    Build a directed knowledge graph from Nmap, ZAP and crawler data.
    Nodes:
      - port:*         (open services)
      - page:*         (URLs)
      - vuln:*         (individual ZAP alerts)
      - threat:*       (abstract threat categories: XSS, Clickjacking, etc.)
    Edges:
      - page -> vuln   (page is affected by vulnerability)
      - vuln -> threat (vulnerability leads to threat category)
      - port -> threat (service can be abused for a threat)
    """
    G = nx.DiGraph()

    def add_node(node_id: str, label: str, node_type: str, **attrs):
        if node_id not in G:
            G.add_node(node_id, label=label, type=node_type, **attrs)

    def add_edge(src: str, dst: str, relation: str):
        if src in G and dst in G:
            G.add_edge(src, dst, relation=relation)

    # ----------------------
    # Ports from Nmap
    # ----------------------
    for p in nmap.get("ports", []):
        port_num = p.get("port")
        service = p.get("service")
        state = p.get("state")
        if port_num is None:
            continue

        node_id = f"port:{port_num}"
        label = f"Port {port_num} ({service or 'unknown'})"
        add_node(node_id, label, "port", service=service, state=state)

    # ----------------------
    # Pages from crawler
    # ----------------------
    for page in crawler.get("pages", []):
        url = page.get("url")
        if not url:
            continue
        # normalize: drop trailing slash
        norm_url = url.rstrip("/")
        node_id = f"page:{norm_url}"
        add_node(node_id, norm_url, "page")

    # ----------------------
    # Threat category nodes (abstract)
    # ----------------------
    threat_defs = {
        "threat:clickjacking": "Clickjacking Risk",
        "threat:xss": "XSS / Client-side Injection Risk",
        "threat:https_downgrade": "HTTPS Downgrade / Transport Security Risk",
        "threat:mime_sniffing": "MIME Sniffing / Content-Type Confusion",
        "threat:ftp_weakness": "FTP Service Weakness / Data Exposure",
        "threat:security_misconfig": "General Security Misconfiguration",
    }
    for tid, label in threat_defs.items():
        add_node(tid, label, "threat")

    # ----------------------
    # ZAP alerts as vuln nodes
    # ----------------------
    for alert in zap.get("alerts", []):
        alert_id = str(alert.get("id", alert.get("pluginId", "")))
        name = alert.get("alert") or alert.get("name") or f"Alert {alert_id}"
        risk = alert.get("risk", "Informational")
        url = (alert.get("url") or "").rstrip("/")

        vuln_node_id = f"vuln:{alert_id}"
        add_node(vuln_node_id, name, "vuln", risk=risk, url=url)

        # page -> vuln
        if url:
            page_node_id = f"page:{url}"
            if page_node_id in G:
                add_edge(page_node_id, vuln_node_id, "has_vulnerability")

        # vuln -> threat mapping (rule-based)
        lower_name = name.lower()
        desc = (alert.get("description") or "").lower()

        if "clickjacking" in desc or "anti-clickjacking" in lower_name:
            add_edge(vuln_node_id, "threat:clickjacking", "leads_to")
        if "content security policy" in lower_name or "csp" in lower_name:
            add_edge(vuln_node_id, "threat:xss", "leads_to")
        if "strict-transport-security" in lower_name or "hsts" in desc:
            add_edge(vuln_node_id, "threat:https_downgrade", "leads_to")
        if "x-content-type-options" in lower_name or "mime-sniffing" in desc:
            add_edge(vuln_node_id, "threat:mime_sniffing", "leads_to")

        # generic misconfig
        if "security misconfiguration" in desc or "misconfig" in desc:
            add_edge(vuln_node_id, "threat:security_misconfig", "leads_to")

    # ----------------------
    # Map ports (especially FTP) to threat nodes
    # ----------------------
    for p in nmap.get("ports", []):
        port_num = p.get("port")
        state = (p.get("state") or "").lower()
        service = (p.get("service") or "").lower()
        node_id = f"port:{port_num}"

        if state == "open" and port_num == 21:
            add_edge(node_id, "threat:ftp_weakness", "may_enable")
            add_edge(node_id, "threat:security_misconfig", "may_enable")
        if state == "open" and service in ("http", "https"):
            add_edge(node_id, "threat:security_misconfig", "exposes")

    return G


def _risk_rank(risk: str) -> int:
    mapping = {
        "informational": 0,
        "info": 0,
        "low": 1,
        "medium": 2,
        "high": 3,
        "critical": 4,
    }
    return mapping.get((risk or "").lower(), 0)


def extract_attack_paths(G: nx.DiGraph) -> List[Dict[str, Any]]:
    """
    Extract human-readable attack paths from the graph.
    We look for short paths (length <= 4) starting from ports/pages
    and ending at threat:* nodes.
    """
    attack_paths: List[Dict[str, Any]] = []
    seen: set[Tuple[str, ...]] = set()

    ports = [n for n, d in G.nodes(data=True) if d.get("type") == "port"]
    pages = [n for n, d in G.nodes(data=True) if d.get("type") == "page"]
    threats = [n for n, d in G.nodes(data=True) if d.get("type") == "threat"]

    def node_label(n: str) -> str:
        return G.nodes[n].get("label", n)

    def node_type(n: str) -> str:
        return G.nodes[n].get("type", "")

    def node_risk(n: str) -> str:
        return G.nodes[n].get("risk", "Informational")

    path_id = 1

    for threat in threats:
        for src in ports + pages:
            try:
                for path in nx.all_simple_paths(G, source=src, target=threat, cutoff=4):
                    key = tuple(path)
                    if key in seen:
                        continue
                    seen.add(key)

                    best_risk = "Informational"
                    best_rank = 0
                    for n in path:
                        if node_type(n) == "vuln":
                            r = node_risk(n)
                            rk = _risk_rank(r)
                            if rk > best_rank:
                                best_rank, best_risk = rk, r

                    steps_labels = [node_label(n) for n in path]
                    summary = " → ".join(steps_labels)

                    attack_paths.append({
                        "id": f"path_{path_id}",
                        "risk": best_risk,
                        "threat": node_label(threat),
                        "summary": summary,
                        "steps": steps_labels,
                    })
                    path_id += 1
            except Exception:
                continue

    return attack_paths
