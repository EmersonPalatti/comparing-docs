from __future__ import annotations

import re
import unicodedata

from src.models import Subject


ABBREVIATIONS = {
    r"\bmat\.?\b": "matematica",
    r"\bestat\.?\b": "estatistica",
    r"\bintro\.?\b": "introducao",
    r"\bprog\.?\b": "programacao",
    r"\badm\.?\b": "administracao",
}


def strip_accents(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    return "".join(char for char in normalized if not unicodedata.combining(char))


def normalize_text(value: str | None) -> str:
    if not value:
        return ""
    text = strip_accents(value).lower()
    for pattern, replacement in ABBREVIATIONS.items():
        text = re.sub(pattern, replacement, text)
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def build_embedding_text(subject: Subject) -> str:
    parts = [f"Subject: {subject.name}"]
    if subject.workload_hours is not None:
        parts.append(f"Workload: {subject.workload_hours}")
    if subject.credits is not None:
        parts.append(f"Credits: {subject.credits}")
    if subject.syllabus:
        parts.append(f"Syllabus: {subject.syllabus}")
    return "\n".join(parts)


def normalize_subject(subject: Subject) -> Subject:
    subject.normalized_name = normalize_text(subject.name)
    subject.normalized_syllabus = normalize_text(subject.syllabus)
    subject.embedding_text = build_embedding_text(subject)
    return subject


def normalize_subjects(subjects: list[Subject]) -> list[Subject]:
    return [normalize_subject(subject) for subject in subjects]
