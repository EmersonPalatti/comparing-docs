from __future__ import annotations

from io import BytesIO

import pandas as pd

from src.evaluator import classification_label, concise_justification
from src.models import Subject
from src.models import SubjectMatch


SUMMARY_COLUMNS = [
    "Selecionar",
    "Disciplina anterior",
    "CH anterior",
    "Disciplina atual",
    "CH atual",
    "Prioridade",
    "Alertas",
    "Compatibilidade CH",
    "Equivalência",
    "Classificação",
    "Revisão manual",
    "Observação do revisor",
]

DETAILED_SCORE_COLUMNS = [
    "Similaridade semântica",
    "Similaridade do nome",
    "Compatibilidade CH",
    "Compatibilidade créditos",
    "Equivalência",
]


def matches_to_dataframe(matches: list[SubjectMatch]) -> pd.DataFrame:
    rows = []
    for match in matches:
        rows.append(
            {
                "Disciplina anterior": match.previous_subject.name,
                "CH anterior": match.previous_subject.workload_hours,
                "Disciplina atual": match.current_subject.name,
                "CH atual": match.current_subject.workload_hours,
                "Selecionar": False,
                "Similaridade semântica": match.semantic_similarity,
                "Similaridade do nome": match.name_similarity,
                "Compatibilidade CH": match.workload_score,
                "Compatibilidade créditos": match.credit_score,
                "Equivalência": match.final_score,
                "Classificação": classification_label(match.classification),
                "Revisão manual": "Sim" if match.requires_manual_review else "Não",
                "Prioridade": match_priority(match),
                "Alertas": " | ".join(match_alerts(match)),
                "Observação do revisor": "",
                "Justificativa": match.justification or concise_justification(match),
            }
        )
    return pd.DataFrame(rows)


def matches_to_detailed_display_dataframe(matches: list[SubjectMatch]) -> pd.DataFrame:
    detailed = matches_to_dataframe(matches)
    if detailed.empty:
        return detailed

    display = detailed.copy()
    for column in DETAILED_SCORE_COLUMNS:
        if column in display.columns:
            display[column] = display[column].map(format_optional_score)
    return display


def matches_to_summary_dataframe(matches: list[SubjectMatch]) -> pd.DataFrame:
    detailed = matches_to_dataframe(matches)
    if detailed.empty:
        return pd.DataFrame(columns=SUMMARY_COLUMNS)

    summary = detailed[SUMMARY_COLUMNS].copy()
    summary["Compatibilidade CH"] = summary["Compatibilidade CH"].map(format_optional_score)
    summary["Equivalência"] = summary["Equivalência"].map(format_percent)
    return summary


def match_alerts(match: SubjectMatch) -> list[str]:
    alerts: list[str] = []
    previous_hours = match.previous_subject.workload_hours
    current_hours = match.current_subject.workload_hours

    if match.name_similarity >= 0.80 and previous_hours is not None and current_hours is not None and previous_hours < current_hours:
        alerts.append("Nome muito similar e carga menor")

    if match.workload_score is None:
        alerts.append("Carga não identificada")
    elif match.workload_score <= 0.20:
        alerts.append("Carga insuficiente")
    elif match.workload_score <= 0.50:
        alerts.append("Carga significativamente menor")
    elif match.workload_score < 1.00:
        alerts.append("Carga um pouco menor")

    if match.final_score >= 0.85:
        alerts.append("Boa similaridade")
    elif match.final_score < 0.50:
        alerts.append("Sem match forte")

    if match.requires_manual_review and match.final_score >= 0.70:
        alerts.append("Revisar escopo")

    return alerts or ["Sem alerta específico"]


def match_priority(match: SubjectMatch) -> str:
    alerts = set(match_alerts(match))
    if "Nome muito similar e carga menor" in alerts:
        return "Alta"
    if match.final_score >= 0.70 and match.requires_manual_review:
        return "Alta"
    if match.final_score >= 0.50:
        return "Média"
    return "Baixa"


def format_percent(value: float | int | None) -> str:
    if value is None or pd.isna(value):
        return ""
    return f"{float(value) * 100:.2f}%"


def format_optional_score(value: float | int | None) -> str:
    if value is None or pd.isna(value):
        return ""
    return f"{float(value):.2f}"


def dataframe_to_xlsx(dataframe: pd.DataFrame) -> bytes:
    safe_dataframe = sanitize_excel_dataframe(dataframe)
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        safe_dataframe.to_excel(writer, index=False, sheet_name="equivalencias")
    return output.getvalue()


def final_review_report_to_xlsx(
    selected_matches: pd.DataFrame,
    previous_subjects: list[Subject],
    current_subjects: list[Subject],
) -> bytes:
    selected = sanitize_excel_dataframe(selected_matches)
    previous_without_selection = subjects_without_selected_match(
        previous_subjects,
        selected,
        subject_column="Disciplina anterior",
    )
    current_not_used = subjects_without_selected_match(
        current_subjects,
        selected,
        subject_column="Disciplina atual",
    )

    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        selected.to_excel(writer, index=False, sheet_name="matches_selecionados")
        sanitize_excel_dataframe(previous_without_selection).to_excel(
            writer,
            index=False,
            sheet_name="anteriores_sem_match",
        )
        sanitize_excel_dataframe(current_not_used).to_excel(writer, index=False, sheet_name="atuais_nao_usadas")
    return output.getvalue()


def subjects_without_selected_match(
    subjects: list[Subject],
    selected_matches: pd.DataFrame,
    subject_column: str,
) -> pd.DataFrame:
    selected_keys = set()
    if subject_column in selected_matches.columns:
        selected_keys = {
            subject_key(name, workload)
            for name, workload in zip(
                selected_matches[subject_column],
                selected_matches[workload_column_for(subject_column)],
            )
        }

    rows = []
    for subject in subjects:
        if subject_key(subject.name, subject.workload_hours) in selected_keys:
            continue
        rows.append(
            {
                "Disciplina": subject.name,
                "Carga horária": subject.workload_hours,
                "Documento fonte": subject.source_document,
                "Ementa": subject.syllabus,
            }
        )
    return pd.DataFrame(rows, columns=["Disciplina", "Carga horária", "Documento fonte", "Ementa"])


def workload_column_for(subject_column: str) -> str:
    if subject_column == "Disciplina anterior":
        return "CH anterior"
    return "CH atual"


def subject_key(name: object, workload: object) -> tuple[str, str]:
    return (str(name).strip().lower(), "" if pd.isna(workload) else str(workload).strip())


FORMULA_PREFIXES = ("=", "+", "-", "@")


def sanitize_excel_dataframe(dataframe: pd.DataFrame) -> pd.DataFrame:
    safe = dataframe.copy()
    for column in safe.columns:
        safe[column] = safe[column].map(sanitize_excel_value)
    return safe


def sanitize_excel_value(value: object) -> object:
    if value is None or pd.isna(value) or isinstance(value, (bool, int, float)):
        return value
    text = str(value)
    stripped = text.lstrip()
    if stripped.startswith(FORMULA_PREFIXES):
        return f"'{text}"
    return text
