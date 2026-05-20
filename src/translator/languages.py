from dataclasses import dataclass

AUTO_LANGUAGE_LABEL = "Auto"


@dataclass(frozen=True)
class LanguageOption:
    code: str
    name: str

    @property
    def label(self) -> str:
        return f"{self.name} ({self.code})"


COMMON_SOURCE_LANGUAGES = [
    LanguageOption("en", "English"),
    LanguageOption("es", "Spanish"),
    LanguageOption("fr", "French"),
    LanguageOption("de", "German"),
    LanguageOption("it", "Italian"),
    LanguageOption("pt", "Portuguese"),
    LanguageOption("ja", "Japanese"),
    LanguageOption("ko", "Korean"),
    LanguageOption("zh", "Chinese"),
    LanguageOption("ru", "Russian"),
    LanguageOption("ar", "Arabic"),
    LanguageOption("hi", "Hindi"),
]


def common_language_labels() -> list[str]:
    return [AUTO_LANGUAGE_LABEL, *(option.label for option in COMMON_SOURCE_LANGUAGES)]


def normalize_source_language(value: str) -> str | None:
    normalized = value.strip().lower()
    if normalized in {"", "auto"}:
        return None

    normalized = normalized.removesuffix(" detected").strip()
    by_code = {option.code: option.code for option in COMMON_SOURCE_LANGUAGES}
    by_name = {option.name.lower(): option.code for option in COMMON_SOURCE_LANGUAGES}
    by_label = {option.label.lower(): option.code for option in COMMON_SOURCE_LANGUAGES}
    if normalized in by_code:
        return by_code[normalized]
    if normalized in by_name:
        return by_name[normalized]
    if normalized in by_label:
        return by_label[normalized]
    if normalized.isalpha() and 2 <= len(normalized) <= 5:
        return normalized

    return None


def source_language_label(code: str | None) -> str:
    if code is None:
        return AUTO_LANGUAGE_LABEL

    for option in COMMON_SOURCE_LANGUAGES:
        if option.code == code:
            return option.label

    return code


def detected_language_label(code: str) -> str:
    for option in COMMON_SOURCE_LANGUAGES:
        if option.code == code:
            return f"{option.name} detected"

    return f"{code} detected"
