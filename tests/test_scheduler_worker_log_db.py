from app.scheduler import worker_log_db


def test_worker_log_db_insert_event(tmp_path, monkeypatch):
    monkeypatch.setattr(worker_log_db, "DATA_DIR", tmp_path)
    conn = worker_log_db.connect()
    try:
        worker_log_db.ensure_schema(conn)
        row_id = worker_log_db.insert_event(
            conn,
            level="INFO",
            action="WORKER.TEST",
            message="hello",
            job_id="bootstrap",
        )
        row = conn.execute(
            "SELECT level, action, job_id, message FROM worker_event_logs WHERE id = ?",
            (row_id,),
        ).fetchone()
        assert row["level"] == "INFO"
        assert row["action"] == "WORKER.TEST"
        assert row["job_id"] == "bootstrap"
        assert row["message"] == "hello"
    finally:
        conn.close()


def test_worker_log_db_insert_email_outbox_and_backup_log(tmp_path, monkeypatch):
    monkeypatch.setattr(worker_log_db, "DATA_DIR", tmp_path)
    conn = worker_log_db.connect()
    try:
        worker_log_db.ensure_schema(conn)
        email_id = worker_log_db.insert_email_outbox(
            conn,
            job_id="heartbeat",
            to_emails="a@example.com,b@example.com",
            subject="s",
            body="b",
            attachments="f1.csv",
            status="SENT",
            error="",
        )
        backup_id = worker_log_db.insert_backup_log(
            conn,
            job_id="backup_check",
            status="SKIPPED",
            detail="db_path=/tmp/fake.db",
        )
        email_row = conn.execute(
            "SELECT job_id, status FROM worker_email_outbox WHERE id = ?",
            (email_id,),
        ).fetchone()
        backup_row = conn.execute(
            "SELECT job_id, status FROM worker_backup_logs WHERE id = ?",
            (backup_id,),
        ).fetchone()
        assert email_row["job_id"] == "heartbeat"
        assert email_row["status"] == "SENT"
        assert backup_row["job_id"] == "backup_check"
        assert backup_row["status"] == "SKIPPED"
    finally:
        conn.close()
