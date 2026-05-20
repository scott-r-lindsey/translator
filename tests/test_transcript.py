from translator.transcript import TranscriptEntry, format_timestamp, render_transcript_entry


def test_format_timestamp() -> None:
    assert format_timestamp(61) == "01:01"
    assert format_timestamp(3_661) == "01:01:01"


def test_render_transcript_entry_includes_timestamp_language_and_text() -> None:
    entry = TranscriptEntry(
        timestamp_seconds=61,
        source_text="hola",
        translated_text="hello",
        detected_language="es",
    )

    assert render_transcript_entry(entry) == "[01:01] Spanish (es)\nhola\nhello"

