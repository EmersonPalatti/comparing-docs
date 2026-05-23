from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class Subject:
    name: str
    source_document: str
    workload_hours: Optional[int] = None
    credits: Optional[float] = None
    semester: Optional[str] = None
    status: Optional[str] = None
    grade: Optional[str] = None
    syllabus: Optional[str] = None
    raw_text: Optional[str] = None
    normalized_name: Optional[str] = None
    normalized_syllabus: Optional[str] = None
    embedding_text: Optional[str] = None


@dataclass
class SubjectMatch:
    previous_subject: Subject
    current_subject: Subject
    semantic_similarity: Optional[float]
    name_similarity: float
    workload_score: Optional[float]
    credit_score: Optional[float]
    final_score: float
    classification: str
    requires_manual_review: bool
    justification: Optional[str] = None
