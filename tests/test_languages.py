from translator.languages import (
    AUTO_LANGUAGE_LABEL,
    common_language_labels,
    detected_language_label,
    normalize_source_language,
    source_language_label,
)


def test_normalize_source_language_accepts_auto_names_and_codes() -> None:
    assert normalize_source_language("") is None
    assert normalize_source_language("Auto") is None
    assert normalize_source_language("Spanish") == "es"
    assert normalize_source_language("Spanish (es)") == "es"
    assert normalize_source_language("es") == "es"
    assert normalize_source_language("Spanish detected") == "es"
    assert normalize_source_language("nl") == "nl"


def test_source_language_labels() -> None:
    assert source_language_label(None) == AUTO_LANGUAGE_LABEL
    assert source_language_label("en") == "English (en)"
    assert source_language_label("xx") == "xx"
    assert detected_language_label("fr") == "French detected"
    assert detected_language_label("xx") == "xx detected"
    assert common_language_labels()[0] == AUTO_LANGUAGE_LABEL
