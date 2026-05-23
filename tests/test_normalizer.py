from src.normalizer import normalize_text


def test_normalize_text_removes_accents_and_expands_abbreviations():
    assert normalize_text("Estat. Descritiva") == "estatistica descritiva"
    assert normalize_text("Mat. Aplicada") == "matematica aplicada"
