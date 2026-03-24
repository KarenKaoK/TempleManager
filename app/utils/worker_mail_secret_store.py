from __future__ import annotations

import ctypes
import platform
from pathlib import Path
from typing import Optional

from app.config import DATA_DIR


class WorkerMailSecretError(RuntimeError):
    pass


def _is_windows() -> bool:
    return platform.system().lower().startswith("win")


class DATA_BLOB(ctypes.Structure):
    _fields_ = [
        ("cbData", ctypes.c_uint32),
        ("pbData", ctypes.POINTER(ctypes.c_ubyte)),
    ]


def _blob_from_bytes(data: bytes) -> DATA_BLOB:
    if not data:
        return DATA_BLOB(0, None)
    buf = ctypes.create_string_buffer(data)
    blob = DATA_BLOB()
    blob.cbData = len(data)
    blob.pbData = ctypes.cast(buf, ctypes.POINTER(ctypes.c_ubyte))
    blob._buffer = buf
    return blob


def _bytes_from_blob(blob: DATA_BLOB) -> bytes:
    if not blob.cbData or not blob.pbData:
        return b""
    return ctypes.string_at(blob.pbData, blob.cbData)


def _crypt_unprotect_data(token: bytes) -> bytes:
    if not _is_windows():
        raise WorkerMailSecretError("Background worker mail secret is only supported on Windows.")
    crypt32 = ctypes.windll.crypt32
    kernel32 = ctypes.windll.kernel32
    in_blob = _blob_from_bytes(token)
    out_blob = DATA_BLOB()
    ok = crypt32.CryptUnprotectData(
        ctypes.byref(in_blob),
        None,
        None,
        None,
        None,
        0,
        ctypes.byref(out_blob),
    )
    if not ok:
        err = ctypes.GetLastError()
        raise WorkerMailSecretError(f"Windows DPAPI 解密失敗（錯誤碼: {err}）。")
    try:
        return _bytes_from_blob(out_blob)
    finally:
        if out_blob.pbData:
            kernel32.LocalFree(out_blob.pbData)


def _crypt_protect_data(plain: bytes) -> bytes:
    if not _is_windows():
        raise WorkerMailSecretError("Background worker mail secret is only supported on Windows.")
    crypt32 = ctypes.windll.crypt32
    kernel32 = ctypes.windll.kernel32
    in_blob = _blob_from_bytes(plain)
    out_blob = DATA_BLOB()
    CRYPTPROTECT_LOCAL_MACHINE = 0x4
    ok = crypt32.CryptProtectData(
        ctypes.byref(in_blob),
        None,
        None,
        None,
        None,
        CRYPTPROTECT_LOCAL_MACHINE,
        ctypes.byref(out_blob),
    )
    if not ok:
        err = ctypes.GetLastError()
        raise WorkerMailSecretError(f"Windows DPAPI 加密失敗（錯誤碼: {err}）。")
    try:
        return _bytes_from_blob(out_blob)
    finally:
        if out_blob.pbData:
            kernel32.LocalFree(out_blob.pbData)


def _resolve_data_root(db_path: Optional[str] = None) -> Path:
    if not db_path:
        return Path(DATA_DIR)
    db = Path(db_path).resolve()
    if db.parent.name == "runtime":
        return db.parent.parent
    return db.parent


def worker_mail_secret_path(db_path: Optional[str] = None) -> Path:
    return _resolve_data_root(db_path) / "worker_mail_secret.bin"


def save_worker_mail_secret(secret: str, *, db_path: Optional[str] = None) -> None:
    if not _is_windows():
        return
    text = (secret or "").strip()
    if not text:
        return
    target = worker_mail_secret_path(db_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    token = _crypt_protect_data(text.encode("utf-8"))
    target.write_bytes(token)


def load_worker_mail_secret(*, db_path: Optional[str] = None) -> str:
    if not _is_windows():
        return ""
    target = worker_mail_secret_path(db_path)
    if not target.exists():
        return ""
    return _crypt_unprotect_data(target.read_bytes()).decode("utf-8").strip()
