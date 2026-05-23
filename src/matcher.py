from __future__ import annotations

from difflib import SequenceMatcher

from src.embedding_service import subject_similarity_matrix
from src.models import Subject, SubjectMatch
from src.normalizer import normalize_text


STRONG_EQUIVALENCY = "strong_equivalency"
LIKELY_EQUIVALENCY = "likely_equivalency"
PARTIAL_SIMILARITY = "partial_similarity"
NO_MATCH = "no_match"


def name_similarity(previous: Subject, current: Subject) -> float:
    previous_name = previous.normalized_name or normalize_text(previous.name)
    current_name = current.normalized_name or normalize_text(current.name)
    if not previous_name or not current_name:
        return 0.0
    ratio = SequenceMatcher(None, previous_name, current_name).ratio()
    previous_tokens = set(previous_name.split())
    current_tokens = set(current_name.split())
    token_score = len(previous_tokens & current_tokens) / max(len(previous_tokens | current_tokens), 1)
    return round(max(ratio, token_score), 4)


def workload_compatibility(previous_hours: int | None, current_hours: int | None) -> float | None:
    if previous_hours is None or current_hours is None or current_hours <= 0:
        return None
    if previous_hours >= current_hours:
        return 1.0
    ratio = previous_hours / current_hours
    if ratio >= 0.8:
        return 0.8
    if ratio >= 0.6:
        return 0.5
    return 0.2


def credit_compatibility(previous_credits: float | None, current_credits: float | None) -> float | None:
    if previous_credits is None or current_credits is None or current_credits <= 0:
        return None
    if previous_credits >= current_credits:
        return 1.0
    ratio = previous_credits / current_credits
    if ratio >= 0.8:
        return 0.8
    if ratio >= 0.6:
        return 0.5
    return 0.2


def context_score(previous: Subject, current: Subject) -> float:
    previous_text = normalize_text(f"{previous.name} {previous.syllabus or ''}")
    current_text = normalize_text(f"{current.name} {current.syllabus or ''}")
    advanced_terms = {"avancado", "ii", "iii", "iv"}
    intro_terms = {"introducao", "basico", "fundamentos", "i"}
    if (set(previous_text.split()) & intro_terms) and (set(current_text.split()) & advanced_terms):
        return 0.6
    return 1.0


def weighted_score(scores: dict[str, float | None], weights: dict[str, float]) -> float:
    available = {key: value for key, value in scores.items() if value is not None}
    total_weight = sum(weights[key] for key in available)
    if total_weight == 0:
        return 0.0
    return sum(float(available[key]) * weights[key] for key in available) / total_weight


def final_score(
    previous: Subject,
    current: Subject,
    semantic_similarity: float | None,
    name_score: float,
    workload_score: float | None,
    credit_score: float | None,
    context: float,
) -> float:
    has_content = bool(previous.syllabus or current.syllabus)
    if has_content and semantic_similarity is not None:
        weights = {
            "semantic": 0.40,
            "name": 0.25,
            "workload": 0.20,
            "credit": 0.10,
            "context": 0.05,
        }
        scores = {
            "semantic": semantic_similarity,
            "name": name_score,
            "workload": workload_score,
            "credit": credit_score,
            "context": context,
        }
    else:
        weights = {"name": 0.60, "workload": 0.30, "context": 0.10}
        scores = {"name": name_score, "workload": workload_score, "context": context}

    score = weighted_score(scores, weights)
    if workload_score is None:
        score *= 0.9
    elif workload_score <= 0.5:
        score *= 0.85
    return round(min(score, 1.0), 4)


def classify(score: float) -> str:
    if score >= 0.85:
        return STRONG_EQUIVALENCY
    if score >= 0.70:
        return LIKELY_EQUIVALENCY
    if score >= 0.50:
        return PARTIAL_SIMILARITY
    return NO_MATCH


def requires_manual_review(classification: str, workload_score: float | None) -> bool:
    if classification in {LIKELY_EQUIVALENCY, PARTIAL_SIMILARITY}:
        return True
    if workload_score is None:
        return True
    return classification != STRONG_EQUIVALENCY


def compare_pair(previous: Subject, current: Subject, semantic_similarity: float | None) -> SubjectMatch:
    name_score = name_similarity(previous, current)
    workload_score = workload_compatibility(previous.workload_hours, current.workload_hours)
    credit_score = credit_compatibility(previous.credits, current.credits)
    context = context_score(previous, current)
    score = final_score(previous, current, semantic_similarity, name_score, workload_score, credit_score, context)
    classification = classify(score)
    return SubjectMatch(
        previous_subject=previous,
        current_subject=current,
        semantic_similarity=round(semantic_similarity, 4) if semantic_similarity is not None else None,
        name_similarity=name_score,
        workload_score=workload_score,
        credit_score=credit_score,
        final_score=score,
        classification=classification,
        requires_manual_review=requires_manual_review(classification, workload_score),
    )


def match_subjects(
    previous_subjects: list[Subject],
    current_subjects: list[Subject],
    top_n: int = 3,
) -> list[SubjectMatch]:
    if not previous_subjects or not current_subjects:
        return []

    semantic_matrix = subject_similarity_matrix(previous_subjects, current_subjects)
    matches: list[SubjectMatch] = []
    for previous_index, previous_subject in enumerate(previous_subjects):
        candidates = [
            compare_pair(previous_subject, current_subject, semantic_matrix[previous_index][current_index])
            for current_index, current_subject in enumerate(current_subjects)
        ]
        matches.extend(sorted(candidates, key=lambda item: item.final_score, reverse=True)[:top_n])
    return matches
