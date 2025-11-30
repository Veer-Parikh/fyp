# backend/app/report_generator.py
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
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak

# ---------------------------------
# Logging
# ---------------------------------
logger = logging.getLogger("report-generator")
logger.setLevel(logging.INFO)

# ---------------------------------
# Gemini Setup (works for 0.8.x)
# ---------------------------------
import google.generativeai as genai

GEMINI_KEY = os.getenv("GEMINI_API_KEY", "")
DEFAULT_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

if GEMINI_KEY:
    genai.configure(api_key=GEMINI_KEY)

def build_compact_context(nmap_data, zap_data, crawl_data, risk_score):
    # Build compact context to avoid token overflow
    lines = []

    lines.append(f"Risk Score: {risk_score}\n")

    # ---- NMAP ----
    lines.append("\nNmap:")
    hosts = nmap_data.get("hosts", [])
    for h in hosts[:5]:
        ports = ", ".join(str(p.get("port")) for p in h.get("ports", [])[:15])
        lines.append(f"- {h.get('host')} ({h.get('state')}) ports: {ports}")

    # ---- ZAP ----
    alerts = zap_data.get("alerts", [])
    lines.append(f"\nZAP: total alerts={len(alerts)}")
    for a in alerts[:10]:
        lines.append(f"- {a.get('risk')} | {a.get('alert')} | {a.get('url')}")

    # ---- CRAWLER ----
    pages = crawl_data.get("pages", [])
    lines.append(f"\nCrawler: {len(pages)} pages crawled.")
    for p in pages[:5]:
        lines.append(f"- {p.get('url')}")

    return "\n".join(lines)


# ---------------------------------
# LLM FUNCTION (JSON GUARANTEED)
# ---------------------------------
def call_gemini_structured(prompt: str, model: str = DEFAULT_MODEL) -> Dict[str, Any]:
    """
    Calls Gemini safely, extracting JSON using candidates[].content.parts[].
    Works around safety blocks & missing parts.
    """
    if not GEMINI_KEY:
        return {"error": "no_api_key"}

    safe_system = (
        "You are a cybersecurity audit assistant producing defensive reports. "
        "Your purpose is to help users understand security issues and improve protection. "
        "All output must be educational, non-exploitative, and safe.\n\n"
        "Return ONLY valid JSON with EXACT keys:\n"
        "{\n"
        "  \"executive_summary\": string,\n"
        "  \"technical_analysis\": string,\n"
        "  \"conclusion\": string,\n"
        "  \"remediation\": array of strings\n"
        "}\n"
        "No markdown, no extra text, JSON ONLY."
    )

    try:
        gem = genai.GenerativeModel(model)

        response = gem.generate_content(
            [
                {"text": safe_system},
                {"text": prompt}
            ],
            generation_config={
                "temperature": 0.2,
                "max_output_tokens": 4096,
            }
        )

        # -------------------------------------
        # FIX: response.text is unavailable when finish_reason = SAFETY
        # We must extract manually from candidates → content → parts
        # -------------------------------------
        if not response.candidates:
            return {"error": "no_candidates", "raw": str(response)}

        candidate = response.candidates[0]
        
        if candidate.finish_reason == 2:
            return {
                "error": "safety_block",
                "message": "Gemini blocked this content for safety.",
                "raw": str(response)
            }

        parts = candidate.content.parts if candidate.content else []
        if not parts:
            return {"error": "no_parts", "raw": str(response)}

        combined_text = ""
        for part in parts:
            if hasattr(part, "text"):
                combined_text += part.text

        raw = combined_text.strip()

        # Extract JSON
        first = raw.find("{")
        last = raw.rfind("}")
        if first == -1:
            return {"error": "json_not_found", "raw": raw}

        try:
            parsed = json.loads(raw[first:last + 1])
            return parsed
        except Exception as e:
            return {"error": "json_parse_failed", "raw": raw, "message": str(e)}

    except Exception as e:
        return {"error": "exception", "message": str(e)}


# ---------------------------------
# PDF HELPERS
# ---------------------------------
def _p(text: str, style):
    return Paragraph(text, style)


def _truncate(text: str, length: int = 120) -> str:
    s = str(text or "")
    return s if len(s) <= length else s[:length - 3] + "..."


def _add_table(story, headers, rows, col_widths=None):
    t = Table([headers] + rows, colWidths=col_widths)
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#eeeeee")),
        ('GRID', (0, 0), (-1, -1), 0.25, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    story.append(t)
    story.append(Spacer(1, 8))


# ---------------------------------
# BUILD PDF STORY
# ---------------------------------
def _build_story(target: str, nmap_data, zap_data, crawl_data, risk_score, ai):
    styles = getSampleStyleSheet()
    normal = styles["Normal"]
    title = styles["Title"]
    heading = ParagraphStyle("Heading", parent=styles["Heading2"], spaceAfter=6)
    small = ParagraphStyle("Small", parent=styles["Normal"], fontSize=9)

    story = []

    # Cover page
    story.append(_p("<b>FAST Security Scan Report</b>", title))
    story.append(Spacer(1, 12))
    story.append(_p(f"Target: {target}", normal))
    story.append(_p(f"Risk Score: <b>{risk_score}/10</b>", normal))
    story.append(Spacer(1, 12))
    story.append(_p(f"LLM Assisted: {'Yes' if ai else 'No'}", small))
    story.append(Spacer(1, 12))

    # Nmap section
    story.append(_p("Nmap Scan Summary", heading))
    hosts = nmap_data.get("hosts", [])
    if hosts:
        rows = []
        for h in hosts:
            ports = ", ".join(str(p.get("port")) for p in h.get("ports", []))
            rows.append([h.get("host"), h.get("state"), _truncate(ports, 80)])
        _add_table(story, ["Host", "State", "Open Ports"], rows, col_widths=[180, 60, 260])
    else:
        story.append(_p("No hosts scanned.", normal))

    story.append(Spacer(1, 12))

    # ZAP section
    story.append(_p("ZAP Findings", heading))
    alerts = zap_data.get("alerts", [])
    if alerts:
        rows = []
        for a in alerts[:50]:
            rows.append([a.get("risk", ""), _truncate(a.get("alert", ""), 70), _truncate(a.get("url", ""), 50)])
        _add_table(story, ["Severity", "Alert", "URL"], rows, col_widths=[70, 280, 150])
    else:
        story.append(_p("No ZAP alerts found.", normal))

    # Crawler section
    if crawl_data.get("pages"):
        story.append(_p("Crawler Summary", heading))
        story.append(_p(f"Pages crawled: {len(crawl_data['pages'])}", normal))
        for p in crawl_data["pages"][:10]:
            story.append(_p(f"- {p.get('url')}", small))
        story.append(Spacer(1, 10))

    # AI Page
    story.append(PageBreak())
    story.append(_p("AI-Generated Security Synopsis", styles["Heading1"]))
    story.append(Spacer(1, 10))

    if ai and not ai.get("error"):
        # Section 1
        story.append(_p("<b>Executive Summary</b>", heading))
        for line in ai["executive_summary"].split("\n"):
            story.append(_p(textwrap.fill(line, 115), normal))
            story.append(Spacer(1, 4))

        # Section 2
        story.append(_p("<b>Detailed Technical Analysis</b>", heading))
        for line in ai["technical_analysis"].split("\n"):
            story.append(_p(textwrap.fill(line, 115), normal))
            story.append(Spacer(1, 4))

        # Section 3
        story.append(_p("<b>Security Conclusion</b>", heading))
        for line in ai["conclusion"].split("\n"):
            story.append(_p(textwrap.fill(line, 115), normal))
            story.append(Spacer(1, 4))

        # Section 4
        story.append(_p("<b>Remediation Checklist</b>", heading))
        for item in ai["remediation"]:
            story.append(_p(f"• {item}", normal))
            story.append(Spacer(1, 4))

    else:
        story.append(_p("<b>Executive Summary</b>", heading))
        story.append(_p("AI was unable to generate a summary.", normal))

    return story


# ---------------------------------
# MAIN PDF GENERATOR
# ---------------------------------
def generate_pdf(target, nmap_data, zap_data, crawl_data, risk_score, use_llm=True, model=None) -> bytes:
    model = model or DEFAULT_MODEL

    ai = None
    if use_llm and GEMINI_KEY:
        compact = build_compact_context(nmap_data, zap_data, crawl_data, risk_score)

        prompt = (
            f"You are reviewing the following scan summary of {target}.\n\n"
            f"{compact}\n\n"
            "Using this summarized data, generate ONLY JSON with fields:\n"
            "executive_summary, technical_analysis, conclusion, remediation."
        )


        ai = call_gemini_structured(prompt, model)
        print("AI SECTIONS:", ai)

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)

    story = _build_story(target, nmap_data, zap_data, crawl_data, risk_score, ai)
    doc.build(story)

    buffer.seek(0)
    return buffer.getvalue()


def generate_pdf_bytes_from_report(*args, **kwargs):
    return generate_pdf(*args, **kwargs)

# # import io
# # from reportlab.lib.pagesizes import letter
# # from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
# # from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
# # from reportlab.lib import colors

# # def _p(text, style):
# #     return Paragraph(str(text), style)

# # def _truncate(text, length=100):
# #     s = str(text or "")
# #     return s if len(s) <= length else s[:length-3] + "..."

# # def generate_pdf(target, nmap_data, zap_data, crawl_data, risk_score, use_llm=False):
# #     buffer = io.BytesIO()
# #     doc = SimpleDocTemplate(buffer, pagesize=letter)

# #     styles = getSampleStyleSheet()
# #     normal = styles["Normal"]
# #     heading = ParagraphStyle("Heading", parent=styles["Heading2"], spaceAfter=6)

# #     story = []

# #     # TITLE
# #     story.append(_p("<b>FAST Security Scan Report</b>", styles["Title"]))
# #     story.append(_p(f"Target: {target}", normal))
# #     story.append(_p(f"Risk Score: {risk_score}/10", normal))
# #     story.append(Spacer(1, 12))

# #     # NMAP
# #     story.append(_p("Nmap Fast Scan Summary", heading))
# #     hosts = nmap_data.get("hosts", [])
# #     if hosts:
# #         rows = [["Host", "State", "Open Ports"]]
# #         for h in hosts:
# #             ports = [str(p["port"]) for p in h.get("ports", [])]
# #             rows.append([h["host"], h["state"], ", ".join(ports)])
# #         t = Table(rows, colWidths=[150, 50, 300])
# #         t.setStyle(TableStyle([
# #             ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#eeeeee")),
# #             ('GRID', (0,0), (-1,-1), 0.25, colors.black)
# #         ]))
# #         story.append(t)
# #     else:
# #         story.append(_p("Nmap returned no results.", normal))

# #     story.append(Spacer(1, 15))

# #     # ZAP
# #     story.append(_p("ZAP Passive Scan (Spider Only)", heading))
# #     alerts = zap_data.get("alerts", [])
# #     if alerts:
# #         rows = [["Severity", "Alert", "URL"]]
# #         for a in alerts[:30]:
# #             rows.append([
# #                 a["risk"],
# #                 _truncate(a["alert"], 60),
# #                 _truncate(a["url"], 60)
# #             ])
# #         t = Table(rows, colWidths=[70, 200, 250])
# #         t.setStyle(TableStyle([
# #             ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#eeeeee")),
# #             ('GRID', (0,0), (-1,-1), 0.25, colors.black)
# #         ]))
# #         story.append(t)
# #     else:
# #         story.append(_p("No ZAP alerts found.", normal))

# #     story.append(Spacer(1, 12))

# #     story.append(_p("FAST MODE: Crawler & AI summary disabled for performance.", normal))

# #     doc.build(story)
# #     buffer.seek(0)
# #     return buffer.getvalue()
# import io
# import os
# import textwrap
# import google.generativeai as genai
# from reportlab.lib.pagesizes import letter
# from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
# from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
# from reportlab.lib import colors

# # -------------------------------
# # Gemini Setup
# # -------------------------------
# GEMINI_KEY = os.getenv("GEMINI_API_KEY", "")

# if GEMINI_KEY:
#     genai.configure(api_key=GEMINI_KEY)

# def call_gemini_summary(prompt: str) -> str:
#     """
#     Uses Gemini 1.5 Flash to generate summary.
#     Returns fallback text if no API key is present.
#     """
#     if not GEMINI_KEY:
#         return "Gemini API key missing – set GEMINI_API_KEY env variable to enable AI insights."

#     try:
#         model = genai.GenerativeModel("gemini-2.5-pro")
#         res = model.generate_content(prompt)
#         return res.text.strip()
#     except Exception as e:
#         return f"Gemini error: {e}"


# # -------------------------------
# # Helpers
# # -------------------------------
# def _p(text, style):
#     return Paragraph(str(text), style)

# def _truncate(text, length=100):
#     s = str(text or "")
#     return s if len(s) <= length else s[:length-3] + "..."

# # -------------------------------
# # Build AI Prompt
# # -------------------------------
# def build_ai_prompt(target, nmap_data, zap_data, risk_score):
#     lines = []
#     lines.append(f"Generate a professional cybersecurity scan report summary for the website: {target}\n")
#     lines.append(f"Overall calculated risk score (0–10): {risk_score}\n")

#     lines.append("Nmap Summary:")
#     hosts = nmap_data.get("hosts", [])
#     if not hosts:
#         lines.append("- No open ports found or scan failed.")
#     else:
#         for h in hosts[:5]:
#             ports = ", ".join([str(p['port']) for p in h.get("ports", [])])
#             lines.append(f"- Host {h['host']} (state: {h['state']}) ports: {ports}")

#     lines.append("\nZAP Summary:")
#     zsum = zap_data.get("summary", {})
#     counts = zsum.get("counts", {})
#     lines.append(f"Alerts: {zsum.get('total',0)} | High:{counts.get('High',0)}, Medium:{counts.get('Medium',0)}, Low:{counts.get('Low',0)}, Info:{counts.get('Info',0)}")

#     # Sample alerts
#     lines.append("\nImportant ZAP Findings:")
#     for a in zap_data.get("alerts", [])[:10]:
#         lines.append(f"- [{a['risk']}] {a['alert']} - {a['url']}")

#     lines.append("""

# Write FOUR SECTIONS:
# 1. Executive Summary (2–3 paragraphs, non-technical + technical)
# 2. Detailed Technical Analysis (explain the meaning of the findings)
# 3. Security Conclusion / Thesis (4–6 sentences, high quality)
# 4. Remediation Checklist (bullet points, action-driven)

# Make the writing clear, authoritative, and professional.
# """)

#     return "\n".join(lines)



# # -------------------------------
# # PDF Generator
# # -------------------------------
# def generate_pdf(target, nmap_data, zap_data, crawl_data, risk_score, use_llm=True):
#     buffer = io.BytesIO()
#     doc = SimpleDocTemplate(buffer, pagesize=letter)

#     styles = getSampleStyleSheet()
#     normal = styles["Normal"]
#     heading = ParagraphStyle("Heading", parent=styles["Heading2"], spaceAfter=6)
#     small = ParagraphStyle("Small", parent=styles["Normal"], fontSize=9)

#     story = []

#     # TITLE
#     story.append(_p("<b>FAST Security Scan Report</b>", styles["Title"]))
#     story.append(_p(f"Target: {target}", normal))
#     story.append(_p(f"Risk Score: {risk_score}/10", normal))
#     story.append(Spacer(1, 12))

#     # --------------------------
#     # NMAP SECTION
#     # --------------------------
#     story.append(_p("Nmap Fast Scan Summary", heading))
#     hosts = nmap_data.get("hosts", [])
#     if hosts:
#         rows = [["Host", "State", "Open Ports"]]
#         for h in hosts:
#             ports = [str(p["port"]) for p in h.get("ports", [])]
#             rows.append([h["host"], h["state"], ", ".join(ports)])
#         t = Table(rows, colWidths=[150, 50, 300])
#         t.setStyle(TableStyle([
#             ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#eeeeee")),
#             ('GRID', (0,0), (-1,-1), 0.25, colors.black)
#         ]))
#         story.append(t)
#     else:
#         story.append(_p("Nmap found no open ports.", normal))

#     story.append(Spacer(1, 15))

#     # --------------------------
#     # ZAP SECTION
#     # --------------------------
#     story.append(_p("ZAP Passive Scan (Spider Only)", heading))
#     alerts = zap_data.get("alerts", [])
#     if alerts:
#         rows = [["Severity", "Alert", "URL"]]
#         for a in alerts[:30]:
#             rows.append([
#                 a["risk"],
#                 _truncate(a["alert"], 60),
#                 _truncate(a["url"], 60)
#             ])
#         t = Table(rows, colWidths=[70, 200, 250])
#         t.setStyle(TableStyle([
#             ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#eeeeee")),
#             ('GRID', (0,0), (-1,-1), 0.25, colors.black)
#         ]))
#         story.append(t)
#     else:
#         story.append(_p("No ZAP alerts found.", normal))

#     story.append(Spacer(1, 15))

#     # --------------------------
#     # AI SECTION
#     # --------------------------
#     if use_llm:
#         story.append(PageBreak())
#         story.append(_p("AI-Generated Security Synopsis", styles["Heading1"]))
#         story.append(Spacer(1, 6))

#         prompt = build_ai_prompt(target, nmap_data, zap_data, risk_score)
#         ai_text = call_gemini_summary(prompt)

#         for para in ai_text.split("\n"):
#             if para.strip():
#                 story.append(_p(textwrap.fill(para, 115), normal))
#                 story.append(Spacer(1, 8))

#     else:
#         story.append(_p("AI summary was disabled.", normal))

#     doc.build(story)
#     buffer.seek(0)
#     return buffer.getvalue()
