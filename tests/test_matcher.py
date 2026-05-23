from src.matcher import classify, match_subjects, workload_compatibility
from src.models import Subject
from src.normalizer import normalize_subjects


def make_subject(name: str, workload: int | None = None, syllabus: str | None = None) -> Subject:
    return normalize_subjects(
        [Subject(name=name, source_document="test", workload_hours=workload, syllabus=syllabus)]
    )[0]


def test_workload_compatibility_rules():
    assert workload_compatibility(80, 80) == 1.0
    assert workload_compatibility(70, 80) == 0.8
    assert workload_compatibility(50, 80) == 0.5
    assert workload_compatibility(30, 80) == 0.2
    assert workload_compatibility(None, 80) is None


def test_classification_thresholds():
    assert classify(0.85) == "strong_equivalency"
    assert classify(0.70) == "likely_equivalency"
    assert classify(0.50) == "partial_similarity"
    assert classify(0.49) == "no_match"


def test_strong_match_sample():
    previous = make_subject(
        "Estatistica Descritiva",
        80,
        "medidas de tendencia central, dispersao, graficos, distribuicao de frequencia",
    )
    current = make_subject(
        "Estatistica I",
        80,
        "estatistica descritiva, media, mediana, variancia, desvio padrao e graficos",
    )

    match = match_subjects([previous], [current], top_n=1)[0]

    assert match.classification in {"strong_equivalency", "likely_equivalency"}
    assert match.workload_score == 1.0


def test_similar_name_with_much_lower_workload_is_not_strong():
    previous = make_subject("Banco de Dados", 40, "modelo relacional, SQL basico")
    current = make_subject(
        "Banco de Dados Avancado",
        80,
        "modelagem relacional, SQL avancado, otimizacao, transacoes, indices",
    )

    match = match_subjects([previous], [current], top_n=1)[0]

    assert match.classification in {"partial_similarity", "likely_equivalency", "no_match"}
    assert match.classification != "strong_equivalency"
    assert match.requires_manual_review is True


def test_no_match_sample():
    previous = make_subject("Comunicacao Empresarial", 40)
    current = make_subject("Calculo Diferencial e Integral", 80)

    match = match_subjects([previous], [current], top_n=1)[0]

    assert match.classification == "no_match"
