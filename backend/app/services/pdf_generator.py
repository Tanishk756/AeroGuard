"""AeroGuard Incident Operational Report PDF Document Renderer."""

from datetime import datetime
import io
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    HRFlowable,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.models.incident import Incident, IncidentSeverity, IncidentStatus
from app.models.incident_event import IncidentEvent, IncidentEventType


class NumberedCanvas(canvas.Canvas):
    """Custom ReportLab Canvas that performs a two-pass page numbering & running header/footer render."""

    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self._saved_page_states: list[dict[str, Any]] = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count: int):
        self.saveState()
        self.setFont("Helvetica-Bold", 8)
        self.setFillColor(colors.HexColor("#64748B"))

        # Running Header (pages > 1)
        if self._pageNumber > 1:
            self.drawString(36, 11 * inch - 28, "AEROGUARD OPERATIONAL INCIDENT REPORT")
            self.drawRightString(8.5 * inch - 36, 11 * inch - 28, "CONFIDENTIAL / COMPLIANCE ARCHIVAL")
            self.setStrokeColor(colors.HexColor("#334155"))
            self.setLineWidth(0.5)
            self.line(36, 11 * inch - 32, 8.5 * inch - 36, 11 * inch - 32)

        # Running Footer (all pages)
        self.setStrokeColor(colors.HexColor("#334155"))
        self.setLineWidth(0.5)
        self.line(36, 36, 8.5 * inch - 36, 36)

        self.setFont("Helvetica", 8)
        self.drawString(36, 24, "AeroGuard Defense Platform — Defensive Situational Awareness & Compliance Reporting")
        page_text = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(8.5 * inch - 36, 24, page_text)
        self.restoreState()


def format_timestamp(dt: datetime | None) -> str:
    if not dt:
        return "N/A"
    return dt.strftime("%Y-%m-%d %H:%M:%S UTC")


def generate_incident_pdf_report(
    export_number: str,
    requested_by: str,
    generated_at: datetime,
    filter_params: dict[str, Any],
    incidents: list[Incident],
    analytics_summary: dict[str, Any] | None = None,
) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=36,
        rightMargin=36,
        topMargin=40,
        bottomMargin=45,
    )

    styles = getSampleStyleSheet()

    # Custom Color Palette
    BG_DARK = colors.HexColor("#0F172A")
    PRIMARY_BLUE = colors.HexColor("#3B82F6")
    TEXT_MAIN = colors.HexColor("#1E293B")
    TEXT_MUTED = colors.HexColor("#64748B")
    BORDER_COLOR = colors.HexColor("#CBD5E1")

    # Typography Styles
    title_style = ParagraphStyle(
        "DocTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=20,
        leading=24,
        textColor=PRIMARY_BLUE,
        spaceAfter=4,
    )
    subtitle_style = ParagraphStyle(
        "DocSubTitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10,
        leading=14,
        textColor=TEXT_MUTED,
        spaceAfter=12,
    )
    h1_style = ParagraphStyle(
        "SectionH1",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=16,
        textColor=colors.HexColor("#0F172A"),
        spaceBefore=14,
        spaceAfter=6,
        keepWithNext=True,
    )
    body_style = ParagraphStyle(
        "BodyTextCustom",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=12,
        textColor=TEXT_MAIN,
    )
    code_style = ParagraphStyle(
        "CodeTextCustom",
        parent=styles["Normal"],
        fontName="Courier",
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#334155"),
    )
    table_cell = ParagraphStyle(
        "TableCell",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8,
        leading=10,
        textColor=TEXT_MAIN,
    )
    table_cell_bold = ParagraphStyle(
        "TableCellBold",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=10,
        textColor=TEXT_MAIN,
    )
    table_cell_code = ParagraphStyle(
        "TableCellCode",
        parent=styles["Normal"],
        fontName="Courier",
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#0F172A"),
    )

    story = []

    # ---------------------------------------------------------------------------
    # HEADER & DOCUMENT COVER SUMMARY
    # ---------------------------------------------------------------------------
    story.append(Paragraph("AeroGuard Operational Incident Report", title_style))
    story.append(Paragraph("Compliance Archival & Operational Review Document", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=PRIMARY_BLUE, spaceAfter=10))

    # Meta Overview Grid Table
    meta_data = [
        [
            Paragraph("EXPORT IDENTIFIER:", table_cell_bold),
            Paragraph(export_number, table_cell_code),
            Paragraph("GENERATED AT:", table_cell_bold),
            Paragraph(format_timestamp(generated_at), table_cell),
        ],
        [
            Paragraph("REQUESTED BY:", table_cell_bold),
            Paragraph(requested_by, table_cell_code),
            Paragraph("TOTAL INCIDENTS:", table_cell_bold),
            Paragraph(str(len(incidents)), table_cell_bold),
        ],
        [
            Paragraph("TIME PRESET / RANGE:", table_cell_bold),
            Paragraph(f"{filter_params.get('start') or 'ALL'} to {filter_params.get('end') or 'NOW'}", table_cell),
            Paragraph("FILTERS APPLIED:", table_cell_bold),
            Paragraph(
                f"Sev: {filter_params.get('severity') or 'ANY'} | Stat: {filter_params.get('status') or 'ANY'}",
                table_cell,
            ),
        ],
    ]
    meta_table = Table(meta_data, colWidths=[1.3 * inch, 2.4 * inch, 1.3 * inch, 2.4 * inch])
    meta_table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
            ("BORDER", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
            ("PADDING", (0, 0), (-1, -1), 5),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ])
    )
    story.append(meta_table)
    story.append(Spacer(1, 12))

    # ---------------------------------------------------------------------------
    # SECTION 1 — EXECUTIVE SUMMARY METRICS
    # ---------------------------------------------------------------------------
    story.append(Paragraph("1. Executive Incident Summary Metrics", h1_style))

    crit_cnt = sum(1 for i in incidents if i.severity == IncidentSeverity.CRITICAL)
    high_cnt = sum(1 for i in incidents if i.severity == IncidentSeverity.HIGH)
    med_cnt = sum(1 for i in incidents if i.severity == IncidentSeverity.MEDIUM)
    low_cnt = sum(1 for i in incidents if i.severity == IncidentSeverity.LOW)

    new_cnt = sum(1 for i in incidents if i.status == IncidentStatus.NEW)
    ack_cnt = sum(1 for i in incidents if i.status == IncidentStatus.ACKNOWLEDGED)
    triaged_cnt = sum(1 for i in incidents if i.status == IncidentStatus.TRIAGED)
    esc_cnt = sum(1 for i in incidents if i.status == IncidentStatus.ESCALATED)
    res_cnt = sum(1 for i in incidents if i.status == IncidentStatus.RESOLVED)
    cls_cnt = sum(1 for i in incidents if i.status == IncidentStatus.CLOSED)

    metrics_data = [
        [
            Paragraph("SEVERITY DISTRIBUTION", table_cell_bold),
            Paragraph("LIFECYCLE STATE DISTRIBUTION", table_cell_bold),
        ],
        [
            Paragraph(
                f"• CRITICAL: <b>{crit_cnt}</b><br/>"
                f"• HIGH: <b>{high_cnt}</b><br/>"
                f"• MEDIUM: <b>{med_cnt}</b><br/>"
                f"• LOW: <b>{low_cnt}</b>",
                table_cell,
            ),
            Paragraph(
                f"• NEW: <b>{new_cnt}</b> | ACKNOWLEDGED: <b>{ack_cnt}</b><br/>"
                f"• TRIAGED: <b>{triaged_cnt}</b> | ESCALATED: <b>{esc_cnt}</b><br/>"
                f"• RESOLVED: <b>{res_cnt}</b> | CLOSED: <b>{cls_cnt}</b>",
                table_cell,
            ),
        ],
    ]
    metrics_table = Table(metrics_data, colWidths=[3.7 * inch, 3.7 * inch])
    metrics_table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EFF6FF")),
            ("BORDER", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
            ("PADDING", (0, 0), (-1, -1), 6),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ])
    )
    story.append(metrics_table)
    story.append(Spacer(1, 14))

    # ---------------------------------------------------------------------------
    # SECTION 2 — PROCEDURAL ACTION TALLIES
    # ---------------------------------------------------------------------------
    story.append(Paragraph("2. Procedural Defensive Action Review", h1_style))

    action_tallies: dict[str, int] = {}
    total_actions = 0
    for inc in incidents:
        events = getattr(inc, "events", []) or []
        for e in events:
            if getattr(e, "event_type", None) == IncidentEventType.ACTION_LOGGED:
                cat = getattr(e, "category", "OTHER") or "OTHER"
                action_tallies[str(cat)] = action_tallies.get(str(cat), 0) + 1
                total_actions += 1

    proc_summary_text = (
        f"Total procedural defensive actions recorded across reporting period: <b>{total_actions}</b>.<br/>"
        + " • ".join([f"<b>{k}</b>: {v}" for k, v in sorted(action_tallies.items())])
        if action_tallies
        else "No procedural defensive actions recorded in selected period."
    )
    story.append(Paragraph(proc_summary_text, body_style))
    story.append(Spacer(1, 14))

    # ---------------------------------------------------------------------------
    # SECTION 3 — DETAILED INCIDENT & TIMELINE RECORDS
    # ---------------------------------------------------------------------------
    story.append(Paragraph(f"3. Operational Incident Records ({len(incidents)} Incidents)", h1_style))

    if not incidents:
        story.append(Paragraph("<i>No operational incident records matched filter criteria.</i>", body_style))
    else:
        for idx, inc in enumerate(incidents, start=1):
            inc_blocks = []

            # Incident Header Sub-Table
            track_ref = inc.primary_track_id or "N/A"
            group_ref = inc.primary_group_id or "N/A"
            assignee_ref = inc.assigned_to or "Unassigned"

            inc_header_data = [
                [
                    Paragraph(f"<b>#{idx} {inc.incident_number}: {inc.title}</b>", table_cell_bold),
                    Paragraph(f"SEVERITY: <b>{inc.severity}</b> | STATUS: <b>{inc.status}</b>", table_cell_bold),
                ],
                [
                    Paragraph(f"CREATED: {format_timestamp(inc.created_at)}<br/>TRACK: <code>{track_ref}</code> | SWARM: <code>{group_ref}</code>", table_cell),
                    Paragraph(f"ASSIGNEE: {assignee_ref}<br/>SOURCE: {inc.source}", table_cell),
                ],
            ]
            inc_table = Table(inc_header_data, colWidths=[4.4 * inch, 3.0 * inch])
            inc_table.setStyle(
                TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F1F5F9")),
                    ("BORDER", (0, 0), (-1, -1), 0.5, colors.HexColor("#94A3B8")),
                    ("PADDING", (0, 0), (-1, -1), 5),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ])
            )
            inc_blocks.append(inc_table)

            # Timeline Events Table
            events = getattr(inc, "events", []) or []
            sorted_events = sorted(events, key=lambda e: (e.sequence, e.timestamp))

            if sorted_events:
                event_rows = [
                    [
                        Paragraph("SEQ", table_cell_bold),
                        Paragraph("TIMESTAMP", table_cell_bold),
                        Paragraph("EVENT TYPE", table_cell_bold),
                        Paragraph("ACTOR / SUMMARY", table_cell_bold),
                    ]
                ]
                for evt in sorted_events:
                    msg_text = evt.message or (f"Category: {evt.category}" if evt.category else "—")
                    actor_str = evt.actor_user_id or "SYSTEM"
                    event_rows.append([
                        Paragraph(str(evt.sequence), table_cell_code),
                        Paragraph(format_timestamp(evt.timestamp), table_cell_code),
                        Paragraph(str(evt.event_type), table_cell_bold),
                        Paragraph(f"[{actor_str}] {msg_text}", table_cell),
                    ])

                evt_table = Table(event_rows, colWidths=[0.5 * inch, 1.8 * inch, 1.8 * inch, 3.3 * inch])
                evt_table.setStyle(
                    TableStyle([
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F8FAFC")),
                        ("BORDER", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
                        ("PADDING", (0, 0), (-1, -1), 4),
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ])
                )
                inc_blocks.append(evt_table)

            inc_blocks.append(Spacer(1, 10))
            story.append(KeepTogether(inc_blocks))

    # ---------------------------------------------------------------------------
    # SECTION 4 — AUDIT PROVENANCE & INTEGRITY FOOTER
    # ---------------------------------------------------------------------------
    story.append(Spacer(1, 10))
    story.append(Paragraph("4. Audit Provenance & Document Integrity", h1_style))
    audit_text = (
        f"This document is an authoritative export generated by AeroGuard Engine.<br/>"
        f"Export Number: <b>{export_number}</b> | Requested By: <b>{requested_by}</b><br/>"
        f"<i>Note: The SHA-256 integrity checksum for this document is computed over the exact final serialized PDF byte stream upon completion.</i>"
    )
    story.append(Paragraph(audit_text, body_style))

    # Build PDF Document
    doc.build(story, canvasmaker=NumberedCanvas)
    return buffer.getvalue()
