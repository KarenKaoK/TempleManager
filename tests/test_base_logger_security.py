from app.logging import base_logger


def test_write_log_redacts_sensitive_values(tmp_path, monkeypatch):
    log_path = tmp_path / "log.log"
    monkeypatch.setattr(base_logger, "LOG_FILE_PATH", log_path)

    base_logger.write_log(
        level="INFO",
        tag="SYSTEM",
        message=(
            "password=abc123 token:tok_xyz secret=s3cr3t "
            "authorization=BearerXYZ api_key=K001 id_number:A123456789 身分證字號:A123456789"
        ),
    )

    content = log_path.read_text(encoding="utf-8")
    assert "abc123" not in content
    assert "tok_xyz" not in content
    assert "s3cr3t" not in content
    assert "BearerXYZ" not in content
    assert "K001" not in content
    assert "A123456789" not in content
    assert "[REDACTED]" in content


def test_write_log_attempts_to_harden_permissions(tmp_path, monkeypatch):
    log_path = tmp_path / "log.log"
    monkeypatch.setattr(base_logger, "LOG_FILE_PATH", log_path)

    called = {}

    def fake_chmod(path, mode):
        called["path"] = str(path)
        called["mode"] = mode

    monkeypatch.setattr(base_logger.os, "chmod", fake_chmod)

    base_logger.write_log(level="INFO", tag="DATA", message="一般訊息")
    assert called["path"] == str(log_path)
    assert called["mode"] == 0o600
