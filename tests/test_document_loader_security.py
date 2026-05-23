from __future__ import annotations

import time

import pytest

from src import document_loader
from src.document_loader import load_document
from src.text_extractor import TextExtractionError


def test_load_document_rejects_oversized_upload(monkeypatch):
    monkeypatch.setattr(document_loader, "MAX_UPLOAD_SIZE_BYTES", 8)
    content = b"0123456789"

    with pytest.raises(TextExtractionError, match="excede o limite permitido"):
        load_document(content, "arquivo.txt")


def test_load_document_rejects_signature_mismatch():
    with pytest.raises(TextExtractionError, match="não corresponde ao tipo real"):
        load_document(b"%PDF-1.7 fake", "arquivo.txt")


def test_load_document_rejects_binary_text_payload():
    with pytest.raises(TextExtractionError, match="conteúdo binário suspeito"):
        load_document(b"\x00\x01\x02\x03", "arquivo.txt")


def test_extract_with_timeout_raises_when_processing_exceeds_limit(monkeypatch):
    monkeypatch.setattr(document_loader, "EXTRACTION_TIMEOUT_SECONDS", 1)

    def slow_extractor(value):
        time.sleep(2)
        return value

    with pytest.raises(TextExtractionError, match="tempo limite"):
        document_loader.extract_with_timeout(slow_extractor, "ok")
