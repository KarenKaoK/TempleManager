"""
Scheduler worker：統一排程主程式。
負責載入 scheduler_config.yaml、註冊排程 jobs（mailer / 報表 / housekeeping 等）、執行排程。
支援 report 欄位：先產生報表再寄信。
"""
from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from app.controller.app_controller import AppController
from app.logging import log_data_change, log_system
from app.mailer.smtp_client import send_email_smtp
from app.mailer.outbox_db import connect, ensure_schema, insert_record
from app.report_generator import activity as report_activity
from app.report_generator import believer as report_believer
from app.report_generator import finance as report_finance
from app.report_generator.cleanup import cleanup_reports


def _log_scheduler_data(action: str, message: str) -> None:
    try:
        log_data_change(action=action, message=message, level="INFO")
    except Exception:
        pass


def _log_scheduler_system(message: str, level: str = "WARN") -> None:
    try:
        log_system(message, level=level)
    except Exception:
        pass


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


def run_backup_schedule_check(db_path: str) -> None:
    controller = None
    try:
        controller = AppController(db_path=db_path)
        ran = controller.run_scheduled_backup_once()
        if ran:
            print("[OK] backup schedule check executed")
            _log_scheduler_data(
                "SCHEDULER.BACKUP.CHECK",
                f"排程備份檢查執行完成（db_path {db_path}，結果 executed）",
            )
        else:
            print("[INFO] backup schedule check skipped")
            _log_scheduler_data(
                "SCHEDULER.BACKUP.CHECK",
                f"排程備份檢查執行完成（db_path {db_path}，結果 skipped）",
            )
    except Exception as e:
        print(f"[ERR] backup schedule check failed: {e}")
        _log_scheduler_system(
            f"排程備份檢查失敗（db_path {db_path}，原因：{e})",
            level="ERROR",
        )
    finally:
        try:
            if controller is not None and getattr(controller, "conn", None) is not None:
                controller.conn.close()
        except Exception:
            pass


def _resolve_runtime(config_path: str, db_path_override: Optional[str] = None) -> Tuple[Dict[str, Any], str, Path, Path, str]:
    cfg = load_cfg(config_path)
    tz = str(cfg.get("timezone", "Asia/Taipei")).strip() or "Asia/Taipei"

    config_file = Path(config_path).resolve()
    project_root = config_file.parents[2]

    if db_path_override:
        db_path_resolved = str(db_path_override)
    else:
        db_path = (cfg.get("db") or {}).get("path", "./app/database/temple.db")
        db_path_resolved = str((project_root / db_path).resolve()) if not Path(db_path).is_absolute() else str(db_path)

    return cfg, tz, config_file, project_root, db_path_resolved


def create_scheduler(
    config_path: str = "app/scheduler/scheduler_config.yaml",
    feature_flags: Optional[Dict[str, bool]] = None,
    db_path_override: Optional[str] = None,
):
    cfg, tz, config_file, project_root, db_path_resolved = _resolve_runtime(
        config_path=config_path,
        db_path_override=db_path_override,
    )
    flags = feature_flags or {}
    mail_enabled = bool(flags.get("mail_enabled", True))
    backup_enabled = bool(flags.get("backup_enabled", True))

    sched = BackgroundScheduler(timezone=tz)

    def run_job(job_id: str) -> None:
        job = next((j for j in (cfg.get("jobs") or []) if str(j.get("id", "")).strip() == job_id), None)
        if not job:
            print(f"[WARN] job not found: {job_id}")
            _log_scheduler_system(f"排程工作不存在（job_id {job_id}）", level="WARN")
            return
        if not bool(job.get("enabled", True)):
            print(f"[INFO] job disabled: {job_id}")
            _log_scheduler_data("SCHEDULER.JOB.SKIP", f"排程工作略過（job_id {job_id}，原因 disabled）")
            return

        to_emails = [str(x).strip() for x in (job.get("to") or []) if str(x).strip()]
        subject = str(job.get("subject", "")).strip()
        body = str(job.get("body", "")).rstrip()

        report_type = str(job.get("report", "")).strip() or None
        if report_type == "daily_finance":
            try:
                out_path = report_finance.generate_daily_report(db_path_resolved)
                attachments = [out_path]
                _log_scheduler_data(
                    "SCHEDULER.REPORT.GENERATE",
                    f"報表產生完成（job_id {job_id}，report daily_finance，檔案 {out_path}）",
                )
            except Exception as e:
                print(f"[ERR] job={job_id} report gen failed: {e}")
                _log_scheduler_system(
                    f"報表產生失敗（job_id {job_id}，report daily_finance，原因：{e}）",
                    level="ERROR",
                )
                return
        elif report_type == "monthly_finance":
            try:
                out_path = report_finance.generate_monthly_report(db_path_resolved)
                attachments = [out_path]
                _log_scheduler_data(
                    "SCHEDULER.REPORT.GENERATE",
                    f"報表產生完成（job_id {job_id}，report monthly_finance，檔案 {out_path}）",
                )
            except Exception as e:
                print(f"[ERR] job={job_id} report gen failed: {e}")
                _log_scheduler_system(
                    f"報表產生失敗（job_id {job_id}，report monthly_finance，原因：{e}）",
                    level="ERROR",
                )
                return
        elif report_type == "daily_activity":
            try:
                out_path = report_activity.generate_daily_activity_report(db_path_resolved)
                attachments = [out_path]
                _log_scheduler_data(
                    "SCHEDULER.REPORT.GENERATE",
                    f"報表產生完成（job_id {job_id}，report daily_activity，檔案 {out_path}）",
                )
            except ValueError as e:
                print(f"[INFO] job={job_id} skipped (no activities): {e}")
                _log_scheduler_data(
                    "SCHEDULER.JOB.SKIP",
                    f"排程工作略過（job_id {job_id}，report daily_activity，原因 no_activities）",
                )
                return
            except Exception as e:
                print(f"[ERR] job={job_id} report gen failed: {e}")
                _log_scheduler_system(
                    f"報表產生失敗（job_id {job_id}，report daily_activity，原因：{e}）",
                    level="ERROR",
                )
                return
        elif report_type == "monthly_believer":
            try:
                out_path = report_believer.generate_monthly_believer_report(db_path_resolved)
                attachments = [out_path]
                _log_scheduler_data(
                    "SCHEDULER.REPORT.GENERATE",
                    f"報表產生完成（job_id {job_id}，report monthly_believer，檔案 {out_path}）",
                )
            except Exception as e:
                print(f"[ERR] job={job_id} report gen failed: {e}")
                _log_scheduler_system(
                    f"報表產生失敗（job_id {job_id}，report monthly_believer，原因：{e}）",
                    level="ERROR",
                )
                return
        else:
            attachments = resolve_paths(project_root, job.get("attachments") or [])

        if not to_emails:
            print(f"[WARN] job={job_id} Job.to is empty, skipped")
            _log_scheduler_system(f"排程工作略過（job_id {job_id}，原因：收件人為空）", level="WARN")
            return
        if not subject:
            print(f"[WARN] job={job_id} Job.subject is empty, skipped")
            _log_scheduler_system(f"排程工作略過（job_id {job_id}，原因：主旨為空）", level="WARN")
            return

        conn = connect(db_path_resolved)
        try:
            ensure_schema(conn)

            try:
                cred_controller = AppController(db_path=db_path_resolved)
                try:
                    smtp_user, smtp_pwd = cred_controller.get_scheduler_mail_credentials()
                finally:
                    try:
                        cred_controller.conn.close()
                    except Exception:
                        pass
                if not smtp_user or not smtp_pwd:
                    raise RuntimeError("Mail credentials not configured")
                send_email_smtp(
                    cfg,
                    to_emails=to_emails,
                    subject=subject,
                    body=body,
                    attachments=attachments,
                    smtp_user=smtp_user,
                    smtp_password=smtp_pwd,
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
                _log_scheduler_data(
                    "SCHEDULER.MAIL.SEND",
                    f"排程郵件寄送成功（job_id {job_id}，outbox_id {outbox_id}，收件者 {','.join(to_emails)}，附件數 {len(attachments)}）",
                )
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
                _log_scheduler_system(
                    f"排程郵件寄送失敗（job_id {job_id}，outbox_id {outbox_id}，原因：{type(e).__name__}: {e}）",
                    level="ERROR",
                )
        finally:
            conn.close()

    if mail_enabled:
        for job in (cfg.get("jobs") or []):
            if not bool(job.get("enabled", True)):
                continue
            job_id = str(job.get("id", "")).strip()
            if not job_id:
                continue
            cron = job.get("cron") or {}
            trigger = CronTrigger(timezone=tz, **cron)
            sched.add_job(run_job, trigger, kwargs={"job_id": job_id}, id=job_id, replace_existing=True)
            _log_scheduler_data(
                "SCHEDULER.JOB.REGISTER",
                f"註冊排程工作（job_id {job_id}，cron {cron}）",
            )

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
                _log_scheduler_data(
                    "SCHEDULER.JOB.REGISTER",
                    f"註冊報表清理工作（job_id reports_cleanup，cron {cleanup_cron}）",
                )
    else:
        print("[INFO] mail jobs disabled by feature flag")
        _log_scheduler_data("SCHEDULER.FEATURE.SKIP", "略過郵件排程（原因：mail_enabled=0）")

    if backup_enabled:
        sched.add_job(
            run_backup_schedule_check,
            IntervalTrigger(minutes=1),
            kwargs={"db_path": db_path_resolved},
            id="auto_backup_check",
            replace_existing=True,
            max_instances=1,
            coalesce=True,
        )
        print("[INFO] auto_backup_check job registered (interval=1m)")
        _log_scheduler_data(
            "SCHEDULER.JOB.REGISTER",
            "註冊排程備份檢查工作（job_id auto_backup_check，trigger interval=1m）",
        )
    else:
        print("[INFO] backup job disabled by feature flag")
        _log_scheduler_data("SCHEDULER.FEATURE.SKIP", "略過備份排程（原因：backup_enabled=0）")

    runtime = {
        "config_file": str(config_file),
        "db_path": db_path_resolved,
        "timezone": tz,
        "mail_enabled": mail_enabled,
        "backup_enabled": backup_enabled,
    }
    _log_scheduler_data(
        "SCHEDULER.CREATE",
        (
            "建立排程器（"
            f"config {runtime['config_file']}，db_path {runtime['db_path']}，tz {runtime['timezone']}，"
            f"mail_enabled {int(runtime['mail_enabled'])}，backup_enabled {int(runtime['backup_enabled'])}）"
        ),
    )
    return sched, runtime


def main() -> int:
    controller = None
    try:
        controller = AppController()
        config_path = controller.get_scheduler_config_path()
        feature_flags = controller.get_scheduler_feature_settings()
        db_path_override = getattr(controller, "db_path", None)
    except Exception:
        config_path = "app/scheduler/scheduler_config.yaml"
        feature_flags = None
        db_path_override = None
    finally:
        try:
            if controller is not None and getattr(controller, "conn", None) is not None:
                controller.conn.close()
        except Exception:
            pass

    try:
        sched, runtime = create_scheduler(
            config_path=config_path,
            feature_flags=feature_flags,
            db_path_override=db_path_override,
        )
        sched.start()
        print(
            f"[START] scheduler worker running. "
            f"config={runtime['config_file']} db={runtime['db_path']} tz={runtime['timezone']} "
            f"mail_enabled={runtime['mail_enabled']} backup_enabled={runtime['backup_enabled']}"
        )

        try:
            while True:
                time.sleep(5)
        except KeyboardInterrupt:
            return 0
        finally:
            sched.shutdown()
    except Exception as e:
        print(f"[ERR] scheduler worker failed to start: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
