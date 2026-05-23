from __future__ import annotations

from datetime import datetime
from io import BytesIO
from typing import Any

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from src.config import DISCLAIMER_PT
from src.models import Subject
from src.report_generator import subjects_without_selected_match


MATCH_COLUMNS = [
    "Disciplina anterior",
    "CH anterior",
    "Disciplina atual",
    "CH atual",
    "Dif. CH",
    "Equivalência",
    "Classificação",
    "Alertas",
    "Observação",
]


def generate_selected_pdf_report(
    selected_matches: pd.DataFrame,
    previous_subjects: list[Subject],
    current_subjects: list[Subject],
    previous_source: str = "Documento anterior",
    current_source: str = "Documento atual",
) -> bytes:
    previous_without_selection = subjects_without_selected_match(
        previous_subjects,
        selected_matches,
        subject_column="Disciplina anterior",
    )
    current_not_used = subjects_without_selected_match(
        current_subjects,
        selected_matches,
        subject_column="Disciplina atual",
    )

    output = BytesIO()
    document = SimpleDocTemplate(
        output,
        pagesize=landscape(A4),
        rightMargin=1.2 * cm,
        leftMargin=1.2 * cm,
        topMargin=1.0 * cm,
        bottomMargin=1.0 * cm,
        title="Relatorio de equivalencia academica",
    )
    styles = build_styles()
    story: list[Any] = []

    story.extend(build_header(styles, previous_source, current_source))
    story.extend(build_summary(styles, selected_matches, previous_without_selection, current_not_used))
    story.extend(
        build_matches_section(
            styles,
            selected_matches,
            title="Matches selecionados pela pessoa revisora",
        )
    )
    story.append(PageBreak())
    story.extend(
        build_subject_section(
            styles,
            previous_without_selection,
            title="Disciplinas anteriores sem match selecionado",
        )
    )
    story.extend(
        build_subject_section(
            styles,
            current_not_used,
            title="Disciplinas atuais não usadas nos matches selecionados",
        )
    )

    document.build(story, onFirstPage=draw_footer, onLaterPages=draw_footer)
    return output.getvalue()


def build_styles():
    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name="ReportTitle",
            parent=styles["Title"],
            fontSize=18,
            leading=22,
            alignment=TA_CENTER,
            spaceAfter=8,
        )
    )
    styles.add(
        ParagraphStyle(
            name="SectionTitle",
            parent=styles["Heading2"],
            fontSize=12,
            leading=15,
            spaceBefore=10,
            spaceAfter=6,
        )
    )
    styles.add(
        ParagraphStyle(
            name="Small",
            parent=styles["BodyText"],
            fontSize=8,
            leading=10,
        )
    )
    styles.add(
        ParagraphStyle(
            name="TableCell",
            parent=styles["BodyText"],
            fontSize=7,
            leading=8,
        )
    )
    return styles


def build_header(styles, previous_source: str, current_source: str) -> list[Any]:
    generated_at = datetime.now().strftime("%d/%m/%Y %H:%M")
    return [
        Paragraph("Relatório de análise de equivalência acadêmica", styles["ReportTitle"]),
        Paragraph(f"<b>Gerado em:</b> {generated_at}", styles["Small"]),
        Paragraph(f"<b>Documento anterior:</b> {escape_text(previous_source)}", styles["Small"]),
        Paragraph(f"<b>Documento atual:</b> {escape_text(current_source)}", styles["Small"]),
        Spacer(1, 6),
        Paragraph(DISCLAIMER_PT, styles["Small"]),
        Spacer(1, 8),
    ]


def build_summary(styles, selected_matches: pd.DataFrame, previous_without: pd.DataFrame, current_not_used: pd.DataFrame):
    manual_count = int((selected_matches.get("Revisão manual", pd.Series(dtype=str)) == "Sim").sum())
    data = [
        ["Matches selecionados", "Anteriores sem match", "Atuais não usadas", "Selecionados com revisão manual"],
        [len(selected_matches), len(previous_without), len(current_not_used), manual_count],
    ]
    table = Table(data, colWidths=[5.0 * cm, 5.0 * cm, 5.0 * cm, 6.0 * cm])
    table.setStyle(summary_table_style())
    return [Paragraph("Resumo", styles["SectionTitle"]), table, Spacer(1, 8)]


def build_matches_section(styles, selected_matches: pd.DataFrame, title: str) -> list[Any]:
    story: list[Any] = [Paragraph(title, styles["SectionTitle"])]
    if selected_matches.empty:
        story.append(Paragraph("Nenhum match foi selecionado.", styles["Small"]))
        return story

    rows = [MATCH_COLUMNS]
    for _, row in selected_matches.iterrows():
        rows.append(
            [
                cell(styles, row.get("Disciplina anterior")),
                row.get("CH anterior", ""),
                cell(styles, row.get("Disciplina atual")),
                row.get("CH atual", ""),
                workload_difference(row.get("CH anterior"), row.get("CH atual")),
                row.get("Equivalência", ""),
                cell(styles, row.get("Classificação")),
                cell(styles, row.get("Alertas")),
                cell(styles, row.get("Observação do revisor")),
            ]
        )

    table = Table(
        rows,
        repeatRows=1,
        colWidths=[3.8 * cm, 1.7 * cm, 3.8 * cm, 1.6 * cm, 1.5 * cm, 2.0 * cm, 3.4 * cm, 4.0 * cm, 4.2 * cm],
    )
    table.setStyle(report_table_style())
    story.append(table)
    return story


def build_subject_section(styles, dataframe: pd.DataFrame, title: str) -> list[Any]:
    story: list[Any] = [Paragraph(title, styles["SectionTitle"])]
    if dataframe.empty:
        story.append(Paragraph("Nenhuma disciplina nesta seção.", styles["Small"]))
        story.append(Spacer(1, 8))
        return story

    rows = [["Disciplina", "Carga horária"]]
    for _, row in dataframe.iterrows():
        rows.append([cell(styles, row.get("Disciplina")), row.get("Carga horária", "")])

    table = Table(rows, repeatRows=1, colWidths=[12.0 * cm, 3.0 * cm])
    table.setStyle(report_table_style())
    story.extend([table, Spacer(1, 8)])
    return story


def cell(styles, value: object) -> Paragraph:
    return Paragraph(escape_text(value), styles["TableCell"])


def escape_text(value: object) -> str:
    if value is None or pd.isna(value):
        return ""
    text = str(value)
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace("\n", "<br/>")
    )


def workload_difference(previous_workload: object, current_workload: object) -> str:
    previous = parse_number(previous_workload)
    current = parse_number(current_workload)
    if previous is None or current is None:
        return "Não calculada"
    difference = previous - current
    if difference > 0:
        return f"+{difference:g}h"
    return f"{difference:g}h"


def parse_number(value: object) -> float | None:
    if value is None or pd.isna(value) or value == "":
        return None
    try:
        return float(str(value).replace(",", "."))
    except ValueError:
        return None


def report_table_style() -> TableStyle:
    return TableStyle(
        [
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E5E7EB")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#111827")),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 8),
            ("FONTSIZE", (0, 1), (-1, -1), 7),
            ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#CBD5E1")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8FAFC")]),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ]
    )


def summary_table_style() -> TableStyle:
    return TableStyle(
        [
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E5E7EB")),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#CBD5E1")),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
        ]
    )


def draw_footer(canvas, document):
    canvas.saveState()
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(colors.HexColor("#64748B"))
    canvas.drawString(1.2 * cm, 0.55 * cm, "Relatório automatizado para apoio à revisão acadêmica. Não representa decisão oficial.")
    canvas.drawRightString(landscape(A4)[0] - 1.2 * cm, 0.55 * cm, f"Página {document.page}")
    canvas.restoreState()
