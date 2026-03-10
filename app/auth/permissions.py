ROLE_ADMIN = "管理員"
ROLE_ACCOUNTANT = "會計"
ROLE_STAFF = "工作人員"


def is_admin(role: str) -> bool:
    return (role or "").strip() == ROLE_ADMIN


def can_manage_accounts(role: str) -> bool:
    return (role or "").strip() == ROLE_ADMIN


def can_access_finance_report(role: str) -> bool:
    return (role or "").strip() in {ROLE_ADMIN, ROLE_ACCOUNTANT}


def can_view_expense_entry(role: str) -> bool:
    return (role or "").strip() in {ROLE_ADMIN, ROLE_ACCOUNTANT}


def can_view_income_all_dates(role: str) -> bool:
    return (role or "").strip() in {ROLE_ADMIN, ROLE_ACCOUNTANT}


def can_edit_any_date(role: str) -> bool:
    return can_view_income_all_dates(role)


def can_edit_handler(role: str) -> bool:
    return can_view_income_all_dates(role)


def can_edit_member(role: str) -> bool:
    return (role or "").strip() in {ROLE_ADMIN, ROLE_ACCOUNTANT}


def can_delete_household_head(role: str) -> bool:
    return (role or "").strip() in {ROLE_ADMIN, ROLE_ACCOUNTANT}
