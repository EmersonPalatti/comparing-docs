from src.models import Subject, SubjectMatch
from src.pdf_report import generate_selected_pdf_report, workload_difference
from src.report_generator import matches_to_summary_dataframe


def test_workload_difference_formats_values():
    assert workload_difference(80, 100) == "-20h"
    assert workload_difference(100, 80) == "+20h"
    assert workload_difference(80, 80) == "0h"
    assert workload_difference(None, 80) == "Não calculada"


def test_generate_selected_pdf_report_returns_pdf_bytes():
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

    pdf = generate_selected_pdf_report(
        selected,
        previous_subjects=[Subject(name="Bioquimica Metabolica", source_document="previous.pdf", workload_hours=80)],
        current_subjects=[Subject(name="Bioquimica Geral", source_document="current.pdf", workload_hours=80)],
        previous_source="previous.pdf",
        current_source="current.pdf",
    )

    assert pdf.startswith(b"%PDF")
    assert len(pdf) > 1000


def test_generate_selected_pdf_report_handles_empty_selection():
    pdf = generate_selected_pdf_report(
        selected_matches=matches_to_summary_dataframe([]),
        previous_subjects=[],
        current_subjects=[],
    )

    assert pdf.startswith(b"%PDF")
