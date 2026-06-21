from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any


def write_reports(report: dict[str, Any], report_dir: str) -> dict[str, str]:
    target_dir = Path(report_dir)
    try:
        target_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise OSError(f"Failed to create report directory: {target_dir}") from exc

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_path = target_dir / f"migration_report_{stamp}.json"
    text_path = target_dir / f"migration_report_{stamp}.txt"

    try:
        json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        text_path.write_text(format_text_report(report), encoding="utf-8")
    except OSError as exc:
        raise OSError(f"Failed to write migration report in {target_dir}") from exc

    return {"json": str(json_path), "text": str(text_path)}


def format_text_report(report: dict[str, Any]) -> str:
    lines = [
        "TempleManager Migration Report",
        "=" * 32,
        f"version: {report.get('version')}",
        f"dry_run: {report.get('dry_run')}",
        f"source: {report.get('source')}",
        f"target: {report.get('target')}",
        f"backup: {report.get('backup')}",
        "",
        "Copied tables:",
    ]
    for item in report.get("copied_tables", []):
        lines.append(f"- {item.get('table')}: {item.get('rows')} rows")

    lines.extend(["", "Schema diff:"])
    lines.append(json.dumps(report.get("schema_diff", {}), ensure_ascii=False, indent=2))

    lines.extend(["", "Validation issues:"])
    issues = report.get("validation_issues", [])
    if not issues:
        lines.append("- none")
    else:
        for issue in issues:
            lines.append(f"- {json.dumps(issue, ensure_ascii=False)}")

    lines.extend(["", f"success: {report.get('success')}"])
    return "\n".join(lines) + "\n"
