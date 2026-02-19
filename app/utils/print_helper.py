from PyQt5.QtPrintSupport import QPrinter, QPrintPreviewDialog, QPrintDialog, QPrintPreviewWidget
from PyQt5.QtGui import QPainter, QFont, QPen, QColor, QPageLayout, QPageSize, QFontDatabase, QPixmap
from PyQt5.QtCore import Qt, QRectF, QPointF
from PyQt5.QtWidgets import QAction, QToolBar, QPushButton, QComboBox, QLineEdit, QLabel, QCheckBox, QApplication
from PyQt5.QtGui import QTextDocument
import re
from datetime import datetime

class PrintHelper:
    @staticmethod
    def _apply_preview_toolbar(preview, do_print, show_address_toggle=False, toggle_address=None):
        """套用統一列印工具列：自訂列印、縮放、關閉返回。"""
        try:
            toolbars = preview.findChildren(QToolBar)
            if not toolbars:
                return
            toolbar = toolbars[0]
            actions = toolbar.actions()

            for action in actions:
                check_text = (action.text() + " " + action.toolTip())
                is_wanted = True

                widget = toolbar.widgetForAction(action)
                if widget:
                    if isinstance(widget, QComboBox):
                        is_wanted = True
                    elif isinstance(widget, (QLineEdit, QLabel)):
                        is_wanted = False

                unwanted_keywords = [
                    "Page", "Setup", "設定", "版面",
                    "Portrait", "Landscape", "直向", "橫向",
                    "1:1", "Actual", "Fit", "Original",
                    "First", "Last", "Previous", "Next",
                    "Single", "Facing", "Overview", "View", "Three",
                    "Show"
                ]
                for kw in unwanted_keywords:
                    if kw in check_text and not isinstance(widget, QComboBox):
                        is_wanted = False
                        break

                if "Print" in check_text or "列印" in check_text:
                    is_wanted = False
                elif "Zoom In" in check_text or "放大" in check_text or "+" in check_text:
                    action.setText("放大")
                    is_wanted = True
                elif "Zoom Out" in check_text or "縮小" in check_text or "-" in check_text:
                    action.setText("縮小")
                    is_wanted = True

                action.setVisible(is_wanted)

            print_btn = QPushButton("🖨️ 列印")
            print_btn.setMinimumHeight(35)
            print_btn.setFont(QFont("Arial", 12))
            print_btn.setStyleSheet("""
                QPushButton {
                    background-color: #0275d8;
                    color: white;
                    border-radius: 5px;
                    padding: 5px 15px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #025aa5;
                }
            """)
            print_btn.clicked.connect(do_print)

            if actions:
                toolbar.insertWidget(actions[0], print_btn)
            else:
                toolbar.addWidget(print_btn)

            if show_address_toggle and callable(toggle_address):
                addr_cb = QCheckBox("列印住址")
                addr_cb.setChecked(True)
                addr_cb.setFont(QFont("Arial", 12))
                addr_cb.setStyleSheet("""
                    QCheckBox {
                        font-weight: bold;
                        margin-left: 15px;
                        color: black;
                        background-color: #f0f0f0;
                        padding: 5px;
                        border-radius: 4px;
                    }
                """)
                addr_cb.stateChanged.connect(toggle_address)
                if actions:
                    toolbar.insertWidget(actions[0], addr_cb)
                else:
                    toolbar.addWidget(addr_cb)

            toolbar.addSeparator()
            close_btn = QPushButton("關閉返回")
            close_btn.setMinimumHeight(35)
            close_btn.setFont(QFont("Arial", 12))
            close_btn.setStyleSheet("""
                QPushButton {
                    background-color: #d9534f;
                    color: white;
                    border-radius: 5px;
                    padding: 5px 15px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #c9302c;
                }
            """)
            close_btn.clicked.connect(preview.close)
            toolbar.addWidget(close_btn)
        except Exception as e:
            print(f"Error customizing toolbar: {e}")

    @staticmethod
    def _report_font_sizes():
        """
        讓表格式報表跟隨目前全域字體大小（小/中/大）。
        回傳：(body_pt, title_pt)
        """
        app = QApplication.instance()
        app_pt = 16
        if app is not None and app.font() is not None:
            try:
                app_pt = int(app.font().pointSize() or 16)
            except Exception:
                app_pt = 16
        return max(10, app_pt), max(14, app_pt + 4)

    @staticmethod
    def print_table_report(title, headers, rows):
        """
        列印表格式報表（Excel 風格格線）
        - title: str
        - headers: List[str]
        - rows: List[List[Any]]
        """
        printer = QPrinter(QPrinter.HighResolution)
        printer.setPageSize(QPageSize(QPageSize.A4))
        printer.setOrientation(QPrinter.Portrait)

        font_family = PrintHelper._get_compatible_font_family()
        body_pt, title_pt = PrintHelper._report_font_sizes()

        def esc(v):
            s = "" if v is None else str(v)
            return (
                s.replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
                .replace('"', "&quot;")
            )

        thead = "".join(f"<th>{esc(h)}</th>" for h in (headers or []))
        tbody = []
        for r in (rows or []):
            cells = "".join(f"<td>{esc(c)}</td>" for c in (r or []))
            tbody.append(f"<tr>{cells}</tr>")

        html = f"""
        <html>
        <head>
          <meta charset="utf-8">
          <style>
            body {{
              font-family: '{font_family}', 'sans-serif';
              font-size: {body_pt}pt;
              color: #222;
              margin: 14px;
            }}
            h2 {{
              margin: 0 0 10px 0;
              font-size: {title_pt}pt;
              font-weight: 700;
            }}
            table {{
              border-collapse: collapse;
              width: 100%;
              table-layout: auto;
            }}
            th, td {{
              border: 1px solid #666;
              padding: 6px 8px;
              vertical-align: middle;
              word-wrap: break-word;
            }}
            th {{
              background: #f3f3f3;
              font-weight: 700;
            }}
          </style>
        </head>
        <body>
          <h2>{esc(title)}</h2>
          <table>
            <thead><tr>{thead}</tr></thead>
            <tbody>{''.join(tbody)}</tbody>
          </table>
        </body>
        </html>
        """

        doc = QTextDocument()
        doc.setHtml(html)

        preview = QPrintPreviewDialog(printer)
        preview.setWindowTitle("列印預覽")
        preview.resize(1000, 800)

        def do_print():
            dialog = QPrintDialog(printer, preview)
            if dialog.exec_() == QPrintDialog.Accepted:
                doc.print_(printer)

        PrintHelper._apply_preview_toolbar(preview, do_print, show_address_toggle=False)
        preview.paintRequested.connect(lambda p: doc.print_(p))
        preview.exec_()

    @staticmethod
    def _force_a4_landscape(printer):
        """
        強制輸出為 A4 橫式，避免系統列印對話框（含存 PDF）覆蓋方向。
        """
        printer.setPageSize(QPageSize(QPageSize.A4))
        printer.setOrientation(QPrinter.Landscape)

    @staticmethod
    def print_wenshu_report(rows, template="blessing"):
        """
        文疏列印：
        - rows: [{"name","birthday","address","prayer"}...]
        - template: "blessing" | "activity_birthday"
        頁面：A4 橫式，左右各半張（直式字、右到左）
        """
        rows = list(rows or [])
        if not rows:
            return

        printer = QPrinter(QPrinter.HighResolution)
        PrintHelper._force_a4_landscape(printer)

        preview = QPrintPreviewDialog(printer)
        preview.setWindowTitle("文疏列印預覽")
        preview.resize(1000, 800)

        def do_print():
            dialog = QPrintDialog(printer, preview)
            if dialog.exec_() == QPrintDialog.Accepted:
                # 使用者在系統列印視窗改了方向時，這裡再強制拉回橫式
                PrintHelper._force_a4_landscape(printer)
                PrintHelper._render_wenshu_pages_landscape(printer, rows, template)

        PrintHelper._apply_preview_toolbar(preview, do_print, show_address_toggle=False)
        preview.paintRequested.connect(
            lambda p: (PrintHelper._force_a4_landscape(p), PrintHelper._render_wenshu_pages_landscape(p, rows, template))
        )
        preview.exec_()

    @staticmethod
    def _build_wenshu_html(rows, template="blessing"):
        # 保留舊方法相容；新流程改用 _build_single_wenshu_html + _render_wenshu_pages_landscape
        if not rows:
            return ""
        return PrintHelper._build_single_wenshu_html(rows[0], template=template)

    @staticmethod
    def _pair_rows_for_half_a4(rows):
        """兩筆一頁（左右半張）；單數最後一頁右半留白。"""
        out = []
        rows = list(rows or [])
        i = 0
        while i < len(rows):
            left = rows[i]
            right = rows[i + 1] if i + 1 < len(rows) else None
            out.append((left, right))
            i += 2
        return out

    @staticmethod
    def _build_single_wenshu_html(row, template="blessing"):
        def esc(v):
            s = "" if v is None else str(v)
            return (
                s.replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
                .replace('"', "&quot;")
            )

        now = datetime.now()
        created = now.strftime("%Y年%m月%d日")
        roc_year = now.year - 1911
        roc_date = f"{roc_year}年{now.month:02d}月{now.day:02d}日"

        name = esc((row or {}).get("name", ""))
        birthday = esc((row or {}).get("birthday", ""))
        address = esc((row or {}).get("address", ""))
        prayer = esc((row or {}).get("prayer", ""))

        if template == "activity_birthday":
            body = f"""
            <div class="sheet">
              <h1>深坑天南宮祝壽文疏</h1>
              <div class="line">祈祝</div>
              <div class="multi">
                聖誕千秋　　聖壽無疆<br/>
                神威顯赫　　神光普照<br/>
                護佑萬民　　賜福添財<br/>
                四季安康　　吉祥如意
              </div>
              <div class="line">弟子　{name}</div>
              <div class="line">生日　{birthday}</div>
              <div class="line">地址　{address}</div>
              <div class="line">建立年月日　{created}</div>
              <div class="line">中華民國　{roc_date}</div>
            </div>
            """
        else:
            body = f"""
            <div class="sheet">
              <h1>祈願消災文疏</h1>
              <div class="line">弟子：{name}</div>
              <div class="line">出生　{birthday}</div>
              <div class="line">地址：{address}</div>
              <div class="line">祈願文：</div>
              <div class="line">{prayer}</div>
              <div class="line">感恩中壇元帥降臨，保佑弟子心願如意</div>
              <div class="line">弟子必感恩還願，中壇元帥慈悲護佑。</div>
              <div class="line">中華民國　{roc_date}</div>
            </div>
            """

        return f"""
        <html>
        <head>
          <meta charset="utf-8">
          <style>
            body {{
              font-family: '{PrintHelper._get_compatible_font_family()}', 'sans-serif';
              font-size: 13pt;
              color: #111;
              margin: 0;
            }}
            .sheet {{ line-height: 1.8; }}
            h1 {{
              font-size: 18pt;
              text-align: center;
              margin: 0 0 8mm 0;
              font-weight: 700;
            }}
            .line {{ margin: 4mm 0; white-space: pre-wrap; }}
            .multi {{ margin: 6mm 0 8mm 0; text-align: center; }}
          </style>
        </head>
        <body>
          {body}
        </body>
        </html>
        """

    @staticmethod
    def _to_roc_birthday_text(birthday_text: str) -> str:
        """
        將生日字串轉為民國格式：
        - 國曆 1944/08/08 -> 國曆33年08月08日
        - 農曆 1944/06/20 -> 農曆33年06月20日
        - 未含前綴時：1944/08/08 -> 33年08月08日
        無法解析則回傳原字串。
        """
        text = str(birthday_text or "").strip()
        if not text:
            return ""

        m = re.match(r"^(?:(農曆|國曆)\s*)?(\d{4})/(\d{1,2})/(\d{1,2})$", text)
        if not m:
            return text

        calendar_type, y, mth, d = m.groups()
        ad_year = int(y)
        roc_year = ad_year - 1911
        core = f"{roc_year}年{int(mth):02d}月{int(d):02d}日"
        if calendar_type:
            return f"{calendar_type}{core}"
        return core

    @staticmethod
    def _draw_wenshu_half_vertical(painter, area: QRectF, row: dict, template: str):
        if not row:
            return

        painter.save()
        painter.translate(area.topLeft())

        w = area.width()
        h = area.height()

        margin = w * 0.06
        content_rect = QRectF(margin, margin, w - 2 * margin, h - 2 * margin)

        painter.setPen(QPen(Qt.black, 2))
        painter.drawRect(content_rect)

        font_family = PrintHelper._get_compatible_font_family()

        def set_font(size_pt, bold=False):
            f = QFont(font_family, size_pt)
            f.setBold(bool(bold))
            painter.setFont(f)
            return painter.fontMetrics()

        def draw_v_text(
            text,
            x_percent,
            y_start_percent,
            font_size,
            spacing=1.15,
            bold=False,
            wrap_columns=1,
            truncate=True,
            column_start_shift_rows=0,
            bottom_padding_percent=0.0,
            column_gap_scale=1.15,
        ):
            text = str(text or "")
            if not text:
                return
            fm = set_font(font_size, bold)
            char_h = fm.height()
            step_y = char_h * spacing
            box = char_h * 1.4
            x_pos_start = content_rect.right() - (content_rect.width() * (x_percent / 100.0))
            y_pos_start = content_rect.top() + (content_rect.height() * (y_start_percent / 100.0))

            bottom_padding = content_rect.height() * float(bottom_padding_percent or 0.0) / 100.0
            usable_h = max(0.0, (content_rect.bottom() - bottom_padding) - y_pos_start)
            max_rows_per_col = max(1, int(usable_h // step_y))
            max_cols = max(1, int(wrap_columns or 1))

            max_chars = max_rows_per_col * max_cols
            if truncate and len(text) > max_chars and max_chars >= 1:
                text = text[: max_chars - 1] + "…"

            col_step_x = box * float(column_gap_scale or 1.15)
            idx = 0
            for col in range(max_cols):
                x_pos = x_pos_start - (col * col_step_x)
                if x_pos < content_rect.left() + box * 0.5:
                    break
                cursor_y = y_pos_start + (col * max(0, int(column_start_shift_rows)) * step_y)
                for _ in range(max_rows_per_col):
                    if idx >= len(text):
                        return
                    ch = text[idx]
                    r = QRectF(x_pos - box / 2.0, cursor_y, box, box)
                    painter.drawText(r, Qt.AlignCenter | Qt.TextDontClip, ch)
                    cursor_y += step_y
                    idx += 1

        name = str((row or {}).get("name", "") or "")
        birthday = str((row or {}).get("birthday", "") or "")
        birthday_roc = PrintHelper._to_roc_birthday_text(birthday)
        address = str((row or {}).get("address", "") or "")
        prayer = str((row or {}).get("prayer", "") or "")

        now = datetime.now()
        roc_year = now.year - 1911
        roc_date = f"{roc_year}年{now.month:02d}月{now.day:02d}日"

        # 人員基本欄位統一字級與格式（弟子/生日/地址）
        person_font_size = 17
        person_spacing = 0.9

        if template == "activity_birthday":
            # 右到左欄位
            draw_v_text("深坑天南宮祝壽文疏", 8, 10, 27, spacing=1.00, bold=True)
            draw_v_text("祈祝", 18, 10, 21, spacing=1.00, bold=True)
            draw_v_text("聖誕千秋      聖壽無疆", 30, 10, 18, spacing=1.00)
            draw_v_text("神威顯赫      神光普照", 40, 10, 18, spacing=1.00)
            draw_v_text("護佑萬民      賜福添財", 50, 10, 18, spacing=1.00)
            draw_v_text("四季安康      吉祥如意", 60, 10, 18, spacing=1.00)
            if prayer:
                draw_v_text(f"{prayer}", 18, 28, 21, spacing=1.00)
            draw_v_text(f"弟子　{name}", 72, 10, person_font_size, spacing=person_spacing)
            draw_v_text(f"生日　{birthday_roc}", 80, 10, person_font_size, spacing=person_spacing)
            draw_v_text(
                f"地址　{address}",
                88,
                34,
                person_font_size,
                spacing=person_spacing,
                wrap_columns=2,
                truncate=True,
                column_start_shift_rows=6,
                column_gap_scale=0.9,
                bottom_padding_percent=10.0,
            )
            draw_v_text(f"中華民國　{roc_date}", 96, 10, 16, spacing=1.00)
        else:
            draw_v_text("祈願消災文疏", 10, 25, 27, spacing=1.00, bold=True)
            draw_v_text("深坑天南宮中壇元帥慈悲護佑", 20, 10, person_font_size, spacing=person_spacing)
            draw_v_text(f"弟子：{name}", 28, 10, person_font_size, spacing=person_spacing)
            draw_v_text(f"出生　{birthday_roc}", 36, 10, person_font_size, spacing=person_spacing)
            draw_v_text(
                f"地址：{address}",
                44,
                10,
                person_font_size,
                spacing=person_spacing,
                wrap_columns=2,
                truncate=True,
                column_start_shift_rows=8,
                column_gap_scale=0.9,
                bottom_padding_percent=10.0,
            )
            draw_v_text("祈願文：", 52, 10, person_font_size, spacing=person_spacing)
            if prayer:
                draw_v_text(f"{prayer}", 60, 10, person_font_size, spacing=person_spacing, wrap_columns=3, truncate=True)
            draw_v_text("感恩中壇元帥降臨，保佑弟子心願如意", 76, 10, 16, spacing=1.00)
            draw_v_text("弟子必感恩還願，中壇元帥慈悲護佑。", 84, 10, 16, spacing=1.00)
            draw_v_text(f"中華民國　{roc_date}", 92, 10, 16, spacing=1.00)

        painter.restore()

    @staticmethod
    def _render_wenshu_pages_landscape(printer, rows, template):
        pairs = PrintHelper._pair_rows_for_half_a4(rows)
        if not pairs:
            return

        painter = QPainter(printer)
        rect = printer.pageRect()
        width = rect.width()
        height = rect.height()

        left_rect = QRectF(0, 0, width / 2.0, height)
        right_rect = QRectF(width / 2.0, 0, width / 2.0, height)

        for page_idx, (left_row, right_row) in enumerate(pairs):
            if page_idx > 0:
                printer.newPage()

            PrintHelper._draw_center_dash_line(painter, int(width / 2), int(height))

            PrintHelper._draw_wenshu_half_vertical(painter, left_rect, left_row, template)
            # 右半若無資料，依需求保留空白
            PrintHelper._draw_wenshu_half_vertical(painter, right_rect, right_row, template)

        painter.end()

    @staticmethod
    def _draw_center_dash_line(painter, x: int, height: int):
        """統一畫中間分隔虛線（更粗更深，預覽與實印都明顯）。"""
        pen = QPen(QColor("#5F5F5F"))
        pen.setWidth(6)
        pen.setStyle(Qt.CustomDashLine)
        pen.setDashPattern([14, 8])
        pen.setCapStyle(Qt.FlatCap)
        painter.setPen(pen)
        painter.drawLine(int(x), 0, int(x), int(height))

    @staticmethod
    def _get_compatible_font_family():
        """
        跨平台字體選擇策略
        """
        db = QFontDatabase()
        families = db.families()
        
        preferred_fonts = [
            "PingFang TC", "Heiti TC", 
            "DFKai-SB", "BiauKai", "標楷體", "KaiTi", 
            "PMingLiU", "MingLiU", "新細明體"
        ]
        
        for font in preferred_fonts:
            if font in families: 
                return font
        return "Sans Serif"

    @staticmethod
    def print_receipt(data):
        # ... (unchanged)
        printer = QPrinter(QPrinter.HighResolution)
        PrintHelper._force_a4_landscape(printer)
        
        preview = QPrintPreviewDialog(printer)
        preview.setWindowTitle("列印預覽")
        preview.resize(1000, 800)
        
        # 列印設定 (使用 dict 以便在 inner function 修改)
        print_settings = {"show_address": True}
        
        # 實作自訂列印功能 (為了確保列印按鈕有效)
        def do_print():
            dialog = QPrintDialog(printer, preview)
            if dialog.exec_() == QPrintDialog.Accepted:
                # 使用者在系統列印視窗改了方向時，這裡再強制拉回橫式
                PrintHelper._force_a4_landscape(printer)
                PrintHelper._handle_print_painter(printer, data, print_settings['show_address'])
                
        def toggle_address(state):
            print_settings['show_address'] = (state == Qt.Checked)
            # 修正: QPrintPreviewDialog 沒有 updatePreview，需透過其內的 QPrintPreviewWidget
            try:
                preview_widget = preview.findChildren(QPrintPreviewWidget)[0]
                preview_widget.updatePreview()
            except:
                pass

        PrintHelper._apply_preview_toolbar(
            preview,
            do_print,
            show_address_toggle=True,
            toggle_address=toggle_address,
        )

        preview.paintRequested.connect(
            lambda p: (PrintHelper._force_a4_landscape(p), PrintHelper._handle_print_painter(p, data, print_settings['show_address']))
        )
        preview.exec_()

    @staticmethod
    def _handle_print_painter(printer, data, print_address=True):
        PrintHelper._force_a4_landscape(printer)
        painter = QPainter(printer)
        
        # 取得可列印範圍 (Pixels)
        rect = printer.pageRect()
        width = rect.width()
        height = rect.height()
        
        # 左半部 (存根聯) - A5 Portrait
        PrintHelper._draw_receipt(painter, data, QRectF(0, 0, width / 2, height), "（存根聯）", print_address)
        
        # 分隔線 (垂直中線)
        PrintHelper._draw_center_dash_line(painter, int(width / 2), int(height))
        
        # 右半部 (收執聯) - A5 Portrait
        PrintHelper._draw_receipt(painter, data, QRectF(width / 2, 0, width / 2, height), "（收執聯）", print_address)
        
        painter.end()

    @staticmethod
    def _draw_receipt(painter, data, area, copy_title, print_address=True):
        """
        繪製單張收據 (A5 Portrait 區域)
        area: QRectF
        """
        painter.save()
        painter.translate(area.topLeft())
        
        w = area.width()
        h = area.height()
        
        # 定義相對單位 (Base Unit)
        # 用高度的 1% 作為基準單位，確保在高解析度下也能等比縮放
        unit = h / 100.0
        
        # 邊框 (5% 邊距)
        margin = w * 0.05
        content_rect = QRectF(margin, margin, w - 2 * margin, h - 2 * margin)
        
        # --- 安裝印章 (浮水印 - 先畫在底層) ---
        # 位置：在天南宮(75%)與日期(95%)之間，約 85% 位置
        seal_path = "app/resources/seal.png"
        pixmap = QPixmap(seal_path)
        
        seal_h = 28 * unit # 高度縮小，避免超出框外
        
        painter.save() # Save for seal
        if not pixmap.isNull():
            # 計算等比例寬度
            aspect_ratio = pixmap.width() / pixmap.height()
            seal_w = seal_h * aspect_ratio
            
            # 定位
            seal_x_center = content_rect.right() - (content_rect.width() * 0.78)
            seal_y_start = content_rect.top() + (content_rect.height() * 0.50)
            
            seal_rect = QRectF(seal_x_center - seal_w/2, seal_y_start, 
                               seal_w, seal_h)
            
            # 設為半透明 (浮水印效果, 不蓋住字)
            painter.setOpacity(0.3) 
            painter.drawPixmap(seal_rect, pixmap, QRectF(pixmap.rect()))
        else:
            # 沒圖片：畫個紅色框框示意
            seal_size = 18 * unit
            seal_x_center = content_rect.right() - (content_rect.width() * 0.85)
            seal_y_start = content_rect.top() + (content_rect.height() * 0.22)
            seal_rect = QRectF(seal_x_center - seal_size/2, seal_y_start, seal_size, seal_size)

            painter.setPen(QPen(Qt.red, 2, Qt.DashLine))
            painter.drawRect(seal_rect)
            painter.setPen(Qt.red)
            painter.drawText(seal_rect, Qt.AlignCenter, "無印章\n(seal.png)")
        painter.restore() # Restore after seal
        
        painter.setPen(QPen(Qt.black, 3))
        painter.drawRect(content_rect)

        # Helper: 設定字體
        font_family = PrintHelper._get_compatible_font_family()

        def set_font(size_pt, bold=False):
            # QFont size is in points usually, which is resolution independent-ish?
            # actually QFont(..., size) in Qt depends on constructor.
            # If int, it's points. If pixel, it's pixels.
            # Let's try to keep it points, but layout boxes must be relative.
            font = QFont(font_family, size_pt)
            if bold: font.setBold(True)
            painter.setFont(font)
            return painter.fontMetrics()

        # Helper: 畫直式文字
        def draw_v_text(text, x_percent, y_start_percent, font_size, spacing=1.1, bold=False):
            fm = set_font(font_size, bold)
            char_h = fm.height()
            
            x_pos = content_rect.right() - (content_rect.width() * (x_percent / 100))
            y_pos = content_rect.top() + (content_rect.height() * (y_start_percent / 100))
            
            cursor_y = y_pos
            
            for char in text:
                # 框框大小也要夠大，用字體高度的倍數比較保險
                box_size = char_h * 1.5
                rect_char = QRectF(x_pos - box_size/2, cursor_y, box_size, box_size)
                
                # 特殊符號旋轉 90 度 (括號)
                if char in ['(', ')', '（', '）']:
                    painter.save()
                    # 移至文字中心
                    center = rect_char.center()
                    painter.translate(center.x(), center.y())
                    painter.rotate(90)
                    
                    # 在原點繪製 (因為已平移)
                    # 修正繪製區域為以 (0,0) 為中心
                    rect_centered = QRectF(-box_size/2, -box_size/2, box_size, box_size)
                    painter.drawText(rect_centered, Qt.AlignCenter | Qt.TextDontClip, char)
                    painter.restore()
                else:
                    painter.drawText(rect_char, Qt.AlignCenter | Qt.TextDontClip, char)
                
                cursor_y += char_h * spacing

        # --- 準備資料 ---
        amount_chinese = PrintHelper.number_to_chinese(data.get('amount', 0))
        date_str = data.get('date', '')
        try:
            dt = datetime.strptime(date_str, "%Y-%m-%d")
            roc_year = dt.year - 1911
            date_text = f"中華民國 {PrintHelper.num_to_cn_simple(roc_year)} 年 {PrintHelper.num_to_cn_simple(dt.month)} 月 {PrintHelper.num_to_cn_simple(dt.day)} 日"
        except:
            date_text = date_str

        # --- 定義字體大小 ---
        FONT_TITLE = 30
        FONT_SERIAL = 12
        FONT_BODY = 18
        FONT_FOOTER = 12
        FONT_DATE = 18

        # --- 佈局座標 (Y 軸) ---
        Y_TITLE = 30
        Y_BODY_START = 6
        Y_FOOTER_START = 18

        # 1. 標題: 感謝狀 (10%)
        draw_v_text("感謝狀", 10, Y_TITLE, FONT_TITLE, spacing=1.1, bold=True)
        
        # 2. 補登字號 (19%)
        draw_v_text("新北市補登字第二七四號", 19, 25, FONT_SERIAL, spacing=1.1)
        
        # --- 本文區 (茲承~住址) ---
        # 3. 茲承 (27%)
        draw_v_text("茲承", 27, Y_BODY_START, FONT_BODY)
        
        # 4. 姓名 (35%)
        payer_name = data.get('payer_name', '')
        draw_v_text(f"{payer_name}  大德捐獻", 35, Y_BODY_START + 5, FONT_BODY, bold=True)
        
        # 5. 項目 (43%)
        item_name = data.get('category_name', '油香')
        draw_v_text(f"本宮{item_name}建設", 43, Y_BODY_START, FONT_BODY)
        
        # 6. 金額 (51%)
        amount_text_full = f"新台幣  {amount_chinese}  元整"
        # 動態計算：若金額太長，縮小間距或字體
        fm_amt = set_font(FONT_BODY)
        char_h_amt = fm_amt.height()
        spacing_amt = 1.1
        total_h_amt = len(amount_text_full) * char_h_amt * spacing_amt
        # 可用高度：底部留一點緩衝 (約 93%)
        max_h_amt = content_rect.height() * (0.93 - (Y_BODY_START / 100.0))
        
        amt_font_size = FONT_BODY
        if total_h_amt > max_h_amt:
            # 優先縮小間距
            spacing_amt = max_h_amt / (len(amount_text_full) * char_h_amt)
            if spacing_amt < 0.85:
                spacing_amt = 0.85
                # 間距縮到 0.85 還不夠，則縮小字體
                amt_font_size = int(max_h_amt / (len(amount_text_full) * char_h_amt * 0.85) * FONT_BODY)
                amt_font_size = max(11, amt_font_size) # 最小不低於 11pt
        
        draw_v_text(amount_text_full, 51, Y_BODY_START, amt_font_size, spacing=spacing_amt)
        
        # 7. 功德 (59%)
        draw_v_text("功德無量  謹此致謝", 59, Y_BODY_START, FONT_BODY)
        
        # 8. 住址 (67%)
        addr_text = "住址："
        if print_address:
            addr_text += data.get('address', '')
            
        # 計算一欄能塞幾個字，若太長則換行
        fm_addr = set_font(FONT_BODY)
        char_h_addr = fm_addr.height()
        # 可用高度：從 Y_BODY_START 到 底部 98%
        limit_h = content_rect.height() * (0.98 - (Y_BODY_START/100.0))
        line_spacing_px = char_h_addr * 0.9
        max_chars = int(limit_h / line_spacing_px)
        
        if len(addr_text) <= max_chars:
            draw_v_text(addr_text, 67, Y_BODY_START, FONT_BODY, spacing=0.9)
        else:
             # 超過長度，分兩行 (防呆：往左移一欄)
             part1 = addr_text[:max_chars]
             part2 = addr_text[max_chars:]
             draw_v_text(part1, 67, Y_BODY_START, FONT_BODY, spacing=0.9)
             # 第二行放在 ˙74% (67與75中間)，高度一半
             draw_v_text(part2, 73, 50, FONT_BODY, spacing=0.9)

        # --- 落款區 (天南宮~經手人) ---
        # 9. 天南宮 (75%)
        draw_v_text("天南宮管理委員會", 75, Y_FOOTER_START, FONT_FOOTER, spacing=1.1, bold=True)
        
        # 10. 地址 (80%)
        draw_v_text("新北市深坑區阿柔里大崙尾一號", 80, Y_FOOTER_START, FONT_FOOTER, spacing=1.1)
        
        # 11. 電話 (85%)
        draw_v_text("電話：(〇二)二六六四〇一一九", 85, Y_FOOTER_START, FONT_FOOTER, spacing=1.1)
        
        # 12. 經手人 (90%)
        handler = data.get('handler', '')
        draw_v_text(f"經手人：{handler}", 90, Y_FOOTER_START, FONT_FOOTER, spacing=1.1)

        # 13. 日期 (95% - 最左邊)
        draw_v_text(date_text, 95, Y_BODY_START, FONT_DATE, spacing=1.0)
        
        # 14. 無效聲明 (改為直式，黑色框框外左側，略高於日期)
        # 日期起始約 6%, 這邊設為 2% 讓它高一點
        # X=103% 表示移出左邊界 (邊距 5%, content 佔 90%, 100%是左邊界, 103%在邊距中間)
        draw_v_text("本感謝狀無本宮簽章無效", 103, 2, 12, spacing=1.0)

        # --- 橫式文字 (使用相對單位 unit 定位) ---
        
        # A. 補印標示 (置底)
        set_font(12)
        # 高度 4 unit, 底部留 1 unit 緩衝
        # QRectF(x, y, w, h)
        rect_copy = QRectF(content_rect.left(), content_rect.bottom() - (4 * unit), 
                           content_rect.width(), 4 * unit)
        painter.drawText(rect_copy, Qt.AlignCenter, copy_title)

        # B. 無效聲明 (原橫式已移除)
        
        # C. 收據編號 No. (右下, 紅色)
        set_font(16, bold=True)
        painter.setPen(Qt.red)
        # 在 copy title 上方，靠右
        rect_no = QRectF(content_rect.right() - (50 * unit), content_rect.bottom() - (10 * unit), 
                         45 * unit, 6 * unit)
        painter.drawText(rect_no, Qt.AlignRight | Qt.AlignVCenter, f"No. {data.get('receipt_number', '')}")
        painter.setPen(Qt.black)

        painter.restore()

    @staticmethod
    def number_to_chinese(number):
        """
        數字轉中文大寫 (簡易版)
        """
        if not str(number).isdigit():
            return str(number)
            
        digits = "零壹貳參肆伍陸柒捌玖"
        units = ["", "拾", "佰", "仟"]
        big_units = ["", "萬", "億"]
        
        n = int(number)
        if n == 0:
            return "零"
            
        s = str(n)[::-1] # 倒過來處理
        result = []
        
        for i, char in enumerate(s):
            d = int(char)
            unit_idx = i % 4
            big_unit_idx = i // 4
            
            if i > 0 and i % 4 == 0:
                result.append(big_units[big_unit_idx])
                
            if d != 0:
                result.append(units[unit_idx])
                result.append(digits[d])
            else:
                # 處理零：如果前一個不是零，且不是單位，才補零 (這裡簡化，直接補，之後再 replace)
                if result and result[-1] != "零":
                     result.append("零")
        
        final_str = "".join(result[::-1])
        # 清理多餘的零
        final_str = final_str.replace("零萬", "萬").replace("零億", "億").strip("零")
        if not final_str:
            return "零"
        return final_str

    @staticmethod
    def num_to_cn_simple(num):
        """阿拉伯數字轉中文數字 (日期用)"""
        mapping = str.maketrans("0123456789", "〇一二三四五六七八九")
        return str(num).translate(mapping)
