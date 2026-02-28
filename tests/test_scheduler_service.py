import app.scheduler.service as service_module


def test_scheduler_service_start_and_stop(monkeypatch):
    called = {"start": 0, "shutdown": 0}
    logs = {"data": [], "system": []}

    class _FakeScheduler:
        def __init__(self):
            self.running = False

        def start(self):
            self.running = True
            called["start"] += 1

        def shutdown(self, wait=False):
            self.running = False
            called["shutdown"] += 1

    fake_sched = _FakeScheduler()

    def _fake_create_scheduler(config_path, feature_flags, db_path_override):
        return fake_sched, {
            "config_file": config_path,
            "db_path": db_path_override or "x.db",
            "timezone": "Asia/Taipei",
            "mail_enabled": bool((feature_flags or {}).get("mail_enabled", True)),
            "backup_enabled": bool((feature_flags or {}).get("backup_enabled", True)),
        }

    monkeypatch.setattr(service_module, "create_scheduler", _fake_create_scheduler)
    monkeypatch.setattr(
        service_module,
        "log_data_change",
        lambda **kwargs: logs["data"].append(kwargs),
    )
    monkeypatch.setattr(
        service_module,
        "log_system",
        lambda message, level="INFO": logs["system"].append({"message": message, "level": level}),
    )

    svc = service_module.SchedulerService(
        config_path="app/scheduler/scheduler_config.yaml",
        feature_flags={"mail_enabled": True, "backup_enabled": True},
        db_path_override="test.db",
    )
    assert svc.is_running is False
    svc.start()
    assert svc.is_running is True
    assert called["start"] == 1
    svc.stop()
    assert svc.is_running is False
    assert called["shutdown"] == 1
    assert any(item.get("action") == "SCHEDULER.SERVICE.START" for item in logs["data"])
    assert any(item.get("action") == "SCHEDULER.SERVICE.STOP" for item in logs["data"])


def test_scheduler_service_reload_applies_new_feature_flags(monkeypatch):
    called = {"start": 0, "shutdown": 0, "flags": []}

    class _FakeScheduler:
        def __init__(self):
            self.running = False

        def start(self):
            self.running = True
            called["start"] += 1

        def shutdown(self, wait=False):
            self.running = False
            called["shutdown"] += 1

    def _fake_create_scheduler(config_path, feature_flags, db_path_override):
        called["flags"].append(dict(feature_flags or {}))
        return _FakeScheduler(), {
            "config_file": config_path,
            "db_path": db_path_override or "x.db",
            "timezone": "Asia/Taipei",
            "mail_enabled": bool((feature_flags or {}).get("mail_enabled", True)),
            "backup_enabled": bool((feature_flags or {}).get("backup_enabled", True)),
        }

    monkeypatch.setattr(service_module, "create_scheduler", _fake_create_scheduler)

    svc = service_module.SchedulerService(feature_flags={"mail_enabled": True, "backup_enabled": True})
    svc.start()
    svc.reload(feature_flags={"mail_enabled": False, "backup_enabled": True})

    assert called["start"] == 2
    assert called["shutdown"] == 1
    assert called["flags"][0]["mail_enabled"] is True
    assert called["flags"][1]["mail_enabled"] is False


def test_scheduler_service_reload_can_update_config_path(monkeypatch):
    called = {"config_paths": []}

    class _FakeScheduler:
        def __init__(self):
            self.running = False

        def start(self):
            self.running = True

        def shutdown(self, wait=False):
            self.running = False

    def _fake_create_scheduler(config_path, feature_flags, db_path_override):
        called["config_paths"].append(config_path)
        return _FakeScheduler(), {
            "config_file": config_path,
            "db_path": db_path_override or "x.db",
            "timezone": "Asia/Taipei",
            "mail_enabled": True,
            "backup_enabled": True,
        }

    monkeypatch.setattr(service_module, "create_scheduler", _fake_create_scheduler)

    svc = service_module.SchedulerService(config_path="a.yaml")
    svc.start()
    svc.reload(config_path="b.yaml")

    assert called["config_paths"] == ["a.yaml", "b.yaml"]
