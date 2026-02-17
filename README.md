# Temple Manager 

## Introduction
Temple Manager 是一款專為寺廟社群設計的 **管理運營系統**，協助寺廟 **提升行政管理效率**，整合 **信眾管理、收支紀錄、活動管理** 等功能，簡化日常營運流程。

本系統提供 **信眾身份管理、戶籍資料建檔、活動報名與紀錄、收支項目管理** 等功能，讓寺廟能夠更有效率地管理內部事務與信眾需求。

Temple Manager 適用於 **中小型廟宇**，幫助管理者 **數位化寺廟運營，提升管理透明度與效率**，讓傳統信仰管理邁向現代化。

## 主要功能特色

### 🏠 信眾管理
- **信眾資料建檔**：統一顯示所有信眾（含戶長與戶員），並以顏色區分身份角色
- **信眾身份管理**：自定義信眾身份類別（如：丁、口等），並在總表中即時顯示
- **快速搜尋**：全域搜尋姓名、電話、地址，支援即時結果清單與一鍵重置
- **資料編輯**：新增、修改、刪除信眾資料，支援自動連動整戶資訊

### 💰 財務管理
- **收入項目管理**：設定各類收入項目與金額
- **支出項目管理**：管理各項支出項目與預算
- **項目分類**：靈活的收入支出分類系統
- **財務會計彙整**：支援日/週/月/年彙整、項目維度彙整、明細檢視與匯出

### 🎯 活動管理
- **活動建立**：建立各類法會、慶典活動
- **方案設定**：支援多種收費方案與項目
- **報名管理**：活動報名人員資料管理
  - 報名人員基本資料錄入（姓名、性別、聯絡方式）
  - 國曆/農曆生日記錄與自動轉換
  - 生肖與生辰時辰記錄
  - 活動項目選擇與數量設定
  - 自動金額計算與收據號碼管理
- **活動狀態**：活動開啟/關閉狀態控制
- **資料搜尋**：支援活動名稱與報名人員姓名搜尋
- **資料列印**：報名人員資料列印功能

### 👥 使用者權限
- **多角色登入**：支援管理員、會計、工作人員
- **安全登入**：bcrypt 密碼加密保護
- **權限控制**：依角色限制收支作業、類別維護與停用資料恢復
- **帳號管理**：僅管理員可新增/重設/停用啟用/刪除帳號，並保留審計紀錄

### 🔤 UI 與日期規範
- **全域字體大小切換**：主頁可選擇小/中/大，並套用到各頁面與主要對話框
- **日期格式統一**：畫面日期輸入與顯示統一為 `YYYY/MM/DD`

## 環境需求與安裝

### 系統需求
- Python 3.8 或以上版本
- macOS / Windows / Linux 作業系統
- 至少 100MB 可用磁碟空間

### 安裝步驟

#### 1. 建立虛擬環境
```bash
python3 -m venv temple_venv
source ./temple_venv/bin/activate  # macOS/Linux
# 或
temple_venv\Scripts\activate       # Windows
```

#### 2. 安裝相依套件
```bash
pip install --upgrade pip
pip install -r requirements.txt
pip install lunardate
```

主要相依套件包括：
- **PyQt5==5.15.9** - GUI 介面框架
- **bcrypt==4.2.1** - 密碼加密
- **pytest==8.3.5** - 測試框架
- **pytest-qt==4.4.0** - PyQt5 測試支援
- **pytest-cov==6.1.1** - 測試覆蓋率
- **pytest-mock==3.14.0** - 模擬測試

#### 3. 驗證安裝
```bash
# 驗證 PyQt5 安裝
    python -c "from PyQt5.QtWidgets import QApplication, QLabel; app = QApplication([]); label = QLabel('PyQt5 安裝成功！'); label.show(); app.exec_()"

# 驗證 bcrypt 安裝
    python -c "import bcrypt; print('bcrypt 安裝成功！')"
    ```

#### 4. Qt Designer（可選）
如需修改 UI 介面，可安裝 Qt Designer：
- **macOS**: 下載 dmg 安裝包 (https://build-system.fman.io/qt-designer-download)
- **Windows**: 透過 Qt 官方安裝程式
- **Linux**: 透過套件管理器安裝 `qt5-designer`


## 使用指南

### 1. 初始化資料庫
首次使用前，請先初始化資料庫（請在 TempleManager 專案根目錄下執行）：
```bash
python -m app.database.setup_db
```

初始化過程會：
- 建立 `temple.db` SQLite 資料庫
- 建立所有必要的資料表（users、households、people、activities 等）
- 建立安全設定與審計紀錄資料表（`app_settings`、`security_logs`）
- 不再建立預設三個帳號；首次啟動會引導建立管理員帳號

### 2. 啟動應用程式
```bash
python -m app.main
```

### 2-1. （可選）重建資料庫後搬回既有資料
若因 schema 調整需刪除重建資料庫，可先備份舊資料再複製回新 DB：
```bash
cp app/database/temple.db ./temple_old.db
rm -f app/database/temple.db
python -m app.database.setup_db
python -m app.database.copy_data --source ./temple_old.db --target app/database/temple.db
rm -rf ./temple_old.db
```
如需連 `users` 一併複製，額外加上 `--include-users`。

### 3. 系統功能導覽

#### 登入系統
- 首次啟動若尚未有管理員帳號，會先進入管理員建立流程
- **UX 優化**：系統登入後會自動進入「信眾資料建檔」頁面，方便快速作業
- 系統會根據使用者角色顯示相應功能
- 可於主頁上方切換全域字體大小（小 / 中 / 大）
- 支援密碼到期提醒（提醒不強制）與閒置自動登出

#### 日期與字體設定
- 日期欄位統一採用 `YYYY/MM/DD` 格式（例如：`2026/02/16`）
- 字體大小切換後，會同步套用至主頁、功能頁與主要彈窗元件

#### 主要功能選單

**類別設定**
- **收入項目建檔作業**：管理各類收入項目與金額設定
- **支出項目建檔作業**：管理各項支出項目與預算
- **信眾身份名稱設定**：自定義信眾身份類別

**資料建檔**
- **信眾資料建檔**：信眾管理主頁面
  - **全方位清單**：一次瀏覽所有戶長與成員，戶長以紅色標示
  - **資料查詢**：支援關鍵字搜尋，並提供「顯示全部」重置功能
  - **點擊連動**：點選任一信眾，自動載入整戶資料與詳細資訊
  - **新增紀錄**：快速新增戶籍或成員，流程直觀且防呆
  - **家庭成員進階管理**（視窗左下角）：
    - **新增/修改/刪除成員**：靈活管理戶籍內的每一位成員
    - **分戶成新戶長**：將指定成員獨立出來成為新的戶號且擔任戶長
    - **變更戶籍與戶長**：支援將成員移轉至其他戶籍，或變更當前戶籍的戶長
    - **順序調整 (上移/下移)**：自定義家庭成員在清單中的顯示順序

**活動頁面**
- **活動管理**：法會活動管理系統
  - 建立新活動：設定活動名稱、日期、方案項目
  - 修改活動：編輯現有活動資料與方案
  - 刪除活動：移除不需要的活動
  - 活動搜尋：快速查找特定活動
  - 報名人員管理：
    - 新增報名人員：錄入參加者詳細資料
    - 修改報名人員：編輯參加者資訊
    - 刪除報名人員：移除報名記錄
    - 搜尋報名人員：按姓名查找參加者
    - 資料列印：輸出報名人員清單
  - 活動狀態控制：開啟/關閉活動報名

**財務會計**
- 依時間粒度（日/週/月/年）彙整收入、支出與淨額
- 可切換「加入項目維度」改為按項目代號彙整
- 提供「今日 / 本週 / 本月 / 今年」快速查詢
- 支援查看收入明細與支出明細
- 匯出 Excel 相容 CSV（含摘要、本期收支結餘、完整明細）

**系統管理（僅管理員）**
- 帳號管理：新增帳號、重設密碼（手動輸入或系統產生臨時密碼）
- 帳號狀態：停用/啟用、刪除（至少保留一位管理員）
- 安全設定：密碼提醒天數、閒置自動登出分鐘
- 審計紀錄：記錄誰在何時對哪個帳號執行重設/刪除/停用等操作

### 4. 角色權限與停用規則

#### 角色定義
- 管理員
- 會計
- 工作人員

#### 收支管理（收入/支出資料登錄）
- 管理員：可新增、查詢、修改、刪除；可補印收入收據；可修改/刪除非當日資料。
- 會計：可新增、查詢、修改、刪除；可補印收入收據；可修改/刪除非當日資料。
- 工作人員：可新增、查詢、修改、刪除；可補印收入收據；僅可修改/刪除當日資料。

#### 財務會計（彙整報表）
- 管理員：可查看摘要與明細、可匯出。
- 會計：可查看摘要與明細、可匯出。
- 工作人員：不可使用。

#### 系統管理（帳號管理）
- 管理員：可新增、重設密碼、停用/啟用、刪除帳號與調整安全設定。
- 會計：不可使用。
- 工作人員：不可使用。

#### 類別設定：收入/支出項目建檔
- 管理員：可新增、修改、停用/啟用。
- 會計：可新增、修改、停用/啟用。
- 工作人員：不可新增、修改、停用/啟用（僅可查看）。

#### 類別設定：信眾身份名稱設定
- 管理員：可新增、修改、刪除。
- 會計：可新增、修改、刪除。
- 工作人員：不可新增、修改、刪除（僅可查看）。

#### 信眾資料建檔（戶長/戶員）
- 管理員：可刪除（停用）戶長/戶員，且可恢復停用資料。
- 會計：可刪除（停用）戶長/戶員，不可恢復停用資料。
- 工作人員：可刪除（停用）戶長/戶員，不可恢復停用資料。

#### 停用/恢復規則（重要）
- 畫面上的「刪除」為停用（Soft Delete），不是實體刪除。
- 停用戶長時，該戶不可有啟用中的戶員（或需先完成戶長變更）。
- 恢復停用資料僅管理員可操作，且需符合：
  - 恢復戶長：同戶不可已有啟用中的戶長。
  - 恢復戶員：同戶必須先有啟用中的戶長。

#### 管理員恢復入口
- 路徑：`資料建檔 -> 信眾資料建檔` 頁面上方 `♻ 恢復停用資料`
- 彈窗支援姓名/電話搜尋，欄位為：類型、姓名、電話。

### 5. 操作流程

#### 信眾管理流程
1. 進入「資料建檔」→「信眾資料建檔」
2. 使用搜尋功能查找現有信眾
3. 點擊「新增戶籍資料」建立新戶籍
4. 填寫戶長基本資料
5. 可進一步新增家庭成員

#### 活動管理流程
1. 進入「活動頁面」→「活動管理」
2. 點擊「新增活動」建立新活動
3. 設定活動名稱、日期、方案項目與金額
4. 管理報名人員資料：
   - 選擇活動後點擊「新增人員」
   - 填寫報名者基本資料（姓名、性別、聯絡方式）
   - 選擇參加的活動項目與數量
   - 系統自動計算總金額
   - 輸入收據號碼與備註
   - 選擇「新增下筆」或「存入離開」
5. 使用搜尋功能查找活動或報名人員
6. 控制活動開啟/關閉狀態

## 資料庫架構

### 主要資料表

#### 使用者管理
- **users**: 使用者帳號與權限管理
  - `id`, `username`, `password_hash`, `role`, `created_at`

#### 信眾管理
- **people**: 個人基本資料
  - `id`, `name`, `gender`, `birthday_ad`, `birthday_lunar`, `birth_time`, `age`, `zodiac`, `phone_home`, `phone_mobile`, `email`, `address`, `zip_code`, `identity`, `note`, `joined_at`

- **households**: 戶長資料
  - `id`, `head_name`, `head_gender`, `head_birthday_ad`, `head_birthday_lunar`, `head_birth_time`, `head_age`, `head_zodiac`, `head_phone_home`, `head_phone_mobile`, `head_email`, `head_address`, `head_zip_code`, `head_identity`, `head_note`, `head_joined_at`, `household_note`

- **household_members**: 戶長與成員關係
  - `id`, `household_id`, `person_id`, `relationship`

#### 財務管理
- **income_items**: 收入項目設定
  - `id`, `name`, `amount`

- **expense_items**: 支出項目設定
  - `id`, `name`, `amount`

#### 身份管理
- **member_identity**: 信眾身份類別
  - `id`, `name`

#### 活動管理
- **activities**: 活動資料
  - `id`, `activity_id`, `name`, `start_date`, `end_date`, `scheme_name`, `scheme_item`, `amount`, `note`, `is_closed`, `created_at`, `updated_at`

- **activity_signups**: 活動報名人員
  - `id`, `activity_id`, `person_name`, `gender`, `birth_ad`, `birth_lunar`, `birth_year`, `zodiac`, `age`, `birth_time`, `phone`, `mobile`, `identity`, `identity_number`, `address`, `note`, `created_at`
  - 新增欄位：`activity_items`（參加的活動項目）、`activity_amount`（活動金額）、`receipt_number`（收據號碼）

### 資料庫設計特點
- 使用 SQLite 輕量級資料庫
- 支援中文排序與搜尋
- 外鍵關聯確保資料完整性
- 自動時間戳記記錄

### 詳細資料庫文件
- [Notion 資料庫文件](https://skitter-apricot-d73.notion.site/SQLite-204ea3ff5528806d8a33cb0ac886045c?source=copy_link)

## 專案架構

### 檔案結構
```
TempleManager/
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── config.py
│   ├── main_window.py
│   ├── auth/
│   │   ├── __init__.py
│   │   └── login.py
│   ├── controller/
│   │   └── app_controller.py
│   ├── database/
│   │   ├── __init__.py
│   │   ├── copy_data.py
│   │   └── setup_db.py
│   ├── dialogs/
│   │   ├── __init__.py
│   │   ├── account_management_dialog.py
│   │   ├── activity_edit_dialog.py
│   │   ├── activity_signup_edit_dialog.py
│   │   ├── base_person_dialog.py
│   │   ├── edit_member_dialog.py
│   │   ├── expense_dialog.py
│   │   ├── finance_report_dialog.py
│   │   ├── income_dialog.py
│   │   ├── income_expense_dialog.py
│   │   ├── login_ui.py
│   │   ├── member_identity_dialog.py
│   │   ├── new_household_dialog.py
│   │   ├── new_member_dialog.py
│   │   ├── plan_edit_dialog.py
│   │   └── transfer_household_dialog.py
│   ├── resources/
│   │   ├── seal.png
│   │   └── seal0.png
│   ├── utils/
│   │   ├── date_utils.py
│   │   ├── font_manager.py
│   │   ├── id_utils.py
│   │   ├── lunar_solar_converter.py
│   │   └── print_helper.py
│   └── widgets/
│       ├── activity_detail_panel.py
│       ├── activity_list_panel.py
│       ├── activity_manage_page.py
│       ├── activity_person_panel.py
│       ├── activity_plan_panel.py
│       ├── activity_signup_page.py
│       ├── auto_resizing_table.py
│       ├── main_page.py
│       └── search_bar.py
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_activity_controller.py
│   ├── test_activity_manage_page.py
│   ├── test_activity_signup_page.py
│   ├── test_app_controller.py
│   ├── test_database.py
│   ├── test_date_utils.py
│   ├── test_account_security.py
│   ├── test_expense_dialog.py
│   ├── test_finance_report_controller.py
│   ├── test_household_people_controller.py
│   ├── test_income_dialog.py
│   ├── test_income_expense_dialog.py
│   ├── test_login_dialog.py
│   ├── test_main_window.py
│   ├── test_member_identity_dialog.py
│   ├── test_print_helper.py
│   ├── test_reactivate_person.py
│   └── test_receipt_logic.py
├── requirements.txt
├── README.md
└── test.ipynb
```

### 架構設計

#### MVC 架構模式
- **Model**: `app/controller/app_controller.py` - 資料存取與業務邏輯
- **View**: `app/widgets/` 與 `app/dialogs/` - 使用者介面元件
- **Controller**: `app/main_window.py` - 視窗控制與事件處理

#### 模組化設計
- **認證模組** (`auth/`): 處理使用者登入與權限
- **資料庫模組** (`database/`): 資料庫初始化與管理
- **對話框模組** (`dialogs/`): 各種資料輸入與設定介面
- **元件模組** (`widgets/`): 可重用的 UI 元件
- **工具模組** (`utils/`): 通用工具函數

#### 技術特點
- **PyQt5**: 跨平台 GUI 框架
- **SQLite**: 輕量級嵌入式資料庫
- **bcrypt**: 安全的密碼加密
- **pytest**: 完整的測試框架支援
- **模組化**: 清晰的程式碼組織結構

## 功能詳細說明

### 信眾管理系統
- **戶籍資料管理**
  - 戶長基本資料：姓名、性別、生日（國曆/農曆）、生肖、年齡
  - 聯絡資訊：電話、手機、電子郵件、地址、郵遞區號
  - 身份設定：自定義身份類別（如：丁、口等）
  - 備註說明：個人特殊備註與加入日期

- **家庭成員管理**
  - 新增家庭成員到現有戶籍
  - 編輯成員詳細資料
  - 刪除成員資料
  - 成員與戶長關係管理

- **搜尋與查詢**
  - 支援姓名、電話、地址等多欄位搜尋
  - 即時搜尋結果顯示
  - 戶籍統計資訊（丁口統計）

### 財務管理系統
- **收入項目管理**
  - 自定義收入項目名稱與代號
  - 設定各項目預設金額
  - 新增、修改、刪除收入項目
  - 項目分類管理

- **支出項目管理**
  - 自定義支出項目名稱與代號
  - 設定各項目預算金額
  - 新增、修改、刪除支出項目
  - 支出分類管理

### 活動管理系統
- **活動建立與管理**
  - 活動基本資訊：名稱、開始日期、結束日期
  - 多方案設定：支援同一活動多種收費方案
  - 方案項目與金額設定
  - 活動備註說明
  - 活動資料搜尋與篩選
  - 活動資料修改與刪除

- **報名人員管理**
  - 報名人員基本資料錄入（姓名、性別、聯絡方式）
  - 支援國曆/農曆生日記錄與自動轉換
  - 生肖與生辰時辰記錄
  - 聯絡資訊與地址記錄
  - 報名日期自動記錄
  - 活動項目選擇與數量設定
  - 自動金額計算功能
  - 收據號碼管理
  - 報名人員搜尋功能
  - 報名資料列印功能

- **活動狀態控制**
  - 活動開啟/關閉狀態管理
  - 即時活動狀態顯示
  - 活動選擇與報名人員關聯

### 系統管理功能
- **使用者權限管理**
  - 四種角色：管理員、會計、委員、工作人員
  - 安全密碼加密儲存
  - 角色權限控制

- **資料備份與維護**
  - SQLite 資料庫自動備份
  - 資料完整性檢查
  - 系統初始化與重置

### 活動人員搜尋
* 快速搜尋：
  - 支援姓名、電話搜尋
  - 即時顯示搜尋結果
  - 同時搜尋戶長和戶員資料
* 自動帶入：
  - 點選搜尋結果自動填入表單
  - 支援姓名、性別、電話、地址等基本資料
  - 包含國曆/農曆生日、生肖、生辰資訊
* 彈性編輯：
  - 自動帶入資料可隨時修改
  - 保留原有表單驗證
  - 支援連續新增及儲存功能

## 測試與開發

### 執行測試
```bash
# 執行所有測試
pytest

# 執行特定測試檔案
pytest tests/test_database.py

# 執行測試並產生覆蓋率報告
pytest --cov=app

# 執行測試並顯示詳細輸出
pytest -v
```

### 測試覆蓋範圍
- **資料庫測試**: 資料表建立、資料操作、查詢功能
- **對話框測試**: 各種輸入對話框的功能測試
- **列印與收據測試**: 收據編號遞增邏輯、金額轉大寫中文、列印格式驗證
- **登入測試**: 使用者認證與權限測試
- **主視窗測試**: 主要功能整合測試

### 開發環境設定
```bash
# 安裝開發相依套件
pip install -r requirements.txt

# 執行測試
pytest

# 程式碼格式檢查（可選）
# flake8 app/
# black app/
```

## 常見問題

### Q: 如何重置資料庫？
A: 刪除 `app/database/temple.db`，再執行 `python -m app.database.setup_db`

### Q: 忘記管理員密碼怎麼辦？
A: 可由其他管理員在「系統管理 -> 帳號管理」執行重設密碼；若系統中已無可登入管理員，請先備份資料庫後重建並重新建立管理員帳號。

### Q: 如何備份資料？
A: 直接複製 `app/database/temple.db` 檔案即可完成資料備份

### Q: 系統支援哪些作業系統？
A: 支援 Windows、macOS、Linux 等所有支援 Python 和 PyQt5 的作業系統

## 授權與支援

本專案為寺廟管理系統，專為提升傳統廟宇數位化管理效率而設計。

如有技術問題或功能建議，歡迎透過 Issue 回報。
