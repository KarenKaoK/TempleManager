"""
測試 app.report_generator.cleanup 的 reports 檔案清理功能。
"""
from datetime import date, timedelta
from pathlib import Path

from app.report_generator.cleanup import cleanup_reports


def _create_file(path: Path) -> Path:
    """在 path 建立檔案（內容無關，cleanup 依檔名日期判斷）。"""
    path.write_text("dummy", encoding="utf-8")
    return path


def test_cleanup_reports_deletes_old_csv_and_keeps_recent(tmp_path):
    """應刪除檔名日期超過 retention_days 的 CSV，保留較新的與非 CSV 檔。"""
    project_root = tmp_path
    reports_dir = tmp_path / "reports"
    reports_dir.mkdir()

    today = date(2026, 2, 23)
    old_date = today - timedelta(days=400)
    new_date = today - timedelta(days=10)

    old_csv = _create_file(
        reports_dir / f"每日收支明細表_{old_date.strftime('%Y%m%d')}.csv"
    )
    new_csv = _create_file(
        reports_dir / f"每日收支明細表_{new_date.strftime('%Y%m%d')}.csv"
    )
    monthly_old = _create_file(
        reports_dir / f"每月收支明細表_{old_date.strftime('%Y%m')}.csv"
    )
    other_file = _create_file(reports_dir / "note.txt")

    cfg = {
        "reports": {
            "cleanup": {
                "enabled": True,
                "dir": "./reports",
                "retention_days": 365,
            }
        }
    }

    cleanup_reports(project_root, cfg, today=today)

    assert not old_csv.exists()
    assert not monthly_old.exists()
    assert new_csv.exists()
    assert other_file.exists()


def test_cleanup_reports_disabled_will_not_delete(tmp_path):
    """enabled 為 False 時不應刪除任何檔案。"""
    project_root = tmp_path
    reports_dir = tmp_path / "reports"
    reports_dir.mkdir()

    today = date(2026, 2, 23)
    old_date = today - timedelta(days=400)

    old_csv = _create_file(
        reports_dir / f"每日活動報表_{old_date.strftime('%Y%m%d')}.csv"
    )

    cfg = {
        "reports": {
            "cleanup": {
                "enabled": False,
                "dir": "./reports",
                "retention_days": 0,
            }
        }
    }

    cleanup_reports(project_root, cfg, today=today)

    assert old_csv.exists()


def test_cleanup_reports_negative_retention_skips(tmp_path):
    """retention_days < 0 視為不刪除任何檔案（安全防護）。"""
    project_root = tmp_path
    reports_dir = tmp_path / "reports"
    reports_dir.mkdir()

    today = date(2026, 2, 23)
    old_date = today - timedelta(days=400)

    old_csv = _create_file(
        reports_dir / f"每月信眾資料表_{old_date.strftime('%Y%m')}.csv"
    )

    cfg = {
        "reports": {
            "cleanup": {
                "enabled": True,
                "dir": "./reports",
                "retention_days": -1,
            }
        }
    }

    cleanup_reports(project_root, cfg, today=today)

    assert old_csv.exists()

