from __future__ import annotations

import ctypes
import json
import os
import platform
import subprocess
import tempfile
import uuid
from pathlib import Path
from typing import Dict


SERVICE_NAME = "TempleManager"


class SecretStoreError(RuntimeError):
    pass


def backend_label() -> str:
    sys_name = platform.system().lower()
    if sys_name.startswith("win"):
        return "Windows Credential Manager"
    if sys_name == "darwin":
        return "macOS Keychain"
    return "Local File (development fallback)"


def _target_name(key: str) -> str:
    return f"{SERVICE_NAME}:{(key or '').strip()}"


def _is_windows() -> bool:
    return platform.system().lower().startswith("win")


def _is_macos() -> bool:
    return platform.system().lower() == "darwin"


def _fallback_file() -> Path:
    p = Path.home() / ".templemanager" / "secrets.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    if not p.exists():
        p.write_text("{}", encoding="utf-8")
        try:
            os.chmod(str(p), 0o600)
        except Exception:
            pass
    return p


def _read_fallback() -> Dict[str, str]:
    p = _fallback_file()
    try:
        data = json.loads(p.read_text(encoding="utf-8") or "{}")
        if isinstance(data, dict):
            return {str(k): str(v) for k, v in data.items()}
    except Exception:
        pass
    return {}


def _write_fallback(data: Dict[str, str]):
    p = _fallback_file()
    p.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    try:
        os.chmod(str(p), 0o600)
    except Exception:
        pass


def _win_set_secret(key: str, value: str):
    CRED_TYPE_GENERIC = 1
    CRED_PERSIST_LOCAL_MACHINE = 2

    class FILETIME(ctypes.Structure):
        _fields_ = [("dwLowDateTime", ctypes.c_uint32), ("dwHighDateTime", ctypes.c_uint32)]

    class CREDENTIALW(ctypes.Structure):
        _fields_ = [
            ("Flags", ctypes.c_uint32),
            ("Type", ctypes.c_uint32),
            ("TargetName", ctypes.c_wchar_p),
            ("Comment", ctypes.c_wchar_p),
            ("LastWritten", FILETIME),
            ("CredentialBlobSize", ctypes.c_uint32),
            ("CredentialBlob", ctypes.POINTER(ctypes.c_ubyte)),
            ("Persist", ctypes.c_uint32),
            ("AttributeCount", ctypes.c_uint32),
            ("Attributes", ctypes.c_void_p),
            ("TargetAlias", ctypes.c_wchar_p),
            ("UserName", ctypes.c_wchar_p),
        ]

    advapi32 = ctypes.WinDLL("Advapi32.dll")
    CredWriteW = advapi32.CredWriteW
    CredWriteW.argtypes = [ctypes.POINTER(CREDENTIALW), ctypes.c_uint32]
    CredWriteW.restype = ctypes.c_int

    target = _target_name(key)
    blob = (value or "").encode("utf-16-le")
    blob_buf = ctypes.create_string_buffer(blob)
    cred = CREDENTIALW()
    cred.Type = CRED_TYPE_GENERIC
    cred.TargetName = target
    cred.CredentialBlobSize = len(blob)
    cred.CredentialBlob = ctypes.cast(blob_buf, ctypes.POINTER(ctypes.c_ubyte))
    cred.Persist = CRED_PERSIST_LOCAL_MACHINE
    cred.UserName = target

    ok = CredWriteW(ctypes.byref(cred), 0)
    if not ok:
        err = ctypes.GetLastError()
        raise SecretStoreError(f"Windows Credential Manager 寫入失敗（錯誤碼: {err}）。")


def _win_get_secret(key: str) -> str:
    CRED_TYPE_GENERIC = 1
    ERROR_NOT_FOUND = 1168

    class FILETIME(ctypes.Structure):
        _fields_ = [("dwLowDateTime", ctypes.c_uint32), ("dwHighDateTime", ctypes.c_uint32)]

    class CREDENTIALW(ctypes.Structure):
        _fields_ = [
            ("Flags", ctypes.c_uint32),
            ("Type", ctypes.c_uint32),
            ("TargetName", ctypes.c_wchar_p),
            ("Comment", ctypes.c_wchar_p),
            ("LastWritten", FILETIME),
            ("CredentialBlobSize", ctypes.c_uint32),
            ("CredentialBlob", ctypes.POINTER(ctypes.c_ubyte)),
            ("Persist", ctypes.c_uint32),
            ("AttributeCount", ctypes.c_uint32),
            ("Attributes", ctypes.c_void_p),
            ("TargetAlias", ctypes.c_wchar_p),
            ("UserName", ctypes.c_wchar_p),
        ]

    PCREDENTIALW = ctypes.POINTER(CREDENTIALW)
    advapi32 = ctypes.WinDLL("Advapi32.dll")
    CredReadW = advapi32.CredReadW
    CredReadW.argtypes = [ctypes.c_wchar_p, ctypes.c_uint32, ctypes.c_uint32, ctypes.POINTER(PCREDENTIALW)]
    CredReadW.restype = ctypes.c_int
    CredFree = advapi32.CredFree
    CredFree.argtypes = [ctypes.c_void_p]
    CredFree.restype = None

    target = _target_name(key)
    pcred = PCREDENTIALW()
    ok = CredReadW(target, CRED_TYPE_GENERIC, 0, ctypes.byref(pcred))
    if not ok:
        err = ctypes.GetLastError()
        if err == ERROR_NOT_FOUND:
            return ""
        raise SecretStoreError(f"Windows Credential Manager 讀取失敗（錯誤碼: {err}）。")
    try:
        cred = pcred.contents
        if not cred.CredentialBlob or cred.CredentialBlobSize <= 0:
            return ""
        raw = ctypes.string_at(cred.CredentialBlob, cred.CredentialBlobSize)
        return raw.decode("utf-16-le")
    finally:
        CredFree(pcred)


def _win_delete_secret(key: str):
    CRED_TYPE_GENERIC = 1
    ERROR_NOT_FOUND = 1168
    advapi32 = ctypes.WinDLL("Advapi32.dll")
    CredDeleteW = advapi32.CredDeleteW
    CredDeleteW.argtypes = [ctypes.c_wchar_p, ctypes.c_uint32, ctypes.c_uint32]
    CredDeleteW.restype = ctypes.c_int

    target = _target_name(key)
    ok = CredDeleteW(target, CRED_TYPE_GENERIC, 0)
    if not ok:
        err = ctypes.GetLastError()
        if err != ERROR_NOT_FOUND:
            raise SecretStoreError(f"Windows Credential Manager 刪除失敗（錯誤碼: {err}）。")


def _mac_set_secret(key: str, value: str):
    p = subprocess.run(
        ["security", "add-generic-password", "-s", SERVICE_NAME, "-a", (key or "").strip(), "-w", value or "", "-U"],
        capture_output=True,
        text=True,
        check=False,
    )
    if p.returncode != 0:
        msg = (p.stderr or p.stdout or "").strip() or "未知錯誤"
        raise SecretStoreError(f"macOS Keychain 寫入失敗：{msg}")


def _mac_get_secret(key: str) -> str:
    p = subprocess.run(
        ["security", "find-generic-password", "-s", SERVICE_NAME, "-a", (key or "").strip(), "-w"],
        capture_output=True,
        text=True,
        check=False,
    )
    if p.returncode != 0:
        return ""
    return (p.stdout or "").strip()


def _mac_delete_secret(key: str):
    subprocess.run(
        ["security", "delete-generic-password", "-s", SERVICE_NAME, "-a", (key or "").strip()],
        capture_output=True,
        text=True,
        check=False,
    )


def validate_writable() -> None:
    probe_key = f"__probe__{uuid.uuid4().hex}"
    try:
        set_secret(probe_key, "ok")
    finally:
        try:
            delete_secret(probe_key)
        except Exception:
            pass


def set_secret(key: str, value: str):
    k = (key or "").strip()
    if not k:
        raise SecretStoreError("secret key 不可為空。")

    if _is_windows():
        _win_set_secret(k, value)
        return
    if _is_macos():
        _mac_set_secret(k, value)
        return

    data = _read_fallback()
    data[k] = str(value or "")
    _write_fallback(data)


def get_secret(key: str) -> str:
    k = (key or "").strip()
    if not k:
        return ""

    if _is_windows():
        return _win_get_secret(k)
    if _is_macos():
        return _mac_get_secret(k)

    return _read_fallback().get(k, "")


def delete_secret(key: str):
    k = (key or "").strip()
    if not k:
        return

    if _is_windows():
        _win_delete_secret(k)
        return
    if _is_macos():
        _mac_delete_secret(k)
        return

    data = _read_fallback()
    if k in data:
        del data[k]
        _write_fallback(data)


def has_secret(key: str) -> bool:
    try:
        return bool(get_secret(key))
    except Exception:
        return False
