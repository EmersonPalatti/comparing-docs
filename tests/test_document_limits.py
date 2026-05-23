from io import BytesIO

import pandas as pd
import pytest

from src.document_loader import load_document
from src.text_extractor import TextExtractionError, extract_text_from_pdf, extract_text_from_spreadsheet, read_binary


def test_read_binary_rejects_file_above_size_limit(monkeypatch):
    monkeypatch.setattr("src.text_extractor.MAX_UPLOAD_BYTES", 4)

    with pytest.raises(TextExtractionError, match="tamanho máximo"):
        read_binary(b"12345")


def test_load_document_accepts_file_at_exact_size_limit(monkeypatch):
    monkeypatch.setattr("src.text_extractor.MAX_UPLOAD_BYTES", 5)

    document = load_document(b"abcde", "arquivo.txt")

    assert document.text == "abcde"
    assert document.filename == "arquivo.txt"


def test_extract_text_from_pdf_stops_after_page_limit(monkeypatch):
    processed_pages = []

    class FakePage:
        def __init__(self, value: str):
            self.value = value

        def extract_text(self):
            processed_pages.append(self.value)
            return self.value

    class FakePDF:
        def __init__(self):
            self.pages = [FakePage("p1"), FakePage("p2"), FakePage("p3")]

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr("src.text_extractor.MAX_PDF_PAGES", 2)
    monkeypatch.setattr("src.text_extractor.pdfplumber.open", lambda *_args, **_kwargs: FakePDF())

    text = extract_text_from_pdf(b"fake pdf")

    assert processed_pages == ["p1", "p2"]
    assert "p3" not in text


def test_extract_text_from_spreadsheet_rejects_above_row_limit(monkeypatch):
    dataframe = pd.DataFrame({"col": [1, 2, 3]})
    content = dataframe.to_csv(index=False).encode("utf-8")
    monkeypatch.setattr("src.text_extractor.MAX_SPREADSHEET_ROWS", 2)

    with pytest.raises(TextExtractionError, match="máximo de 2 linhas"):
        extract_text_from_spreadsheet(content, ".csv")


def test_extract_text_from_spreadsheet_accepts_exact_row_and_column_limits(monkeypatch):
    dataframe = pd.DataFrame({"a": [1, 2], "b": [3, 4]})
    content = dataframe.to_csv(index=False).encode("utf-8")
    monkeypatch.setattr("src.text_extractor.MAX_SPREADSHEET_ROWS", 2)
    monkeypatch.setattr("src.text_extractor.MAX_SPREADSHEET_COLUMNS", 2)

    result = extract_text_from_spreadsheet(content, ".csv")

    assert "a,b" in result
    assert "1,3" in result
