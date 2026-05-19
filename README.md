# Translator

A small Linux desktop shell for live subtitles and translation.

## Setup

```bash
./scripts/setup.sh
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
