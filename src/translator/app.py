from collections.abc import Callable
from queue import SimpleQueue
from tkinter import BOTH, Tk
from tkinter.ttk import Frame, Label, Style
from typing import Any

from translator.audio import AudioActivityMonitor, AudioStatus, PulseAudioActivityMonitor
from translator.config import AppSettings


class SubtitleWindow:
    def __init__(
        self,
        settings: AppSettings,
        audio_monitor: AudioActivityMonitor | None = None,
    ) -> None:
        self._settings = settings
        self._audio_monitor = audio_monitor or PulseAudioActivityMonitor(settings)
        self._status_queue: SimpleQueue[str] = SimpleQueue()
        self._showing_transcript = False
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

        root.protocol("WM_DELETE_WINDOW", lambda: self._close(root))
        root.after(100, lambda: self._poll_status(root, label))
        self._audio_monitor.start(self._status_queue.put)
        root.mainloop()

    def _poll_status(self, root: Any, label: Any) -> None:
        latest_status: str | None = None
        while not self._status_queue.empty():
            message = self._status_queue.get()
            latest_status = self._next_display_message(message, latest_status)

        if latest_status is not None:
            label.configure(text=latest_status)

        root.after(100, lambda: self._poll_status(root, label))

    def _next_display_message(self, message: str, current: str | None) -> str | None:
        if message in PASSIVE_STATUS_MESSAGES and self._showing_transcript:
            return current

        self._showing_transcript = message not in STATUS_MESSAGES
        return message

    def _close(self, root: Any) -> None:
        self._audio_monitor.stop()
        root.destroy()


def main() -> None:
    SubtitleWindow(AppSettings()).run()


if __name__ == "__main__":
    main()


STATUS_MESSAGES = {status.value for status in AudioStatus}
PASSIVE_STATUS_MESSAGES = {
    AudioStatus.LISTENING.value,
    AudioStatus.SILENCE.value,
    AudioStatus.AUDIO_DETECTED.value,
}
