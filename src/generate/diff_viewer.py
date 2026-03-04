"""Generate a standalone HTML dashboard + diff viewer for v1 vs v2 outputs.

Produces one self-contained HTML file with embedded JSON data.
No server needed — open outputs/diff_viewer.html directly in any browser.

Sections:
  1. Pipeline Summary Dashboard   — run stats, confidence breakdown, error log
  2. Per-Account Diff Viewer      — tabbed: Changes | Full Comparison | Changelog | Unknowns
  3. Evidence Heatmap             — confidence per field per version, colour-coded
  4. System Prompt Preview        — shows v2 prompt in a scrollable pane
"""

import json
import re
from pathlib import Path
from typing import Any

from src.utils.logging import get_logger

logger = get_logger(__name__)

# ── field display labels ─────────────────────────────────────────────────────
_FIELD_LABELS: dict[str, str] = {
    "company_name":               "Company Name",
    "business_hours":             "Business Hours",
    "office_address":             "Office Address",
    "services_supported":         "Services Supported",
    "emergency_definition":       "Emergency Definition",
    "emergency_routing_rules":    "Emergency Routing",
    "non_emergency_routing_rules":"Non-Emergency Routing",
    "call_transfer_rules":        "Call Transfer Rules",
    "integration_constraints":    "Integration Constraints",
    "after_hours_flow_summary":   "After-Hours Flow",
    "office_hours_flow_summary":  "Office Hours Flow",
}

_SKIP_FIELDS = {"account_id", "version", "source_type", "updated_at_utc", "questions_or_unknowns", "notes"}


# ── public entry point ────────────────────────────────────────────────────────

def generate_diff_viewer(output_root: Path) -> Path | None:
    """Scan output_root, collect all account data, write diff_viewer.html.

    Returns path to the generated file, or None if no accounts found.
    """
    accounts_dir = output_root / "accounts"
    if not accounts_dir.exists():
        logger.warning("No accounts dir at %s — skipping diff viewer", accounts_dir)
        return None

    accounts_data: list[dict[str, Any]] = []

    for account_dir in sorted(accounts_dir.iterdir()):
        if not account_dir.is_dir():
            continue
        entry = _load_account(account_dir)
        if entry:
            accounts_data.append(entry)

    if not accounts_data:
        logger.warning("No complete account data — skipping diff viewer")
        return None

    report = _load_json(output_root / "summary" / "report.json") or {}
    html   = _render(accounts_data, report)

    out = output_root / "diff_viewer.html"
    out.write_text(html, encoding="utf-8")
    logger.info("Diff viewer written to %s", out)
    return out


# ── data loading ──────────────────────────────────────────────────────────────

def _load_account(account_dir: Path) -> dict[str, Any] | None:
    v1_memo = _load_json(account_dir / "v1" / "memo.json")
    v2_memo = _load_json(account_dir / "v2" / "memo.json")
    if not v1_memo or not v2_memo:
        return None

    v1_ev   = _load_json(account_dir / "v1" / "evidence.json") or {}
    v2_ev   = _load_json(account_dir / "v2" / "evidence.json") or {}
    v2_prompt = _load_text(account_dir / "v2" / "system_prompt.txt") or ""
    changelog = _load_text(account_dir / "changes.md") or ""

    diff = _compute_diff(v1_memo, v2_memo)

    return {
        "account_id":    account_dir.name,
        "v1":            v1_memo,
        "v2":            v2_memo,
        "v1_conf":       _conf_map(v1_ev),
        "v2_conf":       _conf_map(v2_ev),
        "v1_snippets":   _snippet_map(v1_ev),
        "v2_snippets":   _snippet_map(v2_ev),
        "v2_prompt":     v2_prompt,
        "changelog":     changelog,
        "diff":          diff,
        "n_changes":     len(diff),
        "n_unknowns_v2": len(v2_memo.get("questions_or_unknowns") or []),
    }


def _load_json(p: Path) -> dict[str, Any] | None:
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def _load_text(p: Path) -> str | None:
    return p.read_text(encoding="utf-8") if p.exists() else None


def _conf_map(ev: dict[str, Any]) -> dict[str, float]:
    fields = ev.get("fields") or {}
    return {k: float(v.get("confidence", 0.0)) for k, v in fields.items() if isinstance(v, dict)}


def _snippet_map(ev: dict[str, Any]) -> dict[str, list[str]]:
    fields = ev.get("fields") or {}
    return {k: (v.get("snippets") or []) for k, v in fields.items() if isinstance(v, dict)}


def _compute_diff(v1: dict[str, Any], v2: dict[str, Any]) -> list[dict[str, Any]]:
    diffs = []
    for key in sorted(set(v1) | set(v2)):
        if key in _SKIP_FIELDS:
            continue
        if v1.get(key) != v2.get(key):
            diffs.append({"field": key, "old": v1.get(key), "new": v2.get(key)})
    return diffs


# ── value rendering ───────────────────────────────────────────────────────────

def _fmt(val: Any, *, html: bool = True) -> str:
    """Render any memo value as a compact HTML or plain string."""
    if val is None:
        return '<span class="v-null">null</span>' if html else "null"
    if isinstance(val, list):
        if not val:
            return '<span class="v-empty">[ ]</span>' if html else "[]"
        items = [f'<span class="tag">{_esc(str(i))}</span>' for i in val] if html else [str(i) for i in val]
        return " ".join(items) if html else ", ".join(items)
    if isinstance(val, dict):
        if not val:
            return '<span class="v-empty">{ }</span>' if html else "{}"
        rows = []
        for k, v in val.items():
            if isinstance(v, list):
                v_str = ", ".join(str(x) for x in v)
            else:
                v_str = str(v)
            rows.append(f'<span class="kv-key">{_esc(k)}</span> <span class="kv-val">{_esc(v_str)}</span>')
        return "<br>".join(rows)
    return _esc(str(val)) if html else str(val)


def _esc(s: str | None) -> str:
    if s is None:
        return ""
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def _conf_badge(c: float) -> str:
    if c >= 0.9:
        cls, lbl = "cb-high", "HIGH"
    elif c >= 0.6:
        cls, lbl = "cb-mid",  "MID"
    elif c > 0.0:
        cls, lbl = "cb-low",  "LOW"
    else:
        cls, lbl = "cb-none", "—"
    return f'<span class="cbadge {cls}" title="confidence {c:.1f}">{lbl}</span>'


def _conf_cell(c: float) -> str:
    """Coloured table cell for the confidence heatmap."""
    if c >= 0.9:
        cls, lbl = "hm-high", f"{c:.1f}"
    elif c >= 0.6:
        cls, lbl = "hm-mid",  f"{c:.1f}"
    elif c > 0.0:
        cls, lbl = "hm-low",  f"{c:.1f}"
    else:
        cls, lbl = "hm-none", "—"
    return f'<td class="hm-cell {cls}">{lbl}</td>'


# ── changelog markdown → html ─────────────────────────────────────────────────

def _changelog_html(md: str) -> str:
    lines = md.strip().splitlines()
    out   = []
    for line in lines:
        line = line.rstrip()
        if not line:
            continue
        if line.startswith("## "):
            out.append(f'<h4 class="cl-h4">{_esc(line[3:])}</h4>')
        elif line.startswith("# "):
            out.append(f'<h3 class="cl-h3">{_esc(line[2:])}</h3>')
        elif line.startswith("**"):
            out.append(f'<p class="cl-meta">{_esc(line)}</p>')
        elif re.match(r"^-\s+\*\*", line):
            # "- **Updated** `Field`: old → new"  — pretty-print it
            body = line[2:].strip()
            body = re.sub(r"\*\*(.+?)\*\*", r'<strong>\1</strong>', body)
            body = re.sub(r"`(.+?)`", r'<code>\1</code>', body)
            out.append(f'<li class="cl-item">{body}</li>')
        else:
            out.append(f'<p class="cl-plain">{_esc(line)}</p>')
    return "\n".join(out)


# ── prompt → escaped for <pre> ────────────────────────────────────────────────

def _prompt_html(prompt: str) -> str:
    # Highlight section headings (## …) and arrows
    out = _esc(prompt)
    out = re.sub(r"(##[^\n]+)", r'<span class="pr-heading">\1</span>', out)
    out = re.sub(r"(→)", r'<span class="pr-arrow">→</span>', out)
    out = re.sub(r"(\{\{[A-Z_]+\}\})", r'<span class="pr-tool">\1</span>', out)
    return out


# ── per-account HTML block ────────────────────────────────────────────────────

def _account_block(a: dict[str, Any]) -> str:
    aid       = a["account_id"]
    v1        = a["v1"]
    v2        = a["v2"]
    v1c       = a["v1_conf"]
    v2c       = a["v2_conf"]
    v1s       = a["v1_snippets"]
    v2s       = a["v2_snippets"]
    diff      = a["diff"]
    n_ch      = a["n_changes"]
    n_unk     = a["n_unknowns_v2"]
    changelog = a["changelog"]
    prompt    = a["v2_prompt"]

    # ── tab 1: changes only ──────────────────────────────────────────────────
    if diff:
        change_rows = ""
        for d in diff:
            fld   = d["field"]
            label = _FIELD_LABELS.get(fld, fld)
            old   = _fmt(d["old"])
            new   = _fmt(d["new"])
            change_rows += f"""
              <tr>
                <td class="td-field">{_esc(label)}</td>
                <td class="td-old">{old}</td>
                <td class="td-arrow">→</td>
                <td class="td-new">{new}</td>
              </tr>"""
        tab1 = f"""
          <table class="data-table">
            <thead><tr>
              <th style="width:22%">Field</th>
              <th style="width:37%">v1 · Demo Call</th>
              <th style="width:2%"></th>
              <th style="width:37%">v2 · Onboarding Call</th>
            </tr></thead>
            <tbody>{change_rows}</tbody>
          </table>"""
    else:
        tab1 = '<p class="empty-msg">No differences detected between v1 and v2.</p>'

    # ── tab 2: full comparison ───────────────────────────────────────────────
    full_rows = ""
    for fld in _FIELD_LABELS:
        label  = _FIELD_LABELS[fld]
        old_v  = v1.get(fld)
        new_v  = v2.get(fld)
        changed = (old_v != new_v)
        row_cls = "tr-changed" if changed else ""
        c1      = v1c.get(fld, 0.0)
        c2      = v2c.get(fld, 0.0)
        s1      = v1s.get(fld, [])
        s2      = v2s.get(fld, [])
        tip1    = _esc(s1[0]) if s1 else "no snippet"
        tip2    = _esc(s2[0]) if s2 else "no snippet"
        full_rows += f"""
          <tr class="{row_cls}">
            <td class="td-field">{label}</td>
            <td title="{tip1}">{_fmt(old_v)} {_conf_badge(c1)}</td>
            <td title="{tip2}">{_fmt(new_v)} {_conf_badge(c2)}</td>
          </tr>"""
    tab2 = f"""
        <p class="table-hint">🟡 Highlighted rows changed between versions. Hover a cell to see source snippet.</p>
        <table class="data-table">
          <thead><tr>
            <th style="width:22%">Field</th>
            <th>v1 · Demo Call</th>
            <th>v2 · Onboarding Call</th>
          </tr></thead>
          <tbody>{full_rows}</tbody>
        </table>"""

    # ── tab 3: changelog ────────────────────────────────────────────────────
    tab3 = f'<div class="changelog-wrap"><ul class="cl-list">{_changelog_html(changelog)}</ul></div>'

    # ── tab 4: unknowns ─────────────────────────────────────────────────────
    unk_v1 = v1.get("questions_or_unknowns") or []
    unk_v2 = v2.get("questions_or_unknowns") or []

    def _unk_li(items: list[str], cls: str) -> str:
        if not items:
            return '<li class="ok-li">✓ No unresolved fields</li>'
        return "".join(f'<li class="{cls}">⚠ {_esc(u)}</li>' for u in items)

    tab4 = f"""
        <p class="table-hint">Fields not found in the transcript are tracked explicitly — no hallucination.</p>
        <h4 class="unk-head">After onboarding (v2) — {len(unk_v2)} unresolved</h4>
        <ul class="unk-list">{_unk_li(unk_v2, "unk-li")}</ul>
        <h4 class="unk-head" style="margin-top:1.2rem">After demo (v1) — {len(unk_v1)} unresolved</h4>
        <ul class="unk-list">{_unk_li(unk_v1, "unk-li")}</ul>"""

    # ── tab 5: heatmap ───────────────────────────────────────────────────────
    hm_rows = ""
    for fld in _FIELD_LABELS:
        label = _FIELD_LABELS[fld]
        c1    = v1c.get(fld, 0.0)
        c2    = v2c.get(fld, 0.0)
        hm_rows += f"<tr><td class='td-field'>{_esc(label)}</td>{_conf_cell(c1)}{_conf_cell(c2)}</tr>"
    tab5 = f"""
        <p class="table-hint">Evidence confidence per field. <strong>HIGH ≥ 0.9</strong> · <strong>MID ≥ 0.6</strong> · <strong>LOW > 0</strong> · <strong>— not found</strong></p>
        <table class="data-table hm-table">
          <thead><tr><th>Field</th><th>v1 Confidence</th><th>v2 Confidence</th></tr></thead>
          <tbody>{hm_rows}</tbody>
        </table>"""

    # ── tab 6: system prompt preview ─────────────────────────────────────────
    tab6 = f'<pre class="prompt-pre">{_prompt_html(prompt)}</pre>' if prompt else '<p class="empty-msg">system_prompt.txt not found.</p>'

    # ── assemble account block ───────────────────────────────────────────────
    v1_name = _esc(v1.get("company_name") or aid)
    v2_name = _esc(v2.get("company_name") or aid)
    v2_hours = _esc(f"{v2.get('business_hours', {}).get('start','?')}–{v2.get('business_hours', {}).get('end','?')} {v2.get('business_hours', {}).get('timezone','')}")
    v2_transfer = _esc((v2.get("call_transfer_rules") or {}).get("transfer_number") or "—")
    v2_services = ", ".join(v2.get("services_supported") or [])

    return f"""
  <section class="account-card" id="acct-{_esc(aid)}">

    <!-- Account header -->
    <div class="acct-header">
      <div class="acct-title">
        <span class="acct-icon">🏢</span>
        <div>
          <h2 class="acct-name">{v2_name}</h2>
          <span class="acct-id">ID: {_esc(aid)}</span>
        </div>
      </div>
      <div class="acct-pills">
        <span class="pill pill-change">{n_ch} changes</span>
        <span class="pill {'pill-warn' if n_unk else 'pill-ok'}">{n_unk} unknowns</span>
        <span class="pill pill-info">v1 → v2</span>
      </div>
    </div>

    <!-- Quick-facts bar -->
    <div class="qf-bar">
      <div class="qf-item">
        <span class="qf-label">v1 Name</span>
        <span class="qf-val old">{v1_name}</span>
      </div>
      <div class="qf-item">
        <span class="qf-label">v2 Name</span>
        <span class="qf-val new">{v2_name}</span>
      </div>
      <div class="qf-item">
        <span class="qf-label">Business Hours</span>
        <span class="qf-val">{v2_hours}</span>
      </div>
      <div class="qf-item">
        <span class="qf-label">Transfer Number</span>
        <span class="qf-val">{v2_transfer}</span>
      </div>
      <div class="qf-item">
        <span class="qf-label">Services</span>
        <span class="qf-val">{_esc(v2_services)}</span>
      </div>
    </div>

    <!-- Tabs -->
    <div class="tab-bar" role="tablist">
      <button class="tab-btn active" role="tab" onclick="switchTab(this,'{aid}-t1')">🔀 Changes</button>
      <button class="tab-btn"        role="tab" onclick="switchTab(this,'{aid}-t2')">📊 Full Comparison</button>
      <button class="tab-btn"        role="tab" onclick="switchTab(this,'{aid}-t3')">📝 Changelog</button>
      <button class="tab-btn"        role="tab" onclick="switchTab(this,'{aid}-t4')">⚠ Unknowns</button>
      <button class="tab-btn"        role="tab" onclick="switchTab(this,'{aid}-t5')">🔬 Confidence</button>
      <button class="tab-btn"        role="tab" onclick="switchTab(this,'{aid}-t6')">📄 System Prompt</button>
    </div>

    <div id="{aid}-t1" class="tab-pane active">{tab1}</div>
    <div id="{aid}-t2" class="tab-pane">{tab2}</div>
    <div id="{aid}-t3" class="tab-pane">{tab3}</div>
    <div id="{aid}-t4" class="tab-pane">{tab4}</div>
    <div id="{aid}-t5" class="tab-pane">{tab5}</div>
    <div id="{aid}-t6" class="tab-pane">{tab6}</div>

  </section>"""


# ── summary dashboard ─────────────────────────────────────────────────────────

def _dashboard(accounts: list[dict[str, Any]], report: dict[str, Any]) -> str:
    total     = len(accounts)
    total_ch  = sum(a["n_changes"] for a in accounts)
    total_unk = sum(a["n_unknowns_v2"] for a in accounts)
    errors    = report.get("errors") or []
    mode      = report.get("mode") or "rules"
    model_str = f' · {report["model"]}' if report.get("model") else ""
    run_ts    = (report.get("run_finished_at_utc") or "")[:19].replace("T", " ")

    # Confidence breakdown across all accounts using v2
    conf_buckets = {"high": 0, "mid": 0, "low": 0, "none": 0}
    for a in accounts:
        for c in a["v2_conf"].values():
            if c >= 0.9:   conf_buckets["high"] += 1
            elif c >= 0.6: conf_buckets["mid"]  += 1
            elif c > 0.0:  conf_buckets["low"]  += 1
            else:          conf_buckets["none"] += 1
    total_fields = sum(conf_buckets.values()) or 1

    def pct(n: int) -> int:
        return round(n / total_fields * 100)

    bar_high = f'<div class="cbar-seg seg-high" style="width:{pct(conf_buckets["high"])}%" title="HIGH {conf_buckets["high"]} fields"></div>'
    bar_mid  = f'<div class="cbar-seg seg-mid"  style="width:{pct(conf_buckets["mid"])}%"  title="MID {conf_buckets["mid"]} fields"></div>'
    bar_low  = f'<div class="cbar-seg seg-low"  style="width:{pct(conf_buckets["low"])}%"  title="LOW {conf_buckets["low"]} fields"></div>'
    bar_none = f'<div class="cbar-seg seg-none" style="width:{pct(conf_buckets["none"])}%" title="MISSING {conf_buckets["none"]} fields"></div>'

    # Per-account status rows
    acct_rows = ""
    for a in accounts:
        aid    = a["account_id"]
        v2     = a["v2"]
        name   = v2.get("company_name") or aid
        n_ch   = a["n_changes"]
        n_unk  = a["n_unknowns_v2"]
        v1_src = a["v1"].get("source_type", "demo")
        v2_src = v2.get("source_type", "onboarding")
        ok     = report.get("per_account", {}).get(aid, {})
        v1_ok  = ok.get("v1_success", False)
        v2_ok  = ok.get("v2_success", False)
        status = "✓ OK" if (v1_ok and v2_ok) else "✗ FAIL"
        s_cls  = "st-ok" if (v1_ok and v2_ok) else "st-fail"
        acct_rows += f"""
          <tr>
            <td><a href="#acct-{_esc(aid)}" class="acct-link">{_esc(name)}</a></td>
            <td><code class="id-chip">{_esc(aid)}</code></td>
            <td>{_esc(v1_src)} → {_esc(v2_src)}</td>
            <td class="num">{n_ch}</td>
            <td class="num {'unk-num' if n_unk else ''}">{n_unk}</td>
            <td class="{s_cls}">{status}</td>
          </tr>"""

    # Error log
    if errors:
        err_html = "".join(
            f'<li class="err-li">❌ <strong>{_esc(e.get("account","?"))}/{_esc(e.get("version","?"))}</strong>: {_esc(e.get("error",""))}</li>'
            for e in errors
        )
    else:
        err_html = '<li class="ok-li-dash">✓ No errors — clean run</li>'

    return f"""
  <section class="dashboard">

    <!-- Stat cards -->
    <div class="stat-grid">
      <div class="stat-card">
        <div class="stat-num">{total}</div>
        <div class="stat-lbl">Accounts Processed</div>
      </div>
      <div class="stat-card sc-warn">
        <div class="stat-num">{total_ch}</div>
        <div class="stat-lbl">Fields Changed (v1→v2)</div>
      </div>
      <div class="stat-card {'sc-err' if errors else 'sc-ok'}">
        <div class="stat-num">{len(errors)}</div>
        <div class="stat-lbl">Pipeline Errors</div>
      </div>
      <div class="stat-card {'sc-warn' if total_unk else 'sc-ok'}">
        <div class="stat-num">{total_unk}</div>
        <div class="stat-lbl">Unresolved Unknowns</div>
      </div>
      <div class="stat-card sc-info">
        <div class="stat-num">{conf_buckets['high']}</div>
        <div class="stat-lbl">High-Confidence Fields</div>
      </div>
      <div class="stat-card sc-dim">
        <div class="stat-num">{conf_buckets['none']}</div>
        <div class="stat-lbl">Missing / Not Found</div>
      </div>
    </div>

    <!-- Confidence bar -->
    <div class="cbar-wrap">
      <div class="cbar-label">v2 Evidence Confidence</div>
      <div class="cbar">{bar_high}{bar_mid}{bar_low}{bar_none}</div>
      <div class="cbar-legend">
        <span class="cl-dot dot-high"></span>HIGH
        <span class="cl-dot dot-mid"></span>MID
        <span class="cl-dot dot-low"></span>LOW
        <span class="cl-dot dot-none"></span>MISSING
      </div>
    </div>

    <!-- Per-account table -->
    <table class="data-table dash-table">
      <thead><tr>
        <th>Account</th><th>ID</th><th>Pipeline</th>
        <th>Changes</th><th>Unknowns</th><th>Status</th>
      </tr></thead>
      <tbody>{acct_rows}</tbody>
    </table>

    <!-- Run meta + error log -->
    <div class="run-meta">
      <span>Mode: <strong>{_esc(mode)}{_esc(model_str)}</strong></span>
      <span>Completed: <strong>{_esc(run_ts)} UTC</strong></span>
    </div>
    <ul class="err-list">{err_html}</ul>

  </section>"""


# ── full page render ──────────────────────────────────────────────────────────

def _render(accounts: list[dict[str, Any]], report: dict[str, Any]) -> str:
    account_html = "\n".join(_account_block(a) for a in accounts)
    nav_links = "\n".join(
        f'<a href="#acct-{_esc(a["account_id"])}" class="nav-link">{_esc(a["v2"].get("company_name") or a["account_id"])}</a>'
        for a in accounts
    )
    dash = _dashboard(accounts, report)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Clara Pipeline — Dashboard &amp; Diff Viewer</title>
<style>
/* ── Reset & base ── */
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
html{{scroll-behavior:smooth}}
body{{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;
     background:#0d1117;color:#c9d1d9;min-height:100vh;font-size:14px;line-height:1.5}}
a{{color:#58a6ff;text-decoration:none}}
a:hover{{text-decoration:underline}}
code{{background:#161b22;padding:.1em .35em;border-radius:4px;font-size:.85em;color:#79c0ff}}

/* ── Top nav ── */
.topnav{{background:#161b22;border-bottom:1px solid #30363d;padding:.6rem 1.5rem;
         display:flex;align-items:center;gap:1.2rem;position:sticky;top:0;z-index:100;flex-wrap:wrap}}
.topnav-brand{{font-weight:700;font-size:.95rem;color:#f0f6fc;white-space:nowrap}}
.topnav-brand span{{color:#58a6ff}}
.nav-link{{font-size:.8rem;color:#8b949e;padding:.2em .5em;border-radius:4px;white-space:nowrap}}
.nav-link:hover{{background:#1f2937;color:#c9d1d9;text-decoration:none}}
.nav-spacer{{flex:1}}
.nav-hint{{font-size:.75rem;color:#484f58}}

/* ── Page wrapper ── */
.page{{max-width:1200px;margin:0 auto;padding:2rem 1.5rem}}

/* ── Page header ── */
.page-header{{text-align:center;margin-bottom:2.5rem}}
.page-header h1{{font-size:1.75rem;font-weight:700;color:#f0f6fc;margin-bottom:.35rem}}
.page-header .sub{{color:#8b949e;font-size:.85rem}}

/* ── Section titles ── */
.section-title{{font-size:1rem;font-weight:600;color:#f0f6fc;margin-bottom:1rem;
                padding-bottom:.4rem;border-bottom:1px solid #21262d}}

/* ── Dashboard ── */
.dashboard{{margin-bottom:2.5rem}}
.stat-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(145px,1fr));gap:.75rem;margin-bottom:1.2rem}}
.stat-card{{background:#161b22;border:1px solid #30363d;border-radius:10px;
            padding:1.1rem .9rem;text-align:center}}
.stat-card .stat-num{{font-size:2rem;font-weight:700;color:#58a6ff}}
.stat-card .stat-lbl{{font-size:.72rem;color:#8b949e;margin-top:.2rem;text-transform:uppercase;letter-spacing:.04em}}
.sc-ok   .stat-num{{color:#3fb950}}
.sc-warn .stat-num{{color:#d29922}}
.sc-err  .stat-num{{color:#f85149}}
.sc-info .stat-num{{color:#58a6ff}}
.sc-dim  .stat-num{{color:#484f58}}

/* ── Confidence bar ── */
.cbar-wrap{{background:#161b22;border:1px solid #30363d;border-radius:10px;
            padding:1rem 1.1rem;margin-bottom:1.2rem}}
.cbar-label{{font-size:.75rem;color:#8b949e;margin-bottom:.5rem;text-transform:uppercase;letter-spacing:.04em}}
.cbar{{display:flex;height:14px;border-radius:6px;overflow:hidden;background:#21262d}}
.cbar-seg{{transition:width .4s ease}}
.seg-high{{background:#3fb950}}
.seg-mid {{background:#d29922}}
.seg-low {{background:#db6d28}}
.seg-none{{background:#30363d}}
.cbar-legend{{display:flex;gap:1rem;margin-top:.5rem;font-size:.75rem;color:#8b949e;align-items:center}}
.cl-dot{{display:inline-block;width:10px;height:10px;border-radius:50%;margin-right:.25rem}}
.dot-high{{background:#3fb950}}.dot-mid{{background:#d29922}}
.dot-low{{background:#db6d28}}.dot-none{{background:#30363d}}

/* ── Run meta / errors ── */
.run-meta{{display:flex;gap:1.5rem;font-size:.8rem;color:#8b949e;margin:.8rem 0 .4rem;flex-wrap:wrap}}
.run-meta strong{{color:#c9d1d9}}
.err-list{{list-style:none;font-size:.82rem}}
.err-li{{color:#f85149;padding:.2rem 0}}
.ok-li-dash{{color:#3fb950;padding:.2rem 0}}

/* ── Tables ── */
.data-table{{width:100%;border-collapse:collapse;font-size:.82rem;margin-top:.3rem}}
.data-table th{{background:#161b22;color:#8b949e;font-weight:600;padding:.55rem .75rem;
               text-align:left;font-size:.72rem;text-transform:uppercase;letter-spacing:.04em;
               border-bottom:2px solid #30363d;white-space:nowrap}}
.data-table td{{padding:.55rem .75rem;border-bottom:1px solid #21262d;vertical-align:top}}
.data-table tr:last-child td{{border-bottom:none}}
.data-table tr:hover td{{background:#161b22}}
.tr-changed td{{background:#1c1a0f !important}}
.tr-changed:hover td{{background:#222010 !important}}
.td-field{{font-weight:600;color:#7ee787;width:22%;white-space:nowrap}}
.td-old{{color:#f85149}}
.td-new{{color:#3fb950}}
.td-arrow{{color:#484f58;text-align:center;width:24px;font-size:1rem}}
.num{{text-align:right;font-variant-numeric:tabular-nums}}
.unk-num{{color:#d29922}}
.st-ok{{color:#3fb950;font-weight:600}}
.st-fail{{color:#f85149;font-weight:600}}
.acct-link{{color:#58a6ff}}
.id-chip{{background:#21262d;padding:.15em .4em;border-radius:4px;font-size:.8em}}
.dash-table{{margin-top:.5rem}}

/* ── Value chips ── */
.tag{{display:inline-block;background:#1f3a2a;color:#7ee787;border:1px solid #2ea043;
      border-radius:4px;padding:.1em .45em;font-size:.78em;margin:.1em .1em 0 0}}
.v-null{{color:#484f58;font-style:italic}}
.v-empty{{color:#484f58;font-style:italic}}
.kv-key{{color:#79c0ff;font-weight:600}}
.kv-val{{color:#c9d1d9}}

/* ── Confidence badges ── */
.cbadge{{display:inline-block;font-size:.68em;font-weight:700;padding:.12em .4em;
         border-radius:3px;margin-left:.25em;vertical-align:middle}}
.cb-high{{background:#1a3b22;color:#3fb950}}
.cb-mid {{background:#3a2900;color:#d29922}}
.cb-low {{background:#3a1a0f;color:#db6d28}}
.cb-none{{background:#21262d;color:#484f58}}

/* ── Heatmap ── */
.hm-table td.hm-cell{{text-align:center;font-weight:600;font-size:.8em;border-radius:4px;width:15%}}
.hm-high{{background:#1a3b22;color:#3fb950}}
.hm-mid {{background:#3a2900;color:#d29922}}
.hm-low {{background:#3a1a0f;color:#db6d28}}
.hm-none{{background:#21262d;color:#484f58}}

/* ── Account card ── */
.account-card{{background:#161b22;border:1px solid #30363d;border-radius:12px;
               margin-bottom:2rem;overflow:hidden}}
.acct-header{{background:#0d1117;padding:1rem 1.2rem;border-bottom:1px solid #30363d;
              display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:.5rem}}
.acct-title{{display:flex;align-items:center;gap:.75rem}}
.acct-icon{{font-size:1.4rem}}
.acct-name{{font-size:1.05rem;font-weight:700;color:#f0f6fc}}
.acct-id{{font-size:.75rem;color:#484f58;margin-top:.1rem}}
.acct-pills{{display:flex;gap:.4rem;flex-wrap:wrap}}
.pill{{font-size:.72rem;font-weight:600;padding:.2em .65em;border-radius:99px;white-space:nowrap}}
.pill-change{{background:#1c2a3a;color:#58a6ff;border:1px solid #1f6feb}}
.pill-warn  {{background:#3a2500;color:#d29922;border:1px solid #6e4c00}}
.pill-ok    {{background:#1a3b22;color:#3fb950;border:1px solid #2ea043}}
.pill-info  {{background:#1c2a3a;color:#58a6ff;border:1px solid #1f6feb}}

/* ── Quick-facts bar ── */
.qf-bar{{display:flex;gap:0;border-bottom:1px solid #21262d;flex-wrap:wrap}}
.qf-item{{flex:1;min-width:140px;padding:.6rem .9rem;border-right:1px solid #21262d}}
.qf-item:last-child{{border-right:none}}
.qf-label{{font-size:.68rem;color:#484f58;text-transform:uppercase;letter-spacing:.04em}}
.qf-val{{display:block;font-size:.82rem;font-weight:600;color:#c9d1d9;margin-top:.15rem}}
.qf-val.old{{color:#f85149}}
.qf-val.new{{color:#3fb950}}

/* ── Tabs ── */
.tab-bar{{display:flex;background:#0d1117;border-bottom:1px solid #30363d;overflow-x:auto}}
.tab-btn{{background:none;border:none;border-bottom:2px solid transparent;color:#8b949e;
          cursor:pointer;font-size:.8rem;padding:.65rem .95rem;white-space:nowrap;transition:color .15s,border-color .15s}}
.tab-btn:hover{{color:#c9d1d9}}
.tab-btn.active{{color:#58a6ff;border-bottom-color:#58a6ff}}
.tab-pane{{display:none;padding:1.1rem 1.2rem}}
.tab-pane.active{{display:block}}

/* ── Misc tab content ── */
.table-hint{{font-size:.75rem;color:#484f58;margin-bottom:.65rem}}
.empty-msg{{color:#484f58;text-align:center;padding:2rem;font-size:.85rem}}

/* ── Changelog ── */
.changelog-wrap{{background:#0d1117;border:1px solid #21262d;border-radius:8px;padding:1rem 1.2rem}}
.cl-list{{list-style:none}}
.cl-item{{padding:.35rem 0;border-bottom:1px solid #21262d;font-size:.83rem;color:#c9d1d9}}
.cl-item:last-child{{border-bottom:none}}
.cl-item strong{{color:#f0f6fc}}
.cl-item code{{color:#79c0ff}}
.cl-h3{{color:#58a6ff;font-size:.9rem;margin:.6rem 0 .25rem}}
.cl-h4{{color:#8b949e;font-size:.8rem;margin:.5rem 0 .2rem;text-transform:uppercase;letter-spacing:.04em}}
.cl-meta{{color:#484f58;font-size:.75rem;margin-bottom:.3rem}}
.cl-plain{{color:#8b949e;font-size:.78rem}}

/* ── Unknowns ── */
.unk-head{{font-size:.78rem;font-weight:600;color:#8b949e;text-transform:uppercase;
           letter-spacing:.04em;margin-bottom:.4rem}}
.unk-list{{list-style:none}}
.unk-li{{color:#d29922;font-size:.82rem;padding:.25rem 0}}
.ok-li{{color:#3fb950;font-size:.82rem;padding:.25rem 0}}

/* ── System prompt ── */
.prompt-pre{{background:#0d1117;border:1px solid #21262d;border-radius:8px;
             padding:1rem;font-size:.78rem;line-height:1.6;white-space:pre-wrap;
             word-break:break-word;max-height:480px;overflow-y:auto;color:#c9d1d9;
             font-family:"SF Mono","Fira Code","Consolas",monospace}}
.pr-heading{{color:#58a6ff;font-weight:700}}
.pr-arrow{{color:#3fb950}}
.pr-tool{{color:#d2a8ff;background:#1a0a2e;padding:.05em .3em;border-radius:3px}}

/* ── Footer ── */
footer{{text-align:center;padding:2rem 0 1rem;color:#484f58;font-size:.75rem;
        border-top:1px solid #21262d;margin-top:2rem}}
</style>
</head>
<body>

<!-- Top nav -->
<nav class="topnav">
  <span class="topnav-brand">⚡ <span>Clara</span> Pipeline</span>
  {nav_links}
  <span class="nav-spacer"></span>
  <span class="nav-hint">Open in any browser · No server required</span>
</nav>

<main class="page">

  <!-- Page header -->
  <div class="page-header">
    <h1>Pipeline Dashboard &amp; Diff Viewer</h1>
    <p class="sub">Demo call extractions vs Onboarding confirmations · Auto-generated on every run</p>
  </div>

  <!-- Dashboard -->
  <h3 class="section-title">📊 Run Summary</h3>
  {dash}

  <!-- Accounts -->
  <h3 class="section-title">🔀 Account Diff Viewer</h3>
  {account_html}

</main>

<footer>
  Generated by Clara Answers Onboarding Pipeline &nbsp;·&nbsp;
  <code>outputs/diff_viewer.html</code> &nbsp;·&nbsp; No server required
</footer>

<script>
function switchTab(btn, paneId) {{
  var card = btn.closest('.account-card');
  card.querySelectorAll('.tab-btn').forEach(function(b){{b.classList.remove('active')}});
  card.querySelectorAll('.tab-pane').forEach(function(p){{p.classList.remove('active')}});
  btn.classList.add('active');
  document.getElementById(paneId).classList.add('active');
}}
</script>

</body>
</html>"""
