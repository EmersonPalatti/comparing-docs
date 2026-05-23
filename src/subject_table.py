from __future__ import annotations

import math
from typing import Any

import pandas as pd

from src.models import Subject
from src.normalizer import normalize_subjects


EDITABLE_COLUMNS = [
    "name",
    "workload_hours",
    "credits",
    "semester",
    "status",
    "grade",
    "syllabus",
    "source_document",
    "raw_text",
]
REVIEW_COLUMNS = ["Disciplina", "Carga Horaria"]


def subjects_to_edit_dataframe(subjects: list[Subject]) -> pd.DataFrame:
    rows = []
    for subject in subjects:
        rows.append(
            {
                "name": subject.name,
                "workload_hours": subject.workload_hours,
                "credits": subject.credits,
                "semester": subject.semester,
                "status": subject.status,
                "grade": subject.grade,
                "syllabus": subject.syllabus,
                "source_document": subject.source_document,
                "raw_text": subject.raw_text,
            }
        )
    return pd.DataFrame(rows, columns=EDITABLE_COLUMNS)


def subjects_to_review_dataframe(subjects: list[Subject]) -> pd.DataFrame:
    rows = []
    for subject in subjects:
        rows.append(
            {
                "Disciplina": subject.name,
                "Carga Horaria": subject.workload_hours,
            }
        )
    return pd.DataFrame(rows, columns=REVIEW_COLUMNS)


def apply_review_dataframe(
    original_dataframe: pd.DataFrame,
    review_dataframe: pd.DataFrame,
    fallback_source: str,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    original_rows = original_dataframe.to_dict(orient="records")

    for index, review_row in enumerate(review_dataframe.to_dict(orient="records")):
        name = clean_optional_text(review_row.get("Disciplina"))
        if not name:
            continue

        if index < len(original_rows):
            row = {column: original_rows[index].get(column) for column in EDITABLE_COLUMNS}
        else:
            row = {column: None for column in EDITABLE_COLUMNS}
            row["source_document"] = fallback_source

        row["name"] = name
        row["workload_hours"] = clean_optional_int(review_row.get("Carga Horaria"))
        rows.append(row)

    return pd.DataFrame(rows, columns=EDITABLE_COLUMNS)


def edit_dataframe_to_subjects(dataframe: pd.DataFrame, fallback_source: str) -> list[Subject]:
    subjects: list[Subject] = []
    for row in dataframe.to_dict(orient="records"):
        name = clean_optional_text(row.get("name"))
        if not name:
            continue
        subjects.append(
            Subject(
                name=name,
                source_document=clean_optional_text(row.get("source_document")) or fallback_source,
                workload_hours=clean_optional_int(row.get("workload_hours")),
                credits=clean_optional_float(row.get("credits")),
                semester=clean_optional_text(row.get("semester")),
                status=clean_optional_text(row.get("status")),
                grade=clean_optional_text(row.get("grade")),
                syllabus=clean_optional_text(row.get("syllabus")),
                raw_text=clean_optional_text(row.get("raw_text")),
            )
        )
    return normalize_subjects(subjects)


def clean_optional_text(value: Any) -> str | None:
    if value is None or is_nan(value):
        return None
    text = str(value).strip()
    return text or None


def clean_optional_int(value: Any) -> int | None:
    if value is None or is_nan(value) or value == "":
        return None
    try:
        return int(float(str(value).replace(",", ".")))
    except ValueError:
        return None


def clean_optional_float(value: Any) -> float | None:
    if value is None or is_nan(value) or value == "":
        return None
    try:
        return float(str(value).replace(",", "."))
    except ValueError:
        return None


def is_nan(value: Any) -> bool:
    return isinstance(value, float) and math.isnan(value)
