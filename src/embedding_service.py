from __future__ import annotations

from functools import lru_cache

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from src.models import Subject
from src.normalizer import normalize_text


STOPWORDS = {
    "subject",
    "workload",
    "credits",
    "syllabus",
    "disciplina",
    "conteudo",
    "ementa",
    "de",
    "da",
    "do",
    "das",
    "dos",
    "e",
    "a",
    "o",
    "i",
    "ii",
    "iii",
    "iv",
}


@lru_cache(maxsize=512)
def cached_text(value: str) -> str:
    return value


def subject_similarity_matrix(previous_subjects: list[Subject], current_subjects: list[Subject]) -> list[list[float]]:
    texts = [cached_text(subject.embedding_text or subject.name) for subject in previous_subjects + current_subjects]
    if not texts or all(not text.strip() for text in texts):
        return [[0.0 for _ in current_subjects] for _ in previous_subjects]

    vectorizer = TfidfVectorizer(ngram_range=(1, 2), min_df=1)
    matrix = vectorizer.fit_transform(texts)
    previous_matrix = matrix[: len(previous_subjects)]
    current_matrix = matrix[len(previous_subjects) :]
    similarities = cosine_similarity(previous_matrix, current_matrix).tolist()
    for previous_index, previous_subject in enumerate(previous_subjects):
        for current_index, current_subject in enumerate(current_subjects):
            token_score = token_overlap_similarity(previous_subject, current_subject)
            similarities[previous_index][current_index] = max(similarities[previous_index][current_index], token_score)
    return similarities


def token_overlap_similarity(previous: Subject, current: Subject) -> float:
    previous_tokens = meaningful_tokens(previous.embedding_text or previous.name)
    current_tokens = meaningful_tokens(current.embedding_text or current.name)
    if not previous_tokens or not current_tokens:
        return 0.0

    intersection = previous_tokens & current_tokens
    containment = len(intersection) / min(len(previous_tokens), len(current_tokens))
    jaccard = len(intersection) / len(previous_tokens | current_tokens)

    previous_name_tokens = meaningful_tokens(previous.name)
    current_name_tokens = meaningful_tokens(current.name)
    name_overlap = len(previous_name_tokens & current_name_tokens) / max(
        min(len(previous_name_tokens), len(current_name_tokens)),
        1,
    )
    if name_overlap >= 0.5 and containment >= 0.25:
        return min(1.0, max(containment, 0.75))
    return max(containment, jaccard)


def meaningful_tokens(text: str) -> set[str]:
    return {
        token
        for token in normalize_text(text).split()
        if len(token) > 2 and token not in STOPWORDS and not token.isdigit()
    }
