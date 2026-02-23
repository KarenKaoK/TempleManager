"""
Scheduler worker：統一排程主程式。
負責載入 scheduler_config.yaml、註冊排程 jobs（mailer / 報表 / housekeeping 等）、執行排程。
支援 report 欄位：先產生報表再寄信。
"""
from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app.mailer.smtp_client import send_email_smtp
from app.mailer.outbox_db import connect, ensure_schema, insert_record
from app.report_generator import activity as report_activity
from app.report_generator import believer as report_believer
from app.report_generator import finance as report_finance
from app.report_generator.cleanup import cleanup_reports


def load_cfg(path: str) -> Dict[str, Any]:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Config not found: {p.resolve()}")
    with p.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def resolve_paths(base_dir: Path, paths: Optional[List[str]]) -> List[str]:
    """
    將附件相對路徑改成以 base_dir 為基準的絕對路徑。
    我們使用「專案根目錄」當 base_dir（不是 config 所在資料夾）。
    """
    out: List[str] = []
    for x in (paths or []):
        s = str(x).strip()
        if not s:
            continue
        p = Path(s)
        if not p.is_absolute():
            p = (base_dir / p).resolve()
        out.append(str(p))
    return out


def main() -> None:
    config_path = sys.argv[1] if len(sys.argv) > 1 else "app/scheduler/scheduler_config.yaml"
    cfg = load_cfg(config_path)

    tz = str(cfg.get("timezone", "Asia/Taipei")).strip() or "Asia/Taipei"

    # 專案根目錄：TempleManager/
    config_file = Path(config_path).resolve()
    project_root = config_file.parents[2]  # .../TempleManager/app/scheduler/scheduler_config.yaml -> parents[2] = TempleManager

    # DB path：相對路徑以專案根目錄解
    db_path = (cfg.get("db") or {}).get("path", "./app/database/temple.db")
    db_path_resolved = str((project_root / db_path).resolve()) if not Path(db_path).is_absolute() else db_path

    sched = BackgroundScheduler(timezone=tz)

    def run_job(job_id: str) -> None:
        job = next((j for j in (cfg.get("jobs") or []) if str(j.get("id", "")).strip() == job_id), None)
        if not job:
            print(f"[WARN] job not found: {job_id}")
            return
        if not bool(job.get("enabled", True)):
            print(f"[INFO] job disabled: {job_id}")
            return

        to_emails = [str(x).strip() for x in (job.get("to") or []) if str(x).strip()]
        subject = str(job.get("subject", "")).strip()
        body = str(job.get("body", "")).rstrip()

        # 若有 report 欄位，先產生報表再以產出路徑為附件
        report_type = str(job.get("report", "")).strip() or None
        if report_type == "daily_finance":
            try:
                out_path = report_finance.generate_daily_report(db_path_resolved)
                attachments = [out_path]
            except Exception as e:
                print(f"[ERR] job={job_id} report gen failed: {e}")
                return
        elif report_type == "monthly_finance":
            try:
                out_path = report_finance.generate_monthly_report(db_path_resolved)
                attachments = [out_path]
            except Exception as e:
                print(f"[ERR] job={job_id} report gen failed: {e}")
                return
        elif report_type == "daily_activity":
            try:
                out_path = report_activity.generate_daily_activity_report(db_path_resolved)
                attachments = [out_path]
            except ValueError as e:
                print(f"[INFO] job={job_id} skipped (no activities): {e}")
                return
            except Exception as e:
                print(f"[ERR] job={job_id} report gen failed: {e}")
                return
        elif report_type == "monthly_believer":
            try:
                out_path = report_believer.generate_monthly_believer_report(db_path_resolved)
                attachments = [out_path]
            except Exception as e:
                print(f"[ERR] job={job_id} report gen failed: {e}")
                return
        else:
            attachments = resolve_paths(project_root, job.get("attachments") or [])

        if not to_emails:
            print(f"[WARN] job={job_id} Job.to is empty, skipped")
            return
        if not subject:
            print(f"[WARN] job={job_id} Job.subject is empty, skipped")
            return

        # 每次 job 執行都開新的 DB connection（避免 thread error）
        conn = connect(db_path_resolved)
        try:
            ensure_schema(conn)

            try:
                send_email_smtp(
                    cfg,
                    to_emails=to_emails,
                    subject=subject,
                    body=body,
                    attachments=attachments,
                )
                outbox_id = insert_record(
                    conn,
                    job_id=job_id,
                    to_emails=to_emails,
                    subject=subject,
                    body=body,
                    attachments=attachments,
                    status="SENT",
                    error=None,
                )
                print(f"[OK] SENT job={job_id} outbox_id={outbox_id} to={to_emails}")
            except Exception as e:
                outbox_id = insert_record(
                    conn,
                    job_id=job_id,
                    to_emails=to_emails,
                    subject=subject,
                    body=body,
                    attachments=attachments,
                    status="FAILED",
                    error=f"{type(e).__name__}: {e}",
                )
                print(f"[ERR] FAILED job={job_id} outbox_id={outbox_id} err={e}")
        finally:
            conn.close()

    # 註冊 mail 排程
    for job in (cfg.get("jobs") or []):
        if not bool(job.get("enabled", True)):
            continue
        job_id = str(job.get("id", "")).strip()
        if not job_id:
            continue
        cron = job.get("cron") or {}
        trigger = CronTrigger(timezone=tz, **cron)
        sched.add_job(run_job, trigger, kwargs={"job_id": job_id}, id=job_id, replace_existing=True)

    # 註冊 reports 清理排程（若有設定）
    cleanup_cfg = ((cfg.get("reports") or {}).get("cleanup") or {})
    if cleanup_cfg.get("enabled", True):
        cleanup_cron = cleanup_cfg.get("cron") or {}
        if not cleanup_cron:
            cleanup_cron = {"hour": 3, "minute": 30}

        try:
            cleanup_trigger = CronTrigger(timezone=tz, **cleanup_cron)
        except TypeError as e:
            print(f"[ERR] invalid reports.cleanup.cron config: {e}")
        else:

            def run_cleanup() -> None:
                try:
                    cleanup_reports(project_root, cfg)
                except Exception as e:
                    print(f"[ERR] reports_cleanup job failed: {e}")

            sched.add_job(
                run_cleanup,
                cleanup_trigger,
                id="reports_cleanup",
                replace_existing=True,
            )
            print(f"[INFO] reports_cleanup job registered with cron={cleanup_cron}")

    sched.start()
    print(f"[START] scheduler worker running. config={config_file} db={db_path_resolved} tz={tz}")

    try:
        while True:
            time.sleep(5)
    except KeyboardInterrupt:
        pass
    finally:
        sched.shutdown()


if __name__ == "__main__":
    main()
