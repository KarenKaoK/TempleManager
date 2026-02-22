from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from .smtp_client import send_email_smtp
from .outbox_db import connect, ensure_schema, insert_record


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
    config_path = sys.argv[1] if len(sys.argv) > 1 else "app/mailer/mail_config.yaml"
    cfg = load_cfg(config_path)

    tz = str(cfg.get("timezone", "Asia/Taipei")).strip() or "Asia/Taipei"

    # ✅ 專案根目錄：TempleManager/
    config_file = Path(config_path).resolve()
    project_root = config_file.parents[2]  # .../TempleManager/app/mailer/mail_config.yaml -> parents[2] = TempleManager

    # DB path：相對路徑以專案根目錄解
    db_path = (cfg.get("db") or {}).get("path", "./database/temple.db")
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
        attachments = resolve_paths(project_root, job.get("attachments") or [])

        if not to_emails:
            print(f"[WARN] job={job_id} Job.to is empty, skipped")
            return
        if not subject:
            print(f"[WARN] job={job_id} Job.subject is empty, skipped")
            return

        # ✅ 每次 job 執行都開新的 DB connection（避免 thread error）
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

    # 註冊排程
    for job in (cfg.get("jobs") or []):
        if not bool(job.get("enabled", True)):
            continue
        job_id = str(job.get("id", "")).strip()
        if not job_id:
            continue
        cron = job.get("cron") or {}
        trigger = CronTrigger(timezone=tz, **cron)
        sched.add_job(run_job, trigger, kwargs={"job_id": job_id}, id=job_id, replace_existing=True)

    sched.start()
    print(f"[START] mailer worker running. config={config_file} db={db_path_resolved} tz={tz}")

    try:
        while True:
            time.sleep(5)
    except KeyboardInterrupt:
        pass
    finally:
        sched.shutdown()


if __name__ == "__main__":
    main()