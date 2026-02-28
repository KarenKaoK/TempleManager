from __future__ import annotations

from typing import Dict, Optional

from app.logging import log_data_change, log_system
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
        try:
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
            try:
                log_data_change(
                    action="SCHEDULER.SERVICE.START",
                    message=(
                        "啟動排程服務（"
                        f"config {self._runtime.get('config_file')}，"
                        f"db_path {self._runtime.get('db_path')}，"
                        f"mail_enabled {int(bool(self._runtime.get('mail_enabled')))}，"
                        f"backup_enabled {int(bool(self._runtime.get('backup_enabled')))}）"
                    ),
                    level="INFO",
                )
            except Exception:
                pass
        except Exception as e:
            try:
                log_system(f"啟動排程服務失敗（原因：{e}）", level="ERROR")
            except Exception:
                pass
            raise

    def stop(self):
        if self._scheduler is None:
            return
        try:
            if getattr(self._scheduler, "running", False):
                self._scheduler.shutdown(wait=False)
                try:
                    log_data_change(
                        action="SCHEDULER.SERVICE.STOP",
                        message="停止排程服務（scheduler shutdown）",
                        level="INFO",
                    )
                except Exception:
                    pass
        finally:
            self._scheduler = None

    def reload(self, feature_flags: Optional[Dict[str, bool]] = None, config_path: Optional[str] = None):
        if feature_flags is not None:
            self.feature_flags = dict(feature_flags)
        if config_path is not None:
            self.config_path = str(config_path)
        try:
            self.stop()
            self.start()
            try:
                log_data_change(
                    action="SCHEDULER.SERVICE.RELOAD",
                    message=(
                        "重新載入排程服務（"
                        f"config {self.config_path}，"
                        f"mail_enabled {int(bool(self.feature_flags.get('mail_enabled', True)))}，"
                        f"backup_enabled {int(bool(self.feature_flags.get('backup_enabled', True)))}）"
                    ),
                    level="INFO",
                )
            except Exception:
                pass
        except Exception as e:
            try:
                log_system(f"重新載入排程服務失敗（原因：{e}）", level="ERROR")
            except Exception:
                pass
            raise

    @property
    def is_running(self) -> bool:
        return bool(self._scheduler is not None and getattr(self._scheduler, "running", False))

    @property
    def runtime_info(self) -> Dict[str, str]:
        return dict(self._runtime or {})
