from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO

from src.config import EXTRACTION_TIMEOUT_SECONDS, MAX_UPLOAD_SIZE_BYTES
from src.text_extractor import (
    TextExtractionError,
    extract_text_from_pdf,
    extract_text_from_spreadsheet,
    extract_text_from_txt,
    looks_like_binary,
    read_binary,
)


@dataclass
class ExtractedDocument:
    filename: str
    source_document: str
    text: str


PDF_SIGNATURE = b"%PDF-"
ZIP_SIGNATURE = b"PK\x03\x04"
OLE_SIGNATURE = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"
TEXT_SUFFIXES = {".txt", ".md", ".csv"}


def get_filename(file: BinaryIO | bytes | str | Path, fallback: str) -> str:
    if isinstance(file, (str, Path)):
        return Path(file).name
    return getattr(file, "name", fallback)


def load_document(file: BinaryIO | bytes | str | Path, source_document: str) -> ExtractedDocument:
    filename = get_filename(file, source_document)
    suffix = Path(filename).suffix.lower()
    content = read_binary(file)

    if not content:
        raise TextExtractionError("O arquivo enviado está vazio.")
    if len(content) > MAX_UPLOAD_SIZE_BYTES:
        raise TextExtractionError(
            f"O arquivo excede o limite permitido de {MAX_UPLOAD_SIZE_BYTES // (1024 * 1024)} MB."
        )
    ensure_allowed_file_signature(suffix, content)

    if suffix == ".pdf":
        text = extract_with_timeout(extract_text_from_pdf, content)
    elif suffix in {".xlsx", ".xls", ".csv"}:
        text = extract_with_timeout(extract_text_from_spreadsheet, content, suffix)
    elif suffix in {".txt", ".md"}:
        text = extract_with_timeout(extract_text_from_txt, content)
    else:
        raise TextExtractionError(
            "Tipo de arquivo não suportado no MVP. Use PDF com texto selecionável, XLSX, CSV ou TXT."
        )

    return ExtractedDocument(filename=filename, source_document=source_document, text=text)


def extract_with_timeout(extractor, *args):
    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(extractor, *args)
        try:
            return future.result(timeout=EXTRACTION_TIMEOUT_SECONDS)
        except FutureTimeoutError as error:
            future.cancel()
            raise TextExtractionError("A extração excedeu o tempo limite permitido.") from error
        except TextExtractionError:
            raise
        except Exception as error:
            raise TextExtractionError("Falha ao processar o arquivo enviado.") from error


def ensure_allowed_file_signature(suffix: str, content: bytes) -> None:
    if suffix == ".pdf":
        if not content.startswith(PDF_SIGNATURE):
            raise TextExtractionError("O arquivo PDF parece inválido ou corrompido.")
        return

    if suffix == ".xlsx":
        if not content.startswith(ZIP_SIGNATURE):
            raise TextExtractionError("O arquivo XLSX parece inválido ou corrompido.")
        return

    if suffix == ".xls":
        if not content.startswith(OLE_SIGNATURE):
            raise TextExtractionError("O arquivo XLS parece inválido ou corrompido.")
        return

    if suffix in TEXT_SUFFIXES:
        if content.startswith(PDF_SIGNATURE) or content.startswith(ZIP_SIGNATURE) or content.startswith(OLE_SIGNATURE):
            raise TextExtractionError("A extensão do arquivo não corresponde ao tipo real do conteúdo.")
        if looks_like_binary(content):
            raise TextExtractionError("O arquivo enviado parece conter conteúdo binário suspeito.")
        return
