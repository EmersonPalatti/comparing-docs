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

MAX_UPLOAD_SIZE_BYTES = int(os.getenv("MAX_UPLOAD_SIZE_BYTES", 10 * 1024 * 1024))
EXTRACTION_TIMEOUT_SECONDS = int(os.getenv("EXTRACTION_TIMEOUT_SECONDS", "10"))
MAX_PDF_PAGES = int(os.getenv("MAX_PDF_PAGES", "150"))
MAX_PDF_CHARS = int(os.getenv("MAX_PDF_CHARS", "300000"))
MAX_TEXT_LINES = int(os.getenv("MAX_TEXT_LINES", "20000"))
MAX_TEXT_CHARS = int(os.getenv("MAX_TEXT_CHARS", "300000"))
MAX_SPREADSHEET_ROWS = int(os.getenv("MAX_SPREADSHEET_ROWS", "20000"))
MAX_SPREADSHEET_COLUMNS = int(os.getenv("MAX_SPREADSHEET_COLUMNS", "100"))
MAX_SPREADSHEET_CELLS = int(os.getenv("MAX_SPREADSHEET_CELLS", "1000000"))

AUTH_RATE_WINDOW_SECONDS = int(os.getenv("AUTH_RATE_WINDOW_SECONDS", "300"))
AUTH_MAX_ATTEMPTS = int(os.getenv("AUTH_MAX_ATTEMPTS", "5"))
AUTH_LOCKOUT_SECONDS = int(os.getenv("AUTH_LOCKOUT_SECONDS", "600"))
AUTH_BASE_DELAY_SECONDS = float(os.getenv("AUTH_BASE_DELAY_SECONDS", "0.5"))
AUTH_MAX_DELAY_SECONDS = float(os.getenv("AUTH_MAX_DELAY_SECONDS", "4.0"))
AUTH_REGISTRY_MAX_ENTRIES = int(os.getenv("AUTH_REGISTRY_MAX_ENTRIES", "10000"))
AUTH_TRUST_PROXY_HEADERS = os.getenv("AUTH_TRUST_PROXY_HEADERS", "false").lower() == "true"

DISCLAIMER_PT = (
    "Este relatório apresenta uma análise automatizada de similaridade entre disciplinas "
    "com base nos documentos enviados. Ele não representa uma decisão oficial da "
    "instituição de ensino. A aceitação final de equivalência ou aproveitamento de "
    "créditos deve ser realizada por um revisor humano."
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
