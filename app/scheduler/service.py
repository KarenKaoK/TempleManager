from __future__ import annotations

from typing import Dict, Optional

from app.scheduler.worker import create_scheduler


class SchedulerService:
    def __init__(
        self,
        config_path: str = "app/scheduler/scheduler_config.yaml",
        feature_flags: Optional[Dict[str, bool]] = None,
        db_path_override: Optional[str] = None,
    ):
        self.config_path = config_path
        self.feature_flags = dict(feature_flags or {})
        self.db_path_override = db_path_override
        self._scheduler = None
        self._runtime = {}

    def start(self):
        if self._scheduler is not None and getattr(self._scheduler, "running", False):
            return
        self._scheduler, self._runtime = create_scheduler(
            config_path=self.config_path,
            feature_flags=self.feature_flags,
            db_path_override=self.db_path_override,
        )
        self._scheduler.start()
        print(
            f"[START] app scheduler service. "
            f"mail_enabled={self._runtime.get('mail_enabled')} "
            f"backup_enabled={self._runtime.get('backup_enabled')} "
            f"db={self._runtime.get('db_path')}"
        )

    def stop(self):
        if self._scheduler is None:
            return
        try:
            if getattr(self._scheduler, "running", False):
                self._scheduler.shutdown(wait=False)
        finally:
            self._scheduler = None

    def reload(self, feature_flags: Optional[Dict[str, bool]] = None, config_path: Optional[str] = None):
        if feature_flags is not None:
            self.feature_flags = dict(feature_flags)
        if config_path is not None:
            self.config_path = str(config_path)
        self.stop()
        self.start()

    @property
    def is_running(self) -> bool:
        return bool(self._scheduler is not None and getattr(self._scheduler, "running", False))

    @property
    def runtime_info(self) -> Dict[str, str]:
        return dict(self._runtime or {})
