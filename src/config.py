from __future__ import annotations

import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
TEMP_DIR = DATA_DIR / "temp"
SAMPLES_DIR = DATA_DIR / "samples"
OUTPUTS_DIR = BASE_DIR / "outputs"
REPORTS_DIR = OUTPUTS_DIR / "reports"
TABLES_DIR = OUTPUTS_DIR / "tables"

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
LLM_MODEL = os.getenv("LLM_MODEL", "")
USE_LLM_JUSTIFICATION = os.getenv("USE_LLM_JUSTIFICATION", "false").lower() == "true"

MAX_UPLOAD_BYTES = int(os.getenv("MAX_UPLOAD_BYTES", 10 * 1024 * 1024))
MAX_PDF_PAGES = int(os.getenv("MAX_PDF_PAGES", 200))
MAX_SPREADSHEET_ROWS = int(os.getenv("MAX_SPREADSHEET_ROWS", 10000))
MAX_SPREADSHEET_COLUMNS = int(os.getenv("MAX_SPREADSHEET_COLUMNS", 200))

DISCLAIMER_PT = (
    "Este relatório apresenta uma análise automatizada de similaridade entre disciplinas "
    "com base nos documentos enviados. Ele não representa uma decisão oficial da "
    "instituição de ensino. A aceitação final de equivalência ou aproveitamento de "
    "disciplinas depende das regras e da análise da própria instituição."
)

DISCLAIMER_EN = (
    "This report provides an automated similarity analysis between academic subjects "
    "based on the uploaded documents. It does not represent an official institutional "
    "decision. Final acceptance of subject equivalency or credit transfer depends on "
    "the rules and review process of the educational institution."
)

CLASSIFICATION_LABELS_PT = {
    "strong_equivalency": "Forte indicação de equivalência",
    "likely_equivalency": "Provável equivalência, revisar manualmente",
    "partial_similarity": "Similaridade parcial",
    "no_match": "Nenhuma equivalência forte encontrada",
}
