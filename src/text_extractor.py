from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import BinaryIO

import pandas as pd
import pdfplumber

from src.config import MAX_PDF_PAGES, MAX_SPREADSHEET_COLUMNS, MAX_SPREADSHEET_ROWS, MAX_UPLOAD_BYTES

class TextExtractionError(ValueError):
    """Raised when a document cannot be converted into useful text."""


def clean_text(text: str) -> str:
    lines = [line.strip() for line in text.replace("\r", "\n").split("\n")]
    cleaned_lines = []
    previous_blank = False
    for line in lines:
        if not line:
            if not previous_blank:
                cleaned_lines.append("")
            previous_blank = True
            continue
        cleaned_lines.append(" ".join(line.split()))
        previous_blank = False
    return "\n".join(cleaned_lines).strip()


def extract_text_from_pdf(content: bytes) -> str:
    pages: list[str] = []
    with pdfplumber.open(BytesIO(content)) as pdf:
        for page_index, page in enumerate(pdf.pages):
            if page_index >= MAX_PDF_PAGES:
                break
            page_text = page.extract_text() or ""
            if page_text.strip():
                pages.append(page_text)

    text = clean_text("\n\n".join(pages))
    if not text:
        raise TextExtractionError(
            "This PDF does not appear to contain selectable text. OCR support is not available in the current MVP."
        )
    return text


def extract_text_from_spreadsheet(content: bytes, suffix: str) -> str:
    buffer = BytesIO(content)
    if suffix == ".csv":
        dataframe = pd.read_csv(buffer)
    else:
        dataframe = pd.read_excel(buffer)

    if dataframe.empty:
        raise TextExtractionError("O arquivo de planilha está vazio.")
    if len(dataframe.index) > MAX_SPREADSHEET_ROWS:
        raise TextExtractionError(
            f"Limite de planilha excedido: máximo de {MAX_SPREADSHEET_ROWS} linhas por arquivo."
        )
    if len(dataframe.columns) > MAX_SPREADSHEET_COLUMNS:
        raise TextExtractionError(
            f"Limite de planilha excedido: máximo de {MAX_SPREADSHEET_COLUMNS} colunas por arquivo."
        )

    return dataframe.fillna("").to_csv(index=False)


def extract_text_from_txt(content: bytes) -> str:
    for encoding in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            return clean_text(content.decode(encoding))
        except UnicodeDecodeError:
            continue
    raise TextExtractionError("Não foi possível decodificar o arquivo de texto.")


def read_binary(file: BinaryIO | bytes | str | Path) -> bytes:
    if isinstance(file, bytes):
        content = file
    elif isinstance(file, (str, Path)):
        content = Path(file).read_bytes()
    elif hasattr(file, "getvalue"):
        content = file.getvalue()
    else:
        content = file.read()

    if len(content) > MAX_UPLOAD_BYTES:
        raise TextExtractionError(
            f"Arquivo excede o tamanho máximo permitido de {MAX_UPLOAD_BYTES} bytes."
        )
    return content
