from collections.abc import Callable

from pytest import MonkeyPatch

from translator.ui.listen_control import ListenControl


def test_listen_control_ignores_click_until_enabled(monkeypatch: MonkeyPatch) -> None:
    canvas = patch_canvas(monkeypatch)
    calls = 0

    def command() -> None:
        nonlocal calls
        calls += 1

    control = ListenControl(object(), command)

    canvas.click()

    assert calls == 0

    control.set_enabled(True)
    canvas.click()

    assert calls == 1


def test_listen_control_draws_stop_icon_when_listening(monkeypatch: MonkeyPatch) -> None:
    canvas = patch_canvas(monkeypatch)
    control = ListenControl(object(), lambda: None)

    control.set_enabled(True)
    control.set_listening(True)

    assert canvas.operations[-1].name == "rectangle"
    assert canvas.operations[-1].kwargs["fill"] == "#f5f5f5"


def test_listen_control_uses_status_colors(monkeypatch: MonkeyPatch) -> None:
    canvas = patch_canvas(monkeypatch)
    control = ListenControl(object(), lambda: None)

    control.set_enabled(True)
    control.set_status("speech")

    assert canvas.operations[0].kwargs["outline"] == "#22c55e"

    control.set_status("audio")

    assert canvas.operations[0].kwargs["outline"] == "#84cc16"

    control.set_status("error")

    assert canvas.operations[0].kwargs["outline"] == "#f97316"
    assert canvas.operations[1].kwargs["fill"] == "#431407"


def test_listen_control_animates_pulse(monkeypatch: MonkeyPatch) -> None:
    canvas = patch_canvas(monkeypatch)
    control = ListenControl(object(), lambda: None)
    control.set_enabled(True)
    control.set_listening(True)

    first_ring = canvas.operations[0].args
    canvas.run_after_callback()

    assert canvas.operations[0].args != first_ring


def patch_canvas(monkeypatch: MonkeyPatch) -> "FakeCanvas":
    fake_canvas = FakeCanvas()
    monkeypatch.setattr(
        "translator.ui.listen_control.Canvas",
        build_fake_canvas_factory(fake_canvas),
    )
    return fake_canvas


def build_fake_canvas_factory(canvas: "FakeCanvas") -> Callable[..., "FakeCanvas"]:
    def build_canvas(*_args: object, **_kwargs: object) -> FakeCanvas:
        return canvas

    return build_canvas


class FakeCanvas:
    def __init__(self) -> None:
        self.operations: list[CanvasOperation] = []
        self.bindings: dict[str, Callable[[object], None]] = {}
        self.after_callbacks: list[Callable[[], None]] = []

    def bind(self, sequence: str, callback: Callable[[object], None]) -> None:
        self.bindings[sequence] = callback

    def pack(self, *_args: object, **_kwargs: object) -> None:
        return None

    def after(self, _delay_ms: int, callback: Callable[[], None]) -> None:
        self.after_callbacks.append(callback)

    def delete(self, tag: str) -> None:
        assert tag == "all"
        self.operations.clear()

    def create_oval(self, *args: object, **kwargs: object) -> int:
        self.operations.append(CanvasOperation("oval", args, kwargs))
        return len(self.operations)

    def create_line(self, *args: object, **kwargs: object) -> int:
        self.operations.append(CanvasOperation("line", args, kwargs))
        return len(self.operations)

    def create_rectangle(self, *args: object, **kwargs: object) -> int:
        self.operations.append(CanvasOperation("rectangle", args, kwargs))
        return len(self.operations)

    def click(self) -> None:
        self.bindings["<Button-1>"](object())

    def run_after_callback(self) -> None:
        callback = self.after_callbacks.pop(0)
        callback()


class CanvasOperation:
    def __init__(
        self,
        name: str,
        args: tuple[object, ...],
        kwargs: dict[str, object],
    ) -> None:
        self.name = name
        self.args = args
        self.kwargs = kwargs
