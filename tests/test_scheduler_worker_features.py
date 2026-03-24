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

    class _Conn:
        def close(self):
            return None

    class _FakeController:
        def __init__(self, db_path=None):
            self.conn = _Conn()
            self.db_path = db_path or "/tmp/fake.db"

        def get_scheduler_config_path(self):
            return "/tmp/custom_scheduler_config.yaml"

        def get_scheduler_feature_settings(self):
            return {"mail_enabled": False, "backup_enabled": True}

    class _FakeScheduler:
        def start(self):
            return None

        def shutdown(self):
            return None

    class _SnapshotCtx:
        def __enter__(self):
            return "/tmp/worker_snapshot.db"

        def __exit__(self, exc_type, exc, tb):
            return False

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
    monkeypatch.setattr(worker_module, "worker_db_snapshot", lambda *args, **kwargs: _SnapshotCtx())
    monkeypatch.setattr(worker_module, "create_scheduler", _fake_create_scheduler)
    monkeypatch.setattr(
        worker_module.time,
        "sleep",
        lambda _seconds: (_ for _ in ()).throw(KeyboardInterrupt()),
    )

    assert worker_module.main() == 0
    assert calls["config_path"] == "/tmp/custom_scheduler_config.yaml"
    assert calls["feature_flags"] == {"mail_enabled": False, "backup_enabled": True}
    assert calls["db_path_override"] == worker_module.DB_NAME


def test_main_returns_one_when_scheduler_startup_fails(monkeypatch):
    class _Conn:
        def close(self):
            return None

    class _FakeController:
        def __init__(self, db_path=None):
            self.conn = _Conn()
            self.db_path = db_path or "/tmp/fake.db"

        def get_scheduler_config_path(self):
            return "/tmp/custom_scheduler_config.yaml"

        def get_scheduler_feature_settings(self):
            return {"mail_enabled": True, "backup_enabled": True}

    class _SnapshotCtx:
        def __enter__(self):
            return "/tmp/worker_snapshot.db"

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(worker_module, "AppController", _FakeController)
    monkeypatch.setattr(worker_module, "worker_db_snapshot", lambda *args, **kwargs: _SnapshotCtx())
    monkeypatch.setattr(
        worker_module,
        "create_scheduler",
        lambda **kwargs: (_ for _ in ()).throw(RuntimeError("boom")),
    )

    assert worker_module.main() == 1


def test_main_returns_one_when_controller_init_fails(monkeypatch):
    class _SnapshotCtx:
        def __enter__(self):
            return "/tmp/worker_snapshot.db"

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(worker_module, "worker_db_snapshot", lambda *args, **kwargs: _SnapshotCtx())
    monkeypatch.setattr(
        worker_module,
        "AppController",
        lambda db_path=None: (_ for _ in ()).throw(RuntimeError("controller init failed")),
    )

    assert worker_module.main() == 1


def test_main_uses_bootstrap_snapshot_instead_of_touching_live_db(monkeypatch):
    calls = {"snapshot": 0}

    class _Conn:
        def close(self):
            return None

    class _FakeController:
        def __init__(self, db_path=None):
            self.conn = _Conn()
            self.db_path = db_path or "/tmp/fake.db"

        def get_scheduler_config_path(self):
            return "/tmp/custom_scheduler_config.yaml"

        def get_scheduler_feature_settings(self):
            return {"mail_enabled": True, "backup_enabled": True}

    class _FakeScheduler:
        def start(self):
            return None

        def shutdown(self):
            return None

    class _SnapshotCtx:
        def __enter__(self):
            calls["snapshot"] += 1
            return "/tmp/bootstrap_snapshot.db"

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(worker_module, "AppController", _FakeController)
    monkeypatch.setattr(worker_module, "worker_db_snapshot", lambda *args, **kwargs: _SnapshotCtx())
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
    assert calls["snapshot"] == 1


def test_main_closes_bootstrap_controller_before_snapshot_exit(monkeypatch):
    calls = {"closed": 0}

    class _Conn:
        def close(self):
            calls["closed"] += 1

    class _FakeController:
        def __init__(self, db_path=None):
            self.conn = _Conn()
            self.db_path = db_path or "/tmp/fake.db"

        def get_scheduler_config_path(self):
            return "/tmp/custom_scheduler_config.yaml"

        def get_scheduler_feature_settings(self):
            return {"mail_enabled": True, "backup_enabled": True}

    class _FakeScheduler:
        def start(self):
            return None

        def shutdown(self):
            return None

    class _SnapshotCtx:
        def __enter__(self):
            return "/tmp/bootstrap_snapshot.db"

        def __exit__(self, exc_type, exc, tb):
            assert calls["closed"] == 1
            return False

    monkeypatch.setattr(worker_module, "AppController", _FakeController)
    monkeypatch.setattr(worker_module, "worker_db_snapshot", lambda *args, **kwargs: _SnapshotCtx())
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
