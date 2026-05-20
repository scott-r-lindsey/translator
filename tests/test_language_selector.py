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
    assert widgets.options_panel.visible is False
    assert widgets.root.focused is True


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

    assert widgets.options_panel.items[:5] == [
        "Auto",
        "separator",
        "French detected",
        "Spanish detected",
        "separator",
    ]


def test_source_language_selector_selects_highlighted_option(monkeypatch: MonkeyPatch) -> None:
    widgets = patch_language_widgets(monkeypatch)
    selected: list[str | None] = []
    SourceLanguageSelector(object(), None, selected.append)

    widgets.entry.fire("<FocusIn>")
    widgets.options_panel.option("Spanish (es)").fire("<ButtonRelease-1>")

    assert selected == ["es"]
    assert widgets.string_var.get() == "Spanish (es)"
    assert widgets.root.focused is True


def test_source_language_selector_filters_options(monkeypatch: MonkeyPatch) -> None:
    widgets = patch_language_widgets(monkeypatch)
    SourceLanguageSelector(object(), None, lambda _language: None)

    widgets.string_var.set("span")
    widgets.entry.fire("<KeyRelease>", keysym="n")

    assert widgets.options_panel.visible is True
    assert widgets.options_panel.parent is widgets.root
    assert widgets.options_panel.place_kwargs == {"x": 120, "y": 84, "width": 180}
    assert widgets.options_panel.items == ["Spanish (es)"]


def patch_language_widgets(monkeypatch: MonkeyPatch) -> "FakeLanguageWidgets":
    widgets = FakeLanguageWidgets()
    monkeypatch.setattr(
        "translator.ui.language_selector.StringVar",
        widgets.build_string_var,
    )
    monkeypatch.setattr("translator.ui.language_selector.Frame", widgets.build_frame)
    monkeypatch.setattr("translator.ui.language_selector.Label", widgets.build_label)
    monkeypatch.setattr("translator.ui.language_selector.Entry", widgets.build_entry)
    return widgets


class FakeLanguageWidgets:
    def __init__(self) -> None:
        self.string_var = FakeStringVar("")
        self.root = FakeWidget(root_x=40, root_y=20)
        self.entry = FakeEntry()
        self.frames: list[FakeWidget] = []
        self.options_panel = FakeWidget()
        self.entry_shell: FakeWidget | None = None

    def build_string_var(self, *, value: str) -> "FakeStringVar":
        self.string_var = FakeStringVar(value)
        return self.string_var

    def build_frame(self, *_args: object, **_kwargs: object) -> "FakeWidget":
        frame = FakeWidget(parent=_args[0] if _args else None, root=self.root)
        if _kwargs.get("height") == 1:
            frame.text = "separator"
        self.frames.append(frame)
        if len(self.frames) == 1:
            frame.root = self.root
        elif len(self.frames) == 2:
            self.entry_shell = frame
        elif frame.parent is self.root:
            self.options_panel = frame
        return frame

    def build_label(self, *_args: object, text: str, **_kwargs: object) -> "FakeWidget":
        return FakeWidget(parent=_args[0] if _args else None, text=text, root=self.root)

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


class FakeWidget:
    def __init__(
        self,
        parent: object | None = None,
        text: str | None = None,
        root: "FakeWidget | None" = None,
        root_x: int = 0,
        root_y: int = 0,
    ) -> None:
        self.children: list[FakeWidget] = []
        self.parent = parent
        self.root = root or self
        self.visible = False
        self.text = text
        self.bindings: dict[str, Callable[[FakeEvent], None]] = {}
        self.place_kwargs: dict[str, object] = {}
        self.was_lifted = False
        self.focused = False
        self._destroyed = False
        self._root_x = root_x
        self._root_y = root_y
        if isinstance(parent, FakeWidget):
            parent.children.append(self)

    @property
    def items(self) -> list[str]:
        return [
            child.text
            for child in self.children
            if child.text is not None and not child._destroyed
        ]

    def pack(self, *_args: object, **_kwargs: object) -> None:
        self.visible = True

    def pack_forget(self) -> None:
        self.visible = False

    def place(self, *_args: object, **_kwargs: object) -> None:
        self.visible = True
        self.place_kwargs = dict(_kwargs)

    def place_forget(self) -> None:
        self.visible = False

    def lift(self) -> None:
        self.was_lifted = True

    def winfo_x(self) -> int:
        return 13

    def winfo_y(self) -> int:
        return 7

    def winfo_height(self) -> int:
        return 22

    def winfo_width(self) -> int:
        return 180

    def winfo_rootx(self) -> int:
        return 160 if self is not self.root else self._root_x

    def winfo_rooty(self) -> int:
        return 78 if self is not self.root else self._root_y

    def winfo_toplevel(self) -> "FakeWidget":
        return self.root

    def focus_set(self) -> None:
        self.focused = True

    def bind(self, sequence: str, callback: Callable[[FakeEvent], None]) -> None:
        self.bindings[sequence] = callback

    def fire(self, sequence: str) -> None:
        self.bindings[sequence](FakeEvent())

    def option(self, text: str) -> "FakeWidget":
        for child in self.children:
            if child.text == text and not child._destroyed:
                return child
        raise AssertionError(f"Missing option {text}")

    def winfo_children(self) -> list["FakeWidget"]:
        return [child for child in self.children if not child._destroyed]

    def destroy(self) -> None:
        self._destroyed = True


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
