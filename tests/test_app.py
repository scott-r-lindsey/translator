from collections.abc import Callable

from pytest import MonkeyPatch

from translator.app import SubtitleWindow
from translator.audio import (
    AudioStatus,
    DisplayEvent,
    StatusCallback,
    caption_event,
    status_event,
)
from translator.config import AppSettings
from translator.transcript import TranscriptEntry


class FakeRoot:
    def __init__(self) -> None:
        self.title_value = ""
        self.geometry_value = ""
        self.attributes_values: list[tuple[str, object]] = []
        self.protocol_values: list[tuple[str, object]] = []
        self.after_values: list[tuple[int, object]] = []
        self.mainloop_called = False
        self.destroy_called = False
        self.focused = False

    def title(self, value: str) -> None:
        self.title_value = value

    def geometry(self, value: str) -> None:
        self.geometry_value = value

    def attributes(self, name: str, value: object) -> None:
        self.attributes_values.append((name, value))

    def protocol(self, name: str, callback: object) -> None:
        self.protocol_values.append((name, callback))

    def after(self, delay_ms: int, callback: object) -> None:
        self.after_values.append((delay_ms, callback))

    def mainloop(self) -> None:
        self.mainloop_called = True

    def destroy(self) -> None:
        self.destroy_called = True

    def focus_set(self) -> None:
        self.focused = True


class FakeClock:
    def __init__(self) -> None:
        self._time = 0.0

    def now(self) -> float:
        return self._time

    def advance(self, seconds: float) -> None:
        self._time += seconds


def test_subtitle_window_applies_basic_root_settings(monkeypatch: MonkeyPatch) -> None:
    root = FakeRoot()
    monitor = FakeAudioMonitor()
    widgets = FakeWidgetFactory()
    settings = AppSettings(width=900, height=420, opacity=0.8, always_on_top=False)
    window = SubtitleWindow(settings, monitor)

    patch_widgets(monkeypatch, window, root, widgets)

    window.run()

    assert root.title_value == "Live Subtitles"
    assert root.geometry_value == "900x420"
    assert ("-topmost", False) in root.attributes_values
    assert ("-alpha", 0.8) in root.attributes_values
    assert root.protocol_values[0][0] == "WM_DELETE_WINDOW"
    assert root.after_values[0][0] == 100
    assert monitor.prepared is True
    assert monitor.started is False
    assert root.mainloop_called is True
    assert widgets.source_label.initial_text == ""
    assert widgets.translation_label.initial_text == ""
    assert widgets.listen_control.enabled_values == []


def test_subtitle_window_updates_hybrid_caption(monkeypatch: MonkeyPatch) -> None:
    root = FakeRoot()
    monitor = FakeAudioMonitor()
    widgets = FakeWidgetFactory()
    window = SubtitleWindow(AppSettings(), monitor)

    patch_widgets(monkeypatch, window, root, widgets)

    window.run()
    run_first_after(root)
    monitor.emit(caption_event("hola", "hello", "es"))
    run_first_after(root)

    assert widgets.status_label.configured_text == "Ready"
    assert widgets.source_label.configured_text == "hola"
    assert widgets.translation_label.configured_text == "hello"
    assert widgets.language_selector.detected_languages == ["es"]
    assert len(widgets.transcript_view.entries) == 1
    assert widgets.transcript_view.entries[0].source_text == "hola"
    assert widgets.transcript_view.entries[0].translated_text == "hello"


def test_subtitle_window_toggles_between_live_and_transcript(monkeypatch: MonkeyPatch) -> None:
    root = FakeRoot()
    monitor = FakeAudioMonitor()
    widgets = FakeWidgetFactory()
    window = SubtitleWindow(AppSettings(), monitor)

    patch_widgets(monkeypatch, window, root, widgets)

    window.run()
    widgets.mode_toggle.select("transcript")

    assert widgets.live_frame.forgotten is True
    assert widgets.transcript_view.packed is True

    widgets.mode_toggle.select("live")

    assert widgets.transcript_view.forgotten is True
    assert widgets.live_frame.pack_calls[-1]["fill"] == "both"


def test_subtitle_window_clears_stale_caption(monkeypatch: MonkeyPatch) -> None:
    root = FakeRoot()
    monitor = FakeAudioMonitor()
    widgets = FakeWidgetFactory()
    clock = FakeClock()
    window = SubtitleWindow(AppSettings(caption_timeout_seconds=10), monitor)
    window.set_clock(clock.now)

    patch_widgets(monkeypatch, window, root, widgets)

    window.run()
    run_first_after(root)
    monitor.emit(caption_event("hola", "hello", "es"))
    run_first_after(root)

    assert widgets.source_label.configured_text == "hola"
    assert widgets.translation_label.configured_text == "hello"

    clock.advance(9.9)
    run_first_after(root)

    assert widgets.source_label.configured_text == "hola"
    assert widgets.translation_label.configured_text == "hello"

    clock.advance(0.1)
    run_first_after(root)

    assert widgets.source_label.configured_text == ""
    assert widgets.translation_label.configured_text == ""


def test_subtitle_window_keeps_caption_when_timeout_is_zero(monkeypatch: MonkeyPatch) -> None:
    root = FakeRoot()
    monitor = FakeAudioMonitor()
    widgets = FakeWidgetFactory()
    clock = FakeClock()
    window = SubtitleWindow(AppSettings(caption_timeout_seconds=0), monitor)
    window.set_clock(clock.now)

    patch_widgets(monkeypatch, window, root, widgets)

    window.run()
    run_first_after(root)
    monitor.emit(caption_event("hola", "hello", "es"))
    run_first_after(root)
    clock.advance(1_000)
    run_first_after(root)

    assert widgets.source_label.configured_text == "hola"
    assert widgets.translation_label.configured_text == "hello"


def test_listen_button_toggles_audio_capture(monkeypatch: MonkeyPatch) -> None:
    root = FakeRoot()
    monitor = FakeAudioMonitor()
    widgets = FakeWidgetFactory()
    window = SubtitleWindow(AppSettings(), monitor)

    patch_widgets(monkeypatch, window, root, widgets)

    window.run()
    widgets.listen_control.invoke()

    assert monitor.started is False

    run_first_after(root)

    assert widgets.listen_control.enabled is True

    widgets.listen_control.invoke()

    assert monitor.started is True
    assert widgets.listen_control.listening is True

    widgets.listen_control.invoke()
    run_first_after(root)

    assert monitor.stopped is True
    assert widgets.listen_control.listening is False
    assert widgets.status_label.configured_text == "Ready"
    assert widgets.listen_control.status_values[-1] == "ready"


def test_audio_status_updates_listen_control_state(monkeypatch: MonkeyPatch) -> None:
    root = FakeRoot()
    monitor = FakeAudioMonitor()
    widgets = FakeWidgetFactory()
    window = SubtitleWindow(AppSettings(), monitor)

    patch_widgets(monkeypatch, window, root, widgets)

    window.run()
    run_first_after(root)
    monitor.emit(status_event(AudioStatus.SPEECH_DETECTED.value))
    run_first_after(root)

    assert widgets.listen_control.status_values[-1] == "speech"


def test_language_selector_updates_audio_monitor(monkeypatch: MonkeyPatch) -> None:
    root = FakeRoot()
    monitor = FakeAudioMonitor()
    widgets = FakeWidgetFactory()
    window = SubtitleWindow(AppSettings(whisper_language="en"), monitor)

    patch_widgets(monkeypatch, window, root, widgets)

    window.run()
    widgets.language_selector.select("es")

    assert widgets.language_selector.initial_language == "en"
    assert monitor.source_languages == ["es"]


def test_live_view_click_clears_focus(monkeypatch: MonkeyPatch) -> None:
    root = FakeRoot()
    monitor = FakeAudioMonitor()
    widgets = FakeWidgetFactory()
    window = SubtitleWindow(AppSettings(), monitor)

    patch_widgets(monkeypatch, window, root, widgets)

    window.run()
    widgets.source_label.fire("<Button-1>")

    assert root.focused is True


class FakeAudioMonitor:
    def __init__(self) -> None:
        self.prepared = False
        self.started = False
        self.stopped = False
        self.source_languages: list[str | None] = []
        self._callback: StatusCallback | None = None

    def prepare(self, on_status: StatusCallback) -> None:
        self.prepared = True
        self._callback = on_status
        on_status(status_event(AudioStatus.READY.value))

    def start(self, on_status: StatusCallback) -> None:
        self.started = True
        self._callback = on_status
        on_status(status_event(AudioStatus.LISTENING.value))

    def stop(self) -> None:
        self.stopped = True

    def set_source_language(self, language: str | None) -> None:
        self.source_languages.append(language)

    def emit(self, event: DisplayEvent) -> None:
        if self._callback is None:
            raise AssertionError("Monitor was not prepared")

        self._callback(event)


class FakeStyle:
    def configure(self, *_args: object, **_kwargs: object) -> None:
        return None


class FakeWidget:
    def __init__(
        self,
        text: str = "",
        command: Callable[[], None] | None = None,
    ) -> None:
        self.initial_text = text
        self.configured_text = ""
        self.command = command
        self.forgotten = False
        self.pack_calls: list[dict[str, object]] = []
        self.bindings: dict[str, Callable[[object], None]] = {}

    def pack(self, *_args: object, **_kwargs: object) -> None:
        self.pack_calls.append(dict(_kwargs))
        self.forgotten = False

    def pack_forget(self) -> None:
        self.forgotten = True

    def configure(self, *, text: str) -> None:
        self.configured_text = text

    def invoke(self) -> None:
        if self.command is not None:
            self.command()

    def bind(self, sequence: str, callback: Callable[[object], None]) -> None:
        self.bindings[sequence] = callback

    def fire(self, sequence: str) -> None:
        self.bindings[sequence](object())


class FakeWidgetFactory:
    def __init__(self) -> None:
        self.labels: list[FakeWidget] = []
        self.language_selector = FakeLanguageSelector()
        self.listen_control = FakeListenControl()
        self.mode_toggle = FakeModeToggle()
        self.transcript_view = FakeTranscriptView()
        self.frames: list[FakeWidget] = []

    @property
    def status_label(self) -> FakeWidget:
        return self.labels[0]

    @property
    def source_label(self) -> FakeWidget:
        return self.labels[2]

    @property
    def translation_label(self) -> FakeWidget:
        return self.labels[4]

    def build_label(self, *_args: object, **_kwargs: object) -> FakeWidget:
        text = _kwargs.get("text", "")
        if not isinstance(text, str):
            raise AssertionError("Label text must be a string")

        widget = FakeWidget(text=text)
        self.labels.append(widget)
        return widget

    def build_listen_control(
        self,
        _parent: object,
        command: Callable[[], None],
    ) -> "FakeListenControl":
        self.listen_control = FakeListenControl(command)
        return self.listen_control

    def build_language_selector(
        self,
        _parent: object,
        initial_language: str | None,
        on_change: Callable[[str | None], None],
    ) -> "FakeLanguageSelector":
        self.language_selector = FakeLanguageSelector(initial_language, on_change)
        return self.language_selector

    def build_mode_toggle(
        self,
        _parent: object,
        on_change: Callable[[str], None],
    ) -> "FakeModeToggle":
        self.mode_toggle = FakeModeToggle(on_change)
        return self.mode_toggle

    def build_transcript_view(self, _parent: object) -> "FakeTranscriptView":
        self.transcript_view = FakeTranscriptView()
        return self.transcript_view

    def build_frame(self, *_args: object, **_kwargs: object) -> FakeWidget:
        widget = FakeWidget()
        self.frames.append(widget)
        return widget

    @property
    def live_frame(self) -> FakeWidget:
        return self.frames[3]


class ImmediateThread:
    def __init__(
        self,
        *,
        target: Callable[[], None],
        name: str,
        daemon: bool,
    ) -> None:
        self._target = target
        self.name = name
        self.daemon = daemon

    def start(self) -> None:
        self._target()


def patch_widgets(
    monkeypatch: MonkeyPatch,
    window: SubtitleWindow,
    root: FakeRoot,
    widgets: FakeWidgetFactory | None = None,
) -> FakeWidgetFactory:
    widget_factory = widgets or FakeWidgetFactory()
    monkeypatch.setattr("translator.app.Frame", widget_factory.build_frame)
    monkeypatch.setattr("translator.app.Label", widget_factory.build_label)
    monkeypatch.setattr("translator.app.ListenControl", widget_factory.build_listen_control)
    monkeypatch.setattr(
        "translator.app.SourceLanguageSelector",
        widget_factory.build_language_selector,
    )
    monkeypatch.setattr("translator.app.ModeToggle", widget_factory.build_mode_toggle)
    monkeypatch.setattr("translator.app.TranscriptView", widget_factory.build_transcript_view)
    monkeypatch.setattr("translator.app.Style", build_fake_style)
    monkeypatch.setattr("translator.app.Thread", ImmediateThread)
    monkeypatch.setattr(window, "_root_factory", lambda: root)
    return widget_factory


class FakeModeToggle:
    def __init__(self, on_change: Callable[[str], None] | None = None) -> None:
        self._on_change = on_change

    def pack(self, *_args: object, **_kwargs: object) -> None:
        return None

    def select(self, mode: str) -> None:
        if self._on_change is not None:
            self._on_change(mode)


class FakeTranscriptView:
    def __init__(self) -> None:
        self.entries: list[TranscriptEntry] = []
        self.packed = False
        self.forgotten = False
        self.pack_calls: list[dict[str, object]] = []

    def pack(self, *_args: object, **_kwargs: object) -> None:
        self.packed = True
        self.forgotten = False
        self.pack_calls.append(dict(_kwargs))

    def pack_forget(self) -> None:
        self.forgotten = True

    def append(self, entry: TranscriptEntry) -> None:
        self.entries.append(entry)


class FakeLanguageSelector:
    def __init__(
        self,
        initial_language: str | None = None,
        on_change: Callable[[str | None], None] | None = None,
    ) -> None:
        self.initial_language = initial_language
        self._on_change = on_change
        self.detected_languages: list[str | None] = []

    def pack(self, *_args: object, **_kwargs: object) -> None:
        return None

    def add_detected_language(self, code: str | None) -> None:
        self.detected_languages.append(code)

    def select(self, language: str | None) -> None:
        if self._on_change is not None:
            self._on_change(language)


class FakeListenControl:
    def __init__(self, command: Callable[[], None] | None = None) -> None:
        self.enabled = False
        self.listening = False
        self.command = command
        self.enabled_values: list[bool] = []
        self.listening_values: list[bool] = []
        self.status_values: list[str] = []

    def pack(self, *_args: object, **_kwargs: object) -> None:
        return None

    def set_enabled(self, enabled: bool) -> None:
        self.enabled = enabled
        self.enabled_values.append(enabled)

    def set_listening(self, listening: bool) -> None:
        self.listening = listening
        self.listening_values.append(listening)

    def set_status(self, status: str) -> None:
        self.status_values.append(status)

    def invoke(self) -> None:
        if self.command is not None:
            self.command()


def build_fake_style(*_args: object, **_kwargs: object) -> FakeStyle:
    return FakeStyle()


def build_fake_widget(*_args: object, **_kwargs: object) -> FakeWidget:
    return FakeWidget()


def run_first_after(root: FakeRoot) -> None:
    callback = root.after_values[0][1]
    assert callable(callback)
    callback()
