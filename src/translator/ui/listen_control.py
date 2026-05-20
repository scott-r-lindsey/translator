from collections.abc import Callable
from tkinter import Canvas, Event
from typing import Any


class ListenControl:
    def __init__(self, parent: Any, command: Callable[[], None]) -> None:
        self.enabled = False
        self._command = command
        self._status = "loading"
        self._listening = False
        self._hovered = False
        self._pulse = 0
        self._animation_scheduled = False
        self._canvas = Canvas(
            parent,
            width=52,
            height=52,
            bg="#1c1c1c",
            highlightthickness=0,
            bd=0,
        )
        self._canvas.bind("<Button-1>", self._click)
        self._canvas.bind("<Enter>", self._enter)
        self._canvas.bind("<Leave>", self._leave)
        self._draw()
        self._schedule_animation()

    def pack(self, *_args: Any, **_kwargs: Any) -> None:
        self._canvas.pack(*_args, **_kwargs)

    def set_enabled(self, enabled: bool) -> None:
        self.enabled = enabled
        self._draw()

    def set_listening(self, listening: bool) -> None:
        self._listening = listening
        self._status = "listening" if listening else "ready"
        self._draw()

    def set_status(self, status: str) -> None:
        self._status = status
        self._draw()

    def _click(self, _event: Event) -> None:
        if self.enabled:
            self._command()

    def _enter(self, _event: Event) -> None:
        self._hovered = True
        self._draw()

    def _leave(self, _event: Event) -> None:
        self._hovered = False
        self._draw()

    def _schedule_animation(self) -> None:
        if self._animation_scheduled:
            return

        self._animation_scheduled = True
        self._canvas.after(140, self._animate)

    def _animate(self) -> None:
        self._animation_scheduled = False
        self._pulse = (self._pulse + 1) % 12
        self._draw()
        self._schedule_animation()

    def _draw(self) -> None:
        self._canvas.delete("all")
        ring_color = self._ring_color()
        fill_color = self._fill_color()
        radius = 18
        if self._listening or self._status in {"audio", "speech"}:
            radius += self._pulse % 4

        self._canvas.create_oval(
            26 - radius,
            26 - radius,
            26 + radius,
            26 + radius,
            outline=ring_color,
            width=2,
        )
        self._canvas.create_oval(11, 11, 41, 41, fill=fill_color, outline=fill_color)
        if self._listening:
            self._draw_stop_icon()
        elif self._status == "loading":
            self._draw_loading_icon()
        elif self._status == "error":
            self._draw_error_icon()
        else:
            self._draw_microphone_icon()

    def _ring_color(self) -> str:
        if not self.enabled and self._status != "loading":
            return "#3f3f46"
        if self._status == "speech":
            return "#22c55e"
        if self._status == "audio":
            return "#84cc16"
        if self._listening or self._status == "listening":
            return "#38bdf8"
        if self._status == "error":
            return "#f97316"
        if self._status == "loading":
            return "#71717a"
        if self._hovered:
            return "#f5f5f5"
        return "#a3e635"

    def _fill_color(self) -> str:
        if not self.enabled and self._status != "loading":
            return "#27272a"
        if self._status == "error":
            return "#431407"
        if self._listening:
            return "#082f49"
        if self._status == "loading":
            return "#27272a"
        if self._hovered:
            return "#365314"
        return "#1f2937"

    def _draw_microphone_icon(self) -> None:
        color = "#f5f5f5" if self.enabled else "#71717a"
        self._canvas.create_oval(21, 15, 31, 31, outline=color, width=2)
        self._canvas.create_line(21, 24, 21, 27, fill=color, width=2)
        self._canvas.create_line(31, 24, 31, 27, fill=color, width=2)
        self._canvas.create_line(18, 27, 19, 31, fill=color, width=2)
        self._canvas.create_line(34, 27, 33, 31, fill=color, width=2)
        self._canvas.create_line(20, 33, 24, 35, fill=color, width=2)
        self._canvas.create_line(28, 35, 32, 33, fill=color, width=2)
        self._canvas.create_line(26, 36, 26, 40, fill=color, width=2)
        self._canvas.create_line(21, 40, 31, 40, fill=color, width=2)

    def _draw_stop_icon(self) -> None:
        color = "#f5f5f5"
        self._canvas.create_rectangle(19, 19, 33, 33, fill=color, outline=color)

    def _draw_loading_icon(self) -> None:
        color = "#d4d4d8"
        active = self._pulse % 3
        for index, x in enumerate([19, 26, 33]):
            fill = color if index == active else "#52525b"
            self._canvas.create_oval(x - 2, 24, x + 2, 28, fill=fill, outline=fill)

    def _draw_error_icon(self) -> None:
        color = "#fed7aa"
        self._canvas.create_line(26, 17, 26, 29, fill=color, width=3)
        self._canvas.create_oval(24, 34, 28, 38, fill=color, outline=color)

