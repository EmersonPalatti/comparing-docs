from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.auth import credentials_configured, credentials_match, get_expected_credentials
from src.auth import clear_login_failures, initialize_login_state, is_login_locked, register_failed_attempt
from src.config import DISCLAIMER_PT
from src.document_loader import load_document
from src.matcher import match_subjects
from src.pdf_report import generate_selected_pdf_report
from src.report_generator import (
    dataframe_to_xlsx,
    final_review_report_to_xlsx,
    matches_to_dataframe,
    matches_to_detailed_display_dataframe,
    matches_to_summary_dataframe,
)
from src.subject_parser import parse_subjects
from src.subject_table import (
    apply_review_dataframe,
    edit_dataframe_to_subjects,
    subjects_to_edit_dataframe,
    subjects_to_review_dataframe,
)
from src.text_extractor import TextExtractionError


st.set_page_config(page_title="Comparador de Equivalência Acadêmica", layout="wide")


def extract_subject_tables(previous_file, current_file):
    previous_document = load_document(previous_file, "documento_anterior")
    current_document = load_document(current_file, "documento_atual")
    previous_subjects = parse_subjects(previous_document.text, previous_document.filename)
    current_subjects = parse_subjects(current_document.text, current_document.filename)
    if not previous_subjects:
        raise ValueError("Nenhuma disciplina foi encontrada no documento anterior.")
    if not current_subjects:
        raise ValueError("Nenhuma disciplina foi encontrada no documento atual.")
    return (
        subjects_to_edit_dataframe(previous_subjects),
        subjects_to_edit_dataframe(current_subjects),
        previous_document.filename,
        current_document.filename,
    )


def run_comparison_from_tables(
    previous_original_table,
    current_original_table,
    previous_review_table,
    current_review_table,
    previous_source: str,
    current_source: str,
):
    previous_table = apply_review_dataframe(previous_original_table, previous_review_table, previous_source)
    current_table = apply_review_dataframe(current_original_table, current_review_table, current_source)
    previous_subjects = edit_dataframe_to_subjects(previous_table, previous_source)
    current_subjects = edit_dataframe_to_subjects(current_table, current_source)
    if not previous_subjects:
        raise ValueError("Nenhuma disciplina valida foi mantida no documento anterior.")
    if not current_subjects:
        raise ValueError("Nenhuma disciplina valida foi mantida no documento atual.")
    return previous_subjects, current_subjects, match_subjects(previous_subjects, current_subjects)


def main() -> None:
    if not require_login():
        return

    st.title("Comparador de Equivalência Acadêmica")
    st.write(
        "Envie dois documentos acadêmicos para obter uma tabela ranqueada de possíveis equivalências. "
        "A análise usa extração de texto, normalização, similaridade e regras de carga horária."
    )
    st.info(DISCLAIMER_PT)

    previous_file = st.file_uploader(
        "Documento anterior/original",
        type=["pdf", "xlsx", "xls", "csv", "txt", "md"],
        key="previous_file",
    )
    current_file = st.file_uploader(
        "Documento atual/destino",
        type=["pdf", "xlsx", "xls", "csv", "txt", "md"],
        key="current_file",
    )

    if st.button("Extrair disciplinas", type="primary", disabled=not (previous_file and current_file)):
        try:
            with st.spinner("Extraindo disciplinas dos documentos..."):
                previous_table, current_table, previous_source, current_source = extract_subject_tables(
                    previous_file,
                    current_file,
                )
                st.session_state["previous_subjects_df"] = previous_table
                st.session_state["current_subjects_df"] = current_table
                st.session_state["previous_review_df"] = subjects_to_review_dataframe(
                    edit_dataframe_to_subjects(previous_table, previous_source)
                )
                st.session_state["current_review_df"] = subjects_to_review_dataframe(
                    edit_dataframe_to_subjects(current_table, current_source)
                )
                st.session_state["previous_source"] = previous_source
                st.session_state["current_source"] = current_source
                st.session_state.pop("matches_df", None)
                st.session_state.pop("matches_detailed_display_df", None)
                st.session_state.pop("matches_summary_df", None)
        except (TextExtractionError, ValueError) as error:
            st.error(str(error))

    previous_table = st.session_state.get("previous_subjects_df")
    current_table = st.session_state.get("current_subjects_df")
    if previous_table is not None and current_table is not None:
        st.subheader("Revisão das disciplinas extraídas")
        st.write(
            "Revise os nomes e cargas horárias antes da comparação. Linhas com nome vazio serão ignoradas. "
            "Outros dados extraídos, como ementa e documento fonte, continuam preservados internamente."
        )

        previous_column, current_column = st.columns(2)
        with previous_column:
            st.markdown("**Documento anterior/original**")
            previous_edited = st.data_editor(
                st.session_state.get("previous_review_df"),
                key="previous_subjects_editor",
                num_rows="dynamic",
                use_container_width=True,
                hide_index=True,
                column_config=subject_review_column_config(),
            )
        with current_column:
            st.markdown("**Documento atual/destino**")
            current_edited = st.data_editor(
                st.session_state.get("current_review_df"),
                key="current_subjects_editor",
                num_rows="dynamic",
                use_container_width=True,
                hide_index=True,
                column_config=subject_review_column_config(),
            )

        if st.button("Comparar disciplinas revisadas", type="primary"):
            try:
                with st.spinner("Comparando disciplinas revisadas..."):
                    previous_subjects, current_subjects, matches = run_comparison_from_tables(
                        previous_table,
                        current_table,
                        previous_edited,
                        current_edited,
                        st.session_state.get("previous_source", "documento_anterior"),
                        st.session_state.get("current_source", "documento_atual"),
                    )
                    st.session_state["matches_df"] = matches_to_dataframe(matches)
                    st.session_state["matches_detailed_display_df"] = matches_to_detailed_display_dataframe(matches)
                    st.session_state["matches_summary_df"] = matches_to_summary_dataframe(matches)
                    st.session_state["previous_count"] = len(previous_subjects)
                    st.session_state["current_count"] = len(current_subjects)
                    st.session_state["previous_subjects"] = previous_subjects
                    st.session_state["current_subjects"] = current_subjects
            except ValueError as error:
                st.error(str(error))

    summary_dataframe = st.session_state.get("matches_summary_df")
    detailed_dataframe = st.session_state.get("matches_detailed_display_df")
    raw_dataframe = st.session_state.get("matches_df")
    if summary_dataframe is not None and detailed_dataframe is not None and raw_dataframe is not None:
        st.subheader("Resultado")
        render_result_metrics(summary_dataframe)

        classifications = sorted(summary_dataframe["Classificação"].dropna().unique().tolist())
        filter_column, alert_column, manual_column, sort_column = st.columns([2, 2, 1, 1])
        with filter_column:
            selected = st.multiselect("Filtrar por classificacao", classifications, default=classifications)
        with alert_column:
            selected_alerts = st.multiselect("Filtrar por alerta", alert_options(summary_dataframe))
        with manual_column:
            only_manual_review = st.checkbox("Somente revisão manual")
        with sort_column:
            sort_mode = st.selectbox("Ordenar por", ["Prioridade", "Score"], index=0)

        filtered_summary, filtered_detailed = filter_result_tables(
            summary_dataframe,
            detailed_dataframe,
            raw_dataframe,
            selected,
            selected_alerts,
            only_manual_review,
            sort_mode,
        )
        reviewed_summary = st.data_editor(
            style_result_table(filtered_summary),
            key="matches_review_editor",
            use_container_width=True,
            hide_index=True,
            column_config=result_review_column_config(),
            disabled=[column for column in filtered_summary.columns if column not in {"Selecionar", "Observação do revisor"}],
        )

        selected_matches = reviewed_summary[reviewed_summary["Selecionar"] == True].copy()
        download_column_a, download_column_b, download_column_c, download_column_d = st.columns(4)
        with download_column_a:
            st.download_button(
                "Baixar Excel resumido",
                data=dataframe_to_xlsx(reviewed_summary),
                file_name="equivalencias_resumidas.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        with download_column_b:
            st.download_button(
                "Baixar Excel detalhado",
                data=dataframe_to_xlsx(filtered_detailed),
                file_name="equivalencias_detalhadas.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        with download_column_c:
            st.download_button(
                "Baixar relatório selecionado",
                data=final_review_report_to_xlsx(
                    selected_matches,
                    st.session_state.get("previous_subjects", []),
                    st.session_state.get("current_subjects", []),
                ),
                file_name="relatorio_equivalencias_selecionadas.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                disabled=selected_matches.empty,
            )
        with download_column_d:
            st.download_button(
                "Baixar relatório PDF",
                data=generate_selected_pdf_report(
                    selected_matches,
                    st.session_state.get("previous_subjects", []),
                    st.session_state.get("current_subjects", []),
                    st.session_state.get("previous_source", "Documento anterior"),
                    st.session_state.get("current_source", "Documento atual"),
                ),
                file_name="relatorio_equivalencias_selecionadas.pdf",
                mime="application/pdf",
                disabled=selected_matches.empty,
            )

    st.caption(DISCLAIMER_PT)


def require_login() -> bool:
    initialize_login_state(st.session_state)

    if st.session_state.get("authenticated"):
        st.sidebar.caption(f"Logado como {st.session_state.get('authenticated_user', 'usuário')}")
        if st.sidebar.button("Sair"):
            st.session_state.pop("authenticated", None)
            st.session_state.pop("authenticated_user", None)
            st.rerun()
        return True

    expected_username, expected_password = get_expected_credentials(st.secrets)
    st.title("Login")
    st.write("Acesse a ferramenta de comparação acadêmica.")

    if not credentials_configured(expected_username, expected_password):
        st.error(
            "Login não configurado. Configure APP_USERNAME e APP_PASSWORD nas variáveis de ambiente "
            "ou em Secrets do Streamlit Cloud."
        )
        return False

    with st.form("login_form"):
        username = st.text_input("Usuário")
        password = st.text_input("Senha", type="password")
        locked, remaining = is_login_locked(st.session_state)
        if locked:
            remaining_seconds = max(1, int(remaining.total_seconds()))
            minutes, seconds = divmod(remaining_seconds, 60)
            st.warning(f"Muitas tentativas inválidas. Tente novamente em {minutes:02d}:{seconds:02d}.")
        submitted = st.form_submit_button("Entrar", type="primary", disabled=locked)

    if submitted:
        if credentials_match(username, password, expected_username, expected_password):
            st.session_state["authenticated"] = True
            st.session_state["authenticated_user"] = username
            clear_login_failures(st.session_state)
            st.rerun()
        register_failed_attempt(st.session_state)
        st.error("Usuário ou senha inválidos.")

    return False


def subject_review_column_config():
    return {
        "Disciplina": st.column_config.TextColumn("Disciplina", required=True),
        "Carga Horaria": st.column_config.NumberColumn("Carga Horaria", min_value=0, step=1),
    }


def result_review_column_config():
    return {
        "Selecionar": st.column_config.CheckboxColumn(
            "Selecionar",
            help="Marque os pares que devem entrar no relatório final selecionado.",
        ),
        "Disciplina anterior": st.column_config.TextColumn(
            "Disciplina anterior",
            help="Disciplina extraída do documento anterior/original.",
        ),
        "CH anterior": st.column_config.NumberColumn(
            "CH anterior",
            help="Carga horária da disciplina anterior, quando identificada.",
        ),
        "Disciplina atual": st.column_config.TextColumn(
            "Disciplina atual",
            help="Disciplina candidata extraída do documento atual/destino.",
        ),
        "CH atual": st.column_config.NumberColumn(
            "CH atual",
            help="Carga horária da disciplina atual, quando identificada.",
        ),
        "Prioridade": st.column_config.TextColumn(
            "Prioridade",
            help="Prioridade sugerida para análise da linha: Alta, Média ou Baixa.",
        ),
        "Alertas": st.column_config.TextColumn(
            "Alertas",
            help="Sinais automáticos relevantes, como carga menor, ausência de carga ou sem match forte.",
            width="large",
        ),
        "Compatibilidade CH": st.column_config.TextColumn(
            "Compatibilidade CH",
            help="Pontuação de compatibilidade da carga horária entre 0 e 1.",
        ),
        "Equivalência": st.column_config.TextColumn(
            "Equivalência",
            help="Percentual final estimado pela combinação de nome, conteúdo e carga horária.",
        ),
        "Classificação": st.column_config.TextColumn(
            "Classificação",
            help="Interpretação textual da pontuação final. Não representa decisão oficial.",
        ),
        "Revisão manual": st.column_config.TextColumn(
            "Revisão manual",
            help="Indica se o par deve ser revisado com atenção por uma pessoa.",
        ),
        "Observação do revisor": st.column_config.TextColumn(
            "Observação do revisor",
            help="Campo livre para registrar uma observação humana sobre o par selecionado.",
            width="large",
        ),
    }


def render_result_metrics(dataframe):
    strong_count = int((dataframe["Classificação"] == "Forte indicação de equivalência").sum())
    likely_count = int((dataframe["Classificação"] == "Provável equivalência, revisar manualmente").sum())
    manual_count = int((dataframe["Revisão manual"] == "Sim").sum())
    no_match_count = int((dataframe["Classificação"] == "Nenhuma equivalência forte encontrada").sum())

    metric_columns = st.columns(5)
    metric_columns[0].metric("Disciplinas anteriores", st.session_state["previous_count"])
    metric_columns[1].metric("Disciplinas atuais", st.session_state["current_count"])
    metric_columns[2].metric("Possíveis equivalências", strong_count + likely_count)
    metric_columns[3].metric("Revisão manual", manual_count)
    metric_columns[4].metric("Sem equivalência forte", no_match_count)


def filter_result_tables(
    summary_dataframe,
    detailed_dataframe,
    raw_dataframe,
    selected_classifications,
    selected_alerts,
    only_manual_review: bool,
    sort_mode: str,
):
    if selected_classifications:
        mask = summary_dataframe["Classificação"].isin(selected_classifications)
    else:
        mask = summary_dataframe["Classificação"].notna()
    if only_manual_review:
        mask = mask & (summary_dataframe["Revisão manual"] == "Sim")
    if selected_alerts:
        mask = mask & summary_dataframe["Alertas"].apply(lambda value: has_selected_alert(value, selected_alerts))

    filtered_summary = summary_dataframe.loc[mask].copy()
    filtered_detailed = detailed_dataframe.loc[filtered_summary.index].copy()
    if sort_mode == "Prioridade" and not filtered_summary.empty:
        priority_rank = filtered_summary["Prioridade"].map({"Alta": 0, "Média": 1, "Baixa": 2}).fillna(3)
        score = raw_dataframe.loc[filtered_summary.index, "Equivalência"]
        sorted_index = (
            filtered_summary.assign(_priority_rank=priority_rank, _score=score)
            .sort_values(["_priority_rank", "_score"], ascending=[True, False])
            .index
        )
        filtered_summary = filtered_summary.loc[sorted_index]
        filtered_detailed = filtered_detailed.loc[sorted_index]
    elif sort_mode == "Score" and not filtered_summary.empty:
        sorted_index = raw_dataframe.loc[filtered_summary.index, "Equivalência"].sort_values(ascending=False).index
        filtered_summary = filtered_summary.loc[sorted_index]
        filtered_detailed = filtered_detailed.loc[sorted_index]

    return filtered_summary, filtered_detailed


def alert_options(dataframe) -> list[str]:
    alerts: set[str] = set()
    for value in dataframe["Alertas"].dropna().tolist():
        alerts.update(part.strip() for part in str(value).split("|") if part.strip())
    return sorted(alerts)


def has_selected_alert(value, selected_alerts) -> bool:
    alerts = {part.strip() for part in str(value).split("|") if part.strip()}
    return bool(alerts & set(selected_alerts))


def style_result_table(dataframe):
    return dataframe.style.apply(style_result_row, axis=1)


def style_result_row(row):
    styles = [""] * len(row)
    classification = row.get("Classificação", "")
    priority = row.get("Prioridade", "")
    manual_review = row.get("Revisão manual", "")
    final_score = row.get("Equivalência", "")

    if "Prioridade" in row.index:
        styles[row.index.get_loc("Prioridade")] = priority_style(priority)
    if "Classificação" in row.index:
        styles[row.index.get_loc("Classificação")] = classification_style(classification)
    if "Equivalência" in row.index:
        styles[row.index.get_loc("Equivalência")] = final_score_style(final_score)
    if "Revisão manual" in row.index and manual_review == "Sim":
        styles[row.index.get_loc("Revisão manual")] = "color: #b45309; font-weight: 700;"
    if "Alertas" in row.index:
        styles[row.index.get_loc("Alertas")] = alert_style(str(row.get("Alertas", "")))
    return styles


def priority_style(priority: str) -> str:
    if priority == "Alta":
        return "color: #b91c1c; font-weight: 800;"
    if priority == "Média":
        return "color: #b45309; font-weight: 800;"
    if priority == "Baixa":
        return "color: #475569; font-weight: 700;"
    return ""


def classification_style(classification: str) -> str:
    if classification == "Forte indicação de equivalência":
        return "color: #15803d; font-weight: 800;"
    if classification == "Provável equivalência, revisar manualmente":
        return "color: #1d4ed8; font-weight: 800;"
    if classification == "Similaridade parcial":
        return "color: #b45309; font-weight: 800;"
    if classification == "Nenhuma equivalência forte encontrada":
        return "color: #b91c1c; font-weight: 800;"
    return ""


def final_score_style(value: str) -> str:
    score = parse_percent(value)
    if score is None:
        return ""
    if score >= 85:
        return "color: #15803d; font-weight: 800;"
    if score >= 70:
        return "color: #1d4ed8; font-weight: 800;"
    if score >= 50:
        return "color: #b45309; font-weight: 800;"
    return "color: #b91c1c; font-weight: 800;"


def alert_style(alerts: str) -> str:
    normalized = alerts.lower()
    if "insuficiente" in normalized or "sem match" in normalized:
        return "color: #b91c1c; font-weight: 700;"
    if "carga" in normalized or "revisar" in normalized:
        return "color: #b45309; font-weight: 700;"
    if "boa similaridade" in normalized:
        return "color: #15803d; font-weight: 700;"
    return "color: #475569;"


def parse_percent(value: str) -> float | None:
    try:
        return float(str(value).replace("%", "").replace(",", ".").strip())
    except ValueError:
        return None


if __name__ == "__main__":
    main()
