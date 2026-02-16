from csv import writer
from datetime import date, datetime, timedelta

from PyQt5.QtCore import QDate
from PyQt5.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDateEdit,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)


class FinanceReportDialog(QDialog):
    def __init__(self, controller, parent=None):
        super().__init__(parent)
        self.controller = controller
        self.summary_rows = []
        self.detail_rows = []
        self.setWindowTitle("財務會計")
        self.resize(1200, 760)
        self._build_ui()
        self.run_query()

    def _build_ui(self):
        root = QVBoxLayout(self)

        filter_row = QHBoxLayout()

        self.granularity_combo = QComboBox()
        self.granularity_combo.addItem("日", "day")
        self.granularity_combo.addItem("週", "week")
        self.granularity_combo.addItem("月", "month")
        self.granularity_combo.addItem("年", "year")

        self.include_category_checkbox = QCheckBox("加入項目維度")
        self.include_category_checkbox.setChecked(False)

        today = QDate.currentDate()
        self.start_date = QDateEdit()
        self.start_date.setCalendarPopup(True)
        self.start_date.setDisplayFormat("yyyy/MM/dd")
        self.start_date.setDate(QDate(today.year(), today.month(), 1))

        self.end_date = QDateEdit()
        self.end_date.setCalendarPopup(True)
        self.end_date.setDisplayFormat("yyyy/MM/dd")
        self.end_date.setDate(today)

        self.btn_today = QPushButton("今日")
        self.btn_this_week = QPushButton("本週")
        self.btn_this_month = QPushButton("本月")
        self.btn_this_year = QPushButton("今年")
        self.btn_today.clicked.connect(self.set_range_today)
        self.btn_this_week.clicked.connect(self.set_range_this_week)
        self.btn_this_month.clicked.connect(self.set_range_this_month)
        self.btn_this_year.clicked.connect(self.set_range_this_year)

        query_btn = QPushButton("查詢")
        query_btn.clicked.connect(self.run_query)
        self.export_btn = QPushButton("匯出 Excel(CSV)")
        self.export_btn.clicked.connect(self.export_csv)

        filter_row.addWidget(QLabel("彙整粒度:"))
        filter_row.addWidget(self.granularity_combo)
        filter_row.addWidget(self.include_category_checkbox)
        filter_row.addWidget(QLabel("起日:"))
        filter_row.addWidget(self.start_date)
        filter_row.addWidget(QLabel("迄日:"))
        filter_row.addWidget(self.end_date)
        filter_row.addWidget(query_btn)
        filter_row.addWidget(self.btn_today)
        filter_row.addWidget(self.btn_this_week)
        filter_row.addWidget(self.btn_this_month)
        filter_row.addWidget(self.btn_this_year)
        filter_row.addWidget(self.export_btn)
        root.addLayout(filter_row)

        detail_action_row = QHBoxLayout()
        detail_action_row.addWidget(QLabel("摘要"))
        detail_action_row.addStretch()
        self.view_income_btn = QPushButton("查看收入明細")
        self.view_expense_btn = QPushButton("查看支出明細")
        self.view_income_btn.clicked.connect(lambda: self.load_detail_for_selected_row("income"))
        self.view_expense_btn.clicked.connect(lambda: self.load_detail_for_selected_row("expense"))
        detail_action_row.addWidget(self.view_income_btn)
        detail_action_row.addWidget(self.view_expense_btn)
        root.addLayout(detail_action_row)

        self.summary_table = QTableWidget(0, 0)
        self.summary_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.summary_table.setEditTriggers(QTableWidget.NoEditTriggers)
        root.addWidget(self.summary_table, 2)
        self.total_net_label = QLabel("本期收支結餘：0")
        self.total_net_label.setStyleSheet(
            "QLabel {"
            "border: 2px solid #C9A56A;"
            "background: #FFF7E8;"
            "border-radius: 8px;"
            "padding: 8px 12px;"
            "font-weight: 700;"
            "color: #7A4A14;"
            "}"
        )
        root.addWidget(self.total_net_label)

        root.addWidget(QLabel("細項"))
        self.detail_table = QTableWidget(0, 9)
        self.detail_table.setHorizontalHeaderLabels(
            ["日期", "類型", "單號", "項目代號", "項目名稱", "對象", "金額", "經手人", "摘要"]
        )
        self.detail_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.detail_table.setEditTriggers(QTableWidget.NoEditTriggers)
        root.addWidget(self.detail_table, 3)

        footer = QHBoxLayout()
        footer.addStretch()
        close_btn = QPushButton("關閉返回")
        close_btn.clicked.connect(self.accept)
        footer.addWidget(close_btn)
        root.addLayout(footer)

    def _db_date(self, qdate: QDate) -> str:
        return qdate.toString("yyyy-MM-dd")

    def _set_range_and_query(self, start: date, end: date):
        self.start_date.setDate(QDate(start.year, start.month, start.day))
        self.end_date.setDate(QDate(end.year, end.month, end.day))
        self.run_query()

    def set_range_today(self):
        today = date.today()
        self._set_range_and_query(today, today)

    def set_range_this_week(self):
        today = date.today()
        monday = today - timedelta(days=today.weekday())
        sunday = monday + timedelta(days=6)
        self._set_range_and_query(monday, sunday)

    def set_range_this_month(self):
        today = date.today()
        first_day = today.replace(day=1)
        next_month = date(today.year + (today.month // 12), ((today.month % 12) + 1), 1)
        last_day = next_month - timedelta(days=1)
        self._set_range_and_query(first_day, last_day)

    def set_range_this_year(self):
        today = date.today()
        first_day = date(today.year, 1, 1)
        last_day = date(today.year, 12, 31)
        self._set_range_and_query(first_day, last_day)

    def run_query(self):
        start = self._db_date(self.start_date.date())
        end = self._db_date(self.end_date.date())
        include_category = self.include_category_checkbox.isChecked()

        self.summary_rows = self.controller.get_finance_summary_by_period(
            granularity=self.granularity_combo.currentData(),
            start_date=start,
            end_date=end,
            include_category=include_category,
        )
        self._render_summary(include_category)

        self.detail_rows = []
        self._render_detail([])

    def _render_summary(self, include_category: bool):
        self.summary_table.clear()
        if include_category:
            headers = [
                "項目代號",
                "項目名稱",
                "收入筆數",
                "收入總額",
                "支出筆數",
                "支出總額",
                "淨額",
            ]
        else:
            headers = ["期間", "收入筆數", "收入總額", "支出筆數", "支出總額", "淨額"]

        self.summary_table.setColumnCount(len(headers))
        self.summary_table.setHorizontalHeaderLabels(headers)
        self.summary_table.setRowCount(len(self.summary_rows))
        total_net_sum = 0

        for r, row in enumerate(self.summary_rows):
            income_total = int(row.get("income_total") or 0)
            expense_total = int(row.get("expense_total") or 0)
            net_amount = income_total - expense_total
            total_net_sum += net_amount
            if include_category:
                values = [
                    str(row.get("category_id") or ""),
                    str(row.get("category_name") or ""),
                    str(row.get("income_count") or 0),
                    str(income_total),
                    str(row.get("expense_count") or 0),
                    str(expense_total),
                    str(net_amount),
                ]
            else:
                period_display = str(row.get("period_key") or "")
                if self.granularity_combo.currentData() == "week":
                    period_display = self._format_week_range(
                        str(row.get("period_start") or ""),
                        str(row.get("period_end") or ""),
                    )
                values = [
                    period_display,
                    str(row.get("income_count") or 0),
                    str(income_total),
                    str(row.get("expense_count") or 0),
                    str(expense_total),
                    str(net_amount),
                ]

            for c, value in enumerate(values):
                item = QTableWidgetItem(value)
                self.summary_table.setItem(r, c, item)

        self.summary_table.resizeColumnsToContents()
        self.total_net_label.setText(f"本期收支結餘：{total_net_sum}")

    def _format_week_range(self, start_date: str, end_date: str) -> str:
        try:
            ys, ms, ds = [int(x) for x in start_date.split("-")]
            ye, me, de = [int(x) for x in end_date.split("-")]
            if ys == ye:
                return f"{ys}/{ms}/{ds}-{me}/{de}"
            return f"{ys}/{ms}/{ds}-{ye}/{me}/{de}"
        except Exception:
            return f"{start_date}-{end_date}"

    def load_detail_for_selected_row(self, transaction_type: str):
        start = self._db_date(self.start_date.date())
        end = self._db_date(self.end_date.date())
        self.detail_rows = self.controller.get_transactions(
            transaction_type=transaction_type,
            start_date=start,
            end_date=end,
            keyword=None,
        )
        self.detail_rows.sort(
            key=lambda d: (self._safe_date(d.get("date")), str(d.get("receipt_number") or ""))
        )
        self._render_detail(self.detail_rows)

    def _render_detail(self, rows):
        self.detail_table.setRowCount(len(rows))
        for r, row in enumerate(rows):
            tx_type_text = "收入" if row.get("type") == "income" else "支出"
            values = [
                str(row.get("date") or "").replace("-", "/"),
                tx_type_text,
                str(row.get("receipt_number") or ""),
                str(row.get("category_id") or ""),
                str(row.get("category_name") or ""),
                str(row.get("payer_name") or ""),
                str(row.get("amount") or 0),
                str(row.get("handler") or ""),
                str(row.get("note") or ""),
            ]
            for c, value in enumerate(values):
                self.detail_table.setItem(r, c, QTableWidgetItem(value))

    def export_csv(self):
        if not self.summary_rows:
            QMessageBox.information(self, "提示", "目前沒有可匯出的摘要資料")
            return

        path, _ = QFileDialog.getSaveFileName(
            self,
            "匯出報表",
            "finance_report.csv",
            "Excel 相容檔案 (*.csv)",
        )
        if not path:
            return

        try:
            start = self._db_date(self.start_date.date())
            end = self._db_date(self.end_date.date())
            all_details = self.controller.get_transactions(
                transaction_type=None,
                start_date=start,
                end_date=end,
                keyword=None,
            )
            all_details.sort(
                key=lambda d: (
                    0 if d.get("type") == "income" else 1,
                    self._safe_date(d.get("date")),
                    str(d.get("receipt_number") or ""),
                )
            )
            with open(path, "w", newline="", encoding="utf-8-sig") as f:
                w = writer(f)
                w.writerow(["摘要"])
                summary_headers = [
                    self.summary_table.horizontalHeaderItem(i).text()
                    for i in range(self.summary_table.columnCount())
                ]
                w.writerow(summary_headers)
                for row in range(self.summary_table.rowCount()):
                    w.writerow(
                        [
                            self.summary_table.item(row, col).text() if self.summary_table.item(row, col) else ""
                            for col in range(self.summary_table.columnCount())
                        ]
                    )
                w.writerow([])
                w.writerow(["本期收支結餘", self._calculate_total_net_sum()])

                w.writerow([])
                w.writerow(["細項"])
                detail_headers = ["日期", "類型", "單號", "項目代號", "項目名稱", "對象", "金額", "經手人", "摘要"]
                w.writerow(detail_headers)
                for row_data in all_details:
                    tx_type_text = "收入" if row_data.get("type") == "income" else "支出"
                    w.writerow(
                        [
                            str(row_data.get("date") or "").replace("-", "/"),
                            tx_type_text,
                            str(row_data.get("receipt_number") or ""),
                            str(row_data.get("category_id") or ""),
                            str(row_data.get("category_name") or ""),
                            str(row_data.get("payer_name") or ""),
                            str(row_data.get("amount") or 0),
                            str(row_data.get("handler") or ""),
                            str(row_data.get("note") or ""),
                        ]
                    )
            QMessageBox.information(self, "成功", "報表已匯出（可用 Excel 開啟）")
        except Exception as e:
            QMessageBox.critical(self, "匯出失敗", str(e))

    def _calculate_total_net_sum(self) -> int:
        total = 0
        for row in self.summary_rows:
            income_total = int(row.get("income_total") or 0)
            expense_total = int(row.get("expense_total") or 0)
            total += income_total - expense_total
        return total

    def _safe_date(self, value):
        try:
            return datetime.strptime(str(value or ""), "%Y-%m-%d")
        except Exception:
            return datetime.min
