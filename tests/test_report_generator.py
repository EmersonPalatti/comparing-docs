from src.models import Subject, SubjectMatch
from io import BytesIO
from src.report_generator import (
    final_review_report_to_xlsx,
    match_alerts,
    match_priority,
    matches_to_dataframe,
    matches_to_detailed_display_dataframe,
    matches_to_summary_dataframe,
    sanitize_spreadsheet_cell,
)


def test_matches_to_summary_dataframe_formats_final_score_as_percent():
    match = SubjectMatch(
        previous_subject=Subject(name="Bioquimica Metabolica", source_document="previous.pdf", workload_hours=80),
        current_subject=Subject(name="Bioquimica Geral", source_document="current.pdf", workload_hours=80),
        semantic_similarity=0.8,
        name_similarity=0.75,
        workload_score=1.0,
        credit_score=None,
        final_score=0.8213,
        classification="likely_equivalency",
        requires_manual_review=True,
    )

    dataframe = matches_to_summary_dataframe([match])

    assert dataframe.columns.tolist() == [
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
    assert dataframe.loc[0, "Selecionar"] == False
    assert dataframe.loc[0, "Equivalência"] == "82.13%"
    assert dataframe.loc[0, "Compatibilidade CH"] == "1.00"
    assert dataframe.loc[0, "Classificação"] == "Provável equivalência, revisar manualmente"
    assert dataframe.loc[0, "Revisão manual"] == "Sim"
    assert dataframe.loc[0, "Prioridade"] == "Alta"
    assert "Revisar escopo" in dataframe.loc[0, "Alertas"]


def test_matches_to_detailed_display_dataframe_keeps_technical_columns():
    match = SubjectMatch(
        previous_subject=Subject(name="Farmacologia Geral", source_document="previous.pdf", workload_hours=80),
        current_subject=Subject(name="Parasitologia Clinica", source_document="current.pdf", workload_hours=80),
        semantic_similarity=0.25,
        name_similarity=0.2,
        workload_score=1.0,
        credit_score=None,
        final_score=0.4731,
        classification="no_match",
        requires_manual_review=True,
    )

    raw = matches_to_dataframe([match])
    display = matches_to_detailed_display_dataframe([match])

    assert raw.loc[0, "Equivalência"] == 0.4731
    assert display.loc[0, "Equivalência"] == "0.47"
    assert display.loc[0, "Classificação"] == "Nenhuma equivalência forte encontrada"
    assert "Justificativa" in display.columns


def test_alerts_detect_similar_name_with_lower_workload():
    match = SubjectMatch(
        previous_subject=Subject(name="Anatomia Humana", source_document="previous.pdf", workload_hours=80),
        current_subject=Subject(name="Anatomia Humana", source_document="current.pdf", workload_hours=100),
        semantic_similarity=0.7,
        name_similarity=1.0,
        workload_score=0.8,
        credit_score=None,
        final_score=0.76,
        classification="likely_equivalency",
        requires_manual_review=True,
    )

    assert "Nome muito similar e carga menor" in match_alerts(match)
    assert "Carga um pouco menor" in match_alerts(match)
    assert match_priority(match) == "Alta"


def test_alerts_detect_missing_workload_and_low_score():
    match = SubjectMatch(
        previous_subject=Subject(name="Comunicacao Empresarial", source_document="previous.pdf"),
        current_subject=Subject(name="Calculo Diferencial", source_document="current.pdf", workload_hours=80),
        semantic_similarity=0.1,
        name_similarity=0.1,
        workload_score=None,
        credit_score=None,
        final_score=0.25,
        classification="no_match",
        requires_manual_review=True,
    )

    assert "Carga não identificada" in match_alerts(match)
    assert "Sem match forte" in match_alerts(match)
    assert match_priority(match) == "Baixa"


def test_final_review_report_to_xlsx_creates_expected_sheets():
    selected = matches_to_summary_dataframe(
        [
            SubjectMatch(
                previous_subject=Subject(name="Bioquimica Metabolica", source_document="previous.pdf", workload_hours=80),
                current_subject=Subject(name="Bioquimica Geral", source_document="current.pdf", workload_hours=80),
                semantic_similarity=0.8,
                name_similarity=0.75,
                workload_score=1.0,
                credit_score=None,
                final_score=0.8213,
                classification="likely_equivalency",
                requires_manual_review=True,
            )
        ]
    )
    selected.loc[0, "Selecionar"] = True
    selected.loc[0, "Observação do revisor"] = "Enviar para análise."

    workbook = final_review_report_to_xlsx(
        selected,
        previous_subjects=[
            Subject(name="Bioquimica Metabolica", source_document="previous.pdf", workload_hours=80),
            Subject(name="Farmacologia Geral", source_document="previous.pdf", workload_hours=80),
        ],
        current_subjects=[
            Subject(name="Bioquimica Geral", source_document="current.pdf", workload_hours=80),
            Subject(name="Hematologia Básica", source_document="current.pdf", workload_hours=80),
        ],
    )

    import pandas as pd

    sheets = pd.read_excel(BytesIO(workbook), sheet_name=None)

    assert set(sheets) == {"matches_selecionados", "anteriores_sem_match", "atuais_nao_usadas"}
    assert sheets["matches_selecionados"].loc[0, "Observação do revisor"] == "Enviar para análise."
    assert sheets["anteriores_sem_match"].loc[0, "Disciplina"] == "Farmacologia Geral"
    assert sheets["atuais_nao_usadas"].loc[0, "Disciplina"] == "Hematologia Básica"


def test_sanitize_spreadsheet_cell_blocks_formula_like_prefixes():
    assert sanitize_spreadsheet_cell("=HYPERLINK(\"http://example.com\")") == "'=HYPERLINK(\"http://example.com\")"
    assert sanitize_spreadsheet_cell("+cmd") == "'+cmd"
    assert sanitize_spreadsheet_cell("-1+2") == "'-1+2"
    assert sanitize_spreadsheet_cell("@SUM(A1:A2)") == "'@SUM(A1:A2)"


def test_matches_to_dataframe_sanitizes_only_text_fields():
    match = SubjectMatch(
        previous_subject=Subject(name="=HYPERLINK(\"http://bad\")", source_document="previous.pdf", workload_hours=80),
        current_subject=Subject(name="+cmd", source_document="current.pdf", workload_hours=60),
        semantic_similarity=0.8,
        name_similarity=0.75,
        workload_score=1.0,
        credit_score=None,
        final_score=0.8213,
        classification="likely_equivalency",
        requires_manual_review=True,
    )

    dataframe = matches_to_dataframe([match])

    assert dataframe.loc[0, "Disciplina anterior"] == "'=HYPERLINK(\"http://bad\")"
    assert dataframe.loc[0, "Disciplina atual"] == "'+cmd"
    assert dataframe.loc[0, "CH anterior"] == 80
    assert dataframe.loc[0, "CH atual"] == 60


def test_final_review_report_to_xlsx_sanitizes_selected_and_unmatched_text():
    selected = matches_to_summary_dataframe(
        [
            SubjectMatch(
                previous_subject=Subject(name="Disciplina Segura", source_document="previous.pdf", workload_hours=80),
                current_subject=Subject(name="Atual Segura", source_document="current.pdf", workload_hours=80),
                semantic_similarity=0.8,
                name_similarity=0.75,
                workload_score=1.0,
                credit_score=None,
                final_score=0.8213,
                classification="likely_equivalency",
                requires_manual_review=True,
            )
        ]
    )
    selected.loc[0, "Selecionar"] = True
    selected.loc[0, "Observação do revisor"] = "@SUM(A1:A2)"

    workbook = final_review_report_to_xlsx(
        selected,
        previous_subjects=[Subject(name="-1+2", source_document="=prev.pdf", workload_hours=80)],
        current_subjects=[Subject(name="+cmd", source_document="@curr.pdf", workload_hours=80)],
    )

    import pandas as pd

    sheets = pd.read_excel(BytesIO(workbook), sheet_name=None)

    assert sheets["matches_selecionados"].loc[0, "Observação do revisor"] == "'@SUM(A1:A2)"
    assert sheets["anteriores_sem_match"].loc[0, "Disciplina"] == "'-1+2"
    assert sheets["anteriores_sem_match"].loc[0, "Documento fonte"] == "'=prev.pdf"
    assert sheets["atuais_nao_usadas"].loc[0, "Disciplina"] == "'+cmd"
