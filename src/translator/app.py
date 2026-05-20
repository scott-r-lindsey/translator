from collections.abc import Callable
from queue import SimpleQueue
from threading import Thread
from tkinter import BOTH, LEFT, RIGHT, Tk, X
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
from translator.ui.listen_control import ListenControl


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
        self._listen_control: ListenControl | None = None
        self._root_factory: Callable[[], Any] = Tk

    def run(self) -> None:
        root = self._root_factory()
        root.title(self._settings.window_title)
        root.geometry(f"{self._settings.width}x{self._settings.height}")
        root.attributes("-topmost", self._settings.always_on_top)
        root.attributes("-alpha", self._settings.opacity)

        style = Style(root)
        style.configure("Shell.TFrame", background="#111111")
        style.configure("Header.TFrame", background="#1c1c1c")
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

        status_label = Label(
            header,
            text="Loading models...",
            anchor="e",
            justify="right",
            style="Status.TLabel",
        )
        status_label.pack(side=RIGHT, fill=X, expand=True)

        Label(frame, text="Original", anchor="w", style="Section.TLabel").pack(fill=X)
        source_label = Label(
            frame,
            text="",
            anchor="nw",
            justify="left",
            style="Source.TLabel",
            wraplength=max(self._settings.width - 36, 1),
        )
        source_label.pack(fill=BOTH, expand=True)

        Label(frame, text="Translation", anchor="w", style="Section.TLabel").pack(fill=X)
        translation_label = Label(
            frame,
            text="",
            anchor="nw",
            justify="left",
            style="Translation.TLabel",
            wraplength=max(self._settings.width - 36, 1),
        )
        translation_label.pack(fill=BOTH, expand=True)

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

def main() -> None:
    SubtitleWindow(AppSettings()).run()


if __name__ == "__main__":
    main()
