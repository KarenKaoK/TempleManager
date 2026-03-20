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


def test_read_log_tail_text_returns_recent_lines_only(tmp_path, monkeypatch):
    log_path = tmp_path / "log.log"
    monkeypatch.setattr(base_logger, "LOG_FILE_PATH", log_path)
    key = Fernet.generate_key()
    monkeypatch.setattr(base_logger, "_get_or_create_log_fernet_key", lambda: key)

    for idx in range(5):
        base_logger.write_log(level="INFO", tag="SYSTEM", message=f"line-{idx}")

    text = base_logger.read_log_tail_text(2)

    assert "line-4" in text
    assert "line-3" in text
    assert "line-0" not in text


def test_write_log_sanitizes_exception_like_secret_formats(tmp_path, monkeypatch):
    log_path = tmp_path / "log.log"
    monkeypatch.setattr(base_logger, "LOG_FILE_PATH", log_path)
    key = Fernet.generate_key()
    monkeypatch.setattr(base_logger, "_get_or_create_log_fernet_key", lambda: key)

    msg = (
        "Google OAuth failed: {'refresh_token':'rt_123', 'access_token': 'at_456', "
        "'client_secret':\"cs_789\"}, Authorization: Bearer bearer_token_001, "
        "redirect_uri?code=abc999&access_token=tok999"
    )
    base_logger.write_log(level="ERROR", tag="SYSTEM", message=msg)
    text = base_logger.read_log_text()

    assert "rt_123" not in text
    assert "at_456" not in text
    assert "cs_789" not in text
    assert "bearer_token_001" not in text
    assert "abc999" not in text
    assert "tok999" not in text
    assert text.count("[REDACTED]") >= 4
