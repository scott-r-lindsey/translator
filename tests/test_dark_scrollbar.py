from collections.abc import Callable

from pytest import MonkeyPatch

from translator.ui.dark_scrollbar import DarkScrollbar, clamp


def test_dark_scrollbar_updates_thumb_from_scroll_range(monkeypatch: MonkeyPatch) -> None:
    canvas = patch_canvas(monkeypatch)
    scrollbar = DarkScrollbar(object())

    scrollbar.set("0.25", "0.75")

    assert canvas.rectangles[-1] == (2, 25, 10, 75)


def test_dark_scrollbar_thumb_reaches_track_bottom(monkeypatch: MonkeyPatch) -> None:
    canvas = patch_canvas(monkeypatch)
    scrollbar = DarkScrollbar(object())

    scrollbar.set("0.75", "1.0")

    assert canvas.rectangles[-1] == (2, 72, 10, 100)


def test_dark_scrollbar_packs_to_fill_height(monkeypatch: MonkeyPatch) -> None:
    canvas = patch_canvas(monkeypatch)
    scrollbar = DarkScrollbar(object())

    scrollbar.pack(side="right")

    assert canvas.pack_kwargs["side"] == "right"
    assert canvas.pack_kwargs["fill"] == "y"
    assert canvas.pack_kwargs["expand"] is True


def test_dark_scrollbar_grids_to_fill_height(monkeypatch: MonkeyPatch) -> None:
    canvas = patch_canvas(monkeypatch)
    scrollbar = DarkScrollbar(object())

    scrollbar.grid(row=0, column=1)

    assert canvas.grid_kwargs == {"row": 0, "column": 1, "sticky": "ns"}


def test_dark_scrollbar_drag_calls_moveto(monkeypatch: MonkeyPatch) -> None:
    canvas = patch_canvas(monkeypatch)
    commands: list[tuple[str, float]] = []
    scrollbar = DarkScrollbar(object(), capture_commands(commands))
    scrollbar.set("0.0", "0.5")

    canvas.fire("<Button-1>", y=10)
    canvas.fire("<B1-Motion>", y=35)
    canvas.fire("<ButtonRelease-1>", y=35)

    assert commands == [("moveto", 0.5)]


def test_dark_scrollbar_track_click_calls_moveto(monkeypatch: MonkeyPatch) -> None:
    canvas = patch_canvas(monkeypatch)
    commands: list[tuple[str, float]] = []
    scrollbar = DarkScrollbar(object(), capture_commands(commands))
    scrollbar.set("0.0", "0.25")

    canvas.fire("<Button-1>", y=80)

    assert commands == [("moveto", 0.9166666666666666)]


def test_clamp() -> None:
    assert clamp(-1) == 0
    assert clamp(0.5) == 0.5
    assert clamp(2) == 1


def patch_canvas(monkeypatch: MonkeyPatch) -> "FakeCanvas":
    canvas = FakeCanvas()
    monkeypatch.setattr("translator.ui.dark_scrollbar.Canvas", build_fake_canvas(canvas))
    return canvas


def build_fake_canvas(canvas: "FakeCanvas") -> Callable[..., "FakeCanvas"]:
    def build_canvas(*_args: object, **_kwargs: object) -> FakeCanvas:
        return canvas

    return build_canvas


def capture_commands(commands: list[tuple[str, float]]) -> Callable[..., object]:
    def command(name: str, fraction: float) -> None:
        commands.append((name, fraction))

    return command


class FakeCanvas:
    def __init__(self) -> None:
        self.bindings: dict[str, Callable[[FakeEvent], None]] = {}
        self.rectangles: list[tuple[int, int, int, int]] = []
        self.pack_kwargs: dict[str, object] = {}
        self.grid_kwargs: dict[str, object] = {}

    def bind(self, sequence: str, callback: Callable[["FakeEvent"], None]) -> None:
        self.bindings[sequence] = callback

    def pack(self, *_args: object, **_kwargs: object) -> None:
        self.pack_kwargs = dict(_kwargs)

    def grid(self, *_args: object, **_kwargs: object) -> None:
        self.grid_kwargs = dict(_kwargs)

    def delete(self, tag: str) -> None:
        assert tag == "all"
        self.rectangles.clear()

    def create_rectangle(
        self,
        x1: int,
        y1: int,
        x2: int,
        y2: int,
        **_kwargs: object,
    ) -> int:
        self.rectangles.append((x1, y1, x2, y2))
        return len(self.rectangles)

    def winfo_height(self) -> int:
        return 100

    def winfo_width(self) -> int:
        return 12

    def fire(self, sequence: str, *, y: int) -> None:
        self.bindings[sequence](FakeEvent(y))


class FakeEvent:
    def __init__(self, y: int) -> None:
        self.y = y
