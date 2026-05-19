from pytest import MonkeyPatch

from translator.app import SubtitleWindow
from translator.audio import AudioStatus, StatusCallback
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


def test_subtitle_window_applies_basic_root_settings(monkeypatch: MonkeyPatch) -> None:
    root = FakeRoot()
    monitor = FakeAudioMonitor()
    settings = AppSettings(width=800, height=200, opacity=0.8, always_on_top=False)
    window = SubtitleWindow(settings, monitor)

    monkeypatch.setattr("translator.app.Frame", build_fake_widget)
    monkeypatch.setattr("translator.app.Label", build_fake_widget)
    monkeypatch.setattr("translator.app.Style", build_fake_style)
    monkeypatch.setattr(window, "_root_factory", lambda: root)

    window.run()

    assert root.title_value == "Live Subtitles"
    assert root.geometry_value == "800x200"
    assert ("-topmost", False) in root.attributes_values
    assert ("-alpha", 0.8) in root.attributes_values
    assert root.protocol_values[0][0] == "WM_DELETE_WINDOW"
    assert root.after_values[0][0] == 100
    assert monitor.started is True
    assert root.mainloop_called is True


def test_subtitle_window_updates_label_from_audio_status(monkeypatch: MonkeyPatch) -> None:
    root = FakeRoot()
    label = FakeWidget()
    monitor = FakeAudioMonitor()
    window = SubtitleWindow(AppSettings(), monitor)

    monkeypatch.setattr("translator.app.Frame", build_fake_widget)
    monkeypatch.setattr("translator.app.Label", build_label_factory(label))
    monkeypatch.setattr("translator.app.Style", build_fake_style)
    monkeypatch.setattr(window, "_root_factory", lambda: root)

    window.run()
    monitor.emit(AudioStatus.AUDIO_DETECTED)

    callback = root.after_values[0][1]
    assert callable(callback)
    callback()

    assert label.configured_text == "Audio detected"


def test_subtitle_window_keeps_transcript_through_passive_status(monkeypatch: MonkeyPatch) -> None:
    root = FakeRoot()
    label = FakeWidget()
    monitor = FakeAudioMonitor()
    window = SubtitleWindow(AppSettings(), monitor)

    monkeypatch.setattr("translator.app.Frame", build_fake_widget)
    monkeypatch.setattr("translator.app.Label", build_label_factory(label))
    monkeypatch.setattr("translator.app.Style", build_fake_style)
    monkeypatch.setattr(window, "_root_factory", lambda: root)

    window.run()
    monitor.emit_text("hello world")
    monitor.emit(AudioStatus.SILENCE)

    callback = root.after_values[0][1]
    assert callable(callback)
    callback()

    assert label.configured_text == "hello world"


class FakeAudioMonitor:
    def __init__(self) -> None:
        self.started = False
        self.stopped = False
        self._callback: StatusCallback | None = None

    def start(self, on_status: StatusCallback) -> None:
        self.started = True
        self._callback = on_status

    def stop(self) -> None:
        self.stopped = True

    def emit(self, status: AudioStatus) -> None:
        if self._callback is None:
            raise AssertionError("Monitor was not started")

        self._callback(status.value)

    def emit_text(self, text: str) -> None:
        if self._callback is None:
            raise AssertionError("Monitor was not started")

        self._callback(text)


class FakeStyle:
    def configure(self, *_args: object, **_kwargs: object) -> None:
        return None


class FakeWidget:
    def __init__(self) -> None:
        self.configured_text = ""

    def pack(self, *_args: object, **_kwargs: object) -> None:
        return None

    def configure(self, *, text: str) -> None:
        self.configured_text = text


def build_fake_style(*_args: object, **_kwargs: object) -> FakeStyle:
    return FakeStyle()


def build_fake_widget(*_args: object, **_kwargs: object) -> FakeWidget:
    return FakeWidget()


def build_label_factory(label: FakeWidget):
    def factory(*_args: object, **_kwargs: object) -> FakeWidget:
        return label

    return factory
