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


def test_main_uses_scheduler_settings_from_controller(monkeypatch):
    calls = {}
    monkeypatch.setattr(worker_module, "local_db_encryption_enabled", lambda: False)

    class _Conn:
        def close(self):
            return None

    class _FakeController:
        def __init__(self):
            self.conn = _Conn()
            self.db_path = "/tmp/fake.db"

        def get_scheduler_config_path(self):
            return "/tmp/custom_scheduler_config.yaml"

        def get_scheduler_feature_settings(self):
            return {"mail_enabled": False, "backup_enabled": True}

    class _FakeScheduler:
        def start(self):
            return None

        def shutdown(self):
            return None

    def _fake_create_scheduler(config_path, feature_flags=None, db_path_override=None):
        calls["config_path"] = config_path
        calls["feature_flags"] = feature_flags
        calls["db_path_override"] = db_path_override
        return (
            _FakeScheduler(),
            {
                "config_file": config_path,
                "db_path": db_path_override,
                "timezone": "Asia/Taipei",
                "mail_enabled": bool((feature_flags or {}).get("mail_enabled")),
                "backup_enabled": bool((feature_flags or {}).get("backup_enabled")),
            },
        )

    monkeypatch.setattr(worker_module, "AppController", _FakeController)
    monkeypatch.setattr(worker_module, "create_scheduler", _fake_create_scheduler)
    monkeypatch.setattr(
        worker_module.time,
        "sleep",
        lambda _seconds: (_ for _ in ()).throw(KeyboardInterrupt()),
    )

    assert worker_module.main() == 0
    assert calls["config_path"] == "/tmp/custom_scheduler_config.yaml"
    assert calls["feature_flags"] == {"mail_enabled": False, "backup_enabled": True}
    assert calls["db_path_override"] == "/tmp/fake.db"


def test_main_returns_one_when_scheduler_startup_fails(monkeypatch):
    monkeypatch.setattr(worker_module, "local_db_encryption_enabled", lambda: False)

    class _Conn:
        def close(self):
            return None

    class _FakeController:
        def __init__(self):
            self.conn = _Conn()

        def get_scheduler_config_path(self):
            return "/tmp/custom_scheduler_config.yaml"

        def get_scheduler_feature_settings(self):
            return {"mail_enabled": True, "backup_enabled": True}

    monkeypatch.setattr(worker_module, "AppController", _FakeController)
    monkeypatch.setattr(
        worker_module,
        "create_scheduler",
        lambda **kwargs: (_ for _ in ()).throw(RuntimeError("boom")),
    )

    assert worker_module.main() == 1


def test_main_returns_one_when_controller_init_fails(monkeypatch):
    monkeypatch.setattr(
        worker_module,
        "AppController",
        lambda: (_ for _ in ()).throw(RuntimeError("controller init failed")),
    )
    monkeypatch.setattr(worker_module, "local_db_encryption_enabled", lambda: False)

    assert worker_module.main() == 1


def test_main_prepares_and_finalizes_runtime_db_when_encryption_enabled(monkeypatch):
    calls = {"ensure": 0, "finalize": 0}

    class _Conn:
        def close(self):
            return None

    class _FakeController:
        def __init__(self):
            self.conn = _Conn()
            self.db_path = "/tmp/fake.db"

        def get_scheduler_config_path(self):
            return "/tmp/custom_scheduler_config.yaml"

        def get_scheduler_feature_settings(self):
            return {"mail_enabled": True, "backup_enabled": True}

    class _FakeScheduler:
        def start(self):
            return None

        def shutdown(self):
            return None

    monkeypatch.setattr(worker_module, "local_db_encryption_enabled", lambda: True)
    monkeypatch.setattr(
        worker_module,
        "ensure_runtime_db_ready",
        lambda **kwargs: calls.__setitem__("ensure", calls["ensure"] + 1),
    )
    monkeypatch.setattr(
        worker_module,
        "finalize_runtime_db",
        lambda **kwargs: calls.__setitem__("finalize", calls["finalize"] + 1),
    )
    monkeypatch.setattr(worker_module, "AppController", _FakeController)
    monkeypatch.setattr(
        worker_module,
        "create_scheduler",
        lambda config_path, feature_flags=None, db_path_override=None: (
            _FakeScheduler(),
            {
                "config_file": config_path,
                "db_path": db_path_override,
                "timezone": "Asia/Taipei",
                "mail_enabled": True,
                "backup_enabled": True,
            },
        ),
    )
    monkeypatch.setattr(
        worker_module.time,
        "sleep",
        lambda _seconds: (_ for _ in ()).throw(KeyboardInterrupt()),
    )

    assert worker_module.main() == 0
    assert calls["ensure"] == 1
    assert calls["finalize"] == 1
