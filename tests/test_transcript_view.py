from collections.abc import Callable

from pytest import MonkeyPatch

from translator.transcript import TranscriptEntry
from translator.ui.transcript_view import TranscriptView


def test_transcript_view_appends_entries(monkeypatch: MonkeyPatch) -> None:
    widgets = patch_transcript_widgets(monkeypatch)
    text = widgets.text
    view = TranscriptView(object())

    assert widgets.scrollbar.command is not None
    assert text.yscrollcommand is not None
    assert widgets.scrollbar.grid_kwargs == {"row": 0, "column": 1, "sticky": "ns"}

    view.append(
        TranscriptEntry(
            timestamp_seconds=1,
            source_text="hola",
            translated_text="hello",
            detected_language="es",
        )
    )
    view.append(
        TranscriptEntry(
            timestamp_seconds=2,
            source_text="bonjour",
            translated_text="hello",
            detected_language="fr",
        )
    )

    assert text.contents == (
        "[00:01] Spanish (es)\nhola\nhello\n"
        "[00:02] French (fr)\nbonjour\nhello"
    )
    assert text.tags == [
        "meta",
        "source",
        "translation",
        "meta",
        "source",
        "translation",
    ]
    assert set(text.configured_tags) == {"meta", "source", "translation"}
    assert text.states == ["normal", "disabled", "normal", "disabled"]
    assert text.seen_end is True


def test_transcript_view_clears_entries(monkeypatch: MonkeyPatch) -> None:
    widgets = patch_transcript_widgets(monkeypatch)
    text = widgets.text
    view = TranscriptView(object())

    view.append(
        TranscriptEntry(
            timestamp_seconds=1,
            source_text="hola",
            translated_text="hello",
            detected_language="es",
        )
    )
    view.clear()

    assert text.contents == ""


def patch_transcript_widgets(monkeypatch: MonkeyPatch) -> "FakeTranscriptWidgets":
    widgets = FakeTranscriptWidgets()
    monkeypatch.setattr("translator.ui.transcript_view.Frame", widgets.build_frame)
    monkeypatch.setattr("translator.ui.transcript_view.DarkScrollbar", widgets.build_scrollbar)
    monkeypatch.setattr("translator.ui.transcript_view.Text", widgets.build_text)
    return widgets


class FakeTranscriptWidgets:
    def __init__(self) -> None:
        self.frame = FakeFrame()
        self.scrollbar = FakeScrollbar()
        self.text = FakeText()

    def build_frame(self, *_args: object, **_kwargs: object) -> "FakeFrame":
        return self.frame

    def build_scrollbar(self, *_args: object, **_kwargs: object) -> "FakeScrollbar":
        return self.scrollbar

    def build_text(
        self,
        *_args: object,
        yscrollcommand: Callable[[str, str], None],
        **_kwargs: object,
    ) -> "FakeText":
        self.text.yscrollcommand = yscrollcommand
        return self.text


class FakeFrame:
    def pack(self, *_args: object, **_kwargs: object) -> None:
        return None

    def pack_forget(self) -> None:
        return None

    def rowconfigure(self, row: int, *, weight: int) -> None:
        assert row == 0
        assert weight == 1

    def columnconfigure(self, column: int, *, weight: int) -> None:
        assert column in {0, 1}
        assert weight == (1 if column == 0 else 0)


class FakeScrollbar:
    def __init__(self) -> None:
        self.command: Callable[..., object] | None = None
        self.pack_kwargs: dict[str, object] = {}
        self.grid_kwargs: dict[str, object] = {}

    def set(self, _first: str, _last: str) -> None:
        return None

    def set_command(self, command: Callable[..., object]) -> None:
        self.command = command

    def pack(self, *_args: object, **_kwargs: object) -> None:
        self.pack_kwargs = dict(_kwargs)

    def grid(self, *_args: object, **_kwargs: object) -> None:
        self.grid_kwargs = dict(_kwargs)


class FakeText:
    def __init__(self) -> None:
        self.contents = ""
        self.yscrollcommand: Callable[[str, str], None] | None = None
        self.tags: list[str] = []
        self.configured_tags: list[str] = []
        self.states: list[str] = []
        self.seen_end = False

    def yview(self, *_args: object) -> tuple[float, float] | None:
        return None

    def pack(self, *_args: object, **_kwargs: object) -> None:
        return None

    def pack_forget(self) -> None:
        return None

    def grid(self, *_args: object, **_kwargs: object) -> None:
        return None

    def configure(self, *, state: str) -> None:
        self.states.append(state)

    def tag_configure(self, tag: str, **_kwargs: object) -> None:
        self.configured_tags.append(tag)

    def index(self, position: str) -> str:
        assert position == "end-1c"
        return "1.0" if not self.contents else "1.1"

    def insert(self, _position: object, text: str, tag: str | None = None) -> None:
        self.contents += text
        if tag is not None:
            self.tags.append(tag)

    def delete(self, start: str, _end: object) -> None:
        assert start == "1.0"
        self.contents = ""

    def see(self, _position: object) -> None:
        self.seen_end = True
