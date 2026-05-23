from src.subject_parser import analyze_lines, parse_subjects
from src.subject_table import (
    apply_review_dataframe,
    edit_dataframe_to_subjects,
    subjects_to_edit_dataframe,
    subjects_to_review_dataframe,
)


def test_parse_simple_structured_subjects():
    text = """
    Estatistica Descritiva - 80h
    Conteudo: medidas de tendencia central, dispersao, graficos.

    Banco de Dados - 40h
    Conteudo: modelo relacional, SQL basico.
    """

    subjects = parse_subjects(text, "sample.txt")

    assert len(subjects) == 2
    assert subjects[0].name == "Estatistica Descritiva"
    assert subjects[0].workload_hours == 80
    assert "medidas" in subjects[0].syllabus


def test_parse_pdf_extracted_code_table_subjects():
    text = """
    Código Disciplina CH Período Nota Situação
    Anatomia e
    fundamentos de
    BIO101 Histologia 100h 1º - A cursar
    histologia dos
    Humana
    tecidos epitelial,
    Organização da
    célula
    BIO102 Biologia Celular 60h 1º - A cursar organelas,
    citoesqueleto,
    Química
    base, tampões,
    BIO103 Aplicada à 60h 1º - A cursar
    reações
    Saúde
    Conteúdo programático simplificado
    """

    subjects = parse_subjects(text, "pdf_sample.pdf")

    assert [subject.name for subject in subjects] == [
        "Anatomia e Histologia Humana",
        "Biologia Celular",
        "Química Aplicada à Saúde",
    ]
    assert [subject.workload_hours for subject in subjects] == [100, 60, 60]


def test_analyze_lines_marks_codes_and_workloads():
    lines = analyze_lines("BIO102 Biologia Celular 60h 1º - A cursar organelas,")

    assert len(lines) == 1
    assert lines[0].has_subject_code is True
    assert lines[0].has_workload is True


def test_code_table_parser_stops_before_program_content_section():
    text = """
    Farmacologia interações
    FAR401 80h 4º 8,0 Aprovado
    Geral medicamentosas
    Conteúdo programático simplificado
    Farmacologia Geral dose-resposta; receptores; efeitos adversos.
    """

    subjects = parse_subjects(text, "sample.pdf")

    assert len(subjects) == 1
    assert subjects[0].name == "Farmacologia Geral"
    assert "Conteúdo programático" not in (subjects[0].raw_text or "")


def test_edit_dataframe_to_subjects_ignores_blank_rows_and_normalizes():
    subjects = parse_subjects("Disciplina: Estat. Descritiva - 80h", "sample.txt")
    dataframe = subjects_to_edit_dataframe(subjects)
    dataframe.loc[0, "name"] = "Estatística Descritiva"
    dataframe.loc[1, "name"] = ""

    edited_subjects = edit_dataframe_to_subjects(dataframe, "fallback.txt")

    assert len(edited_subjects) == 1
    assert edited_subjects[0].name == "Estatística Descritiva"
    assert edited_subjects[0].normalized_name == "estatistica descritiva"


def test_review_dataframe_preserves_hidden_subject_data():
    subjects = parse_subjects(
        "Disciplina: Bioquimica Metabolica - 80h\nConteudo: enzimas e metabolismo energetico.",
        "sample.txt",
    )
    original = subjects_to_edit_dataframe(subjects)
    review = subjects_to_review_dataframe(subjects)
    review.loc[0, "Disciplina"] = "Bioquimica Geral"
    review.loc[0, "Carga Horaria"] = 60

    updated = apply_review_dataframe(original, review, "fallback.txt")
    edited_subjects = edit_dataframe_to_subjects(updated, "fallback.txt")

    assert edited_subjects[0].name == "Bioquimica Geral"
    assert edited_subjects[0].workload_hours == 60
    assert "enzimas" in (edited_subjects[0].syllabus or "")
