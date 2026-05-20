from collections.abc import Callable
from tkinter import Entry, Event, Frame, Label, StringVar
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
        self._overlay_parent = cast(Any, self._frame).winfo_toplevel()
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
        self._entry.bind("<FocusIn>", self._show_options)
        self._entry.bind("<KeyRelease>", self._filter_options)
        self._entry.bind("<Return>", self._apply_selection_and_blur)
        self._entry.bind("<Escape>", self._hide_options)
        self._entry.bind("<FocusOut>", self._apply_selection)
        self._options_panel = Frame(
            self._overlay_parent,
            bg="#111111",
            highlightthickness=1,
            highlightbackground="#3f3f46",
        )
        self._options_visible = False
        self._refresh_options()

    def pack(self, *_args: Any, **_kwargs: Any) -> None:
        self._frame.pack(*_args, **_kwargs)

    def add_detected_language(self, code: str | None) -> None:
        if code is None or code in self._detected_codes:
            return

        self._detected_codes.insert(0, code)
        self._detected_codes = self._detected_codes[:5]
        self._refresh_options()

    def _show_options(self, _event: Event | None = None) -> None:
        if not self._options_visible:
            x = self._entry_shell.winfo_rootx() - self._overlay_parent.winfo_rootx()
            y = (
                self._entry_shell.winfo_rooty()
                - self._overlay_parent.winfo_rooty()
                + self._entry_shell.winfo_height()
                + 4
            )
            self._options_panel.place(
                x=x,
                y=y,
                width=self._entry_shell.winfo_width(),
            )
            cast(Any, self._options_panel).lift()
            self._options_visible = True
        self._refresh_options()

    def _hide_options(self, _event: Event | None = None) -> None:
        if self._options_visible:
            self._options_panel.place_forget()
            self._options_visible = False

    def _filter_options(self, event: Event) -> None:
        if event.keysym in {"Return", "Escape"}:
            return

        self._show_options()

    def _select_option(self, label: str) -> None:
        self._value.set(label)
        self._apply_selection()
        self._clear_focus()

    def _apply_selection_and_blur(self, event: Event | None = None) -> None:
        self._apply_selection(event)
        self._clear_focus()

    def _apply_selection(self, _event: Event | None = None) -> None:
        selected_language = normalize_source_language(self._value.get())
        self._value.set(source_language_label(selected_language))
        self._on_change(selected_language)
        self._hide_options()

    def _clear_focus(self) -> None:
        self._overlay_parent.focus_set()

    def _refresh_options(self) -> None:
        for child in self._options_panel.winfo_children():
            child.destroy()

        groups = self._groups()
        for group_index, labels in enumerate(groups):
            if group_index > 0:
                self._add_separator()
            for label in labels:
                self._add_option(label)

    def _groups(self) -> list[list[str]]:
        filter_text = self._value.get().strip().lower()
        detected = [detected_language_label(code) for code in self._detected_codes]
        common = [
            label
            for label in common_language_labels()
            if label == AUTO_LANGUAGE_LABEL or label not in detected
        ]
        groups = [[AUTO_LANGUAGE_LABEL], detected, common[1:]]
        return [
            filtered
            for group in groups
            if (
                filtered := [
                    label
                    for label in group
                    if not filter_text
                    or filter_text == AUTO_LANGUAGE_LABEL.lower()
                    or filter_text in label.lower()
                ]
            )
        ]

    def _add_separator(self) -> None:
        Frame(self._options_panel, bg="#3f3f46", height=1).pack(
            fill="x",
            padx=8,
            pady=4,
        )

    def _add_option(self, label: str) -> None:
        option = Label(
            self._options_panel,
            text=label,
            bg="#111111",
            fg="#f5f5f5",
            activebackground="#365314",
            activeforeground="#f5f5f5",
            anchor="w",
            cursor="hand2",
            font=("Inter", 10),
        )
        option.pack(fill="x", padx=8, pady=1, ipady=4)
        option.bind(
            "<ButtonRelease-1>",
            lambda _event, option_label=label: self._select_option(option_label),
        )
