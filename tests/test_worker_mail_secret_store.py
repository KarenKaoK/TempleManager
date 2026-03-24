from app.utils import worker_mail_secret_store


def test_worker_mail_secret_path_uses_data_dir_for_runtime_db(tmp_path):
    runtime_db = tmp_path / "runtime" / "temple.db"
    runtime_db.parent.mkdir(parents=True, exist_ok=True)

    path = worker_mail_secret_store.worker_mail_secret_path(str(runtime_db))

    assert path == tmp_path / "worker_mail_secret.bin"


def test_worker_mail_secret_path_uses_db_parent_for_plain_db(tmp_path):
    db = tmp_path / "temple.db"

    path = worker_mail_secret_store.worker_mail_secret_path(str(db))

    assert path == tmp_path / "worker_mail_secret.bin"
