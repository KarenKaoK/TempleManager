import argparse
import sys

from app.controller.app_controller import AppController


def main():
    parser = argparse.ArgumentParser(description="TempleManager backup scheduler runner")
    parser.add_argument("--run-once", action="store_true", help="run schedule check once (default)")
    parser.add_argument("--force", action="store_true", help="force backup once, ignore schedule condition")
    args = parser.parse_args()

    controller = AppController()
    try:
        if args.force:
            result = controller.create_local_backup(manual=False)
            controller.mark_backup_run()
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


if __name__ == "__main__":
    raise SystemExit(main())
