from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO

from src.text_extractor import (
    TextExtractionError,
    extract_text_from_pdf,
    extract_text_from_spreadsheet,
    extract_text_from_txt,
    read_binary,
)


@dataclass
class ExtractedDocument:
    filename: str
    source_document: str
    text: str


def get_filename(file: BinaryIO | bytes | str | Path, fallback: str) -> str:
    if isinstance(file, (str, Path)):
        return Path(file).name
    return getattr(file, "name", fallback)


def load_document(file: BinaryIO | bytes | str | Path, source_document: str) -> ExtractedDocument:
    filename = get_filename(file, source_document)
    suffix = Path(filename).suffix.lower()
    try:
        content = read_binary(file)
    except TextExtractionError as error:
        raise TextExtractionError(f"{filename}: {error}") from error

    if not content:
        raise TextExtractionError("O arquivo enviado está vazio.")

    if suffix == ".pdf":
        text = extract_text_from_pdf(content)
    elif suffix in {".xlsx", ".xls", ".csv"}:
        text = extract_text_from_spreadsheet(content, suffix)
    elif suffix in {".txt", ".md"}:
        text = extract_text_from_txt(content)
    else:
        raise TextExtractionError(
            "Tipo de arquivo não suportado no MVP. Use PDF com texto selecionável, XLSX, CSV ou TXT."
        )

    return ExtractedDocument(filename=filename, source_document=source_document, text=text)
