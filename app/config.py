import os
from pathlib import Path
import platform
from platformdirs import user_data_dir
from typing import Optional

# 設定專案根目錄
BASE_DIR = str(Path(__file__).resolve().parent)

APP_NAME = "TempleManager"


def get_data_dir(app_name: str = APP_NAME) -> Path:
    # appauthor=False 可避免 Windows 產生 <AppAuthor>/<AppName> 雙層資料夾
    return Path(user_data_dir(app_name, appauthor=False))


def local_db_encryption_enabled() -> bool:
    if os.environ.get("TEMPLEMANAGER_DISABLE_LOCAL_DB_ENCRYPTION") == "1":
        return False
    if os.environ.get("TEMPLEMANAGER_DB_PATH"):
        return False
    sys_name = platform.system().lower()
    return sys_name.startswith("win") or sys_name == "darwin"


def resolve_db_name(data_dir: Optional[Path] = None) -> str:
    """
    DB 路徑優先順序：
    1) TEMPLEMANAGER_DB_PATH（手動覆蓋）
    2) Windows / macOS 啟用地端加密時，使用 runtime/temple.db
    3) 其他平台或未啟用時，使用使用者資料目錄中的 temple.db
    """
    env_db_path = os.environ.get("TEMPLEMANAGER_DB_PATH")
    if env_db_path:
        return str(Path(env_db_path))

    resolved_data_dir = Path(data_dir) if data_dir else get_data_dir()
    resolved_data_dir.mkdir(parents=True, exist_ok=True)
    if data_dir is None and local_db_encryption_enabled():
        return str(resolved_data_dir / "runtime" / "temple.db")
    return str(resolved_data_dir / "temple.db")


def resolve_encrypted_db_name(data_dir: Optional[Path] = None) -> str:
    resolved_data_dir = Path(data_dir) if data_dir else get_data_dir()
    resolved_data_dir.mkdir(parents=True, exist_ok=True)
    return str(resolved_data_dir / "temple.db.enc")


def resolve_legacy_plain_db_name(data_dir: Optional[Path] = None) -> str:
    resolved_data_dir = Path(data_dir) if data_dir else get_data_dir()
    resolved_data_dir.mkdir(parents=True, exist_ok=True)
    return str(resolved_data_dir / "temple.db")


DATA_DIR = get_data_dir()
DATA_DIR.mkdir(parents=True, exist_ok=True)

# 資料庫路徑（Windows / macOS 啟用地端加密時，此路徑為 runtime 明文 DB）
DB_NAME = resolve_db_name(data_dir=DATA_DIR)


# 預設使用者帳號
DEFAULT_USERS = [
    ("admin", "admin123", "管理員"),
    ("accountant", "acc123", "會計"),
    ("committee", "com123", "委員"),
    ("staff", "staff123", "工作人員")
]

# 角色類型
USER_ROLES = ('管理員', '會計', '委員', '工作人員')
