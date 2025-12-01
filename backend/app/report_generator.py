# backend/app/report_generator.py
import io
import os
import json
import textwrap
import logging
from typing import Dict, Any, Optional

from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table,
    TableStyle, PageBreak
)

# Logging
logger = logging.getLogger("report-generator")
logger.setLevel(logging.INFO)

# Gemini Setup
import google.generativeai as genai

GEMINI_KEY = os.getenv("GEMINI_API_KEY", "")
DEFAULT_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

if GEMINI_KEY:
    genai.configure(api_key=GEMINI_KEY)


# ---------------------------------------------------------
# Compact context summary generator
# ---------------------------------------------------------
def build_compact_context(nmap_data, zap_data, crawl_data, risk_score):
    lines = []
    lines.append(f"Risk Score: {risk_score}\n")

    # NMAP
    lines.append("\nNmap:")
    hosts = nmap_data.get("hosts", [])
    for h in hosts[:5]:
        ports = ", ".join(str(p.get("port")) for p in h.get("ports", [])[:10])
        lines.append(f"- {h.get('host')} ({h.get('state')}) ports: {ports}")

    # ZAP
    alerts = zap_data.get("alerts", [])
    lines.append(f"\nZAP Alerts: {len(alerts)}")
    for a in alerts[:10]:
        lines.append(f"- {a.get('risk')} | {a.get('alert')} | {a.get('url')}")

    # Crawler
    pages = crawl_data.get("pages", [])
    lines.append(f"\nCrawler pages: {len(pages)}")
    for p in pages[:5]:
        lines.append(f"- {p.get('url')}")

    return "\n".join(lines)


# ---------------------------------------------------------
# Gemini JSON-only call (robust)
# ---------------------------------------------------------
def call_gemini_structured(prompt: str, model: Optional[str] = None) -> Dict[str, Any]:
    """
    FINAL STABLE VERSION
    - Works with your Gemini SDK (generate_content(list_of_parts))
    - Handles parts, text fallback, weird protobuf objects
    - Extracts JSON reliably even if wrapped inside text
    """

    if not GEMINI_KEY:
        return {"error": "no_api_key"}

    model = model or DEFAULT_MODEL

    system_prompt = (
        "You are a cybersecurity audit assistant. Return only VALID JSON:\n"
        "{\n"
        "  \"executive_summary\": string,\n"
        "  \"technical_analysis\": string,\n"
        "  \"conclusion\": string,\n"
        "  \"remediation\": array of strings\n"
        "}\n"
        "NO markdown. NO explanation. JSON ONLY."
    )

    full_prompt = system_prompt + "\n\n" + prompt

    try:
        gem = genai.GenerativeModel(model)

        # IMPORTANT: Your SDK ONLY accepts list-of-dicts input
        response = gem.generate_content(
            [{"text": full_prompt}],
            generation_config={
                "temperature": 0.2,
                "max_output_tokens": 4096
            }
        )

        if not response or not hasattr(response, "candidates") or not response.candidates:
            return {"error": "no_candidates", "raw": str(response)}

        cand = response.candidates[0]
        content = getattr(cand, "content", None)
        if content is None:
            return {"error": "no_content", "raw": str(response)}

        # Extract `parts` OR fallback to content.text
        parts = getattr(content, "parts", None)

        # CASE A: parts exist but protobuf repeated field → convert to list
        if parts:
            try:
                parts = list(parts)
            except:
                parts = [parts]
        else:
            # CASE B: content.text exists
            text_fallback = getattr(content, "text", None)
            if text_fallback:
                parts = [{"text": text_fallback}]
            else:
                return {"error": "no_parts", "raw": str(response)}

        # Extract combined text
        extracted = ""
        for p in parts:
            if hasattr(p, "text"):
                extracted += p.text
            elif isinstance(p, dict):
                extracted += p.get("text", "")
            else:
                extracted += str(p)

        extracted = extracted.strip()
        if not extracted:
            return {"error": "empty_text", "raw": str(response)}

        # Find JSON inside any messy wrapper text
        start = extracted.find("{")
        end = extracted.rfind("}")
        if start == -1 or end == -1:
            return {"error": "json_not_found", "raw": extracted[:500]}

        json_str = extracted[start:end+1]

        # Try clean parse
        try:
            parsed = json.loads(json_str)
        except Exception:
            # Attempt unescape, then parse again
            try:
                parsed = json.loads(json_str.encode("utf-8").decode("unicode_escape"))
            except Exception as e:
                return {"error": "json_parse_failed", "raw": json_str[:1000], "message": str(e)}

        # Validate keys
        required = ["executive_summary", "technical_analysis", "conclusion", "remediation"]
        if not all(k in parsed for k in required):
            return {"error": "invalid_structure", "raw": json_str[:800]}

        return parsed

    except Exception as e:
        logger.error(f"Gemini API exception: {e}", exc_info=True)
        return {"error": "exception", "message": str(e)}

# ---------------------------------------------------------
# PDF Table helper
# ---------------------------------------------------------
def _add_table(story, headers, rows, col_widths=None):
    styles = getSampleStyleSheet()
    cell = ParagraphStyle("cell", parent=styles["Normal"], fontSize=8, wordWrap="CJK")

    wrapped_headers = [Paragraph(str(h), cell) for h in headers]
    wrapped_rows = [[Paragraph(str(c), cell) for c in r] for r in rows]

    t = Table([wrapped_headers] + wrapped_rows, colWidths=col_widths, repeatRows=1)
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#dddddd")),
        ('GRID', (0,0), (-1,-1), 0.25, colors.black),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
    ]))

    story.append(t)
    story.append(Spacer(1, 10))


# ---------------------------------------------------------
# Build PDF content
# ---------------------------------------------------------
def _build_story(target, nmap_data, zap_data, crawl_data, risk_score, ai):
    styles = getSampleStyleSheet()
    normal = styles["Normal"]
    title = styles["Title"]
    heading = ParagraphStyle("Heading", parent=styles["Heading2"], spaceAfter=6)

    story = []

    # Title Page
    story.append(Paragraph("<b>Security Scan Report</b>", title))
    story.append(Spacer(1, 12))
    story.append(Paragraph(f"Target: {target}", normal))
    story.append(Paragraph(f"Risk Score: {risk_score}/10", normal))
    story.append(Paragraph(f"LLM Assisted: {'Yes' if ai else 'No'}", normal))
    story.append(Spacer(1, 20))

    # NMAP
    story.append(Paragraph("Nmap Scan Summary", heading))
    hosts = nmap_data.get("hosts", [])
    if hosts:
        rows = []
        for h in hosts:
            ports = ", ".join(
                f"{p.get('port')} ({p.get('service','')})"
                for p in h.get("ports", [])
            )
            rows.append([h.get("host"), h.get("state"), ports])
        _add_table(story, ["Host", "State", "Ports"], rows, [140, 60, 260])
    else:
        story.append(Paragraph("No hosts scanned.", normal))

    story.append(Spacer(1, 20))

    # ZAP
    story.append(Paragraph("ZAP Findings", heading))
    alerts = zap_data.get("alerts", [])
    if alerts:
        rows = []
        for a in alerts[:60]:
            rows.append([
                a.get("risk"),
                a.get("alert"),
                a.get("url")
            ])
        _add_table(story, ["Risk", "Alert", "URL"], rows, [60, 230, 170])
    else:
        story.append(Paragraph("No alerts found.", normal))

    story.append(Spacer(1, 20))

    # Crawler
    story.append(Paragraph("Crawler Summary", heading))
    pages = crawl_data.get("pages", [])
    for p in pages[:10]:
        story.append(Paragraph(f"- {p.get('url')}", normal))

    # AI Page
    story.append(PageBreak())
    story.append(Paragraph("AI Security Assessment", title))
    story.append(Spacer(1, 15))

    # Case 1: AI completely missing
    if ai is None:
        story.append(Paragraph("AI summary was not requested.", normal))
        return story

    # Case 2: AI returned an error
    if ai.get("error"):
        story.append(Paragraph("LLM summary not available.", normal))
        story.append(Spacer(1, 10))
        story.append(Paragraph(f"Reason: {ai.get('error')}", normal))
        return story

    # Case 3: AI returned structured JSON correctly
    exec_sum = ai.get("executive_summary") or "No executive summary provided."
    tech = ai.get("technical_analysis") or "No technical analysis provided."
    conc = ai.get("conclusion") or "No conclusion provided."
    remediation_list = ai.get("remediation") or []

    story.append(Paragraph("<b>Executive Summary</b>", heading))
    story.append(Paragraph(exec_sum, normal))
    story.append(Spacer(1, 10))

    story.append(Paragraph("<b>Technical Analysis</b>", heading))
    story.append(Paragraph(tech, normal))
    story.append(Spacer(1, 10))

    story.append(Paragraph("<b>Conclusion</b>", heading))
    story.append(Paragraph(conc, normal))
    story.append(Spacer(1, 10))

    story.append(Paragraph("<b>Remediation Checklist</b>", heading))
    if remediation_list:
        for r in remediation_list:
            story.append(Paragraph(f"- {r}", normal))
    else:
        story.append(Paragraph("No remediation steps provided.", normal))

    return story


# ---------------------------------------------------------
# Main PDF generator (NO LLM CALL HERE)
# ---------------------------------------------------------
def generate_pdf(target, nmap_data, zap_data, crawl_data, risk_score, ai=None):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)

    story = _build_story(target, nmap_data, zap_data, crawl_data, risk_score, ai)
    doc.build(story)

    buffer.seek(0)
    return buffer.getvalue()


def generate_pdf_bytes_from_report(*args, **kwargs):
    return generate_pdf(*args, **kwargs)