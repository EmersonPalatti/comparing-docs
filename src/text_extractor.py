from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import BinaryIO

import pandas as pd
import pdfplumber

from src.config import (
    MAX_PDF_CHARS,
    MAX_PDF_PAGES,
    MAX_SPREADSHEET_CELLS,
    MAX_SPREADSHEET_COLUMNS,
    MAX_SPREADSHEET_ROWS,
    MAX_TEXT_CHARS,
    MAX_TEXT_LINES,
)


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
    try:
        with pdfplumber.open(BytesIO(content)) as pdf:
            if len(pdf.pages) > MAX_PDF_PAGES:
                raise TextExtractionError(
                    f"O PDF excede o limite de páginas suportado ({MAX_PDF_PAGES})."
                )

            total_chars = 0
            for page in pdf.pages:
                page_text = page.extract_text() or ""
                if page_text.strip():
                    total_chars += len(page_text)
                    if total_chars > MAX_PDF_CHARS:
                        raise TextExtractionError(
                            "O PDF excede o limite de conteúdo suportado para extração segura."
                        )
                    pages.append(page_text)
    except TextExtractionError:
        raise
    except Exception as error:
        raise TextExtractionError("Falha ao ler o PDF enviado.") from error

    text = clean_text("\n\n".join(pages))
    if not text:
        raise TextExtractionError(
            "This PDF does not appear to contain selectable text. OCR support is not available in the current MVP."
        )
    return text


def extract_text_from_spreadsheet(content: bytes, suffix: str) -> str:
    buffer = BytesIO(content)
    try:
        if suffix == ".csv":
            dataframe = pd.read_csv(buffer, nrows=MAX_SPREADSHEET_ROWS + 1)
        else:
            dataframe = pd.read_excel(buffer, nrows=MAX_SPREADSHEET_ROWS + 1)
    except Exception as error:
        raise TextExtractionError("Falha ao ler a planilha enviada.") from error

    if dataframe.empty:
        raise TextExtractionError("O arquivo de planilha está vazio.")
    if len(dataframe.index) > MAX_SPREADSHEET_ROWS:
        raise TextExtractionError(f"A planilha excede o limite de linhas ({MAX_SPREADSHEET_ROWS}).")
    if len(dataframe.columns) > MAX_SPREADSHEET_COLUMNS:
        raise TextExtractionError(f"A planilha excede o limite de colunas ({MAX_SPREADSHEET_COLUMNS}).")
    if dataframe.size > MAX_SPREADSHEET_CELLS:
        raise TextExtractionError("A planilha excede o limite de células suportado.")

    return dataframe.fillna("").to_csv(index=False)


def extract_text_from_txt(content: bytes) -> str:
    if looks_like_binary(content):
        raise TextExtractionError("O arquivo de texto parece conter conteúdo binário suspeito.")
    for encoding in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            decoded = content.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    else:
        raise TextExtractionError("Não foi possível decodificar o arquivo de texto.")

    lines = decoded.splitlines()
    if len(lines) > MAX_TEXT_LINES:
        raise TextExtractionError(f"O arquivo de texto excede o limite de linhas ({MAX_TEXT_LINES}).")

    cleaned = clean_text(decoded)
    if len(cleaned) > MAX_TEXT_CHARS:
        raise TextExtractionError("O arquivo de texto excede o limite de conteúdo suportado.")
    return cleaned


def looks_like_binary(content: bytes) -> bool:
    if b"\x00" in content:
        return True
    if not content:
        return False
    sample = content[:4096]
    suspicious = 0
    for value in sample:
        if value in (9, 10, 13):
            continue
        if value < 32 or value == 127:
            suspicious += 1
    return suspicious / len(sample) > 0.30


def read_binary(file: BinaryIO | bytes | str | Path) -> bytes:
    if isinstance(file, bytes):
        return file
    if isinstance(file, (str, Path)):
        return Path(file).read_bytes()
    if hasattr(file, "getvalue"):
        return file.getvalue()
    return file.read()
