from PyQt5.QtPrintSupport import QPrinter, QPrintDialog, QPrintPreviewDialog
from PyQt5.QtGui import QTextDocument, QPageLayout, QPageSize
from PyQt5.QtCore import QSizeF
from PyQt5.QtWidgets import QApplication

class PrintHelper:
    @staticmethod
    def print_receipt(data):
        """
        列印收據 (A4 一半，一式兩份)
        data: {
            receipt_number, date, payer_name, category_name, amount, note, handler
        }
        """
        printer = QPrinter(QPrinter.HighResolution)
        # 設定為 A4
        printer.setPageSize(QPageSize(QPageSize.A4))
        
        # 預覽對話框
        preview = QPrintPreviewDialog(printer)
        preview.paintRequested.connect(lambda p: PrintHelper._handle_print(p, data))
        preview.exec_()

    @staticmethod
    def _handle_print(printer, data):
        document = QTextDocument()
        
        # CSS 樣式
        style = """
        <style>
            .receipt-container {
                width: 100%;
                height: 45%; /* 大約一半高度 */
                border: 2px solid #333;
                padding: 20px;
                box-sizing: border-box;
                font-family: "Microsoft JhengHei", sans-serif;
            }
            .header {
                text-align: center;
                font-size: 24px;
                font-weight: bold;
                margin-bottom: 5px;
            }
            .sub-header {
                text-align: right;
                font-size: 14px;
                color: #555;
            }
            .footer {
                margin-top: 30px;
                text-align: right;
                font-size: 16px;
            }
            .copy-mark {
                text-align: center;
                font-size: 12px;
                color: #888;
                margin-top: 10px;
            }
            table {
                width: 100%;
                border-collapse: collapse;
                margin-top: 15px;
            }
            td {
                padding: 8px;
                font-size: 18px;
                border-bottom: 1px solid #ddd;
            }
        </style>
        """
        
        handler_name = data.get('handler') or "______________"
        
        def single_receipt(title_suffix):
            return f"""
            <div class="receipt-container">
                <div class="header">宮廟感謝狀/收據</div>
                <div class="sub-header">收據號碼：{data.get('receipt_number')}</div>
                <br>
                <table width="100%" cellpadding="5">
                    <tr>
                        <td><b>日期：</b> {data.get('date')}</td>
                        <td><b>大德：</b> {data.get('payer_name')}</td>
                    </tr>
                    <tr>
                        <td colspan="2"><b>項目：</b> {data.get('category_name')} ({data.get('category_id')})</td>
                    </tr>
                    <tr>
                        <td colspan="2"><b>金額：</b> NT$ {data.get('amount')}</td>
                    </tr>
                     <tr>
                        <td colspan="2"><b>備註：</b> {data.get('note')}</td>
                    </tr>
                </table>
                <div class="footer">
                    經手人：{handler_name} &nbsp;&nbsp;&nbsp; 蓋章：______________
                </div>
                <div class="copy-mark">{title_suffix}</div>
            </div>
            """

        # 組合 HTML：兩個收據，中間分隔
        html_content = f"""
        <html>
        <head>{style}</head>
        <body>
            {single_receipt("（廟方存根聯）")}
            <br>
            <div style="height: 50px; text-align: center; line-height: 50px; color: #ccc;">- - - - - 裁切線 - - - - -</div>
            <br>
            {single_receipt("（信徒收執聯）")}
        </body>
        </html>
        """
        
        document.setHtml(html_content)
        document.print_(printer)
