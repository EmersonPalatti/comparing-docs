from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import BinaryIO

import pandas as pd
import pdfplumber


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
        for page in pdf.pages:
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
        return file
    if isinstance(file, (str, Path)):
        return Path(file).read_bytes()
    if hasattr(file, "getvalue"):
        return file.getvalue()
    return file.read()
