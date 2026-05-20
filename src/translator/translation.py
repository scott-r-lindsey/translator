from __future__ import annotations

import importlib
import re
import time
from dataclasses import dataclass
from typing import Any, Protocol

from translator.config import AppSettings

WHISPER_TO_NLLB_LANGUAGE = {
    "ar": "arb_Arab",
    "de": "deu_Latn",
    "en": "eng_Latn",
    "es": "spa_Latn",
    "fr": "fra_Latn",
    "hi": "hin_Deva",
    "it": "ita_Latn",
    "ja": "jpn_Jpan",
    "ko": "kor_Hang",
    "pt": "por_Latn",
    "ru": "rus_Cyrl",
    "zh": "zho_Hans",
}


@dataclass(frozen=True)
class Translation:
    source_text: str
    translated_text: str
    source_language: str | None
    target_language: str
    latency_ms: float


class Translator(Protocol):
    def translate(self, transcription: TranslatableText) -> Translation:
        ...


class TranslatableText(Protocol):
    @property
    def text(self) -> str:
        ...

    @property
    def language(self) -> str | None:
        ...


class NoOpTranslator:
    def __init__(self, target_language: str) -> None:
        self._target_language = target_language

    def translate(self, transcription: TranslatableText) -> Translation:
        return Translation(
            source_text=transcription.text,
            translated_text=transcription.text,
            source_language=transcription.language,
            target_language=self._target_language,
            latency_ms=0.0,
        )


class NllbTranslator:
    def __init__(self, settings: AppSettings) -> None:
        self._settings = settings
        self._tokenizer: Any | None = None
        self._model: Any | None = None

    def translate(self, transcription: TranslatableText) -> Translation:
        if not transcription.text:
            return Translation(
                source_text="",
                translated_text="",
                source_language=transcription.language,
                target_language=self._settings.translation_target_language,
                latency_ms=0.0,
            )

        tokenizer, model = self._load_model()
        source_language = nllb_language_for_whisper_language(transcription.language)
        tokenizer.src_lang = source_language
        started_at = time.perf_counter()
        inputs = tokenizer(transcription.text, return_tensors="pt")
        inputs = move_tokenizer_inputs(inputs, translation_device_target(self._settings))
        output_tokens = model.generate(
            **inputs,
            forced_bos_token_id=tokenizer.convert_tokens_to_ids(
                self._settings.translation_target_language
            ),
            max_new_tokens=self._settings.translation_max_new_tokens,
            no_repeat_ngram_size=self._settings.translation_no_repeat_ngram_size,
            repetition_penalty=self._settings.translation_repetition_penalty,
        )
        translated_text = clean_repeated_words(
            tokenizer.batch_decode(output_tokens, skip_special_tokens=True)[0],
            self._settings.translation_repeated_word_limit,
        )
        latency_ms = (time.perf_counter() - started_at) * 1_000
        return Translation(
            source_text=transcription.text,
            translated_text=translated_text,
            source_language=source_language,
            target_language=self._settings.translation_target_language,
            latency_ms=latency_ms,
        )

    def prepare(self) -> None:
        self._load_model()

    def _load_model(self) -> tuple[Any, Any]:
        if self._tokenizer is None or self._model is None:
            self._tokenizer, self._model = build_nllb_model(self._settings)

        return self._tokenizer, self._model


def build_nllb_model(settings: AppSettings) -> tuple[Any, Any]:
    transformers = importlib.import_module("transformers")
    torch = importlib.import_module("torch")
    tokenizer = transformers.AutoTokenizer.from_pretrained(settings.translation_model)
    dtype = torch_dtype_for_name(torch, settings.translation_compute_dtype)
    model = transformers.AutoModelForSeq2SeqLM.from_pretrained(
        settings.translation_model,
        dtype=dtype,
    )
    model = model.to(translation_device_target(settings))

    return tokenizer, model


def torch_dtype_for_name(torch: Any, dtype_name: str) -> Any:
    return getattr(torch, dtype_name)


def translation_device_target(settings: AppSettings) -> str:
    if settings.translation_device == "cuda":
        return f"cuda:{settings.translation_device_index}"

    return settings.translation_device


def move_tokenizer_inputs(inputs: Any, device_target: str) -> Any:
    if device_target == "cpu":
        return inputs

    return inputs.to(device_target)


def nllb_language_for_whisper_language(language: str | None) -> str:
    if language is None:
        return "eng_Latn"

    return WHISPER_TO_NLLB_LANGUAGE.get(language, "eng_Latn")


def render_translation(
    transcription: TranslatableText,
    translation: Translation | None,
    display_mode: str,
) -> str:
    if translation is None or display_mode == "original":
        return transcription.text

    if display_mode == "translation":
        return translation.translated_text

    return f"{transcription.text}\n{translation.translated_text}"


def clean_repeated_words(text: str, repeated_word_limit: int) -> str:
    tokens = re.findall(r"\w+|\W+", text)
    cleaned: list[str] = []
    last_word = ""
    repeat_count = 0

    for token in tokens:
        if not token.isalnum():
            cleaned.append(token)
            continue

        normalized = token.casefold()
        if normalized == last_word:
            repeat_count += 1
        else:
            last_word = normalized
            repeat_count = 1

        if repeat_count <= repeated_word_limit:
            cleaned.append(token)
        elif cleaned and not cleaned[-1].isalnum():
            cleaned.pop()

    return "".join(cleaned).strip()
