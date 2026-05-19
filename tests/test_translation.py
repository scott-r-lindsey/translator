from typing import Any

from pytest import MonkeyPatch

from translator.config import AppSettings
from translator.transcription import Transcription
from translator.translation import (
    NllbTranslator,
    Translation,
    nllb_language_for_whisper_language,
    render_translation,
    translation_device_target,
)


def test_nllb_language_for_whisper_language_maps_common_codes() -> None:
    assert nllb_language_for_whisper_language("es") == "spa_Latn"
    assert nllb_language_for_whisper_language("ja") == "jpn_Jpan"
    assert nllb_language_for_whisper_language(None) == "eng_Latn"
    assert nllb_language_for_whisper_language("unknown") == "eng_Latn"


def test_render_translation_modes() -> None:
    transcription = Transcription(text="hola", language="es")
    translation = Translation(
        source_text="hola",
        translated_text="hello",
        source_language="spa_Latn",
        target_language="eng_Latn",
        latency_ms=10,
    )

    assert render_translation(transcription, translation, "original") == "hola"
    assert render_translation(transcription, translation, "translation") == "hello"
    assert render_translation(transcription, translation, "both") == "hola\nhello"


def test_translation_device_target_includes_cuda_index() -> None:
    assert translation_device_target(AppSettings(translation_device="cpu")) == "cpu"
    settings = AppSettings(translation_device="cuda", translation_device_index=1)

    assert translation_device_target(settings) == "cuda:1"


def test_nllb_translator_uses_language_and_target_tokens(monkeypatch: MonkeyPatch) -> None:
    tokenizer = FakeTokenizer()
    model = FakeModel()

    def build_model(_settings: AppSettings) -> tuple[FakeTokenizer, FakeModel]:
        return tokenizer, model

    monkeypatch.setattr("translator.translation.build_nllb_model", build_model)
    translator = NllbTranslator(AppSettings(translation_target_language="eng_Latn"))

    translation = translator.translate(Transcription(text="hola", language="es"))

    assert tokenizer.src_lang == "spa_Latn"
    assert model.forced_bos_token_id == 7
    assert translation.translated_text == "hello"
    assert translation.source_language == "spa_Latn"
    assert translation.target_language == "eng_Latn"
    assert translation.latency_ms > 0


class FakeTokenizerInputs(dict[str, object]):
    def to(self, _device: str) -> "FakeTokenizerInputs":
        return self


class FakeTokenizer:
    def __init__(self) -> None:
        self.src_lang = ""

    def __call__(self, text: str, *, return_tensors: str) -> FakeTokenizerInputs:
        assert text == "hola"
        assert return_tensors == "pt"
        return FakeTokenizerInputs(input_ids=[1])

    def convert_tokens_to_ids(self, token: str) -> int:
        assert token == "eng_Latn"
        return 7

    def batch_decode(self, _tokens: object, *, skip_special_tokens: bool) -> list[str]:
        assert skip_special_tokens is True
        return ["hello"]


class FakeModel:
    def __init__(self) -> None:
        self.forced_bos_token_id = 0

    def generate(self, **kwargs: Any) -> list[list[int]]:
        self.forced_bos_token_id = int(kwargs["forced_bos_token_id"])
        return [[1, 2, 3]]
