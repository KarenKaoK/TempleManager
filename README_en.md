# TempleManager

![TempleManager Demo](assets/temple_management.gif)

TempleManager is a desktop application for temple administration, including believer records, activity registration, lighting registration, finance tracking, backups, and scheduled email reports.

## Highlights

- Role-based access control for administrator, accountant, committee member, and staff
- Believer / household management
- Activity setup and signup management
- Lighting setup and signup management
- Income / expense entry and finance reports
- Local and Google Drive backup support
- Scheduled email reports through an external worker process

## Requirements

- Python 3.8+
- macOS / Windows / Linux

## Installation

```bash
python3 -m venv temple_venv
source ./temple_venv/bin/activate
pip install --upgrade pip
pip install --only-binary=:all: -r requirements.txt
```

On Windows:

```bash
temple_venv\Scripts\activate
pip install --upgrade pip
pip install --only-binary=:all: -r requirements.txt
```

## Run the App

```bash
./temple_venv/bin/python -m app.main
```

On Windows:

```bash
temple_venv\Scripts\python.exe -m app.main
```

## Local Data Protection

- On Windows and macOS, the app stores the long-term database as an encrypted file.
- A runtime plaintext database is only prepared when needed.
- The app re-encrypts the runtime database when the application closes.

## Scheduler and Email Reports

The main application currently does not auto-start the internal scheduler during login flow.
Production scheduling should use the external worker:

```bash
python -m app.scheduler.worker
```

The scheduler config file is stored externally. On first use, the app copies the built-in template `scheduler_config.yaml` into the user data directory. Users can also choose another external config file from the report schedule settings dialog.
For Windows, you can use [`scripts/start_worker.example.bat`](/Users/huangrensyuan/Desktop/codes/TempleManager/scripts/start_worker.example.bat) as a reference launcher. It also writes console output to `worker_stdout.log` in the project root.
At startup, the worker prepares the runtime DB for the real application data and loads the scheduler config path / feature flags saved by the app. If it cannot load the real app settings, it now fails fast instead of silently falling back to the repo-local `app/database/temple.db`.

### Windows

Use Task Scheduler to keep the worker running in the background.
Prefer "Create Task" instead of "Create Basic Task".

Suggested command:

```bash
temple_venv\Scripts\python.exe -m app.scheduler.worker
```

Set `Start in` to the project root directory.
If you store the Gmail account and App Password from the UI, the Task Scheduler job must run under the same Windows user that originally stored that secret in Credential Manager.

### macOS

Use `launchd` to keep the worker running in the background.

Suggested command:

```bash
./temple_venv/bin/python -m app.scheduler.worker
```

Set `WorkingDirectory` to the project root directory.

## Backups

- Local backup
- Google Drive backup through OAuth
- Backup settings are managed from the system administration area

## Testing

```bash
./temple_venv/bin/python -m pytest -q
```

## Logs

- The application log file is stored in the user data directory as `log.log` (next to the main app data / DB).
- Log lines are encrypted at rest line by line.
- The system log viewer loads the most recent 1000 lines by default for better performance.
- Use "Load All" in the log viewer if you need the full history.
- If a specific line cannot be decrypted, it will be shown as `[UNREADABLE LOG LINE]`.
- If you launch the worker from a Windows `.bat` file, you may also keep `worker_stdout.log` in the project root as plain-text console diagnostics; it does not replace `log.log`.
- If you launch the worker from a Windows `.bat` file, you may also keep `%LOCALAPPDATA%\TempleManager\worker_stdout.log` as plain-text console diagnostics; it does not replace `log.log`.

## Notes

- Do not enable both the external worker and the internal app scheduler entry at the same time.
- If you update `scheduler_config.yaml`, the external worker will use the updated configuration.
- The built-in `app/scheduler/scheduler_config.yaml` is only the template/default source; production worker execution should use the external config path saved by the app.
