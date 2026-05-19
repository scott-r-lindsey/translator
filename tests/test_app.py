from pytest import MonkeyPatch

from translator.app import SubtitleWindow
from translator.config import AppSettings


class FakeRoot:
    def __init__(self) -> None:
        self.title_value = ""
        self.geometry_value = ""
        self.attributes_values: list[tuple[str, object]] = []
        self.mainloop_called = False

    def title(self, value: str) -> None:
        self.title_value = value

    def geometry(self, value: str) -> None:
        self.geometry_value = value

    def attributes(self, name: str, value: object) -> None:
        self.attributes_values.append((name, value))

    def mainloop(self) -> None:
        self.mainloop_called = True


def test_subtitle_window_applies_basic_root_settings(monkeypatch: MonkeyPatch) -> None:
    root = FakeRoot()
    settings = AppSettings(width=800, height=200, opacity=0.8, always_on_top=False)
    window = SubtitleWindow(settings)

    monkeypatch.setattr("translator.app.Frame", build_fake_widget)
    monkeypatch.setattr("translator.app.Label", build_fake_widget)
    monkeypatch.setattr("translator.app.Style", build_fake_style)
    monkeypatch.setattr(window, "_root_factory", lambda: root)

    window.run()

    assert root.title_value == "Live Subtitles"
    assert root.geometry_value == "800x200"
    assert ("-topmost", False) in root.attributes_values
    assert ("-alpha", 0.8) in root.attributes_values
    assert root.mainloop_called is True


class FakeStyle:
    def configure(self, *_args: object, **_kwargs: object) -> None:
        return None


class FakeWidget:
    def pack(self, *_args: object, **_kwargs: object) -> None:
        return None


def build_fake_style(*_args: object, **_kwargs: object) -> FakeStyle:
    return FakeStyle()


def build_fake_widget(*_args: object, **_kwargs: object) -> FakeWidget:
    return FakeWidget()
