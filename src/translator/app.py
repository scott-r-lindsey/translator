from collections.abc import Callable
from queue import SimpleQueue
from threading import Thread
from time import monotonic
from tkinter import BOTH, LEFT, RIGHT, Button, Tk, X
from tkinter.ttk import Frame, Label, Style
from typing import Any

from translator.audio import (
    AudioActivityMonitor,
    AudioStatus,
    DisplayEvent,
    DisplayEventKind,
    PulseAudioActivityMonitor,
    status_event,
)
from translator.config import AppSettings
from translator.transcript import TranscriptEntry
from translator.ui.language_selector import SourceLanguageSelector
from translator.ui.listen_control import ListenControl
from translator.ui.mode_toggle import ModeToggle
from translator.ui.transcript_view import TranscriptView


class SubtitleWindow:
    def __init__(
        self,
        settings: AppSettings,
        audio_monitor: AudioActivityMonitor | None = None,
    ) -> None:
        self._settings = settings
        self._audio_monitor = audio_monitor or PulseAudioActivityMonitor(settings)
        self._event_queue: SimpleQueue[DisplayEvent] = SimpleQueue()
        self._is_listening = False
        self._language_selector: SourceLanguageSelector | None = None
        self._listen_control: ListenControl | None = None
        self._mode_toggle: ModeToggle | None = None
        self._transcript_view: TranscriptView | None = None
        self._clear_transcript_button: Any | None = None
        self._live_frame: Any | None = None
        self._content_frame: Any | None = None
        self._root: Any | None = None
        self._current_mode = "live"
        self._mode_geometries = {
            "live": f"{settings.width}x{settings.height}",
            "transcript": f"{settings.width}x{settings.height * 2}",
        }
        self._has_transcript_entries = False
        self._last_caption_at: float | None = None
        self._clock: Callable[[], float] = monotonic
        self._root_factory: Callable[[], Any] = Tk

    def run(self) -> None:
        root = self._root_factory()
        self._root = root
        root.title(self._settings.window_title)
        root.geometry(self._mode_geometries["live"])
        root.attributes("-topmost", self._settings.always_on_top)
        root.attributes("-alpha", self._settings.opacity)

        style = Style(root)
        style.configure("Shell.TFrame", background="#111111")
        style.configure("Header.TFrame", background="#1c1c1c")
        style.configure(
            "HeaderMuted.TLabel",
            background="#1c1c1c",
            foreground="#9ca3af",
            font=("Inter", 10),
        )
        style.configure(
            "Status.TLabel",
            background="#1c1c1c",
            foreground="#d8d8d8",
            font=("Inter", 12),
            padding=12,
        )
        style.configure(
            "Section.TLabel",
            background="#111111",
            foreground="#9ca3af",
            font=("Inter", 11),
            padding=(18, 14, 18, 4),
        )
        style.configure(
            "Source.TLabel",
            background="#111111",
            foreground="#c7c7c7",
            font=("Inter", 18),
            padding=(18, 0, 18, 12),
        )
        style.configure(
            "Translation.TLabel",
            background="#111111",
            foreground="#f5f5f5",
            font=("Inter", 26),
            padding=(18, 0, 18, 18),
        )

        frame = Frame(root, style="Shell.TFrame")
        frame.pack(fill=BOTH, expand=True)

        header = Frame(frame, style="Header.TFrame")
        header.pack(fill=X)

        listen_control = ListenControl(header, self._toggle_listening)
        listen_control.pack(side=LEFT, padx=12, pady=10)
        self._listen_control = listen_control

        language_selector = SourceLanguageSelector(
            header,
            self._settings.whisper_language,
            self._audio_monitor.set_source_language,
        )
        language_selector.pack(side=LEFT, padx=(0, 12), pady=10)
        self._language_selector = language_selector

        mode_toggle = ModeToggle(header, self._set_mode)
        mode_toggle.pack(side=LEFT, padx=(0, 12), pady=10)
        self._mode_toggle = mode_toggle

        clear_transcript_button = Button(
            header,
            text="Clear",
            command=self._clear_transcript,
            state="disabled",
            bg="#1c1c1c",
            fg="#a1a1aa",
            activebackground="#27272a",
            activeforeground="#f5f5f5",
            disabledforeground="#52525b",
            relief="flat",
            bd=0,
            highlightthickness=0,
            padx=8,
            pady=3,
            font=("Inter", 10),
            cursor="hand2",
        )
        self._clear_transcript_button = clear_transcript_button

        status_label = Label(
            header,
            text="Loading models...",
            anchor="e",
            justify="right",
            style="Status.TLabel",
        )
        status_label.pack(side=RIGHT, fill=X, expand=True)

        content_frame = Frame(frame, style="Shell.TFrame")
        content_frame.pack(fill=BOTH, expand=True)
        self._content_frame = content_frame

        live_frame = Frame(content_frame, style="Shell.TFrame")
        live_frame.pack(fill=BOTH, expand=True)
        self._live_frame = live_frame

        original_label = Label(
            live_frame,
            text="Original",
            anchor="w",
            style="Section.TLabel",
        )
        original_label.pack(fill=X)
        source_label = Label(
            live_frame,
            text="",
            anchor="nw",
            justify="left",
            style="Source.TLabel",
            wraplength=max(self._settings.width - 36, 1),
        )
        source_label.pack(fill=BOTH, expand=True)

        translation_heading = Label(
            live_frame,
            text="Translation",
            anchor="w",
            style="Section.TLabel",
        )
        translation_heading.pack(fill=X)
        translation_label = Label(
            live_frame,
            text="",
            anchor="nw",
            justify="left",
            style="Translation.TLabel",
            wraplength=max(self._settings.width - 36, 1),
        )
        translation_label.pack(fill=BOTH, expand=True)
        live_focus_targets = (
            live_frame,
            original_label,
            source_label,
            translation_heading,
            translation_label,
        )
        for widget in live_focus_targets:
            widget.bind("<Button-1>", lambda _event, app_root=root: app_root.focus_set())

        self._transcript_view = TranscriptView(content_frame)

        root.protocol("WM_DELETE_WINDOW", lambda: self._close(root))
        root.after(
            100,
            lambda: self._poll_events(
                root,
                status_label,
                source_label,
                translation_label,
            ),
        )
        Thread(
            target=self._prepare_audio_monitor,
            name="model-preload",
            daemon=True,
        ).start()
        root.mainloop()

    def _poll_events(
        self,
        root: Any,
        status_label: Any,
        source_label: Any,
        translation_label: Any,
    ) -> None:
        while not self._event_queue.empty():
            event = self._event_queue.get()
            if event.kind is DisplayEventKind.STATUS:
                status_label.configure(text=event.text)
                self._handle_status(event.text)
            elif event.kind is DisplayEventKind.CAPTION:
                source_label.configure(text=event.source_text)
                translation_label.configure(text=event.translated_text or event.source_text)
                self._last_caption_at = self._clock()
                self._append_transcript_entry(event)
                if self._language_selector is not None:
                    self._language_selector.add_detected_language(event.detected_language)

        self._clear_expired_caption(source_label, translation_label)
        root.after(
            100,
            lambda: self._poll_events(root, status_label, source_label, translation_label),
        )

    def _toggle_listening(self) -> None:
        if self._is_listening:
            self._audio_monitor.stop()
            self._is_listening = False
            self._event_queue.put(status_event("Ready"))
            if self._listen_control is not None:
                self._listen_control.set_listening(False)
            return

        if self._listen_control is None or not self._listen_control.enabled:
            return

        self._audio_monitor.start(self._event_queue.put)
        self._is_listening = True
        self._listen_control.set_listening(True)

    def _close(self, root: Any) -> None:
        self._audio_monitor.stop()
        root.destroy()

    def set_clock(self, clock: Callable[[], float]) -> None:
        self._clock = clock

    def _set_mode(self, mode: str) -> None:
        if self._live_frame is None or self._transcript_view is None:
            return
        if mode == self._current_mode:
            return

        self._remember_current_geometry()
        if mode == "transcript":
            self._live_frame.pack_forget()
            self._transcript_view.pack(fill=BOTH, expand=True)
            self._current_mode = mode
            self._apply_current_geometry()
            self._update_clear_transcript_button()
            return

        self._transcript_view.pack_forget()
        self._live_frame.pack(fill=BOTH, expand=True)
        self._current_mode = "live"
        self._apply_current_geometry()
        self._update_clear_transcript_button()

    def _remember_current_geometry(self) -> None:
        if self._root is None:
            return

        self._mode_geometries[self._current_mode] = self._root.geometry()

    def _apply_current_geometry(self) -> None:
        if self._root is None:
            return

        before_x = self._root.winfo_rootx()
        before_y = self._root.winfo_rooty()
        geometry = self._geometry_with_current_origin(self._mode_geometries[self._current_mode])
        self._root.geometry(geometry)
        self._root.update_idletasks()

        after_x = self._root.winfo_rootx()
        after_y = self._root.winfo_rooty()
        if after_x == before_x and after_y == before_y:
            return

        origin_x, origin_y = _geometry_origin_values(geometry)
        corrected_geometry = (
            f"{_geometry_size(geometry)}"
            f"{_geometry_position(origin_x + before_x - after_x)}"
            f"{_geometry_position(origin_y + before_y - after_y)}"
        )
        self._root.geometry(corrected_geometry)

    def _geometry_with_current_origin(self, geometry: str) -> str:
        if self._root is None:
            return geometry

        size = _geometry_size(geometry)
        return f"{size}{_geometry_origin(self._root.geometry())}"

    def _append_transcript_entry(self, event: DisplayEvent) -> None:
        if self._transcript_view is None:
            return

        self._transcript_view.append(
            TranscriptEntry(
                timestamp_seconds=self._clock(),
                source_text=event.source_text,
                translated_text=event.translated_text,
                detected_language=event.detected_language,
            )
        )
        self._has_transcript_entries = True
        self._update_clear_transcript_button()

    def _clear_transcript(self) -> None:
        if self._transcript_view is None:
            return

        self._transcript_view.clear()
        self._has_transcript_entries = False
        self._update_clear_transcript_button()

    def _update_clear_transcript_button(self) -> None:
        if self._clear_transcript_button is None:
            return

        if self._current_mode != "transcript":
            self._clear_transcript_button.pack_forget()
            return

        self._clear_transcript_button.pack(side=LEFT, padx=(0, 12), pady=10)
        state = "normal" if self._has_transcript_entries else "disabled"
        self._clear_transcript_button.configure(state=state)

    def _prepare_audio_monitor(self) -> None:
        try:
            self._audio_monitor.prepare(self._event_queue.put)
        except Exception as error:
            self._event_queue.put(status_event(f"Model load unavailable: {error}"))

    def _handle_status(self, status: str) -> None:
        if self._listen_control is None:
            return

        if status == AudioStatus.READY.value:
            self._listen_control.set_enabled(True)
            self._listen_control.set_status("ready")
        elif status == AudioStatus.LISTENING.value:
            self._listen_control.set_status("listening")
        elif status == AudioStatus.AUDIO_DETECTED.value:
            self._listen_control.set_status("audio")
        elif status == AudioStatus.SPEECH_DETECTED.value:
            self._listen_control.set_status("speech")
        elif status == AudioStatus.SILENCE.value:
            self._listen_control.set_status("listening")
        elif "unavailable" in status.lower():
            self._listen_control.set_enabled(False)
            self._listen_control.set_status("error")
        elif status.startswith("Loading "):
            self._listen_control.set_enabled(False)
            self._listen_control.set_status("loading")

    def _clear_expired_caption(self, source_label: Any, translation_label: Any) -> None:
        if self._settings.caption_timeout_seconds == 0 or self._last_caption_at is None:
            return

        elapsed_seconds = self._clock() - self._last_caption_at
        if elapsed_seconds < self._settings.caption_timeout_seconds:
            return

        source_label.configure(text="")
        translation_label.configure(text="")
        self._last_caption_at = None


def main() -> None:
    SubtitleWindow(AppSettings()).run()


def _geometry_size(geometry: str) -> str:
    for index, character in enumerate(geometry):
        if index > 0 and character in {"+", "-"}:
            return geometry[:index]
    return geometry


def _geometry_origin(geometry: str) -> str:
    for index, character in enumerate(geometry):
        if index > 0 and character in {"+", "-"}:
            return geometry[index:]
    return "+0+0"


def _geometry_origin_values(geometry: str) -> tuple[int, int]:
    origin = _geometry_origin(geometry)
    values: list[int] = []
    start = 0
    for index, character in enumerate(origin):
        if index > 0 and character in {"+", "-"}:
            values.append(int(origin[start:index]))
            start = index
    values.append(int(origin[start:]))
    if len(values) < 2:
        return (0, 0)
    return (values[0], values[1])


def _geometry_position(value: int) -> str:
    if value < 0:
        return str(value)
    return f"+{value}"


if __name__ == "__main__":
    main()
