from collections.abc import Callable
from tkinter import Button, Frame
from typing import Any


class ModeToggle:
    def __init__(self, parent: Any, on_change: Callable[[str], None]) -> None:
        self._on_change = on_change
        self._mode = "live"
        self._frame = Frame(parent, bg="#1c1c1c")
        self._live_button = self._build_button("Live", "live")
        self._transcript_button = self._build_button("Transcript", "transcript")
        self._live_button.pack(side="left")
        self._transcript_button.pack(side="left", padx=(4, 0))
        self._sync_buttons()

    def pack(self, *_args: Any, **_kwargs: Any) -> None:
        self._frame.pack(*_args, **_kwargs)

    def set_mode(self, mode: str) -> None:
        if mode == self._mode:
            return

        self._mode = mode
        self._sync_buttons()
        self._on_change(mode)

    def _build_button(self, text: str, mode: str) -> Button:
        return Button(
            self._frame,
            text=text,
            command=lambda: self.set_mode(mode),
            bg="#27272a",
            fg="#f5f5f5",
            activebackground="#365314",
            activeforeground="#f5f5f5",
            relief="flat",
            bd=0,
            padx=10,
            pady=6,
        )

    def _sync_buttons(self) -> None:
        self._configure_button(self._live_button, self._mode == "live")
        self._configure_button(self._transcript_button, self._mode == "transcript")

    def _configure_button(self, button: Button, selected: bool) -> None:
        button.configure(
            bg="#365314" if selected else "#27272a",
            fg="#f5f5f5" if selected else "#d4d4d8",
        )

