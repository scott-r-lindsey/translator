from tkinter import END, Frame, Text
from typing import Any, Protocol, cast

from translator.languages import source_language_label
from translator.transcript import TranscriptEntry, format_timestamp
from translator.ui.dark_scrollbar import DarkScrollbar


class ScrollableText(Protocol):
    def yview(self, *args: object) -> tuple[float, float] | None:
        ...


class TranscriptView:
    def __init__(self, parent: Any) -> None:
        self._frame = Frame(
            parent,
            bg="#111111",
        )
        self._scrollbar = DarkScrollbar(self._frame)
        self._text = Text(
            self._frame,
            bg="#111111",
            fg="#f5f5f5",
            insertbackground="#f5f5f5",
            relief="flat",
            wrap="word",
            padx=18,
            pady=16,
            font=("Inter", 14),
            state="disabled",
            highlightthickness=0,
            yscrollcommand=self._scrollbar.set,
        )
        self._scrollbar.set_command(cast(ScrollableText, self._text).yview)
        self._frame.rowconfigure(0, weight=1)
        self._frame.columnconfigure(0, weight=1)
        self._frame.columnconfigure(1, weight=0)
        self._text.grid(row=0, column=0, sticky="nsew")
        self._scrollbar.grid(row=0, column=1, sticky="ns")
        self._text.tag_configure(
            "meta",
            foreground="#9ca3af",
            font=("Inter", 10),
            spacing1=8,
            spacing3=3,
        )
        self._text.tag_configure(
            "source",
            foreground="#c7c7c7",
            font=("Inter", 13),
            spacing3=3,
        )
        self._text.tag_configure(
            "translation",
            foreground="#f5f5f5",
            font=("Inter", 16),
            spacing3=10,
        )

    def pack(self, *_args: Any, **_kwargs: Any) -> None:
        self._frame.pack(*_args, **_kwargs)

    def pack_forget(self) -> None:
        self._frame.pack_forget()

    def append(self, entry: TranscriptEntry) -> None:
        self._text.configure(state="normal")
        if self._text.index("end-1c") != "1.0":
            self._text.insert(END, "\n")

        self._insert_entry(entry)
        self._text.see(END)
        self._text.configure(state="disabled")

    def clear(self) -> None:
        self._text.configure(state="normal")
        self._text.delete("1.0", END)
        self._text.configure(state="disabled")

    def _insert_entry(self, entry: TranscriptEntry) -> None:
        timestamp = format_timestamp(entry.timestamp_seconds)
        language = source_language_label(entry.detected_language)
        self._text.insert(END, f"[{timestamp}] {language}\n", "meta")
        if entry.source_text:
            self._text.insert(END, f"{entry.source_text}\n", "source")
        if entry.translated_text:
            self._text.insert(END, entry.translated_text, "translation")
