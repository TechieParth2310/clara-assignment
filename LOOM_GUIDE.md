# Loom Video Script + Submission Guide

> **GitHub Repo (SUBMIT THIS):** https://github.com/TechieParth2310/clara-assignment
> **Target video length:** 4–5 minutes

---

## BEFORE YOU RECORD — Setup Checklist

Do these things BEFORE clicking Record:

1. Open **Terminal** — `cd /Users/parthkothawade/clara-assignment`
2. Open **VS Code** — open the `clara-assignment` folder, file explorer visible on left
3. Open **Browser** — drag `outputs/diff_viewer.html` into Chrome and open it
4. Open **GitHub** in another browser tab — https://github.com/TechieParth2310/clara-assignment
5. Zoom terminal font: `Cmd +` three times so text is big
6. Zoom VS Code: `Cmd +` twice
7. Turn off notifications — top right menu bar → Do Not Disturb ON
8. Open Loom → choose **Screen + Cam** mode → 1080p quality
9. Do a 5-second test recording first to confirm mic and screen look good

---

## THE SCRIPT — Say This, Show This, Type This

---

### [0:00 – 0:25] INTRO

**Look at camera. Say:**
> "Hi, my name is Parth. I'm going to walk you through the Clara onboarding automation pipeline I built for this assignment.
> The problem: when a new business signs up for Clara Answers, two calls happen — a demo call first, then a formal onboarding call. Right now someone manually listens to both and configures the AI agent. This pipeline automates that completely. Let me show you."

---

### [0:25 – 1:00] SHOW THE PROJECT STRUCTURE

**Switch to VS Code. File explorer is open on the left.**

**Say:**
> "Here's the project. The `src` folder has all the pipeline code — extraction, versioning, output generation. The `data` folder has the real call transcripts. `outputs` is what gets generated on every run. `scripts` has the bootstrap script."

**While saying this, slowly click to expand in VS Code:**
- Click `src/` — show `extract/`, `generate/`, `versioning/`
- Click `data/` — show `demo/` and `onboarding/`
- Click `outputs/` — show `accounts/` and `diff_viewer.html`

**Click `data/manifest.json`. Say:**
> "This is the manifest — it tells the pipeline which transcripts belong to which client. We have Ben's Electric Solutions here — the real client from the assignment — plus a test account."

---

### [1:00 – 1:30] SHOW THE REAL TRANSCRIPTS

**Click `data/demo/bens_electric_demo.txt`. Say:**
> "Demo call transcript for Ben Penoyer — electrical contractor in Calgary. Extracted from the real Fireflies recording. This gave us the rough initial details."

**Click `data/onboarding/bens_electric_onboarding.txt`. Say:**
> "Onboarding call — transcribed from the real M4A recording using Whisper AI. This confirmed exact details: Monday to Friday 8am to 4:30pm, $115 service call fee, and a special after-hours emergency exception for GNM Pressure Washing — a property management client who manages 20 gas stations. Real facts, from the real call."

---

### [1:30 – 2:30] RUN THE PIPELINE LIVE

**Click Terminal. Type `clear` and press Enter.**

**Type exactly this and press Enter:**
```
rm -rf outputs/accounts/bens_electric && .venv/bin/python -m src.main --batch --mode rules
```

**Say while it runs:**
> "Deleting Ben's Electric outputs and running fresh. Watch the logs — loaded manifest, extracting v1 from the demo call, writing outputs, now reading the onboarding call, extracting v2, merging with v1, writing changelog, generating the dashboard. Done. Zero errors."

**Now run it again immediately. Type:**
```
.venv/bin/python -m src.main --batch --mode rules
```

**Say:**
> "I run it again without deleting. It says UNCHANGED — skipping write. It hashed the outputs, compared them, found nothing changed, skipped. This is idempotency — run it a hundred times, same result, no corruption."

---

### [2:30 – 4:00] SHOW THE DASHBOARD

**Switch to browser with `diff_viewer.html` open. Refresh the page first (Cmd+R).**

**Say:**
> "The pipeline auto-generates this visual dashboard. Single HTML file, no server needed, opens in any browser."

**Point to the stat cards at the top. Say:**
> "Two accounts processed, changes detected, zero errors, confidence breakdown. The green bar shows how many fields were extracted with HIGH confidence — found word-for-word in the transcript."

**Click on Ben's Electric section → click "🔀 Changes" tab. Say:**
> "This is the diff. Every field that changed from demo call to onboarding call. Old value red on left, confirmed value green on right. Hours went from unknown to 8am–4:30pm. After-hours policy updated to include the GNM emergency exception. Routing rules got more specific."

**Click "📊 Full Comparison" tab. Say:**
> "Full comparison — all fields side by side. Yellow rows are changes. HIGH badge means the pipeline found that value verbatim in the transcript."

**Click "⚠ Unknowns" tab. Say:**
> "This is the anti-hallucination feature. Any field the pipeline could not find is listed here as unknown — never invented. Office address, emergency routing — not in the transcript, so flagged honestly."

**Click "🔬 Confidence" tab. Say:**
> "Confidence heatmap — green is HIGH confidence, grey dash means not found. You can see exactly which fields are solid and which need a human."

**Click "📄 System Prompt" tab. Say:**
> "This is the actual system prompt generated for the Retell agent. Business hours flow, after-hours flow with the GNM exception, transfer protocol, screening rules. Auto-generated from the extracted data. Ready to paste into Retell."

---

### [4:00 – 4:30] SHOW OUTPUT FILES + GITHUB

**Switch to VS Code. Open `outputs/accounts/bens_electric/v2/agent_spec.json`. Say:**
> "Agent spec JSON — all extracted fields plus system prompt — ready for Retell API upload."

**Open `outputs/accounts/bens_electric/changes.md`. Say:**
> "Human-readable changelog with timestamps. Full audit trail of what changed and when."

**Switch to browser → GitHub tab: https://github.com/TechieParth2310/clara-assignment. Say:**
> "Full source code is here on GitHub — public repo. All the pipeline code, transcripts, and generated outputs are included. README has setup guide and architecture."

---

### [4:30 – 4:45] CLOSE

**Look at camera. Say:**
> "To summarise — this pipeline reads two real call transcripts, extracts structured data without hallucinating, versions it from demo to onboarding, generates a production-ready agent spec and system prompt, and produces a visual dashboard. One command, zero errors, fully idempotent. Thank you."

---

## SUBMIT THESE TWO THINGS

| What | Link |
|------|------|
| **GitHub Repo** | https://github.com/TechieParth2310/clara-assignment |
| **Loom Video** | *(paste your link here after recording)* |

---

## FINAL CHECKLIST

- [ ] GitHub repo is public — confirm by opening it in an incognito window
- [ ] Video is 4–5 minutes
- [ ] Showed both transcript files
- [ ] Ran pipeline live in terminal (with logs visible)
- [ ] Showed idempotency (second run said UNCHANGED)
- [ ] Showed dashboard: Changes tab, Unknowns tab, System Prompt tab
- [ ] Showed GitHub repo on camera
- [ ] Submitted both GitHub link + Loom link
