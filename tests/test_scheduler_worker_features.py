from pathlib import Path

import app.scheduler.worker as worker_module
from app.scheduler import worker_log_db


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


def test_create_scheduler_mail_job_does_not_require_undefined_connect(monkeypatch, tmp_path):
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

    sent = {"count": 0}

    class _SnapshotCtx:
        def __enter__(self):
            return str((tmp_path / "worker_snapshot.db").resolve())

        def __exit__(self, exc_type, exc, tb):
            return False

    class _Conn:
        def close(self):
            return None

    class _FakeController:
        def __init__(self, db_path=None):
            self.conn = _Conn()

        def get_scheduler_mail_credentials(self):
            return ("user@gmail.com", "pwd")

    monkeypatch.setattr(worker_module, "load_cfg", lambda _path: cfg)
    monkeypatch.setattr(worker_module, "worker_db_snapshot", lambda *args, **kwargs: _SnapshotCtx())
    monkeypatch.setattr(worker_module, "AppController", _FakeController)
    monkeypatch.setattr(worker_module, "_insert_worker_email_outbox", lambda **kwargs: 1)
    monkeypatch.setattr(
        worker_module,
        "send_email_smtp",
        lambda *args, **kwargs: sent.__setitem__("count", sent["count"] + 1),
    )
    monkeypatch.setattr(worker_module, "log_data_change", lambda **kwargs: None)
    monkeypatch.setattr(worker_module, "log_system", lambda *args, **kwargs: None)

    sched, _runtime = worker_module.create_scheduler(
        config_path="app/scheduler/scheduler_config.yaml",
        feature_flags={"mail_enabled": True, "backup_enabled": False},
    )
    job = sched.get_job("mail_job_1")
    job.func(*job.args, **job.kwargs)

    assert sent["count"] == 1


def test_main_uses_scheduler_settings_from_controller(monkeypatch):
    calls = {}
    monkeypatch.setattr(worker_log_db, "DATA_DIR", __import__("pathlib").Path("/tmp/templemanager_worker_feature_1"))

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

        def get_backup_settings(self):
            return {
                "enabled": True,
                "frequency": "daily",
                "time": "23:00",
                "weekday": 1,
                "monthday": 1,
                "last_scheduled_run_at": "",
            }

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

        def get_backup_settings(self):
            return {
                "enabled": True,
                "frequency": "daily",
                "time": "23:00",
                "weekday": 1,
                "monthday": 1,
                "last_scheduled_run_at": "",
            }

        def get_backup_settings(self):
            return {
                "enabled": True,
                "frequency": "daily",
                "time": "23:00",
                "weekday": 1,
                "monthday": 1,
                "last_scheduled_run_at": "",
            }

        def get_backup_settings(self):
            return {
                "enabled": True,
                "frequency": "daily",
                "time": "23:00",
                "weekday": 1,
                "monthday": 1,
                "last_scheduled_run_at": "",
            }

        def get_backup_settings(self):
            return {
                "enabled": True,
                "frequency": "daily",
                "time": "23:00",
                "weekday": 1,
                "monthday": 1,
                "last_scheduled_run_at": "",
            }

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
    monkeypatch.setattr(worker_log_db, "DATA_DIR", __import__("pathlib").Path("/tmp/templemanager_worker_feature_2"))

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

        def get_backup_settings(self):
            return {
                "enabled": True,
                "frequency": "daily",
                "time": "23:00",
                "weekday": 1,
                "monthday": 1,
                "last_scheduled_run_at": "",
            }

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
    monkeypatch.setattr(worker_log_db, "DATA_DIR", __import__("pathlib").Path("/tmp/templemanager_worker_feature_3"))

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

        def get_backup_settings(self):
            return {
                "enabled": True,
                "frequency": "daily",
                "time": "23:00",
                "weekday": 1,
                "monthday": 1,
                "last_scheduled_run_at": "",
            }

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


def test_main_reloads_scheduler_when_reload_requested(monkeypatch):
    calls = {"configs": [], "starts": 0, "shutdowns": 0, "bootstrap": 0}
    monkeypatch.setattr(worker_log_db, "DATA_DIR", __import__("pathlib").Path("/tmp/templemanager_worker_feature_reload"))

    class _Conn:
        def close(self):
            return None

    class _FakeController:
        def __init__(self, db_path=None):
            self.conn = _Conn()
            self.db_path = db_path or "/tmp/fake.db"
            calls["bootstrap"] += 1

        def get_scheduler_config_path(self):
            return "b.yaml" if calls["bootstrap"] >= 2 else "a.yaml"

        def get_scheduler_feature_settings(self):
            if calls["bootstrap"] >= 2:
                return {"mail_enabled": False, "backup_enabled": True}
            return {"mail_enabled": True, "backup_enabled": True}

        def get_backup_settings(self):
            return {
                "enabled": True,
                "frequency": "daily",
                "time": "23:00",
                "weekday": 1,
                "monthday": 1,
                "last_scheduled_run_at": "",
            }

    class _FakeScheduler:
        def __init__(self):
            self.running = False

        def start(self):
            self.running = True
            calls["starts"] += 1

        def shutdown(self):
            self.running = False
            calls["shutdowns"] += 1

    class _SnapshotCtx:
        def __enter__(self):
            return "/tmp/worker_snapshot.db"

        def __exit__(self, exc_type, exc, tb):
            return False

    def _fake_create_scheduler(config_path, feature_flags=None, db_path_override=None):
        calls["configs"].append((config_path, dict(feature_flags or {})))
        return (
            _FakeScheduler(),
            {
                "config_file": config_path,
                "db_path": db_path_override,
                "timezone": "Asia/Taipei",
                "mail_enabled": bool((feature_flags or {}).get("mail_enabled", True)),
                "backup_enabled": bool((feature_flags or {}).get("backup_enabled", True)),
            },
        )

    sleep_calls = {"n": 0}

    def _fake_sleep(_seconds):
        sleep_calls["n"] += 1
        if sleep_calls["n"] == 1:
            conn = worker_log_db.connect()
            try:
                worker_log_db.ensure_schema(conn)
                worker_log_db.request_reload(conn)
            finally:
                conn.close()
            return None
        raise KeyboardInterrupt()

    monkeypatch.setattr(worker_module, "AppController", _FakeController)
    monkeypatch.setattr(worker_module, "worker_db_snapshot", lambda *args, **kwargs: _SnapshotCtx())
    monkeypatch.setattr(worker_module, "create_scheduler", _fake_create_scheduler)
    monkeypatch.setattr(worker_module.time, "sleep", _fake_sleep)

    assert worker_module.main() == 0
    assert calls["configs"][0][0] == "a.yaml"
    assert calls["configs"][1][0] == "b.yaml"
    assert calls["configs"][1][1]["mail_enabled"] is False
    assert calls["starts"] == 2
    assert calls["shutdowns"] >= 2
