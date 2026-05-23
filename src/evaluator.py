from __future__ import annotations

from src.config import CLASSIFICATION_LABELS_PT
from src.models import SubjectMatch


def classification_label(classification: str) -> str:
    return CLASSIFICATION_LABELS_PT.get(classification, classification)


def concise_justification(match: SubjectMatch) -> str:
    parts = [
        f"Similaridade do nome: {match.name_similarity:.2f}.",
        f"Pontuação final: {match.final_score:.2f}.",
    ]
    if match.semantic_similarity is not None:
        parts.append(f"Similaridade de conteúdo: {match.semantic_similarity:.2f}.")
    if match.workload_score is None:
        parts.append("Carga horária ausente em ao menos uma disciplina; revisão manual recomendada.")
    elif match.workload_score < 0.8:
        parts.append("A carga horária anterior é inferior à atual, reduzindo a confiança.")
    return " ".join(parts)
