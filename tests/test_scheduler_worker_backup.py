import app.scheduler.worker as worker_module
from app.scheduler import worker_log_db


def test_run_backup_schedule_check_runs_controller_and_closes_conn(monkeypatch):
    called = {"run_once": 0, "closed": 0, "db_path": ""}
    logs = {"data": [], "system": []}
    monkeypatch.setattr(worker_log_db, "DATA_DIR", __import__("pathlib").Path("/tmp/templemanager_worker_test"))

    class _SnapshotCtx:
        def __enter__(self):
            return "/tmp/worker_backup_snapshot.db"

        def __exit__(self, exc_type, exc, tb):
            return False

    class _SnapshotCtx:
        def __enter__(self):
            return "/tmp/worker_backup_snapshot.db"

        def __exit__(self, exc_type, exc, tb):
            return False

    class _Conn:
        def close(self):
            called["closed"] += 1

    class _FakeController:
        def __init__(self, db_path=None):
            called["db_path"] = db_path
            self.conn = _Conn()

        def run_scheduled_backup_once(self):
            called["run_once"] += 1
            return True

    monkeypatch.setattr(worker_module, "worker_db_snapshot", lambda *args, **kwargs: _SnapshotCtx())
    monkeypatch.setattr(worker_module, "_worker_backup_should_run", lambda now=None: True)
    monkeypatch.setattr(worker_module, "AppController", _FakeController)
    monkeypatch.setattr(
        worker_module,
        "log_data_change",
        lambda **kwargs: logs["data"].append(kwargs),
    )
    monkeypatch.setattr(
        worker_module,
        "log_system",
        lambda message, level="INFO": logs["system"].append({"message": message, "level": level}),
    )
    worker_module.run_backup_schedule_check("/tmp/fake.db")

    assert called["db_path"] == "/tmp/worker_backup_snapshot.db"
    assert called["run_once"] == 1
    assert called["closed"] == 1
    assert any(item.get("action") == "SCHEDULER.BACKUP.CHECK" for item in logs["data"])


def test_run_backup_schedule_check_skips_without_snapshot_when_precheck_fails(monkeypatch):
    called = {"snapshot": 0}
    monkeypatch.setattr(worker_log_db, "DATA_DIR", __import__("pathlib").Path("/tmp/templemanager_worker_test_skip"))

    class _SnapshotCtx:
        def __enter__(self):
            called["snapshot"] += 1
            return "/tmp/worker_backup_snapshot.db"

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(worker_module, "worker_db_snapshot", lambda *args, **kwargs: _SnapshotCtx())
    monkeypatch.setattr(worker_module, "_worker_backup_should_run", lambda now=None: False)

    worker_module.run_backup_schedule_check("/tmp/fake.db")

    assert called["snapshot"] == 0
