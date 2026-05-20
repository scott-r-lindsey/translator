from collections.abc import Callable

from pytest import MonkeyPatch

from translator.ui.language_selector import SourceLanguageSelector


class FakeEvent:
    def __init__(self, keysym: str = "") -> None:
        self.keysym = keysym


def test_source_language_selector_applies_typed_name(monkeypatch: MonkeyPatch) -> None:
    widgets = patch_language_widgets(monkeypatch)
    selected: list[str | None] = []
    SourceLanguageSelector(object(), None, selected.append)

    widgets.string_var.set("Spanish")
    widgets.entry.fire("<Return>")

    assert selected == ["es"]
    assert widgets.string_var.get() == "Spanish (es)"
    assert widgets.listbox.visible is False


def test_source_language_selector_accepts_auto(monkeypatch: MonkeyPatch) -> None:
    widgets = patch_language_widgets(monkeypatch)
    selected: list[str | None] = []
    SourceLanguageSelector(object(), "en", selected.append)

    widgets.string_var.set("Auto")
    widgets.entry.fire("<Return>")

    assert selected == [None]
    assert widgets.string_var.get() == "Auto"


def test_source_language_selector_adds_detected_languages(monkeypatch: MonkeyPatch) -> None:
    widgets = patch_language_widgets(monkeypatch)
    selector = SourceLanguageSelector(object(), None, lambda _language: None)

    selector.add_detected_language("es")
    selector.add_detected_language("fr")
    selector.add_detected_language("es")

    assert widgets.listbox.items[:3] == ["Auto", "French detected", "Spanish detected"]


def test_source_language_selector_selects_highlighted_option(monkeypatch: MonkeyPatch) -> None:
    widgets = patch_language_widgets(monkeypatch)
    selected: list[str | None] = []
    SourceLanguageSelector(object(), None, selected.append)

    widgets.entry.fire("<FocusIn>")
    widgets.listbox.selected_index = 2
    widgets.listbox.fire("<<ListboxSelect>>")

    assert selected == ["es"]
    assert widgets.string_var.get() == "Spanish (es)"


def test_source_language_selector_filters_options(monkeypatch: MonkeyPatch) -> None:
    widgets = patch_language_widgets(monkeypatch)
    SourceLanguageSelector(object(), None, lambda _language: None)

    widgets.string_var.set("span")
    widgets.entry.fire("<KeyRelease>", keysym="n")

    assert widgets.listbox.visible is True
    assert widgets.listbox.items == ["Spanish (es)"]


def patch_language_widgets(monkeypatch: MonkeyPatch) -> "FakeLanguageWidgets":
    widgets = FakeLanguageWidgets()
    monkeypatch.setattr(
        "translator.ui.language_selector.StringVar",
        widgets.build_string_var,
    )
    monkeypatch.setattr("translator.ui.language_selector.Frame", widgets.build_frame)
    monkeypatch.setattr("translator.ui.language_selector.Label", widgets.build_label)
    monkeypatch.setattr("translator.ui.language_selector.Entry", widgets.build_entry)
    monkeypatch.setattr("translator.ui.language_selector.Listbox", widgets.build_listbox)
    return widgets


class FakeLanguageWidgets:
    def __init__(self) -> None:
        self.string_var = FakeStringVar("")
        self.entry = FakeEntry()
        self.listbox = FakeListbox()

    def build_string_var(self, *, value: str) -> "FakeStringVar":
        self.string_var = FakeStringVar(value)
        return self.string_var

    def build_frame(self, *_args: object, **_kwargs: object) -> "FakeWidget":
        return FakeWidget()

    def build_label(self, *_args: object, **_kwargs: object) -> "FakeWidget":
        return FakeWidget()

    def build_entry(
        self,
        *_args: object,
        textvariable: "FakeStringVar",
        width: int,
        **_kwargs: object,
    ) -> "FakeEntry":
        assert width == 18
        self.entry = FakeEntry()
        self.entry.textvariable = textvariable
        return self.entry

    def build_listbox(
        self,
        *_args: object,
        height: int,
        **_kwargs: object,
    ) -> "FakeListbox":
        assert height == 6
        self.listbox = FakeListbox()
        return self.listbox


class FakeWidget:
    def pack(self, *_args: object, **_kwargs: object) -> None:
        return None


class FakeStringVar:
    def __init__(self, value: str) -> None:
        self._value = value

    def get(self) -> str:
        return self._value

    def set(self, value: str) -> None:
        self._value = value


class FakeEntry:
    def __init__(self) -> None:
        self.textvariable: FakeStringVar | None = None
        self.bindings: dict[str, Callable[[FakeEvent], None]] = {}

    def pack(self, *_args: object, **_kwargs: object) -> None:
        return None

    def bind(self, sequence: str, callback: Callable[[FakeEvent], None]) -> None:
        self.bindings[sequence] = callback

    def fire(self, sequence: str, keysym: str = "") -> None:
        self.bindings[sequence](FakeEvent(keysym))


class FakeListbox:
    def __init__(self) -> None:
        self.items: list[str] = []
        self.visible = False
        self.selected_index: int | None = None
        self.bindings: dict[str, Callable[[FakeEvent], None]] = {}

    def pack(self, *_args: object, **_kwargs: object) -> None:
        self.visible = True

    def pack_forget(self) -> None:
        self.visible = False

    def bind(self, sequence: str, callback: Callable[[FakeEvent], None]) -> None:
        self.bindings[sequence] = callback

    def delete(self, _start: object, _end: object) -> None:
        self.items.clear()

    def insert(self, _index: object, item: str) -> None:
        self.items.append(item)

    def curselection(self) -> tuple[int, ...]:
        if self.selected_index is None:
            return ()

        return (self.selected_index,)

    def get(self, index: int) -> str:
        return self.items[index]

    def fire(self, sequence: str) -> None:
        self.bindings[sequence](FakeEvent())

