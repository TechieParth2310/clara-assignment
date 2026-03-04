# Loom Video Guide + Submission Checklist

Everything you need to record the video and submit the assignment.

---

## PART 1 — Pre-Recording Setup

### Step 1: Run a clean verification first

Open your terminal and run:

```bash
cd /Users/parthkothawade/clara-assignment
rm -rf outputs/accounts outputs/summary outputs/diff_viewer.html
bash scripts/bootstrap_and_verify.sh
```

You should see 11 lines of `✅` ending with `All checks passed ✅`.
If anything fails, do not record yet — fix it first.

### Step 2: Prepare your screen before hitting Record

Open these things in this order so you can switch between them smoothly:

| Window               | What to have open                                                        |
| -------------------- | ------------------------------------------------------------------------ |
| **Terminal**         | `cd /Users/parthkothawade/clara-assignment && source .venv/bin/activate` |
| **VS Code / Editor** | Project root open, file explorer visible on the left                     |
| **Browser tab 1**    | `outputs/diff_viewer.html` already open                                  |
| **Browser tab 2**    | (optional) GitHub repo page                                              |

Increase your terminal font to **14pt minimum** — small fonts look unreadable in videos.
In VS Code use `Cmd +` twice to zoom in.
Turn off all notifications (Slack, email, calendar).

### Step 3: Install Loom

1. Download from https://www.loom.com/download
2. Choose **"Screen + Cam"** mode when recording
3. Set video quality to 1080p
4. Do a 10-second test recording first to check your mic and screen look good

---

## PART 2 — The 5-Minute Script (Say This, Show This)

Read this section carefully before recording. The timestamps are your guide.

---

### [0:00 – 0:30] What You Built

**Say:**

> "Hi, I'm [your name]. I built an onboarding automation pipeline for Clara Answers.
> The problem it solves is this: when a new business becomes a Clara customer,
> a sales demo call happens first, then a formal onboarding call happens later.
> Right now, someone has to manually listen to both calls and configure the AI agent.
> This pipeline automates that entirely. It reads the transcripts, extracts all the
> operational rules, and generates a production-ready AI agent spec — without any
> manual work."

**Show:**

- VS Code open with the project folder
- Slowly scroll through the left panel so they can see: `src/`, `data/`, `outputs/`, `workflows/`, `scripts/`, `README.md`
- Just a 10-second scroll, no need to open anything yet

---

### [0:30 – 1:15] The Input Data

**Say:**

> "Here is the input. We have two transcripts for the same client — Acme Corp.
> First, the demo call transcript."

**Show:** Open `data/demo/acme_001_demo.txt`

- Scroll through it briefly
- Point out: the company name, business hours (9am-5pm), transfer number (0100), services (Sales + Support)

**Say:**

> "And here is the onboarding call — same client, a few weeks later."

**Show:** Open `data/onboarding/acme_001_onboarding.txt`

- Point out: hours changed to 8am-6pm, transfer number changed to 0199, Billing was added as a service

**Say:**

> "Both transcripts are registered in `manifest.json` — this is the config that tells
> the pipeline which files belong to which client."

**Show:** Open `data/manifest.json` — point to the v1/v2 entries

---

### [1:15 – 2:15] Run the Pipeline Live

**Say:**

> "Let me delete the outputs so you can watch the pipeline generate everything
> from scratch."

**In terminal, type and run:**

```bash
rm -rf outputs/accounts outputs/summary outputs/diff_viewer.html
python -m src.main --batch --mode rules
```

**While the logs appear, say:**

> "It loaded the manifest... extracted v1 from the demo call... wrote the outputs...
> extracted v2 from the onboarding call... merged it with v1... wrote the changelog...
> generated the diff viewer dashboard... and finished with zero errors.
> The whole pipeline ran in under a second."

**Now show idempotency — run it again immediately:**

```bash
python -m src.main --batch --mode rules
```

**Say:**

> "I run it again — and notice: it says UNCHANGED, skipping write.
> It computed the outputs, compared them to what's already on disk using a content hash,
> found nothing changed, and skipped the write. This is idempotency —
> you can run it a hundred times and it won't corrupt or duplicate anything."

---

### [2:15 – 3:15] Show the Outputs + Dashboard

**Say:**

> "Now let me show you what was generated. Instead of opening JSON files manually,
> the pipeline auto-generates a visual dashboard."

**Switch to browser — open `outputs/diff_viewer.html`**

**Point out the top dashboard section:**

> "At the top: 1 account processed, 7 field changes, 0 errors, 4 unresolved unknowns.
> The green bar is the confidence breakdown — most fields were extracted with HIGH
> confidence because they were found verbatim in the transcript."

**Click the "Changes" tab on the account card:**

> "This is the diff view. Every field that changed between the demo call and the
> onboarding call is shown here — old value in red, new value in green.
> Company name, business hours, services, transfer number, routing rules,
> after-hours policy — seven changes in total."

**Click "Full Comparison":**

> "This shows every field side by side for v1 and v2.
> The yellow rows are the ones that changed.
> The HIGH badges mean the pipeline found that value verbatim in the transcript —
> it didn't guess or invent anything."

**Click "Unknowns":**

> "This is important. Four fields were not found in either transcript —
> emergency definition, emergency routing, integration constraints, and office hours flow.
> Instead of hallucinating a value, the pipeline explicitly flags them as unknown.
> This is by design — safe automation means being honest about what you don't know."

**Click "Confidence" tab:**

> "This is the evidence heatmap — confidence score per field per version.
> Green means it was found directly in the transcript text.
> Grey dash means it wasn't found — that's why those fields are in the unknowns list."

---

### [3:15 – 4:00] The Agent Spec + System Prompt

**Say:**

> "The pipeline doesn't just extract data — it generates the actual AI agent
> configuration, ready to deploy on Retell."

**Click "System Prompt" tab in the dashboard:**

> "This is the v2 system prompt. It was generated automatically from the extracted data.
> It has a Business Hours Flow — greeting, ask purpose, collect name and number,
> route to the right team, transfer, and fallback if the transfer fails.
> It has an After-Hours Flow — check for emergency, collect details, attempt transfer,
> apologise if it fails.
> And a Transfer-Fail Protocol — what the agent says if it can't connect the caller."

**Say:**

> "This is ready to paste directly into Retell. The tool placeholders —
> TRANSFER_CALL, LOG_CALL_RECORD, SCHEDULE_CALLBACK —
> map directly to Retell's function calling format."

**Switch to VS Code, open `outputs/accounts/acme_001/v2/agent_spec.json`:**

> "The agent spec file contains the system prompt plus all the key variables —
> business hours, timezone, transfer number — and the tool invocation placeholders."

---

### [4:00 – 4:40] Architecture

**Say:**

> "Let me show how it works under the hood."

**Open `workflows/ARCHITECTURE.md` in VS Code:**

> "Pipeline A reads the demo call, extracts v1.
> Pipeline B reads the onboarding call, extracts v2, then merges it with v1
> using a deep merge — new values override old ones, but if a field was in v1
> and not mentioned in the onboarding call, it's preserved rather than wiped.
> Then six quality gates run: schema validation, anti-hallucination check,
> evidence alignment, idempotency guard, merge safety, and optional strict mode."

---

### [4:40 – 5:00] Close

**Say:**

> "To summarise — this pipeline takes two call transcripts for any client,
> extracts structured operational rules without hallucinating,
> versions the data from v1 to v2 with a human-readable changelog,
> generates a production-ready Retell agent spec and system prompt,
> and produces a visual dashboard showing everything.
> It runs with one command, it's idempotent, it's fully logged, and it works offline.
> The README has the full setup guide. Thank you."

**Show the README for the last 10 seconds** — just scroll through it slowly.

---

## PART 3 — GitHub Setup

Run these commands **once** to push to GitHub:

```bash
cd /Users/parthkothawade/clara-assignment

# Initialize and commit everything
git init
git add .
git commit -m "feat: complete Clara onboarding automation pipeline"

# Create a new repo at https://github.com/new first, then:
git remote add origin https://github.com/<your-username>/clara-assignment.git
git branch -M main
git push -u origin main
```

If your repo is **private**, add the hiring team as collaborators:
**GitHub.com → Your repo → Settings → Collaborators → Add people**

---

## PART 4 — Final Submission Checklist

Go through every item before you hit submit:

### Code

- [ ] `bash scripts/bootstrap_and_verify.sh` → all 11 lines show `✅`
- [ ] `python -m src.main --validate-only` → shows `2 passed, 0 failed`
- [ ] `outputs/diff_viewer.html` opens in browser, shows the dashboard correctly
- [ ] `outputs/accounts/acme_001/changes.md` has 7 changes listed
- [ ] `outputs/summary/report.json` shows `"errors": []`

### Repository

- [ ] All files are committed and pushed to GitHub
- [ ] README.md is readable and complete on the GitHub page
- [ ] `outputs/` folder is included (not in .gitignore)

### Video

- [ ] Loom video is between 3 and 5 minutes
- [ ] You showed the demo transcript AND the onboarding transcript
- [ ] You ran `python -m src.main --batch --mode rules` live on camera
- [ ] You showed the diff viewer dashboard in the browser
- [ ] You showed the system prompt
- [ ] Your face is visible (screen + cam mode)

### Submit

- [ ] Email (or form) includes the **GitHub repo link**
- [ ] Email (or form) includes the **Loom video link**
- [ ] If repo is private, confirm collaborator access was granted
