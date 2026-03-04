"""CLI entrypoint: python -m src.main"""

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.config import config
from src.utils.logging import get_logger
from src.utils.io import write_json, read_json, ensure_dir
from src.extract.extractor import process_transcript

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Manifest loader
# ---------------------------------------------------------------------------

def load_manifest(manifest_path: Path) -> dict[str, Any]:
    """Load and validate manifest.json.

    Returns the parsed manifest dict.
    Raises ValueError if schema is invalid.
    """
    if not manifest_path.exists():
        raise FileNotFoundError(f"Manifest not found: {manifest_path}")

    data = read_json(manifest_path)

    if not isinstance(data, dict) or "accounts" not in data:
        raise ValueError("Manifest must have a top-level 'accounts' array")

    accounts = data["accounts"]
    if not isinstance(accounts, list):
        raise ValueError("manifest.accounts must be a list")

    for i, acct in enumerate(accounts):
        if not isinstance(acct, dict):
            raise ValueError(f"manifest.accounts[{i}] must be an object")
        if "account_id" not in acct:
            raise ValueError(f"manifest.accounts[{i}] missing 'account_id'")
        if "versions" not in acct or not isinstance(acct["versions"], list):
            raise ValueError(f"manifest.accounts[{i}] missing or invalid 'versions'")
        for j, ver in enumerate(acct["versions"]):
            for key in ("version", "source_type", "input_path"):
                if key not in ver:
                    raise ValueError(
                        f"manifest.accounts[{i}].versions[{j}] missing '{key}'"
                    )

    return data


# ---------------------------------------------------------------------------
# CLI parser
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser with all flags."""
    parser = argparse.ArgumentParser(
        prog="python -m src.main",
        description="Clara Answers pipeline — transcript → memo + agent spec",
    )
    parser.add_argument("--input", default="data", help="Root folder containing manifest.json")
    parser.add_argument("--output", default="outputs", help="Root output folder")
    parser.add_argument(
        "--mode",
        choices=["rules", "ollama"],
        default="rules",
        help="Extraction mode — rules (default) or ollama (requires local Ollama server)",
    )
    parser.add_argument(
        "--model",
        default="llama3.2:3b",
        help="Ollama model name (only used with --mode ollama)",
    )
    parser.add_argument("--batch", action="store_true", help="Process all accounts from manifest")

    # Phase 8 — CLI enhancements
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Run validation on existing outputs without processing",
    )
    parser.add_argument(
        "--account",
        type=str,
        default=None,
        help="Process a single account by ID",
    )
    parser.add_argument(
        "--version",
        type=str,
        default=None,
        help="Process a specific version only (e.g. v1, v2)",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Fail on low-confidence fields (confidence < 0.6)",
    )
    return parser


# ---------------------------------------------------------------------------
# Validate-only mode
# ---------------------------------------------------------------------------

def run_validate_only(output_root: Path, strict: bool = False) -> None:
    """Run validation on existing outputs without re-processing.

    Checks every memo.json and evidence.json found in outputs.
    """
    from src.utils.validate import validate_memo_schema, validate_evidence, validate_evidence_alignment

    accounts_dir = output_root / "accounts"
    if not accounts_dir.exists():
        logger.error("No outputs directory found at %s", accounts_dir)
        return

    total_ok = 0
    total_fail = 0

    for account_dir in sorted(accounts_dir.iterdir()):
        if not account_dir.is_dir():
            continue
        for version_dir in sorted(account_dir.iterdir()):
            if not version_dir.is_dir():
                continue

            memo_path = version_dir / "memo.json"
            evidence_path = version_dir / "evidence.json"

            if not memo_path.exists():
                continue

            label = f"{account_dir.name}/{version_dir.name}"
            try:
                memo = read_json(memo_path)
                validate_memo_schema(memo)

                if evidence_path.exists():
                    evidence = read_json(evidence_path)
                    validate_evidence(evidence)
                    validate_evidence_alignment(memo, evidence)

                    # Strict mode: fail on low-confidence fields
                    if strict:
                        _check_strict_confidence(evidence, label)

                logger.info("✓ VALID: %s", label)
                total_ok += 1
            except Exception as exc:
                logger.error("✗ INVALID: %s — %s", label, exc)
                total_fail += 1

    logger.info("Validation complete: %d passed, %d failed", total_ok, total_fail)
    if total_fail > 0:
        sys.exit(1)


def _check_strict_confidence(evidence: dict[str, Any], label: str) -> None:
    """In strict mode, fail if any evidence field has confidence < 0.6."""
    fields = evidence.get("fields", {})
    low_confidence: list[str] = []
    for field_name, entry in fields.items():
        conf = entry.get("confidence", 0.0)
        if conf < 0.6:
            low_confidence.append(f"{field_name} (confidence={conf})")
    if low_confidence:
        raise ValueError(
            f"Strict mode: low-confidence fields in {label}: {', '.join(low_confidence)}"
        )


# ---------------------------------------------------------------------------
# Manifest-driven batch processing
# ---------------------------------------------------------------------------

def run_batch(
    input_root: Path,
    output_root: Path,
    mode: str,
    model: str = "llama3.2:3b",
    filter_account: str | None = None,
    filter_version: str | None = None,
    strict: bool = False,
) -> dict:
    """Process all accounts from manifest.json.

    Args:
        input_root: Root data folder containing manifest.json.
        output_root: Root output folder.
        mode: Extraction mode (rules or ollama).
        model: Ollama model name.
        filter_account: If set, only process this account.
        filter_version: If set, only process this version.
        strict: If True, fail on low-confidence evidence fields.

    Returns:
        Summary report dict.
    """
    started_at = datetime.now(timezone.utc).isoformat()
    per_account: dict[str, dict] = {}
    errors: list[dict] = []

    # Phase 1 — Load manifest
    manifest_path = input_root / "manifest.json"
    manifest = load_manifest(manifest_path)
    accounts = manifest["accounts"]

    logger.info("Loaded manifest with %d account(s)", len(accounts))

    for acct in accounts:
        account_id = acct["account_id"]

        # Filter by account if specified
        if filter_account and account_id != filter_account:
            continue

        per_account[account_id] = {}
        prev_memo_dict = None
        prev_evidence_dict = None

        # Process versions sequentially
        for ver_entry in acct["versions"]:
            version = ver_entry["version"]
            source_type = ver_entry["source_type"]
            input_path = Path(ver_entry["input_path"])

            # Filter by version if specified
            if filter_version and version != filter_version:
                continue

            if not input_path.exists():
                msg = f"Input file not found: {input_path}"
                logger.error(msg)
                errors.append({"account": account_id, "version": version, "error": msg})
                per_account[account_id][f"{version}_success"] = False
                continue

            # Auto-detect previous version if exists
            if version != "v1":
                prev_version = f"v{int(version[1:]) - 1}"
                prev_dir = output_root / "accounts" / account_id / prev_version
                if prev_dir.exists():
                    try:
                        prev_memo_dict = read_json(prev_dir / "memo.json")
                        prev_evidence_dict = read_json(prev_dir / "evidence.json")
                    except Exception:
                        logger.warning("Could not load %s outputs for %s", prev_version, account_id)
                        prev_memo_dict = None
                        prev_evidence_dict = None

            try:
                process_transcript(
                    path=input_path,
                    output_root=output_root,
                    mode=mode,
                    model=model,
                    version=version,
                    source_type=source_type,
                    account_id=account_id,
                    prev_memo_dict=prev_memo_dict,
                    prev_evidence_dict=prev_evidence_dict,
                )
                per_account[account_id][f"{version}_success"] = True
                logger.info("%s done for %s", version, account_id)

                # After successful processing, update prev for next version
                ver_dir = output_root / "accounts" / account_id / version
                if ver_dir.exists():
                    prev_memo_dict = read_json(ver_dir / "memo.json")
                    prev_evidence_dict = read_json(ver_dir / "evidence.json")

            except Exception as exc:
                logger.exception("Failed %s for %s", version, account_id)
                errors.append({"account": account_id, "version": version, "error": str(exc)})
                per_account[account_id][f"{version}_success"] = False

    finished_at = datetime.now(timezone.utc).isoformat()

    report = {
        "run_started_at_utc": started_at,
        "run_finished_at_utc": finished_at,
        "mode": mode,
        "model": model if mode == "ollama" else None,
        "per_account": per_account,
        "errors": errors,
    }

    # Strict mode post-check
    if strict and not errors:
        try:
            run_validate_only(output_root, strict=True)
        except SystemExit:
            errors.append({"account": "ALL", "version": "ALL", "error": "Strict mode validation failed"})

    summary_dir = output_root / "summary"
    ensure_dir(summary_dir)
    write_json(summary_dir / "report.json", report)
    logger.info("Summary written to %s", summary_dir / "report.json")

    # Generate diff viewer HTML
    try:
        from src.generate.diff_viewer import generate_diff_viewer
        viewer_path = generate_diff_viewer(output_root)
        if viewer_path:
            logger.info("Diff viewer written to %s", viewer_path)
    except Exception as exc:
        logger.warning("Diff viewer generation failed (non-fatal): %s", exc)

    return report


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    """CLI entrypoint."""
    parser = build_parser()
    args = parser.parse_args()

    config.input_root = Path(args.input)
    config.output_root = Path(args.output)
    config.extraction_mode = args.mode

    # Validate-only mode
    if args.validate_only:
        run_validate_only(config.output_root, strict=args.strict)
        return

    if not args.batch:
        parser.print_help()
        sys.exit(0)

    report = run_batch(
        config.input_root,
        config.output_root,
        args.mode,
        args.model,
        filter_account=args.account,
        filter_version=args.version,
        strict=args.strict,
    )

    total = len(report["per_account"])
    errs = len(report["errors"])
    logger.info("Run complete — %d account(s) processed, %d error(s)", total, errs)


if __name__ == "__main__":
    main()
