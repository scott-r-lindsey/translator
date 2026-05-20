from collections.abc import Callable
from tkinter import Canvas, Event, Y
from typing import Any


class DarkScrollbar:
    def __init__(self, parent: Any, command: Callable[..., object] | None = None) -> None:
        self._command = command
        self._first = 0.0
        self._last = 1.0
        self._drag_start_y: int | None = None
        self._drag_start_first = 0.0
        self._hovered = False
        self._dragging = False
        self._canvas = Canvas(
            parent,
            width=12,
            height=1,
            bg="#111111",
            highlightthickness=0,
            bd=0,
        )
        self._canvas.bind("<Configure>", self._configure)
        self._canvas.bind("<Button-1>", self._click)
        self._canvas.bind("<B1-Motion>", self._drag)
        self._canvas.bind("<ButtonRelease-1>", self._release)
        self._canvas.bind("<Enter>", self._enter)
        self._canvas.bind("<Leave>", self._leave)
        self._draw()

    def pack(self, *_args: Any, **_kwargs: Any) -> None:
        _kwargs.setdefault("fill", Y)
        _kwargs.setdefault("expand", True)
        self._canvas.pack(*_args, **_kwargs)

    def grid(self, *_args: Any, **_kwargs: Any) -> None:
        _kwargs.setdefault("sticky", "ns")
        self._canvas.grid(*_args, **_kwargs)

    def set_command(self, command: Callable[..., object]) -> None:
        self._command = command

    def set(self, first: str | float, last: str | float) -> None:
        self._first = clamp(float(first))
        self._last = clamp(float(last))
        self._draw()

    def _configure(self, _event: Event) -> None:
        self._draw()

    def _enter(self, _event: Event) -> None:
        self._hovered = True
        self._draw()

    def _leave(self, _event: Event) -> None:
        self._hovered = False
        self._draw()

    def _click(self, event: Event) -> None:
        top, bottom = self._thumb_bounds()
        if top <= event.y <= bottom:
            self._drag_start_y = event.y
            self._drag_start_first = self._first
            self._dragging = True
            self._draw()
            return

        self._move_to_event_y(event.y)

    def _drag(self, event: Event) -> None:
        if self._drag_start_y is None:
            return

        track_height = self._track_height()
        thumb_height = self._thumb_height()
        movable_height = max(track_height - thumb_height, 1)
        delta = event.y - self._drag_start_y
        self._moveto(self._drag_start_first + (delta / movable_height))

    def _release(self, _event: Event) -> None:
        self._drag_start_y = None
        self._dragging = False
        self._draw()

    def _move_to_event_y(self, y: int) -> None:
        track_height = self._track_height()
        thumb_height = self._thumb_height()
        movable_height = max(track_height - thumb_height, 1)
        self._moveto((y - (thumb_height / 2)) / movable_height)

    def _moveto(self, fraction: float) -> None:
        fraction = clamp(fraction)
        if self._command is not None:
            self._command("moveto", fraction)

    def _draw(self) -> None:
        self._canvas.delete("all")
        width = self._canvas_width()
        height = self._track_height()
        self._canvas.create_rectangle(0, 0, width, height, fill="#111111", outline="#111111")
        if self._last - self._first >= 0.999:
            return

        top, bottom = self._thumb_bounds()
        color = "#71717a" if self._dragging else "#52525b" if self._hovered else "#3f3f46"
        self._canvas.create_rectangle(2, top, width - 2, bottom, fill=color, outline=color)

    def _thumb_bounds(self) -> tuple[int, int]:
        track_height = self._track_height()
        top = int(self._first * track_height)
        bottom = int(self._last * track_height)
        minimum_height = self._minimum_thumb_height()
        if bottom - top >= minimum_height:
            return top, bottom

        if self._last >= 1:
            bottom = track_height
            top = max(bottom - minimum_height, 0)
        else:
            bottom = min(top + minimum_height, track_height)
        return top, bottom

    def _thumb_height(self) -> int:
        visible_fraction = max(self._last - self._first, 0.05)
        return max(int(self._track_height() * visible_fraction), self._minimum_thumb_height())

    def _minimum_thumb_height(self) -> int:
        return 28

    def _track_height(self) -> int:
        return max(self._canvas.winfo_height(), 1)

    def _canvas_width(self) -> int:
        return max(self._canvas.winfo_width(), 12)


def clamp(value: float) -> float:
    return min(max(value, 0.0), 1.0)
