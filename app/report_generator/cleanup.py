from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any, Dict


def _extract_date_from_filename(path: Path) -> date | None:
    """
    從檔名解析日期，支援：
      - *_YYYYMMDD.csv -> 依年月日建立 date
      - *_YYYYMM.csv   -> 以該月 1 號建立 date
    解析失敗時回傳 None。
    """
    stem = path.stem
    # 先取最後一段（假設報表檔名為 xxx_yyyymmdd 或 xxx_yyyymm）
    suffix = stem.rsplit("_", 1)[-1]
    if suffix.isdigit():
        if len(suffix) == 8:
            y, m, d = int(suffix[0:4]), int(suffix[4:6]), int(suffix[6:8])
            try:
                return date(y, m, d)
            except ValueError:
                return None
        if len(suffix) == 6:
            y, m = int(suffix[0:4]), int(suffix[4:6])
            try:
                return date(y, m, 1)
            except ValueError:
                return None
    return None


def cleanup_reports(project_root: Path, cfg: Dict[str, Any], today: date | None = None) -> None:
    """
    根據設定清理 reports 目錄中的舊 CSV 報表。

    設定路徑：
      reports.cleanup.enabled: 是否啟用
      reports.cleanup.dir:     報表目錄（可為相對或絕對路徑）
      reports.cleanup.retention_days: 保留天數（超過才刪除）
    """
    reports_cfg = (cfg.get("reports") or {}).get("cleanup") or {}

    if not reports_cfg:
        print("[INFO] reports.cleanup not configured, skip cleanup.")
        return

    if not bool(reports_cfg.get("enabled", True)):
        print("[INFO] reports.cleanup disabled, skip cleanup.")
        return

    raw_dir = str(reports_cfg.get("dir", "./reports")).strip() or "./reports"
    reports_dir = Path(raw_dir)
    if not reports_dir.is_absolute():
        reports_dir = (project_root / reports_dir).resolve()

    if not reports_dir.exists():
        print(f"[WARN] reports cleanup directory not found: {reports_dir}")
        return
    if not reports_dir.is_dir():
        print(f"[WARN] reports cleanup path is not a directory: {reports_dir}")
        return

    try:
        retention_days = int(reports_cfg.get("retention_days", 365))
    except (TypeError, ValueError):
        retention_days = 365

    if retention_days < 0:
        # 負值視為不刪除任何檔案，避免誤刪
        print(
            f"[WARN] reports.cleanup.retention_days < 0, skip cleanup. value={retention_days}"
        )
        return

    if today is None:
        today = date.today()

    deleted = 0
    scanned = 0
    errors = 0

    for entry in reports_dir.iterdir():
        if not entry.is_file():
            continue
        if entry.suffix.lower() != ".csv":
            continue

        scanned += 1
        file_date = _extract_date_from_filename(entry)
        if file_date is None:
            print(f"[INFO] reports cleanup skip (no date in name): {entry.name}")
            continue

        age_days = (today - file_date).days

        if age_days <= retention_days:
            continue

        try:
            entry.unlink()
            deleted += 1
            print(
                f"[OK] reports cleanup removed: {entry} age_days={age_days} "
                f"retention_days={retention_days}"
            )
        except OSError as e:
            errors += 1
            print(f"[ERR] reports cleanup delete failed for {entry}: {e}")

    print(
        f"[INFO] reports cleanup done. dir={reports_dir} "
        f"scanned={scanned} deleted={deleted} errors={errors} retention_days={retention_days}"
    )

