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

### Windows

Use Task Scheduler to keep the worker running in the background.

Suggested command:

```bash
temple_venv\Scripts\python.exe -m app.scheduler.worker
```

Set `Start in` to the project root directory.

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

## Notes

- Do not enable both the external worker and the internal app scheduler entry at the same time.
- If you update `scheduler_config.yaml`, the external worker will use the updated configuration.
