import sqlite3
from pathlib import Path

import pytest
import migrations.engine as migration_engine

from migrations.engine import MigrationOptions, run_migration
from migrations.schema_inventory import diff_inventories, inventory_database, list_user_tables
from migrations.validators import run_common_validations


def _create_old_main_schema_db(db_path: Path):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.executescript(
        """
        CREATE TABLE users (
            id TEXT PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            display_name TEXT,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL,
            is_active INTEGER DEFAULT 1,
            must_change_password INTEGER DEFAULT 0,
            password_changed_at TEXT,
            last_login_at TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE audit_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_type TEXT NOT NULL,
            actor_username TEXT NOT NULL,
            target_type TEXT NOT NULL DEFAULT 'USER',
            target_id TEXT,
            result TEXT NOT NULL DEFAULT 'SUCCESS',
            reason TEXT,
            detail TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE app_settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE backup_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            trigger_mode TEXT NOT NULL,
            status TEXT NOT NULL,
            backup_file TEXT,
            file_size_bytes INTEGER,
            error_message TEXT
        );
        CREATE TABLE income_items (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            amount REAL DEFAULT 0,
            is_active INTEGER DEFAULT 1
        );
        CREATE TABLE expense_items (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            amount INTEGER DEFAULT 0,
            is_active INTEGER DEFAULT 1
        );
        CREATE TABLE member_identity (
            id TEXT PRIMARY KEY,
            name TEXT UNIQUE NOT NULL
        );
        CREATE TABLE people (
            id TEXT PRIMARY KEY,
            household_id TEXT NOT NULL,
            role_in_household TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'ACTIVE',
            name TEXT NOT NULL,
            gender TEXT,
            birthday_ad TEXT,
            birthday_lunar TEXT,
            lunar_is_leap INTEGER DEFAULT 0,
            birth_time TEXT,
            age INTEGER,
            age_offset INTEGER DEFAULT 0,
            zodiac TEXT,
            phone_home TEXT,
            phone_mobile TEXT,
            address TEXT,
            zip_code TEXT,
            note TEXT,
            joined_at TEXT
        );
        CREATE TABLE activities (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            activity_start_date TEXT NOT NULL,
            activity_end_date TEXT NOT NULL,
            note TEXT,
            status INTEGER DEFAULT 1,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE activity_plans (
            id TEXT PRIMARY KEY,
            activity_id TEXT NOT NULL,
            name TEXT NOT NULL,
            items TEXT,
            price_type TEXT NOT NULL,
            fixed_price INTEGER DEFAULT 0,
            note TEXT,
            suggested_price INTEGER DEFAULT 0,
            min_price INTEGER DEFAULT 0,
            allow_qty INTEGER DEFAULT 1,
            sort_order INTEGER DEFAULT 0,
            is_active INTEGER DEFAULT 1,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE activity_signups (
            id TEXT PRIMARY KEY,
            activity_id TEXT NOT NULL,
            person_id TEXT NOT NULL,
            group_id TEXT NOT NULL,
            signup_kind TEXT NOT NULL DEFAULT 'INITIAL',
            signup_time TEXT NOT NULL,
            note TEXT,
            total_amount INTEGER NOT NULL DEFAULT 0,
            is_paid INTEGER DEFAULT 0,
            paid_at TEXT,
            payment_txn_id INTEGER,
            payment_receipt_number TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE activity_signup_plans (
            id TEXT PRIMARY KEY,
            signup_id TEXT NOT NULL,
            plan_id TEXT NOT NULL,
            qty INTEGER NOT NULL DEFAULT 1,
            unit_price_snapshot INTEGER NOT NULL DEFAULT 0,
            amount_override INTEGER,
            line_total INTEGER NOT NULL DEFAULT 0,
            note TEXT
        );
        CREATE TABLE transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            type TEXT NOT NULL,
            category_id TEXT NOT NULL,
            category_name TEXT,
            amount INTEGER DEFAULT 0,
            payer_person_id TEXT,
            payer_name TEXT,
            handler TEXT,
            receipt_number TEXT,
            note TEXT,
            is_voided INTEGER DEFAULT 0,
            source_type TEXT,
            source_id TEXT,
            adjustment_kind TEXT,
            adjusts_txn_id INTEGER,
            is_system_generated INTEGER DEFAULT 0,
            is_deleted INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE lighting_items (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            fee INTEGER NOT NULL DEFAULT 0,
            kind TEXT NOT NULL DEFAULT 'JI_XIANG',
            sort_order INTEGER DEFAULT 0,
            is_active INTEGER DEFAULT 1,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE lighting_signups (
            id TEXT PRIMARY KEY,
            signup_year INTEGER NOT NULL,
            person_id TEXT NOT NULL,
            group_id TEXT NOT NULL,
            signup_kind TEXT NOT NULL DEFAULT 'INITIAL',
            total_amount INTEGER NOT NULL DEFAULT 0,
            note TEXT,
            is_paid INTEGER DEFAULT 0,
            paid_at TEXT,
            payment_txn_id INTEGER,
            payment_receipt_number TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE lighting_signup_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            signup_id TEXT NOT NULL,
            lighting_item_id TEXT NOT NULL,
            lighting_item_name TEXT NOT NULL,
            fee_snapshot INTEGER NOT NULL DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(signup_id, lighting_item_id)
        );
        """
    )
    cur.execute("INSERT INTO users (id, username, password_hash, role) VALUES ('U1', 'admin', 'x', '管理員')")
    cur.execute("INSERT INTO app_settings (key, value) VALUES ('security/idle_logout_minutes', '15')")
    cur.execute("INSERT INTO income_items (id, name, amount) VALUES ('90', '活動收入', 0)")
    cur.execute("INSERT INTO expense_items (id, name, amount) VALUES ('E01', '採買', 0)")
    cur.execute("INSERT INTO member_identity (id, name) VALUES ('M01', '信徒')")
    cur.execute(
        """
        INSERT INTO people (id, household_id, role_in_household, status, name)
        VALUES ('P1', 'H1', 'HEAD', 'ACTIVE', '王小明')
        """
    )
    cur.execute(
        """
        INSERT INTO activities (id, name, activity_start_date, activity_end_date)
        VALUES ('A1', '法會', '2026-01-01', '2026-01-01')
        """
    )
    cur.execute(
        """
        INSERT INTO activity_plans (id, activity_id, name, price_type)
        VALUES ('AP1', 'A1', '隨喜', 'FREE')
        """
    )
    cur.execute(
        """
        INSERT INTO transactions (
            id, date, type, category_id, category_name, amount,
            payer_person_id, payer_name, handler, receipt_number, source_type, source_id
        ) VALUES (1, '2026-01-01', 'income', '90', '活動收入', 1200,
            'P1', '王小明', '櫃台A', '1150001', 'ACTIVITY_SIGNUP', 'S1')
        """
    )
    cur.execute(
        """
        INSERT INTO activity_signups (
            id, activity_id, person_id, group_id, signup_time,
            total_amount, is_paid, payment_txn_id, payment_receipt_number
        ) VALUES ('S1', 'A1', 'P1', 'G1', '2026-01-01 09:00:00',
            1200, 1, 1, '1150001')
        """
    )
    cur.execute(
        """
        INSERT INTO activity_signup_plans (
            id, signup_id, plan_id, qty, unit_price_snapshot, line_total
        ) VALUES ('ASP1', 'S1', 'AP1', 1, 1200, 1200)
        """
    )
    cur.execute("INSERT INTO lighting_items (id, name, fee) VALUES ('L01', '太歲燈', 500)")
    cur.execute(
        """
        INSERT INTO lighting_signups (id, signup_year, person_id, group_id, total_amount)
        VALUES ('LS1', 2026, 'P1', 'LG1', 500)
        """
    )
    cur.execute(
        """
        INSERT INTO lighting_signup_items (signup_id, lighting_item_id, lighting_item_name, fee_snapshot)
        VALUES ('LS1', 'L01', '太歲燈', 500)
        """
    )
    conn.commit()
    conn.close()


def test_schema_inventory_reports_current_added_columns(tmp_path):
    source = tmp_path / "old.db"
    target = tmp_path / "new.db"
    _create_old_main_schema_db(source)

    from app.database.setup_db import initialize_database

    initialize_database(str(target))
    diff = diff_inventories(inventory_database(str(source)), inventory_database(str(target)))

    assert diff["column_diffs"]["activity_signups"]["added_in_target"] == [
        "paper_receipt_number",
        "prayer",
        "receipt_method",
    ]
    assert diff["column_diffs"]["lighting_signups"]["added_in_target"] == [
        "paper_receipt_number",
        "receipt_method",
    ]
    assert diff["column_diffs"]["transactions"]["added_in_target"] == [
        "paper_receipt_number",
        "payment_method",
        "receipt_method",
        "transfer_last5",
    ]


def test_main_to_current_migration_copies_data_and_defaults(tmp_path):
    source = tmp_path / "old.db"
    target = tmp_path / "new.db"
    backup_dir = tmp_path / "backups"
    report_dir = tmp_path / "reports"
    _create_old_main_schema_db(source)

    report = run_migration(
        MigrationOptions(
            source=str(source),
            target=str(target),
            version="v20260608_main_to_current",
            backup_dir=str(backup_dir),
            report_dir=str(report_dir),
        )
    )

    assert report["success"] is True
    assert Path(report["backup"]).is_file()
    assert Path(report["report_files"]["json"]).is_file()
    assert Path(report["report_files"]["text"]).is_file()

    conn = sqlite3.connect(target)
    conn.row_factory = sqlite3.Row
    try:
        tx = conn.execute(
            """
            SELECT payment_method, transfer_last5, receipt_method, paper_receipt_number
            FROM transactions
            WHERE id = 1
            """
        ).fetchone()
        assert tx["payment_method"] == "cash"
        assert tx["transfer_last5"] is None
        assert tx["receipt_method"] == "ELECTRONIC"
        assert tx["paper_receipt_number"] is None

        signup = conn.execute(
            """
            SELECT prayer, receipt_method, paper_receipt_number
            FROM activity_signups
            WHERE id = 'S1'
            """
        ).fetchone()
        assert signup["prayer"] is None
        assert signup["receipt_method"] == "ELECTRONIC"
        assert signup["paper_receipt_number"] is None

        assert conn.execute("SELECT COUNT(*) FROM activity_signups").fetchone()[0] == 1
        assert conn.execute("SELECT COUNT(*) FROM transactions").fetchone()[0] == 1
    finally:
        conn.close()


def test_dry_run_does_not_create_requested_target(tmp_path):
    source = tmp_path / "old.db"
    target = tmp_path / "new.db"
    _create_old_main_schema_db(source)

    report = run_migration(
        MigrationOptions(
            source=str(source),
            target=str(target),
            version="v20260608_main_to_current",
            backup_dir=str(tmp_path / "backups"),
            report_dir=str(tmp_path / "reports"),
            dry_run=True,
        )
    )

    assert report["success"] is True
    assert not target.exists()
    assert Path(report["backup"]).is_file()


def test_migration_rejects_source_only_schema_before_target_or_backup_changes(tmp_path):
    source = tmp_path / "old.db"
    target = tmp_path / "existing-target.db"
    backup_dir = tmp_path / "backups"
    report_dir = tmp_path / "reports"
    _create_old_main_schema_db(source)

    conn = sqlite3.connect(source)
    try:
        conn.execute("ALTER TABLE people ADD COLUMN legacy_code TEXT")
        conn.execute(
            """
            CREATE TABLE legacy_notes (
                id INTEGER PRIMARY KEY,
                content TEXT
            )
            """
        )
        conn.commit()
    finally:
        conn.close()

    original_target_content = b"existing target must remain unchanged"
    target.write_bytes(original_target_content)

    with pytest.raises(ValueError) as exc_info:
        run_migration(
            MigrationOptions(
                source=str(source),
                target=str(target),
                version="v20260608_main_to_current",
                backup_dir=str(backup_dir),
                report_dir=str(report_dir),
                replace_target=True,
            )
        )

    error_message = str(exc_info.value)
    assert "Migration preflight rejected incompatible schema entries" in error_message
    assert "source-only table: legacy_notes" in error_message
    assert "source-only column: people.legacy_code" in error_message
    assert target.read_bytes() == original_target_content
    assert not backup_dir.exists()
    assert not report_dir.exists()


def test_migration_rejects_unexpected_target_only_column_before_backup(
    tmp_path,
    monkeypatch,
):
    source = tmp_path / "old.db"
    target = tmp_path / "new.db"
    backup_dir = tmp_path / "backups"
    report_dir = tmp_path / "reports"
    _create_old_main_schema_db(source)

    original_initialize_database = migration_engine.initialize_database

    def initialize_with_unexpected_column(db_path):
        original_initialize_database(db_path)
        conn = sqlite3.connect(db_path)
        try:
            conn.execute("ALTER TABLE transactions ADD COLUMN currency TEXT")
            conn.commit()
        finally:
            conn.close()

    monkeypatch.setattr(
        migration_engine,
        "initialize_database",
        initialize_with_unexpected_column,
    )

    with pytest.raises(ValueError) as exc_info:
        run_migration(
            MigrationOptions(
                source=str(source),
                target=str(target),
                version="v20260608_main_to_current",
                backup_dir=str(backup_dir),
                report_dir=str(report_dir),
            )
        )

    assert "unexpected target-only column: transactions.currency" in str(exc_info.value)
    assert not target.exists()
    assert not backup_dir.exists()
    assert not report_dir.exists()


def test_common_validations_detect_row_primary_key_and_foreign_key_changes(tmp_path):
    source = tmp_path / "old.db"
    target = tmp_path / "new.db"
    _create_old_main_schema_db(source)

    report = run_migration(
        MigrationOptions(
            source=str(source),
            target=str(target),
            version="v20260608_main_to_current",
            backup_dir=str(tmp_path / "backups"),
            report_dir=str(tmp_path / "reports"),
        )
    )
    assert report["success"] is True

    target_conn = sqlite3.connect(target)
    try:
        target_conn.execute(
            "UPDATE people SET name = ? WHERE id = ?",
            ("被修改的姓名", "P1"),
        )
        target_conn.execute(
            "UPDATE expense_items SET id = ? WHERE id = ?",
            ("CHANGED", "E01"),
        )
        target_conn.execute(
            "UPDATE activity_signups SET person_id = ? WHERE id = ?",
            ("MISSING_PERSON", "S1"),
        )
        target_conn.commit()
    finally:
        target_conn.close()

    source_conn = sqlite3.connect(source)
    target_conn = sqlite3.connect(target)
    source_conn.row_factory = sqlite3.Row
    target_conn.row_factory = sqlite3.Row
    try:
        issues = run_common_validations(
            source_conn,
            target_conn,
            list_user_tables(source_conn),
        )
    finally:
        target_conn.close()
        source_conn.close()

    issue_types = {issue["type"] for issue in issues}
    assert "row_data_mismatch" in issue_types
    assert "primary_key_mismatch" in issue_types
    assert "foreign_key_violations" in issue_types

    row_issue = next(
        issue
        for issue in issues
        if issue["type"] == "row_data_mismatch" and issue["table"] == "people"
    )
    assert row_issue["samples"] == ["P1"]
