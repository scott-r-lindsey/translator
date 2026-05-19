from collections.abc import Callable
from tkinter import BOTH, Tk
from tkinter.ttk import Frame, Label, Style
from typing import Any

from translator.config import AppSettings


class SubtitleWindow:
    def __init__(self, settings: AppSettings) -> None:
        self._settings = settings
        self._root_factory: Callable[[], Any] = Tk

    def run(self) -> None:
        root = self._root_factory()
        root.title(self._settings.window_title)
        root.geometry(f"{self._settings.width}x{self._settings.height}")
        root.attributes("-topmost", self._settings.always_on_top)
        root.attributes("-alpha", self._settings.opacity)

        style = Style(root)
        style.configure("Shell.TFrame", background="#111111")
        style.configure(
            "Subtitle.TLabel",
            background="#111111",
            foreground="#f5f5f5",
            font=("Inter", 24),
            padding=24,
        )

        frame = Frame(root, style="Shell.TFrame")
        frame.pack(fill=BOTH, expand=True)

        label = Label(
            frame,
            text=self._settings.placeholder_text,
            anchor="center",
            justify="center",
            style="Subtitle.TLabel",
            wraplength=max(self._settings.width - 48, 1),
        )
        label.pack(fill=BOTH, expand=True)

        root.mainloop()


def main() -> None:
    SubtitleWindow(AppSettings()).run()


if __name__ == "__main__":
    main()
