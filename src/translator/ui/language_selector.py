from collections.abc import Callable
from tkinter import END, Entry, Event, Frame, Label, Listbox, StringVar
from typing import Any, cast

from translator.languages import (
    AUTO_LANGUAGE_LABEL,
    common_language_labels,
    detected_language_label,
    normalize_source_language,
    source_language_label,
)


class SourceLanguageSelector:
    def __init__(
        self,
        parent: Any,
        initial_language: str | None,
        on_change: Callable[[str | None], None],
    ) -> None:
        self._on_change = on_change
        self._detected_codes: list[str] = []
        self._value = StringVar(value=source_language_label(initial_language))
        self._frame = Frame(parent, bg="#1c1c1c")
        Label(
            self._frame,
            text="Source Language",
            bg="#1c1c1c",
            fg="#9ca3af",
            font=("Inter", 10),
        ).pack(side="left", padx=(4, 6))
        self._entry_shell = Frame(
            self._frame,
            bg="#111111",
            highlightthickness=1,
            highlightbackground="#3f3f46",
            highlightcolor="#84cc16",
        )
        self._entry_shell.pack(side="left")
        self._entry = Entry(
            self._entry_shell,
            textvariable=self._value,
            width=18,
            bg="#111111",
            fg="#f5f5f5",
            insertbackground="#f5f5f5",
            relief="flat",
            highlightthickness=0,
            bd=0,
        )
        self._entry.pack(side="left", padx=8, ipady=5)
        self._listbox = Listbox(
            self._frame,
            height=6,
            bg="#111111",
            fg="#f5f5f5",
            selectbackground="#365314",
            selectforeground="#f5f5f5",
            relief="flat",
            highlightthickness=1,
            highlightbackground="#3f3f46",
        )
        self._listbox_visible = False
        self._refresh_options()
        self._entry.bind("<FocusIn>", self._show_options)
        self._entry.bind("<KeyRelease>", self._filter_options)
        self._entry.bind("<Return>", self._apply_selection)
        self._entry.bind("<Escape>", self._hide_options)
        self._entry.bind("<FocusOut>", self._apply_selection)
        self._listbox.bind("<<ListboxSelect>>", self._select_highlighted)
        self._listbox.bind("<ButtonRelease-1>", self._select_highlighted)

    def pack(self, *_args: Any, **_kwargs: Any) -> None:
        self._frame.pack(*_args, **_kwargs)

    def add_detected_language(self, code: str | None) -> None:
        if code is None or code in self._detected_codes:
            return

        self._detected_codes.insert(0, code)
        self._detected_codes = self._detected_codes[:5]
        self._refresh_options()

    def _show_options(self, _event: Event | None = None) -> None:
        if not self._listbox_visible:
            self._listbox.pack(side="left", padx=(8, 0))
            self._listbox_visible = True
        self._refresh_options()

    def _hide_options(self, _event: Event | None = None) -> None:
        if self._listbox_visible:
            self._listbox.pack_forget()
            self._listbox_visible = False

    def _filter_options(self, event: Event) -> None:
        if event.keysym in {"Return", "Escape"}:
            return

        self._show_options()

    def _select_highlighted(self, _event: Event | None = None) -> None:
        listbox = cast(Any, self._listbox)
        selection = cast(tuple[int, ...], listbox.curselection())
        if not selection:
            return

        self._value.set(cast(str, listbox.get(selection[0])))
        self._apply_selection()

    def _apply_selection(self, _event: Event | None = None) -> None:
        selected_language = normalize_source_language(self._value.get())
        self._value.set(source_language_label(selected_language))
        self._on_change(selected_language)
        self._hide_options()

    def _refresh_options(self) -> None:
        filter_text = self._value.get().strip().lower()
        labels = [
            label
            for label in self._values()
            if not filter_text
            or filter_text == AUTO_LANGUAGE_LABEL.lower()
            or filter_text in label.lower()
        ]
        self._listbox.delete(0, END)
        for label in labels:
            self._listbox.insert(END, label)

    def _values(self) -> list[str]:
        detected = [detected_language_label(code) for code in self._detected_codes]
        common = [
            label
            for label in common_language_labels()
            if label == AUTO_LANGUAGE_LABEL or label not in detected
        ]
        return [AUTO_LANGUAGE_LABEL, *detected, *common[1:]]
