# backend/app/killchain_report.py

from typing import Dict, Any, List
import io, base64

from reportlab.lib.pagesizes import letter
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    Image,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors


def generate_killchain_pdf(result: Dict[str, Any],
                           attack_paths: List[Dict[str, Any]]) -> bytes:
    """
    Generates kill-chain PDF including:
    - Target summary
    - XAI analysis
    - Attack graph PNG (optional)
    - Attack paths table (clean, wrapped)
    """

    buffer = io.BytesIO()

    # Slightly narrower margins so table has space
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=40,
        rightMargin=40,
        topMargin=40,
        bottomMargin=40,
    )

    styles = getSampleStyleSheet()

    title = styles["Heading1"]
    subtitle = styles["Heading2"]
    normal = styles["BodyText"]

    mono_small = ParagraphStyle(
        "MonoSmall",
        parent=normal,
        fontName="Helvetica",
        fontSize=9,
        leading=11,
    )

    elements = []

    target = result.get("target")
    scan_mode = result.get("scan_mode")
    risk_score = result.get("risk_score")

    # Header
    elements.append(Paragraph("Kill-Chain Mapping Report", title))
    elements.append(Spacer(1, 10))

    elements.append(Paragraph(f"<b>Target:</b> {target}", normal))
    elements.append(Paragraph(f"<b>Scan Mode:</b> {scan_mode}", normal))
    elements.append(Paragraph(f"<b>Overall Risk Score:</b> {risk_score}", normal))
    elements.append(Spacer(1, 14))

    # XAI block
    ai = result.get("ai", {})
    if ai:
        elements.append(Paragraph("XAI Security Summary", subtitle))
        elements.append(Spacer(1, 6))

        for key, label in [
            ("executive_summary", "Executive Summary"),
            ("technical_analysis", "Technical Analysis"),
            ("conclusion", "Conclusion"),
        ]:
            if ai.get(key):
                elements.append(Paragraph(f"<b>{label}</b>", normal))
                elements.append(Paragraph(ai[key], mono_small))
                elements.append(Spacer(1, 8))

    # Attack graph image (if present)
    graph_png = result.get("graph_png")
    if graph_png:
        try:
            img_bytes = base64.b64decode(graph_png.split(",")[1])
            img = Image(io.BytesIO(img_bytes), width=480, height=320)
            elements.append(Spacer(1, 16))
            elements.append(Paragraph("Attack Graph Visualization", subtitle))
            elements.append(Spacer(1, 8))
            elements.append(img)
            elements.append(Spacer(1, 18))
        except Exception as e:
            elements.append(Spacer(1, 10))
            elements.append(
                Paragraph(f"<b>Note:</b> Graph image could not be embedded ({e})", mono_small)
            )
            elements.append(Spacer(1, 12))

    # Attack paths table
    elements.append(Paragraph("Attack Paths (Kill-Chain)", subtitle))
    elements.append(Spacer(1, 6))

    if not attack_paths:
        elements.append(Paragraph("No attack paths were detected.", normal))
    else:
        # Table header
        table_data: List[List[Any]] = [
            [
                Paragraph("<b>ID</b>", normal),
                Paragraph("<b>Threat</b>", normal),
                Paragraph("<b>Risk</b>", normal),
                Paragraph("<b>Summary</b>", normal),
            ]
        ]

        for p in attack_paths:
            pid = p.get("id", "")
            threat = p.get("threat", "")
            risk = p.get("risk", "")
            summary = p.get("summary", "")

            # Use Paragraph so text wraps nicely
            row = [
                Paragraph(str(pid), mono_small),
                Paragraph(threat, mono_small),
                Paragraph(risk, mono_small),
                Paragraph(summary, mono_small),
            ]
            table_data.append(row)

        # Total content width ~= page width - margins (~532 pt on letter with our margins)
        # Adjust colWidths so summary gets the largest share
        table = Table(
            table_data,
            colWidths=[40, 140, 60, 252],
            repeatRows=1,
        )

        table.setStyle(
            TableStyle(
                [
                    # Header
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#111827")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, 0), 9),

                    # Body
                    ("FONTSIZE", (0, 1), (-1, -1), 8),
                    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),

                    # Padding
                    ("LEFTPADDING", (0, 0), (-1, -1), 4),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                    ("TOPPADDING", (0, 0), (-1, -1), 3),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 3),

                    # Zebra rows
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1),
                     [colors.whitesmoke, colors.HexColor("#E5E7EB")]),

                    # Grid
                    ("GRID", (0, 0), (-1, -1), 0.3, colors.gray),
                ]
            )
        )

        elements.append(table)

    doc.build(elements)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes
