# TempleManager Offline DB Migrations

This folder contains reusable offline migration tooling for SQLite application DBs.

## Current migration

`v20260608_main_to_current` migrates the main branch DB schema to the current schema.

Schema additions:

```text
activity_signups
+ prayer TEXT
+ receipt_method TEXT DEFAULT 'ELECTRONIC'
+ paper_receipt_number TEXT

lighting_signups
+ receipt_method TEXT DEFAULT 'ELECTRONIC'
+ paper_receipt_number TEXT

transactions
+ payment_method TEXT DEFAULT 'cash'
+ transfer_last5 TEXT
+ receipt_method TEXT DEFAULT 'ELECTRONIC'
+ paper_receipt_number TEXT
```

For rows created before these columns existed, payment method defaults to `cash`, receipt method
defaults to `ELECTRONIC`, and transfer/paper receipt details default to `NULL`.

Worker log DB and mailer outbox DB are not part of this migration.

## Schema preflight

Before creating a backup or modifying the requested target, the migration compares every source
table and column with a temporary database initialized from the current application schema.

The migration stops with exit code `1` if any table or column exists only in the source. All
source-only entries are included in the error output.

Target-only tables and columns must be explicitly allowed by the selected migration version.
Unexpected additions stop the migration so that later application schema changes cannot silently
change the behavior of an existing migration version.

No target, backup, or report files are created or changed when this preflight fails.

## Validation

After copying and committing data, every migration runs mandatory validation:

- SQLite `PRAGMA integrity_check`
- SQLite `PRAGMA foreign_key_check`
- source and target row counts for every copied table
- primary key set equality for every copied table
- exact equality of every source column value, matched by primary key
- target `NOT NULL` columns
- transaction totals grouped by type
- signup payment transaction references
- migration-version-specific defaults for newly added columns

Validation reports include counts and at most 20 primary-key samples. Existing field values are not
included, avoiding unnecessary personal or financial data in reports.

If validation fails, the target is retained for investigation, `success` is `false`, and the CLI
returns exit code `2`. The target must not be used by the application.

## Dry run

```bash
python -m migrations.migrate \
  --source /path/to/old.db \
  --target /path/to/new.db \
  --version v20260608_main_to_current \
  --backup-dir /path/to/backups \
  --report-dir /path/to/reports \
  --dry-run
```

Dry run creates a temporary target DB, performs the full copy and validation flow, writes reports,
and does not overwrite the requested target path.

## Production run

Stop the old app first, then run:

```bash
python -m migrations.migrate \
  --source /path/to/old.db \
  --target /path/to/new.db \
  --version v20260608_main_to_current \
  --backup-dir /path/to/backups \
  --report-dir /path/to/reports
```

If the target DB already exists and must be rebuilt, pass `--replace-target`.

## Rollback

The migration never modifies the source DB. It also creates a source backup before copying data.
If validation fails, keep using the old DB or restore from the generated backup.

## Adding future migrations

Keep the shared framework in place and add a new version file:

```text
migrations/versions/vYYYYMMDD_description.py
```

Each version file should define `MIGRATION = MigrationSpec(...)` with table selection,
new-column defaults, transforms, and version-specific validators when needed.
