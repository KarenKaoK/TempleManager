from app.logging import base_logger
from cryptography.fernet import Fernet
import pytest


def test_write_log_redacts_sensitive_values(tmp_path, monkeypatch):
    log_path = tmp_path / "log.log"
    monkeypatch.setattr(base_logger, "LOG_FILE_PATH", log_path)
    key = Fernet.generate_key()
    monkeypatch.setattr(base_logger, "_get_or_create_log_fernet_key", lambda: key)

    base_logger.write_log(
        level="INFO",
        tag="SYSTEM",
        message=(
            "password=abc123 token:tok_xyz secret=s3cr3t "
            "authorization=BearerXYZ api_key=K001 id_number:A123456789 身分證字號:A123456789"
        ),
    )

    raw = log_path.read_text(encoding="utf-8")
    assert "abc123" not in raw
    assert "tok_xyz" not in raw
    assert "s3cr3t" not in raw
    assert "BearerXYZ" not in raw
    assert "K001" not in raw
    assert "A123456789" not in raw
    assert "[REDACTED]" not in raw

    decrypted = base_logger.read_log_text()
    assert "[REDACTED]" in decrypted


def test_write_log_attempts_to_harden_permissions(tmp_path, monkeypatch):
    log_path = tmp_path / "log.log"
    monkeypatch.setattr(base_logger, "LOG_FILE_PATH", log_path)
    key = Fernet.generate_key()
    monkeypatch.setattr(base_logger, "_get_or_create_log_fernet_key", lambda: key)

    called = {}

    def fake_chmod(path, mode):
        called["path"] = str(path)
        called["mode"] = mode

    monkeypatch.setattr(base_logger.os, "chmod", fake_chmod)

    base_logger.write_log(level="INFO", tag="DATA", message="一般訊息")
    assert called["path"] == str(log_path)
    assert called["mode"] == 0o600


def test_read_log_text_raises_when_ciphertext_invalid(tmp_path, monkeypatch):
    log_path = tmp_path / "log.log"
    monkeypatch.setattr(base_logger, "LOG_FILE_PATH", log_path)
    key = Fernet.generate_key()
    monkeypatch.setattr(base_logger, "_get_or_create_log_fernet_key", lambda: key)
    log_path.write_text("not-encrypted-line\n", encoding="utf-8")
    with pytest.raises(Exception):
        base_logger.read_log_text()
