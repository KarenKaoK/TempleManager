import app.scheduler.worker as worker_module


def test_create_scheduler_respects_mail_and_backup_feature_flags(monkeypatch):
    cfg = {
        "timezone": "Asia/Taipei",
        "db": {"path": "./app/database/temple.db"},
        "jobs": [
            {
                "id": "mail_job_1",
                "enabled": True,
                "to": ["a@example.com"],
                "subject": "s",
                "body": "b",
                "cron": {"hour": 1, "minute": 2},
            }
        ],
        "reports": {"cleanup": {"enabled": True, "cron": {"hour": 3, "minute": 30}}},
    }
    monkeypatch.setattr(worker_module, "load_cfg", lambda _path: cfg)

    sched, runtime = worker_module.create_scheduler(
        config_path="app/scheduler/scheduler_config.yaml",
        feature_flags={"mail_enabled": False, "backup_enabled": True},
    )
    job_ids = {j.id for j in sched.get_jobs()}
    assert "auto_backup_check" in job_ids
    assert "mail_job_1" not in job_ids
    assert "reports_cleanup" not in job_ids
    assert runtime["mail_enabled"] is False
    assert runtime["backup_enabled"] is True


def test_create_scheduler_can_disable_backup_only(monkeypatch):
    cfg = {
        "timezone": "Asia/Taipei",
        "db": {"path": "./app/database/temple.db"},
        "jobs": [
            {
                "id": "mail_job_1",
                "enabled": True,
                "to": ["a@example.com"],
                "subject": "s",
                "body": "b",
                "cron": {"hour": 1, "minute": 2},
            }
        ],
        "reports": {"cleanup": {"enabled": False}},
    }
    monkeypatch.setattr(worker_module, "load_cfg", lambda _path: cfg)

    sched, runtime = worker_module.create_scheduler(
        config_path="app/scheduler/scheduler_config.yaml",
        feature_flags={"mail_enabled": True, "backup_enabled": False},
    )
    job_ids = {j.id for j in sched.get_jobs()}
    assert "auto_backup_check" not in job_ids
    assert "mail_job_1" in job_ids
    assert runtime["mail_enabled"] is True
    assert runtime["backup_enabled"] is False
