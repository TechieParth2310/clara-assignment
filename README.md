# Clara Answers — Onboarding Automation Pipeline# Clara Answers — Onboarding Automation Pipeline# Clara Answers — Intern Assignment

A production-grade, zero-cost, offline-capable pipeline that converts client call transcripts into structured operational configurations and deployable AI agent specifications for Clara Answers.A zero-cost, offline-capable automation pipeline that converts client call transcripts into structured operational configurations and deployable AI agent specifications for Clara Answers.A local, offline-compatible pipeline that extracts structured data from sales call transcripts and generates AI agent specifications for Clara.

------## What It Does

## What It Does## Architecture & Data Flow1. Reads **demo call** transcripts from `data/demo/` and produces **v1** outputs: a customer memo, agent spec, and evidence file.

1. Reads a **demo call** transcript → produces **v1** outputs: memo, agent spec, evidence, and system prompt.2. Reads **onboarding call** transcripts from `data/onboarding/` and produces **v2** outputs for the same account, plus a `changes.md` diff.

2. Reads an **onboarding call** transcript → produces **v2** outputs with a smart merge and `changes.md` diff.

3. Writes `outputs/summary/report.json` with run metadata and per-account status.```3. Writes a `summary/report.json` with run metadata and per-account status.

4. Generates a standalone **diff viewer** HTML page for visual v1→v2 comparison.

Demo Transcript ──┐

The pipeline is **deterministic, idempotent, and batch-capable** — same inputs always produce the same outputs.

                   ├──▶ Extract ──▶ Normalize ──▶ Validate ──▶ v1 OutputsExtraction currently runs in **rules mode** (deterministic, offline). Ollama LLM mode will be added in the next step.

---

Manifest.json ─────┘

## Architecture

---

`````

Demo Transcript ──────┐Onboarding Transcript ──┐

                       ├──▶ Extract ──▶ Normalize ──▶ Anti-Hallucination ──▶ Validate ──▶ v1 Outputs

Manifest.json ─────────┘                         ├──▶ Extract ──▶ Normalize ──▶ Deep Merge (with v1) ──▶ v2 Outputs## Project Structure



Onboarding Transcript ──┐v1 Outputs ──────────────┘ + changes.md

                         ├──▶ Extract ──▶ Normalize ──▶ Deep Merge (with v1) ──▶ Validate ──▶ v2 Outputs + changes.md

v1 Outputs ──────────────┘````

`````

clara-assignment/

**Pipeline A** (Demo → v1): Reads a demo call transcript and generates a preliminary agent configuration.

**Pipeline A** (Demo → v1): Reads a demo call transcript and generates a preliminary agent configuration — memo, agent spec, evidence map, and system prompt.├── data/

**Pipeline B** (Onboarding → v2): Reads an onboarding call transcript, merges with v1 preserving unchanged fields, produces a v2 configuration with a human-readable changelog.

│ ├── demo/ # Demo call transcripts (.txt)

See [`workflows/ARCHITECTURE.md`](workflows/ARCHITECTURE.md) for the full node-by-node flow diagram.

**Pipeline B** (Onboarding → v2): Reads an onboarding call transcript, extracts updated data, merges it with v1 preserving unchanged fields, and produces a v2 configuration with a human-readable changelog.│ └── onboarding/ # Onboarding call transcripts (.txt)

---

├── outputs/

## Project Structure

See [`workflows/ARCHITECTURE.md`](workflows/ARCHITECTURE.md) for the full node-by-node flow diagram.│ ├── accounts/

````

clara-assignment/│   │   └── <account_id>/

├── data/

│   ├── manifest.json              # Account registry — defines what to process---│   │       ├── v1/

│   ├── demo/                      # Demo call transcripts (.txt)

│   │   └── acme_001_demo.txt│   │       │   ├── memo.json

│   └── onboarding/                # Onboarding call transcripts (.txt)

│       └── acme_001_onboarding.txt## Project Structure│   │       │   ├── agent_spec.json

├── outputs/

│   ├── accounts/│   │       │   └── evidence.json

│   │   └── <account_id>/

│   │       ├── v1/```│   │       ├── v2/

│   │       │   ├── memo.json          # Structured account memo

│   │       │   ├── agent_spec.json    # Retell agent draft specclara-assignment/│   │       │   ├── memo.json

│   │       │   ├── evidence.json      # Source snippets + confidence scores

│   │       │   └── system_prompt.txt  # Generated agent conversation prompt├── data/│   │       │   ├── agent_spec.json

│   │       ├── v2/

│   │       │   ├── memo.json│   ├── manifest.json              # Account registry — defines what to process│   │       │   └── evidence.json

│   │       │   ├── agent_spec.json

│   │       │   ├── evidence.json│   ├── demo/                      # Demo call transcripts (.txt)│   │       └── changes.md

│   │       │   └── system_prompt.txt

│   │       └── changes.md             # v1 → v2 human-readable changelog│   │   └── acme_001_demo.txt│   └── summary/

│   ├── summary/

│   │   └── report.json                # Run metadata + per-account status│   └── onboarding/                # Onboarding call transcripts (.txt)│       └── report.json

│   └── diff_viewer.html               # Visual v1 vs v2 diff viewer (open in browser)

├── src/│       └── acme_001_onboarding.txt├── src/

│   ├── main.py                    # CLI entrypoint

│   ├── config.py                  # Settings + env├── outputs/│   ├── main.py        # CLI entrypoint

│   ├── extract/

│   │   ├── extractor.py           # Pipeline orchestrator│   ├── accounts/│   ├── config.py      # Settings + env

│   │   ├── rules_fallback.py      # Deterministic regex extraction

│   │   ├── ollama_client.py       # Local LLM extraction via Ollama│   │   └── <account_id>/│   ├── extract/       # Transcript parsing & schemas

│   │   ├── prompt.py              # LLM prompt builder + JSON parser

│   │   ├── normalize.py           # Post-processing, anti-hallucination, merge│   │       ├── v1/│   ├── generate/      # Agent prompt generation

│   │   └── schema.py              # Typed dataclass schemas

│   ├── generate/│   │       │   ├── memo.json          # Structured account memo│   ├── utils/         # Shared helpers

│   │   └── agent_prompt.py        # System prompt + agent spec builder

│   ├── utils/│   │       │   ├── agent_spec.json    # Retell agent draft spec│   └── versioning/    # Merge logic + changelog

│   │   ├── io.py                  # File I/O helpers

│   │   ├── validate.py            # Schema validation + evidence alignment│   │       │   ├── evidence.json      # Source snippets + confidence├── .env.example

│   │   ├── text.py                # Text utilities

│   │   └── logging.py             # Structured logging│   │       │   └── system_prompt.txt  # Generated agent prompt├── requirements.txt

│   └── versioning/

│       ├── changelog.py           # Diff generator (changes.md)│   │       ├── v2/└── README.md

│       └── merge.py               # (Reserved for future merge strategies)

├── scripts/│   │       │   ├── memo.json```

│   ├── bootstrap_and_verify.sh    # One-command: setup + run + verify

│   └── run_ollama_batch.sh        # Ollama mode helper│   │       │   ├── agent_spec.json

├── workflows/

│   ├── clara_pipeline_workflow.json   # Workflow export (n8n-equivalent)│   │       │   ├── evidence.json---

│   └── ARCHITECTURE.md                # Visual pipeline architecture diagrams

├── .env.example│   │       │   └── system_prompt.txt

├── .gitignore

├── requirements.txt│   │       └── changes.md             # v1 → v2 changelog## Quick Start

├── pyrightconfig.json

└── README.md│   └── summary/

````

│ └── report.json # Run metadata + per-account status```bash

---

├── src/bash scripts/bootstrap_and_verify.sh

## Quick Start (One Command)

│ ├── main.py # CLI entrypoint```

```bash

bash scripts/bootstrap_and_verify.sh│   ├── config.py                  # Settings + env

```

│ ├── extract/This single command creates the virtual environment, installs dependencies, runs the CLI, executes a batch run, and verifies outputs — printing a short pass/fail report.

This script creates the venv, installs dependencies, runs the full pipeline, and verifies all outputs — printing a pass/fail report for every check.

│ │ ├── extractor.py # Pipeline orchestrator

---

│ │ ├── rules_fallback.py # Deterministic regex extraction---

## Manual Setup

│ │ ├── ollama_client.py # Local LLM extraction via Ollama

````bash

# 1. Create virtual environment│   │   ├── prompt.py              # LLM prompt builder + JSON parser## Setup (manual)

python3 -m venv .venv

source .venv/bin/activate│   │   ├── normalize.py           # Post-processing, anti-hallucination, merge



# 2. Install dependencies│   │   └── schema.py              # Typed dataclass schemas```bash

pip install -r requirements.txt

│   ├── generate/python3 -m venv .venv

# 3. Copy environment config

cp .env.example .env│   │   └── agent_prompt.py        # System prompt + agent spec buildersource .venv/bin/activate



# 4. Run the pipeline│   ├── utils/pip install -r requirements.txt

python -m src.main --input data --output outputs --mode rules --batch

```│   │   ├── io.py                  # File I/O helperscp .env.example .env



---│   │   ├── validate.py            # Schema validation + evidence alignment```



## How to Add New Accounts│   │   ├── text.py                # Text utilities



1. Place the demo transcript in `data/demo/` named `<account_id>_demo.txt`│   │   └── logging.py             # Structured logging---

2. Place the onboarding transcript in `data/onboarding/` named `<account_id>_onboarding.txt`

3. Register the account in `data/manifest.json`:│   └── versioning/



```json│       ├── changelog.py           # Diff generator (changes.md)## Running the Pipeline

{

  "accounts": [│       └── merge.py               # (Reserved for future merge strategies)

    {

      "account_id": "acme_001",├── scripts/```bash

      "versions": [

        { "version": "v1", "source_type": "demo",       "input_path": "data/demo/acme_001_demo.txt" },│   ├── bootstrap_and_verify.sh    # One-command: setup + run + verifypython -m src.main --input data --output outputs --mode rules --batch

        { "version": "v2", "source_type": "onboarding", "input_path": "data/onboarding/acme_001_onboarding.txt" }

      ]│   └── run_ollama_batch.sh        # Ollama mode helper```

    }

  ]├── workflows/

}

```│   ├── clara_pipeline_workflow.json   # Workflow export (n8n-equivalent)| Flag       | Description                                                     |



4. Run: `python -m src.main --batch --mode rules`│   └── ARCHITECTURE.md                # Visual pipeline architecture| ---------- | --------------------------------------------------------------- |



---├── .env.example| `--input`  | Root folder containing `demo/` and `onboarding/` subdirectories |



## CLI Reference├── .gitignore| `--output` | Root folder where all outputs are written                       |



```bash├── requirements.txt| `--mode`   | Extraction mode — `rules` (default) or `ollama` (coming soon)   |

python -m src.main [OPTIONS]

```├── pyrightconfig.json| `--batch`  | Process all transcripts in one run                              |



| Flag | Description |└── README.md

|------|-------------|

| `--input PATH` | Root folder containing `manifest.json` (default: `data`) |```Running with empty data folders is safe — it will produce an empty summary report and exit cleanly.

| `--output PATH` | Root folder for all outputs (default: `outputs`) |

| `--mode` | Extraction mode: `rules` (default, offline) or `ollama` (local LLM) |

| `--model NAME` | Ollama model name (default: `llama3.2:3b`) |

| `--batch` | Process all accounts from manifest |------

| `--account ID` | Process a single account by ID |

| `--version VER` | Process only a specific version (e.g., `v1`) |

| `--validate-only` | Validate existing outputs without re-processing |

| `--strict` | Fail if any field has confidence < 0.6 |## Quick Start (One Command)## Output Layout



### Examples



```bash```bash| Path                                       | Description                              |

# Full batch run (rules mode, fastest, zero dependencies)

python -m src.main --batch --mode rulesbash scripts/bootstrap_and_verify.sh| ------------------------------------------ | ---------------------------------------- |



# Single account only```| `outputs/accounts/<id>/v1/memo.json`       | Extracted customer memo from demo call   |

python -m src.main --batch --account acme_001

| `outputs/accounts/<id>/v1/agent_spec.json` | Generated agent specification            |

# Validate existing outputs

python -m src.main --validate-onlyThis script:| `outputs/accounts/<id>/v1/evidence.json`   | Source snippets backing each field       |



# Strict validation1. Creates a Python virtual environment (`.venv`)| `outputs/accounts/<id>/v2/...`             | Updated versions from onboarding call    |

python -m src.main --validate-only --strict

2. Installs dependencies| `outputs/accounts/<id>/changes.md`         | Human-readable diff between v1 and v2    |

# Ollama LLM mode

python -m src.main --batch --mode ollama --model llama3.2:3b3. Runs the full pipeline on all transcripts| `outputs/summary/report.json`              | Run metadata, per-account status, errors |

````

4. Verifies outputs exist

---

---

## Output Format

---

### 1. Account Memo (`memo.json`)

## Naming Convention

Structured JSON capturing all operational rules extracted from the transcript:

## Manual Setup

| Field | Type | Description |

|-------|------|-------------|Account IDs are derived from the transcript filename if not present in the file itself.

| `company_name` | string \| null | Legal business name |

| `business_hours` | object | `{days, start, end, timezone}` |```bashExample: `acme_001_demo.txt`→`account_id = acme_001`

| `office_address` | string \| null | Physical address |

| `services_supported` | list | Services handled (e.g., Sales, Support, Billing) |# 1. Create virtual environment

| `emergency_definition` | list | What qualifies as an emergency |

| `emergency_routing_rules` | object | How emergencies are routed |python3 -m venv .venv---

| `non_emergency_routing_rules` | object | Routing for standard calls |

| `call_transfer_rules` | object | `{transfer_number, max_attempts, retry_delay_seconds, fail_message}` |source .venv/bin/activate

| `integration_constraints` | list | CRM, ticketing, or other system constraints |

| `after_hours_flow_summary` | string \| null | What happens for after-hours calls |## Next Step

| `office_hours_flow_summary` | string \| null | What happens during business hours |

| `questions_or_unknowns` | list | Fields not found — no hallucination, explicit tracking |# 2. Install dependencies

| `notes` | string \| null | Free-form notes |

| `version` | string | `"v1"` or `"v2"` |pip install -r requirements.txtOllama LLM extraction mode — pass `--mode ollama` to use a local LLM for richer field extraction.

| `source_type` | string | `"demo"` or `"onboarding"` |

| `updated_at_utc` | string | ISO 8601 UTC timestamp |

### 2. Agent Spec (`agent_spec.json`)# 3. Copy environment config---

Retell-compatible agent draft specification:cp .env.example .env

- `agent_name`, `voice_style`, `system_prompt`

- `key_variables` — all variable references used in the prompt (timezone, hours, transfer numbers)## Ollama Mode

- `tool_invocation_placeholders` — `{{TRANSFER_CALL}}`, `{{SEND_SMS_CONFIRMATION}}`, `{{LOG_CALL_RECORD}}`, `{{SCHEDULE_CALLBACK}}`, `{{RECORD_MESSAGE}}`

- `call_transfer_protocol`, `transfer_fail_protocol`# 4. Run the pipeline

### 3. System Prompt (`system_prompt.txt`)python -m src.main --input data --output outputs --mode rules --batchUses a locally-running LLM via [Ollama](https://ollama.com) — **zero cost, fully offline**.

Complete, production-ready conversation prompt with:```

- **Business Hours Flow**:### Prerequisites
  1. Warm greeting by company name

  2. Ask purpose of call---

  3. Collect caller's full name

  4. Collect callback number1. Install Ollama: https://ollama.com/download

  5. Route or transfer based on purpose

  6. Transfer-fail fallback (take message, confirm callback)## How to Plug In Dataset Files2. Pull the model:

  7. "Is there anything else I can help you with?"

  8. Polite close ```bash

- **After-Hours Flow**:1. Place demo transcripts in `data/demo/` with naming: `<account_id>_demo.txt` ollama pull llama3.2:3b
  1. Greeting + state closed hours

  2. Confirm whether situation is an emergency2. Place onboarding transcripts in `data/onboarding/` with naming: `<account_id>_onboarding.txt` ```

  3. If emergency: collect name, number, address → attempt transfer → if fail: apologize + assure follow-up

  4. If non-emergency: collect details → confirm callback during next business hours3. Register accounts in `data/manifest.json`:3. Start the server:

  5. "Is there anything else I can help you with?"

  6. Close ```bash

- **Call Transfer Protocol**: Hold message → transfer attempt → retry logic → fail protocol```json ollama serve

- **Transfer-Fail Protocol**: Apologise → collect details → confirm follow-up

{ ```

### 4. Evidence Map (`evidence.json`)

"accounts": [

Per-field audit trail showing exactly what was found where:

    {### Run

| Confidence | Meaning |

|------------|---------| "account_id": "acme_001",

| `0.9` | Value found verbatim in transcript |

| `0.6` | Value inferred from partial word matches | "versions": [```bash

| `0.3` | Value inferred from structure (no direct text match) |

| `0.0` | Value not found — reported in `questions_or_unknowns` | { "version": "v1", "source_type": "demo", "input_path": "data/demo/acme_001_demo.txt" },python -m src.main --input data --output outputs --mode ollama --model llama3.2:3b --batch

### 5. Changelog (`changes.md`) { "version": "v2", "source_type": "onboarding", "input_path": "data/onboarding/acme_001_onboarding.txt" }```

Human-readable diff showing field-by-field changes from v1 → v2. ]

### 6. Summary Report (`report.json`) }Or use the helper script (checks Ollama is up, activates venv, runs batch):

Run metadata: timestamps, mode, model, per-account `v1_success`/`v2_success`, error list. ]

### 7. Diff Viewer (`outputs/diff_viewer.html`)}```bash

Open `outputs/diff_viewer.html` in any browser — no server required. Shows:```bash scripts/run_ollama_batch.sh

- Side-by-side v1 vs v2 memo comparison

- Colour-coded changed fields (yellow highlight)# optionally pass a different model:

- Evidence confidence scores per field

- Changelog summary4. Run: `python -m src.main --input data --output outputs --mode rules --batch`bash scripts/run_ollama_batch.sh llama3.1:8b

---```

## Versioning & Diff (v1 → v2)---

The pipeline strictly separates demo-derived assumptions from onboarding-confirmed rules:### Evidence tracking

- **v1** (demo): Preliminary configuration based on a sales demo call — may have gaps## CLI Reference

- **v2** (onboarding): Updated operational configuration based on the formal onboarding call

In `v2/evidence.json`, fields that were explicitly mentioned in the onboarding transcript carry fresh snippets and a confidence score from the LLM. Fields that were unchanged from v1 carry forward their original v1 snippets; fields not tracked in either version have empty snippets.

When v2 is generated:

1. New non-empty values override old values (e.g., updated business hours, new transfer number)```bash

2. Fields not mentioned in onboarding are **preserved from v1** (e.g., office address)python -m src.main [OPTIONS]

3. Fields absent from both versions are set to `null` / `[]` / `{}` — no hallucination```

4. `changes.md` documents every changed field with old → new values

5. `questions_or_unknowns` lists all fields still unresolved after both calls| Flag | Description |

|------|-------------|

---| `--input` | Root folder containing `manifest.json` (default: `data`) |

| `--output` | Root output folder (default: `outputs`) |

## Extraction Modes| `--mode` | Extraction mode: `rules` (default) or `ollama` |

| `--model` | Ollama model name (default: `llama3.2:3b`) |

### Rules Mode (Default — Zero Cost, Fully Offline)| `--batch` | Process all accounts from manifest |

| `--account ID` | Process only a specific account |

Deterministic regex extraction against structured transcript headers. Works reliably on formatted transcripts.| `--version VER` | Process only a specific version (e.g., `v1`) |

| `--validate-only` | Validate existing outputs without re-processing |

**Use this for**: Reproducibility, CI/CD, deterministic outputs.| `--strict` | Fail if any evidence field has confidence < 0.6 |

### Ollama Mode (Zero Cost — Local LLM)### Examples

Uses a locally-running LLM via [Ollama](https://ollama.com) for natural-language understanding.```bash

# Full batch run

```bashpython -m src.main --batch --mode rules

# Install and start Ollama (one-time setup)

ollama pull llama3.2:3b# Single account

ollama servepython -m src.main --batch --account acme_001



# Run# Validate existing outputs

python -m src.main --batch --mode ollama --model llama3.2:3bpython -m src.main --validate-only



# Or use the helper script# Strict validation

bash scripts/run_ollama_batch.shpython -m src.main --validate-only --strict

```

# Ollama LLM mode

**Use this for**: Unstructured transcripts, richer extraction of nuanced details.python -m src.main --batch --mode ollama --model llama3.2:3b

````

Anti-hallucination protection runs in both modes: any extracted value that cannot be traced back to the transcript is stripped and logged as an unknown.

---

---

## Output Format

## Quality Gates

### 1. Account Memo (`memo.json`)

| Gate | Implementation | Failure Behaviour |

|------|---------------|-------------------|Structured JSON with fields:

| Schema Validation | `validate_memo_schema()` — checks keys, types, nested structures | Hard fail — logs error, skips write |- `account_id`, `company_name`, `business_hours`, `office_address`

| Anti-Hallucination | `strip_unsupported_fields()` — verifies list items exist in transcript | Strips value, logs WARNING, adds to unknowns |- `services_supported`, `emergency_definition`, `emergency_routing_rules`

| Evidence Alignment | `validate_evidence_alignment()` — memo ↔ evidence field parity | Hard fail |- `non_emergency_routing_rules`, `call_transfer_rules`

| Idempotency | SHA-256 content hash before write | Skips write with INFO log |- `integration_constraints`, `after_hours_flow_summary`, `office_hours_flow_summary`

| Deep Merge Safety | `deep_merge_strict()` — null/empty never overwrites non-null | Silent protection |- `questions_or_unknowns`, `notes`, `version`, `source_type`, `updated_at_utc`

| Strict Mode | `--strict` — rejects confidence < 0.6 | Hard fail if enabled |

### 2. Agent Spec (`agent_spec.json`)

---

Retell-compatible agent draft specification:

## Retell Setup- `agent_name`, `voice_style`, `system_prompt`

- `key_variables` (timezone, business hours, transfer numbers)

The pipeline outputs **Retell-compatible** agent specifications in `agent_spec.json`.- `tool_invocation_placeholders` (e.g., `{{TRANSFER_CALL}}`, `{{LOG_CALL_RECORD}}`)

- `call_transfer_protocol`, `transfer_fail_protocol`

1. Open [https://retell.ai](https://retell.ai) and create a new agent- `version`, `source_type`

2. Copy the contents of `outputs/accounts/<id>/v2/system_prompt.txt` into the agent's system prompt field

3. Set `key_variables` values from `agent_spec.json` in the agent settings panel### 3. System Prompt (`system_prompt.txt`)

4. Use `tool_invocation_placeholders` to wire up function calls (`{{TRANSFER_CALL}}`, etc.)

Complete conversation prompt including:

---- **Business Hours Flow**: Greeting → Ask purpose → Collect name/number → Route/Transfer → Fallback → "Anything else?" → Close

- **After-Hours Flow**: Greeting → Purpose → Emergency check → If emergency: collect info + transfer → If non-emergency: take message + confirm callback → "Anything else?" → Close

## Workflow Export- **Call Transfer Protocol**: Hold message → Transfer attempt → Retry logic → Fail protocol

- **Transfer-Fail Protocol**: Apologize → Collect details → Confirm follow-up

`/workflows` contains:- **General Guidelines**: Collect info first, never disclose internals, stay empathetic



- **`clara_pipeline_workflow.json`** — 12-node structured workflow export (n8n-equivalent), documenting every pipeline step, data flow, error handling, and idempotency logic### 4. Evidence Map (`evidence.json`)

- **`ARCHITECTURE.md`** — Visual ASCII pipeline diagrams for Pipeline A and Pipeline B

Per-field audit trail:

The pipeline is implemented as a Python CLI (not n8n nodes) because it requires zero infrastructure — no Docker, no n8n server. Every node in the workflow JSON maps 1:1 to a Python function. Converting to n8n requires creating Function nodes per step and replacing the manifest trigger with an n8n webhook.- `value`: The extracted value (mirrors memo.json)

- `snippets`: Source text fragments from the transcript

---- `confidence`: 0.9 (found verbatim), 0.6 (inferred), 0.3 (carried from previous version), 0.0 (not found)



## Known Limitations### 5. Changelog (`changes.md`)



1. **Transcript format dependency**: Rules mode expects structured key-value headers. Fully unstructured conversation needs Ollama mode.Human-readable diff showing what changed from v1 → v2, field by field.

2. **Sequential processing**: Accounts are processed one at a time. For 50+ accounts, parallel processing would be needed.

3. **No task tracker integration**: `report.json` serves as the tracking artifact. Production would integrate with Asana/Linear.### 6. Summary Report (`report.json`)

4. **No Retell API integration**: Pipeline produces a ready-to-paste spec. Programmatic creation via Retell API was not available on the free tier.

5. **No audio transcription**: Pipeline accepts text transcripts. Audio → transcript requires an upstream Whisper step.Run metadata: timestamps, extraction mode, per-account success/failure, errors.



------



## Production Improvements## Versioning & Diff (v1 → v2)



1. **Retell API integration** — auto-create/update agents via Retell APIThe pipeline strictly separates:

2. **n8n deployment** — run as proper workflow nodes with webhook triggers- **v1** (demo-derived): Preliminary assumptions based on demo call — may have incomplete data

3. **Database backend** — replace local JSON with Supabase/PostgreSQL- **v2** (onboarding-confirmed): Updated operational configuration based on onboarding call

4. **Task tracker sync** — auto-create Asana/Linear items per account

5. **Whisper transcription** — add automatic audio→transcript step (offline, via OpenAI Whisper)When v2 is generated:

6. **Parallel processing** — concurrent account processing for large batches1. New fields override old values (e.g., updated business hours, new transfer number)

7. **CI/CD pipeline** — run bootstrap_and_verify.sh on every push2. Fields not mentioned in onboarding are **preserved** from v1 (e.g., office address)

8. **Comprehensive test suite** — pytest regression tests for edge cases3. Fields not found in either version are set to `null` / `[]` / `{}`

9. **Confidence ML model** — replace rule-based confidence with learned heuristics4. `changes.md` documents every change with old → new values

10. **Webhook triggers** — auto-process new transcripts on file upload5. `questions_or_unknowns` lists fields that remain unresolved



------



## Ethics & Data Handling## Extraction Modes



- No customer personal data beyond what is in the provided dataset### Rules Mode (Default — Zero Cost)

- No raw recordings included in the repository

- Transcripts treated as confidential input — not published publiclyDeterministic regex-based extraction. Parses structured transcript headers like:

- No paid APIs or subscriptions used — fully open-source, zero-cost```

- Fully reproducible with Python 3.10+ and standard libraries onlyCompany Name: Acme Corp

Business Hours: Monday to Friday 9am to 5pm
Transfer Number: +1-800-555-0100
````

**Advantages**: Fully offline, deterministic, zero-cost, reproducible.

### Ollama Mode (Zero Cost — Local LLM)

Uses a locally-running LLM via [Ollama](https://ollama.com) for richer extraction from unstructured conversation.

```bash
# Prerequisites
ollama pull llama3.2:3b
ollama serve

# Run
python -m src.main --batch --mode ollama --model llama3.2:3b
```

Or use the helper script:

```bash
bash scripts/run_ollama_batch.sh
```

**Advantages**: Handles unstructured conversation, extracts nuanced details.
**Trade-off**: Requires Ollama installed locally (free, open-source).

---

## Retell Setup

This pipeline outputs agent configurations compatible with [Retell AI](https://retell.ai).

### If Retell Free Tier Is Available

1. Create a Retell account at https://retell.ai
2. Navigate to Agent creation
3. Copy the contents of `system_prompt.txt` into the agent's system prompt field
4. Configure `key_variables` from `agent_spec.json` in the agent settings

### If Retell API Is Not Accessible on Free Tier

The pipeline produces a complete **Agent Draft Spec** (`agent_spec.json`) that contains:

- The full system prompt ready to paste into any Retell agent UI
- All configuration variables (business hours, transfer numbers, timezone)
- Tool invocation placeholders matching Retell's function calling format
- Call transfer and fallback protocols

This spec serves as the authoritative configuration document — ready to import when API access is available.

---

## Workflow Export (n8n Equivalent)

The `/workflows` directory contains:

- **`clara_pipeline_workflow.json`** — Structured workflow export documenting the 12-node pipeline, equivalent to an n8n workflow JSON export
- **`ARCHITECTURE.md`** — Visual pipeline architecture with ASCII flow diagrams

The pipeline is implemented as a Python CLI rather than n8n nodes because:

1. **Zero-cost**: No Docker or n8n server infrastructure required
2. **Single-command**: `python -m src.main --batch` runs the full workflow
3. **Deterministic**: Same inputs always produce same outputs
4. **Portable**: Works on any machine with Python 3.10+

Each node in `clara_pipeline_workflow.json` maps directly to a Python function. Converting to n8n requires: (1) setting up n8n locally via Docker, (2) creating Function nodes for each pipeline step, (3) replacing the manifest trigger with an n8n webhook trigger.

---

## Quality Gates

| Gate                   | Description                                                                                             |
| ---------------------- | ------------------------------------------------------------------------------------------------------- |
| **Schema Validation**  | Every memo is validated against `REQUIRED_MEMO_SCHEMA` — checks required keys, types, nested structures |
| **Anti-Hallucination** | `strip_unsupported_fields()` verifies list items exist in transcript text before accepting them         |
| **Evidence Alignment** | `validate_evidence_alignment()` ensures memo ↔ evidence field parity                                    |
| **Idempotency**        | SHA-256 content hash comparison prevents redundant writes on re-run                                     |
| **Deep Merge Safety**  | New null/empty values never overwrite existing non-null data from previous versions                     |
| **Strict Mode**        | Optional `--strict` flag rejects fields with confidence < 0.6                                           |

---

## Known Limitations

1. **Transcript format dependency**: Rules mode expects structured key-value headers in transcripts. Unstructured conversational text requires Ollama mode.
2. **Single-threaded processing**: Accounts are processed sequentially. For large batches (50+ accounts), parallel processing would improve throughput.
3. **No task tracker integration**: The assignment suggests Asana/alternative integration. The `report.json` summary serves as the tracking artifact.
4. **No UI/dashboard**: Outputs are JSON files reviewed manually or via scripts.
5. **Ollama mode sensitivity**: LLM extraction quality varies by model. The anti-hallucination layer strips artifacts, but occasional edge cases may slip through on very small models.
6. **No audio transcription**: Pipeline accepts text transcripts. For audio-only input, a local Whisper step would need to be added upstream.

---

## What I Would Improve With Production Access

1. **Retell API Integration**: Programmatically create/update agents via Retell API
2. **n8n Orchestration**: Deploy as proper n8n workflow nodes with webhook triggers
3. **Database Storage**: Replace local JSON with Supabase/PostgreSQL for querying and multi-user access
4. **Task Tracker**: Auto-create Asana/Linear items for each new account onboarding
5. **Whisper Transcription**: Add automatic audio → transcript step (local, free, via OpenAI Whisper)
6. **Parallel Processing**: Process multiple accounts concurrently
7. **Diff Viewer UI**: Web-based side-by-side v1 vs v2 comparison with highlighted changes
8. **Webhook Triggers**: Auto-process new transcripts on file upload
9. **Comprehensive Test Suite**: pytest-based regression testing for edge cases
10. **Confidence ML Model**: Replace rule-based confidence scoring with learned heuristics

---

## Ethics & Data Handling

- ✅ No customer personal data beyond what is in the provided dataset
- ✅ No raw recordings included in the repository
- ✅ Transcripts are treated as confidential input files
- ✅ No paid APIs, credits, or subscriptions used — zero-cost constraint met
- ✅ Fully reproducible with open-source tools only

```

```
