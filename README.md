# Translator

A small Linux desktop shell for live subtitles and translation.

## Setup

```bash
./scripts/setup.sh
```

## Run

```bash
uv run translator-shell
```

## Check

```bash
./scripts/test.sh
./scripts/lint.sh
./scripts/typecheck.sh
```

## Git Hooks

The setup script enables tracked hooks for this clone. The commit hook enforces
Conventional Commits. The pre-push hook runs lint, typechecking, and tests.

Valid commit examples:

```bash
feat: add live subtitle shell
fix(audio): handle empty chunks
chore!: drop unsupported Python version
```
