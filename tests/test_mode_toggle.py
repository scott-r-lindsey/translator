from collections.abc import Callable

from pytest import MonkeyPatch

from translator.ui.mode_toggle import ModeToggle


def test_mode_toggle_changes_mode_and_button_styles(monkeypatch: MonkeyPatch) -> None:
    widgets = FakeModeWidgets()
    monkeypatch.setattr("translator.ui.mode_toggle.Frame", widgets.build_frame)
    monkeypatch.setattr("translator.ui.mode_toggle.Button", widgets.build_button)
    selected_modes: list[str] = []

    toggle = ModeToggle(object(), selected_modes.append)

    assert widgets.buttons[0].configured["bg"] == "#365314"
    assert widgets.buttons[1].configured["bg"] == "#27272a"

    widgets.buttons[1].invoke()

    assert selected_modes == ["transcript"]
    assert widgets.buttons[0].configured["bg"] == "#27272a"
    assert widgets.buttons[1].configured["bg"] == "#365314"

    toggle.set_mode("transcript")

    assert selected_modes == ["transcript"]


class FakeModeWidgets:
    def __init__(self) -> None:
        self.buttons: list[FakeButton] = []

    def build_frame(self, *_args: object, **_kwargs: object) -> "FakeFrame":
        return FakeFrame()

    def build_button(
        self,
        *_args: object,
        text: str,
        command: Callable[[], None],
        **_kwargs: object,
    ) -> "FakeButton":
        button = FakeButton(text, command)
        self.buttons.append(button)
        return button


class FakeFrame:
    def pack(self, *_args: object, **_kwargs: object) -> None:
        return None


class FakeButton:
    def __init__(self, text: str, command: Callable[[], None]) -> None:
        self.text = text
        self._command = command
        self.configured: dict[str, object] = {}

    def pack(self, *_args: object, **_kwargs: object) -> None:
        return None

    def configure(self, **kwargs: object) -> None:
        self.configured.update(kwargs)

    def invoke(self) -> None:
        self._command()

