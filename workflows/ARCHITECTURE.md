# Clara Pipeline — Workflow Architecture

## Pipeline A: Demo Call → Agent v1

```
┌─────────────┐    ┌──────────────┐    ┌────────────────┐    ┌─────────────┐
│  manifest    │───▶│  Read Demo   │───▶│  Extract Data  │───▶│  Normalize  │
│  .json       │    │  Transcript  │    │  (rules/LLM)   │    │  & Validate │
└─────────────┘    └──────────────┘    └────────────────┘    └──────┬──────┘
                                                                    │
                   ┌──────────────┐    ┌────────────────┐    ┌──────▼──────┐
                   │  Write v1    │◀───│  Build Agent   │◀───│  Build      │
                   │  Outputs     │    │  Spec + Prompt │    │  Evidence   │
                   └──────┬───────┘    └────────────────┘    └─────────────┘
                          │
                          ▼
              outputs/accounts/<id>/v1/
              ├── memo.json
              ├── agent_spec.json
              ├── evidence.json
              └── system_prompt.txt
```

## Pipeline B: Onboarding Call → Agent v2

```
┌─────────────┐    ┌──────────────┐    ┌────────────────┐    ┌─────────────┐
│  manifest    │───▶│  Read Onbrd  │───▶│  Extract Data  │───▶│  Normalize  │
│  .json       │    │  Transcript  │    │  (rules/LLM)   │    │  & Validate │
└─────────────┘    └──────────────┘    └────────────────┘    └──────┬──────┘
                                                                    │
   ┌──────────────────────────────────────────────────────────┐     │
   │  Load v1 memo.json (previous version)                    │─────┤
   └──────────────────────────────────────────────────────────┘     │
                                                               ┌────▼────┐
                                                               │  Deep   │
                                                               │  Merge  │
                                                               └────┬────┘
                                                                    │
                   ┌──────────────┐    ┌────────────────┐    ┌──────▼──────┐
                   │  Write v2    │◀───│  Build Agent   │◀───│  Build      │
                   │  Outputs     │    │  Spec + Prompt │    │  Evidence   │
                   └──────┬───────┘    └────────────────┘    └─────────────┘
                          │
                          ├──▶ outputs/accounts/<id>/v2/
                          │    ├── memo.json
                          │    ├── agent_spec.json
                          │    ├── evidence.json
                          │    └── system_prompt.txt
                          │
                          └──▶ outputs/accounts/<id>/changes.md
```

## Quality Gates

```
┌─────────────────────────────────────────────────────────┐
│                    QUALITY GATES                         │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  1. Schema Validation    → REQUIRED_MEMO_SCHEMA check   │
│  2. Anti-Hallucination   → strip fields not in text     │
│  3. Evidence Alignment   → memo ↔ evidence sync check   │
│  4. Idempotency Guard    → SHA-256 content hash         │
│  5. Deep Merge Safety    → null/empty protection        │
│  6. Strict Mode          → confidence ≥ 0.6 required    │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

## CLI Commands

| Command                                       | Description                          |
| --------------------------------------------- | ------------------------------------ |
| `python -m src.main --batch --mode rules`     | Full batch run (rules mode)          |
| `python -m src.main --batch --mode ollama`    | Full batch run (Ollama LLM)          |
| `python -m src.main --validate-only`          | Validate existing outputs            |
| `python -m src.main --validate-only --strict` | Strict validation (confidence ≥ 0.6) |
| `python -m src.main --account acme_001`       | Single account processing            |
| `bash scripts/bootstrap_and_verify.sh`        | One-command setup + run + verify     |
