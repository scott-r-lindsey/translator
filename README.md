# Translator

A small Linux desktop shell for live subtitles and translation.

## Setup

```bash
./scripts/setup.sh
cp .env.dist .env
```

## Run

```bash
./scripts/run.sh
```

The app uses `pactl` and `parec` to listen to the default sink monitor on
PulseAudio or PipeWire. To choose a specific source, set
`TRANSLATOR_AUDIO_SOURCE` before running:

```bash
TRANSLATOR_AUDIO_SOURCE=alsa_output.pci-0000_00_1f.3.analog-stereo.monitor ./scripts/run.sh
```

The app uses WebRTC VAD to mark speech after sustained voice activity and
returns to silence after a quiet gap. Continuous speech is split at
`TRANSLATOR_SPEECH_MAX_MS` with `TRANSLATOR_SPEECH_OVERLAP_MS` carried into the
next chunk for context.

To write completed speech chunks as WAV files for debugging, set:

```bash
TRANSLATOR_DEBUG_AUDIO_DIR=debug/audio ./scripts/run.sh
```

If segmentation is too eager or too strict, tune the VAD aggressiveness:

```bash
TRANSLATOR_VAD_AGGRESSIVENESS=3 ./scripts/run.sh
```

`0` is least aggressive and `3` is most aggressive.

Debug files include the segment end reason, for example:
`segment-0001-silence.wav` or `segment-0002-max-duration.wav`.

Completed speech chunks are transcribed with faster-whisper. The default model
is `large-v3` on CUDA with `int8_float16` compute. The first run downloads the
model.

To choose a specific NVIDIA GPU, set the CUDA device index:

```bash
TRANSLATOR_WHISPER_DEVICE_INDEX=1 ./scripts/run.sh
```

Useful transcription settings:

```bash
TRANSLATOR_WHISPER_MODEL=large-v3
TRANSLATOR_WHISPER_DEVICE=cuda
TRANSLATOR_WHISPER_DEVICE_INDEX=0
TRANSLATOR_WHISPER_COMPUTE_TYPE=int8_float16
TRANSLATOR_WHISPER_LANGUAGE=
```

Leave `TRANSLATOR_WHISPER_LANGUAGE` empty for automatic language detection.

## Check

```bash
./scripts/test.sh
./scripts/lint.sh
./scripts/typecheck.sh
```

The test script prints terminal coverage and writes an HTML report to
`htmlcov/index.html`.

## Git Hooks

The setup script enables tracked hooks for this clone. The commit hook enforces
Conventional Commits. The pre-push hook runs lint, typechecking, and tests.

Valid commit examples:

```bash
feat: add live subtitle shell
fix(audio): handle empty chunks
chore!: drop unsupported Python version
```
