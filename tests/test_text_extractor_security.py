from __future__ import annotations

from io import BytesIO

import pandas as pd
import pytest

from src import text_extractor
from src.text_extractor import TextExtractionError, extract_text_from_spreadsheet, extract_text_from_txt


def test_extract_text_from_txt_applies_line_limit(monkeypatch):
    monkeypatch.setattr(text_extractor, "MAX_TEXT_LINES", 1)
    content = b"linha 1\nlinha 2\n"

    with pytest.raises(TextExtractionError, match="limite de linhas"):
        extract_text_from_txt(content)


def test_extract_text_from_txt_applies_character_limit(monkeypatch):
    monkeypatch.setattr(text_extractor, "MAX_TEXT_CHARS", 4)

    with pytest.raises(TextExtractionError, match="limite de conteúdo"):
        extract_text_from_txt(b"12345")


def test_extract_text_from_spreadsheet_rejects_too_many_rows(monkeypatch):
    monkeypatch.setattr(text_extractor, "MAX_SPREADSHEET_ROWS", 1)
    dataframe = pd.DataFrame({"disciplina": ["A", "B"]})
    buffer = BytesIO()
    dataframe.to_csv(buffer, index=False)

    with pytest.raises(TextExtractionError, match="limite de linhas"):
        extract_text_from_spreadsheet(buffer.getvalue(), ".csv")
