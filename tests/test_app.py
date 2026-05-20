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


class FakeRoot:
    def __init__(self) -> None:
        self.title_value = ""
        self.geometry_value = ""
        self.attributes_values: list[tuple[str, object]] = []
        self.protocol_values: list[tuple[str, object]] = []
        self.after_values: list[tuple[int, object]] = []
        self.mainloop_called = False
        self.destroy_called = False

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

    def pack(self, *_args: object, **_kwargs: object) -> None:
        return None

    def configure(self, *, text: str) -> None:
        self.configured_text = text

    def invoke(self) -> None:
        if self.command is not None:
            self.command()


class FakeWidgetFactory:
    def __init__(self) -> None:
        self.labels: list[FakeWidget] = []
        self.language_selector = FakeLanguageSelector()
        self.listen_control = FakeListenControl()

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
    monkeypatch.setattr("translator.app.Frame", build_fake_widget)
    monkeypatch.setattr("translator.app.Label", widget_factory.build_label)
    monkeypatch.setattr("translator.app.ListenControl", widget_factory.build_listen_control)
    monkeypatch.setattr(
        "translator.app.SourceLanguageSelector",
        widget_factory.build_language_selector,
    )
    monkeypatch.setattr("translator.app.Style", build_fake_style)
    monkeypatch.setattr("translator.app.Thread", ImmediateThread)
    monkeypatch.setattr(window, "_root_factory", lambda: root)
    return widget_factory


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
