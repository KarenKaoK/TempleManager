from __future__ import annotations

from migrations.engine import MigrationSpec


MIGRATION = MigrationSpec(
    name="v20260608_main_to_current",
    column_defaults={
        "activity_signups": {"prayer": None},
        "transactions": {"payment_method": "cash", "transfer_last5": None},
    },
)
