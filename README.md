# Clara Answers — Onboarding Automation Pipeline

A production-grade pipeline that converts client call transcripts into structured AI agent configurations for Clara Answers. Built as part of the Clara internship assignment.

---

## What It Does

1. Reads a **demo call** transcript → extracts preliminary business rules → writes **v1** outputs (memo, agent spec, evidence, system prompt)
2. Reads an **onboarding call** transcript → extracts confirmed rules → deep-merges with v1 → writes **v2** outputs + `changes.md`
3. Runs 6 quality gates: schema validation, anti-hallucination check, evidence alignment, idempotency guard, merge safety, strict mode
4. Generates a standalone **visual dashboard** (`outputs/diff_viewer.html`) showing the full v1→v2 diff — no server required

The pipeline is **deterministic, idempotent, and batch-capable**. Same inputs always produce the same outputs. Running it twice changes nothing.

---

## Quick Start

```bash
# 1. Clone the repo
git clone https://github.com/TechieParth2310/clara-assignment.git
cd clara-assignment

# 2. Create virtual environment and install dependencies
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 3. Run the full pipeline
python -m src.main --batch --mode rules

# 4. Open the visual dashboard
open outputs/diff_viewer.html
```

Or run the bootstrap script which does everything and verifies 11 checks:

```bash
bash scripts/bootstrap_and_verify.sh
```

Expected output:
```
✅ venv ok
✅ deps ok
✅ cli help ok
✅ batch run ok
✅ report.json exists
✅ v1 outputs ok
✅ v2 outputs ok
✅ changelog ok
✅ diff_viewer.html ok
✅ validate-only ok
✅ idempotency ok

All checks passed ✅
```

---

## Architecture

```
Demo Transcript ──────────┐
                           ├──▶ Extract ──▶ Normalize ──▶ Validate ──▶ v1 Outputs
Manifest (data/) ──────────┘

Onboarding Transcript ────┐
                           ├──▶ Extract ──▶ Normalize ──▶ Deep Merge (v1) ──▶ v2 Outputs + changes.md
v1 Outputs ────────────────┘
                                                                     ↓
                                                          diff_viewer.html (auto-generated)
```

**Pipeline A (Demo → v1):** Reads the demo call transcript, extracts a preliminary agent configuration.

**Pipeline B (Onboarding → v2):** Reads the onboarding transcript, merges confirmed values over v1, preserving any fields not mentioned in the onboarding call. Produces a versioned diff.

Full node-by-node diagram: [`workflows/ARCHITECTURE.md`](workflows/ARCHITECTURE.md)

---

## Project Structure

```
clara-assignment/
├── data/
│   ├── manifest.json                    # Account registry
│   ├── demo/
│   │   ├── bens_electric_demo.txt       # Real demo call — Ben's Electric Solutions
│   │   └── acme_001_demo.txt            # Test account
│   └── onboarding/
│       ├── bens_electric_onboarding.txt # Real onboarding call (transcribed from recording)
│       └── acme_001_onboarding.txt      # Test account
│
├── outputs/
│   ├── accounts/
│   │   └── <account_id>/
│   │       ├── v1/
│   │       │   ├── memo.json            # Structured account memo (from demo call)
│   │       │   ├── agent_spec.json      # Retell agent spec (v1)
│   │       │   ├── evidence.json        # Source quotes + confidence scores
│   │       │   └── system_prompt.txt    # Generated system prompt (v1)
│   │       ├── v2/
│   │       │   ├── memo.json            # Merged memo (from onboarding call)
│   │       │   ├── agent_spec.json      # Retell agent spec (v2, production-ready)
│   │       │   ├── evidence.json        # Updated evidence map
│   │       │   └── system_prompt.txt    # Final system prompt (v2)
│   │       └── changes.md              # Human-readable changelog (v1 → v2)
│   ├── summary/
│   │   └── report.json                 # Run summary — accounts, errors, confidence
│   └── diff_viewer.html                # Visual dashboard (open in any browser)
│
├── src/
│   ├── main.py                         # CLI entrypoint
│   ├── config.py                       # Global settings
│   ├── extract/                        # Transcript extraction logic
│   │   ├── extractor.py                # Orchestrates v1/v2 extraction
│   │   ├── rules_fallback.py           # Regex rules extraction (offline)
│   │   ├── ollama_client.py            # LLM extraction via Ollama
│   │   ├── normalize.py                # Field normalisation
│   │   ├── schema.py                   # Memo schema definition
│   │   └── prompt.py                   # Ollama prompt templates
│   ├── generate/
│   │   ├── agent_prompt.py             # System prompt generator
│   │   └── diff_viewer.py              # Dashboard HTML generator
│   ├── versioning/
│   │   ├── merge.py                    # Deep merge v1 + v2
│   │   └── changelog.py               # Changelog writer
│   └── utils/
│       ├── io.py                       # File I/O helpers
│       ├── validate.py                 # Schema + quality gate validation
│       ├── logging.py                  # Structured logger
│       └── text.py                     # Text utilities
│
├── scripts/
│   ├── bootstrap_and_verify.sh         # One-command setup + 11-check verification
│   └── run_ollama_batch.sh             # Run pipeline in Ollama LLM mode
│
├── workflows/
│   ├── ARCHITECTURE.md                 # Full pipeline architecture diagram
│   └── clara_pipeline_workflow.json    # Workflow export
│
├── requirements.txt
└── .env.example
```

---

## CLI Reference

```bash
# Run all accounts in batch (rules mode — offline, deterministic)
python -m src.main --batch --mode rules

# Run a single account
python -m src.main --account bens_electric --mode rules

# Validate outputs only (no re-run)
python -m src.main --validate-only

# Run with Ollama LLM (requires Ollama running locally with llama3.2:3b)
python -m src.main --batch --mode ollama --model llama3.2:3b
```

---

## Output Format

### `memo.json`
Structured extraction of all operational rules from the transcript:
- `company_name`, `business_hours`, `services_supported`
- `call_transfer_rules` — transfer number, max attempts, fail message
- `non_emergency_routing_rules`, `after_hours_flow_summary`
- `emergency_definition`, `emergency_routing_rules`
- `questions_or_unknowns` — fields not found in the transcript (never hallucinated)
- `version`, `source_type`, `updated_at_utc`

### `evidence.json`
Per-field source evidence:
```json
{
  "account_id": "bens_electric",
  "version": "v2",
  "fields": {
    "business_hours": {
      "confidence": "HIGH",
      "snippet": "Monday to Friday 8am to 4:30pm"
    }
  }
}
```

### `agent_spec.json`
Complete Retell-compatible agent specification including the generated system prompt and all configuration variables.

### `system_prompt.txt`
Ready-to-deploy instruction prompt for the Clara AI voice agent. Includes:
- Business hours greeting flow
- Call qualification and routing logic
- Emergency detection and transfer protocol
- After-hours policy with voicemail flow
- Transfer-fail fallback behaviour

### `changes.md`
Human-readable changelog showing every field that changed from v1 to v2, with old and new values.

### `diff_viewer.html`
Standalone visual dashboard. Open in any browser — no internet or server needed.

**Tabs per account:**
- **🔀 Changes** — side-by-side diff, red=old, green=new
- **📊 Full Comparison** — all fields with confidence badges
- **📝 Changelog** — rendered markdown diff
- **⚠ Unknowns** — fields not found in transcript
- **🔬 Confidence** — per-field heatmap for v1 and v2
- **📄 System Prompt** — full generated prompt, syntax highlighted

---

## Extraction Modes

### Rules Mode (default)
Deterministic regex-based extraction. Works fully offline. No API keys needed.

```bash
python -m src.main --batch --mode rules
```

### Ollama Mode
LLM-based extraction using a local Ollama model. Requires [Ollama](https://ollama.ai) installed and running.

```bash
ollama pull llama3.2:3b
python -m src.main --batch --mode ollama --model llama3.2:3b
```

---

## Real Client Data — Ben's Electric Solutions

This pipeline was run on real call data provided in the assignment:

| | Demo Call | Onboarding Call |
|---|---|---|
| **Source** | Fireflies recording (Jan 8 2026) | M4A recording (Jan 14 2026) — transcribed with Whisper |
| **Client** | Ben Penoyer, Ben's Electric Solutions, Calgary AB |
| **Key v1 facts** | Services, routing intent, after-hours policy |
| **Key v2 confirmations** | Hours: Mon–Fri 8am–4:30pm MT, transfer: 403-870-8494, GNM Pressure Washing emergency exception |

**Changes detected (v1 → v2):** Business hours confirmed, routing rules refined, after-hours emergency exception added for GNM Pressure Washing (Chevron and Esso properties), service call fee documented ($115 callout + $90/hr).

---

## Quality Gates

Every run passes through 6 checks before writing output:

| Gate | What it checks |
|------|---------------|
| Schema validation | All required fields present with correct types |
| Anti-hallucination | No field contains invented values — unknowns are explicit |
| Evidence alignment | Every memo field has a matching evidence entry |
| Idempotency guard | Content hash check — skips write if output unchanged |
| Merge safety | v2 never wipes a v1 field unless explicitly overridden |
| Strict mode | Optional — rejects any output with unknown fields |

---

## Adding a New Account

1. Add transcript files:
   ```
   data/demo/<account_id>_demo.txt
   data/onboarding/<account_id>_onboarding.txt
   ```

2. Register in `data/manifest.json`:
   ```json
   {
     "account_id": "new_client",
     "versions": [
       { "version": "v1", "source_type": "demo", "input_path": "data/demo/new_client_demo.txt" },
       { "version": "v2", "source_type": "onboarding", "input_path": "data/onboarding/new_client_onboarding.txt" }
     ]
   }
   ```

3. Run:
   ```bash
   python -m src.main --batch --mode rules
   ```

---

## Requirements

- Python 3.10+
- No external API keys required for rules mode
- Ollama (optional) for LLM mode

```
openai-whisper
```
(Already in requirements.txt — used for transcribing raw audio recordings)

---

## Author

Parth Kothawade — Clara Answers Internship Assignment, March 2026
