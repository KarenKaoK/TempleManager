import argparse
import sys

from app.controller.app_controller import AppController
from app.config import DB_NAME, DATA_DIR, local_db_encryption_enabled, resolve_encrypted_db_name, resolve_legacy_plain_db_name
from app.utils.local_db_store import ensure_runtime_db_ready, finalize_runtime_db


def main():
    if local_db_encryption_enabled():
        ensure_runtime_db_ready(
            runtime_db_path=DB_NAME,
            encrypted_db_path=resolve_encrypted_db_name(DATA_DIR),
            legacy_plain_db_path=resolve_legacy_plain_db_name(DATA_DIR),
        )

    parser = argparse.ArgumentParser(description="TempleManager backup scheduler runner")
    parser.add_argument("--run-once", action="store_true", help="run schedule check once (default)")
    parser.add_argument("--force", action="store_true", help="force backup once, ignore schedule condition")
    args = parser.parse_args()

    controller = AppController()
    try:
        if args.force:
            result = controller.create_local_backup(manual=False)
            controller.mark_backup_run(scheduled=True)
            print(f"[backup] SUCCESS(force): {result.get('backup_file')}")
            return 0

        ran = controller.run_scheduled_backup_once()
        if ran:
            print("[backup] SUCCESS: scheduled backup executed")
        else:
            print("[backup] SKIP: schedule condition not met")
        return 0
    except Exception as e:
        print(f"[backup] FAILED: {e}", file=sys.stderr)
        return 1
    finally:
        try:
            controller.conn.close()
        except Exception:
            pass
        if local_db_encryption_enabled():
            finalize_runtime_db(
                runtime_db_path=DB_NAME, encrypted_db_path=resolve_encrypted_db_name(DATA_DIR)
            )


if __name__ == "__main__":
    raise SystemExit(main())
