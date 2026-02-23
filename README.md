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
- **活動管理頁（管理端）**：活動清單、活動資料、報名統計與列印
  - 報名名單（明細）：繳費狀態、姓名、電話、方案、金額
  - 總品項列印：方案品項彙總總數量
  - 文疏列印：單筆/批次列印
    - 支援兩種格式：**活動祝壽** / **祈願消災（加持）**
    - 列印版面採 **A4 橫式半張（左右各一份）**、直式右到左
    - 強制輸出 A4 橫式（含存 PDF），避免系統列印對話框改回直式
    - 文疏中線與收據中線採加粗虛線分隔
    - 加持格式「祈願文」可帶入預設祈求；過長內容自動換欄並截斷
  - 繳費作業：勾選未繳費名單後匯入收入資料
- **活動報名頁（作業端）**
  - 人員快速搜尋（姓名/電話）與資料帶入
  - 整戶報名彈窗（可同時設定多位成員方案）
  - 已報名明細集中「修改報名 / 刪除報名」
- **文疏祈求欄位邏輯**
  - 勾選「套用預設祈求」時：將預設值回填到每列祈求欄
  - 祈求欄可逐列手動覆寫，列印以該列內容為優先
- **關閉返回**：活動管理與活動報名頁皆提供右下角「關閉返回」

### 👥 使用者權限
- **多角色登入**：支援管理員、會計、工作人員
- **安全登入**：bcrypt 密碼加密保護
- **登入封面自訂**：管理員可上傳登入封面照片並設定登入標題（毛筆風字體）
- **權限控制**：依角色限制收支作業、類別維護與停用資料恢復
- **帳號管理**：僅管理員可新增/重設/停用啟用/刪除帳號，並保留審計紀錄

### 🔤 UI 與日期規範
- **全域字體大小切換**：主頁可選擇小/中/大，並套用到各頁面與主要對話框
- **日期格式統一**：畫面日期輸入與顯示統一為 `YYYY/MM/DD`
- **主頁表格可讀性**：信眾戶長/戶員清單支援水平捲動，欄位內容過長時可左右查看

### ✉️ 排程與自動寄信
- **統一排程服務**：`python -m app.scheduler.worker` 長駐執行，依 `app/mailer/mail_config.yaml` 觸發排程
- **自動報表產生**：寄信前自動產出 CSV 報表為附件，無需手動產生
- **支援多封不同排程信件**：Heartbeat 心跳、每日/每月收支、活動報名狀況、信眾資料表
- **寄送紀錄寫入 SQLite**：`email_outbox` 表記錄 SENT / FAILED、保留錯誤訊息以供排查
- **支援 Gmail App Password（安全機制）**：帳號與密碼透過環境變數讀取且不會將密碼明碼寫入 YAML


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
pip install --only-binary=:all: -r requirements.txt
```
`--only-binary=:all:` 說明：
- 強制 pip 只安裝預編譯 wheel，不從原始碼編譯套件。
- 可避免 PyQt5 在某些環境（例如缺少 `qmake`）安裝失敗。
- 若某套件暫無對應 wheel，pip 會直接報錯，便於快速定位相依版本問題。

建議：使用 Python 3.12 建立虛擬環境，可降低 GUI 相依套件 wheel 相容性問題。

主要相依套件包括：
- **PyQt5==5.15.11** - GUI 介面框架
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
若你已在使用既有資料庫（`app/database/temple.db`），通常不需要重複初始化；此步驟主要用於首次安裝或重建資料庫時。

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

### 2-2. 啟動自動發信排程

設定環境變數（Gmail App Password）：
```bash
export GMAIL_USER="your@gmail.com"
export GMAIL_APP_PASSWORD="your_app_password"
```

啟動排程：
```bash
python -m app.scheduler.worker
```

排程設定檔位於 `app/mailer/mail_config.yaml`。以下為預設排程的報表類型與寄送時間：

| 排程 Job | 說明 | 排程時間 | 報表檔名 |
|----------|------|----------|----------|
| heartbeat | 心跳信（確認服務運行） | 每日 09:05 | 無附件 |
| daily_finance_report | 每日收支明細表 | 每日 20:00 | 每日收支明細表_yyyymmdd.csv |
| monthly_finance_report | 每月收支明細表 | 每月最後一日 20:00 | 每月收支明細表_yyyymm.csv |
| daily_activity_report | 每日活動報名狀況 | 每日 08:00 | 每日活動報表_yyyymmdd.csv |
| monthly_believer_report | 每月信眾資料表 | 每月最後一日 10:00 | 每月信眾資料表_yyyymm.csv |

**注意**：
- 報表產生與寄信皆由排程自動執行，輸出至 `reports/` 目錄
- `daily_activity_report` 僅於活動期間內寄送；當日若無進行中活動則不產報、不寄信

### 3. 系統功能導覽

#### 登入系統
- 首次啟動若尚未有管理員帳號，會先進入管理員建立流程
- 登入頁可顯示封面照片與標題文字（由「系統管理 -> 封面設定」維護）
- 封面會隨登入視窗大小調整，維持比例並以左右滿版呈現
- **UX 優化**：系統登入後會自動進入「信眾資料建檔」頁面，方便快速作業
- 系統會根據使用者角色顯示相應功能
- 可於主頁上方切換全域字體大小（小 / 中 / 大）
- 支援密碼到期提醒（提醒不強制）與閒置自動登出

#### 日期與字體設定
- 日期欄位統一採用 `YYYY/MM/DD` 格式（例如：`2026/02/16`）
- 字體大小切換後，會同步套用至主頁、功能頁與主要彈窗元件
- 年齡顯示採「依國曆生日即時計算」，若有人工修正則以校正值（`age_offset`）持續套用於後續年度
- 修改信眾電話時，聯絡電話與手機號碼至少需保留一個（可清空其中一個）

#### 主要功能選單

**類別設定**
- **收入項目建檔作業**：管理各類收入項目與金額設定
- 系統啟動時會自動補齊保留收入項目：`90 活動收入`、`91 點燈收入`
- 若項目已存在則略過建立（並同步名稱）
- 一般收入項目代號自動編號時，保留代號 `90/91` 不納入遞增計算，仍以 `01` 起算
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
- **活動管理**（以檢視/統計/列印為主）
  - 建立新活動：設定活動名稱、日期、方案項目
  - 修改活動：編輯現有活動資料與方案
  - 刪除活動：移除不需要的活動
  - 報名統計與列印：
    - 報名名單（明細）列印
    - 總品項列印
    - 文疏列印（單筆/批次）
      - 活動祝壽格式：
        - `祈祝`段落下可放入預設祈求內容
      - 祈願消災（加持）格式：
        - 內容為 `祈願消災文疏 / 弟子 / 出生 / 地址 / 祈願文 / 固定文句 / 中華民國日期`
        - `預設祈求` 套用到每列祈求欄後可手動修改
      - 長文字處理：
        - 地址過長時採平行分欄顯示（第二欄由中後段開始）
        - 祈願文過長時自動換欄，超出可用空間會截斷
      - 輸出一致性：
        - 文疏與收據列印皆強制 A4 橫式，避免存 PDF 方向錯誤
  - 繳費（勾選未繳費名單）：
    - 經手人為必填
    - 匯入收入資料登錄作業（收據號碼依規則連續）
    - 項目固定帶入 `90 活動收入`
    - 摘要格式：`[活動結束日期 活動名稱] 方案摘要`

- **活動報名**（新增/修改/刪除集中在此頁）
  - 快速搜尋人員（姓名/電話），可從任一成員展開整戶報名
  - 已報名明細可直接「修改報名 / 刪除報名」
  - 從活動「繳費」匯入收入資料時：
    - 項目固定帶入 `90 活動收入`

**財務會計**
- 依時間粒度（日/週/月/年）彙整收入、支出與淨額
- 可切換「加入項目維度」改為按項目代號彙整
- 提供「今日 / 本週 / 本月 / 今年」快速查詢
- 支援查看收入明細與支出明細
- 匯出 Excel 相容 CSV（含摘要、本期收支結餘、完整明細）

**系統管理（僅管理員）**
- 帳號管理：新增帳號、重設密碼（手動輸入或系統產生臨時密碼）
- 帳號狀態：停用/啟用、刪除（至少保留一位管理員）
- 資料備份與維護：本機/Google Drive 備份、立即備份、排程設定（內建）、備份紀錄查詢
- 安全設定：密碼提醒天數、閒置自動登出分鐘
- 封面設定：上傳登入封面照片與設定登入標題
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

#### 資料備份與維護
- 管理員：可設定備份目的地與排程、執行立即備份、查看備份紀錄與錯誤訊息。
- 會計：不可使用。
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
3. 設定活動名稱、日期、方案與金額
4. 進入「活動報名」：
   - 搜尋任一人員（姓名/電話）
   - 開啟整戶報名彈窗，勾選成員與方案後一次存入
   - 在已報名明細進行「修改報名 / 刪除報名」
5. 回到「活動管理」查看「報名統計與列印」：
   - 列印名單、總品項列印、文疏列印（祝壽/加持）
   - 勾選未繳費名單並輸入經手人後執行繳費

#### 收支管理流程
1. 進入「收支管理」→ 選擇「收入資料登錄」或「支出資料登錄」
2. 選擇年度 / 月份（可切換全部、前後月）
3. 新增收支資料：
   - 日期（`YYYY/MM/DD`）
   - 項目代號 / 項目名稱
   - 金額、經手人、摘要/備註
4. 儲存後可於列表查詢、右鍵修改/刪除（依角色與當日規則限制）
5. 收入資料可列印/補印收據（依權限）

#### 財務會計流程
1. 進入「財務會計」
2. 選擇時間粒度（日 / 週 / 月 / 年）與起訖日期
3. 可勾選是否加入項目維度（依項目代號彙整）
4. 查看摘要（收入、支出、本期收支結餘）與明細
5. 需要時匯出 Excel 相容 CSV（含摘要與完整明細）

#### 系統管理流程（僅管理員）
1. 進入「系統管理」
2. 帳號管理：新增帳號、重設密碼、停用/啟用、刪除帳號
3. 安全設定：調整密碼提醒天數、閒置自動登出分鐘
4. 封面設定：上傳登入封面照片與設定登入標題
5. 資料備份：設定本機/Google Drive（OAuth）、執行立即備份、查看備份紀錄

## 資料庫架構

### 主要資料表

#### 使用者管理
- **users**: 使用者帳號與權限管理
  - `id`, `username`, `password_hash`, `role`, `is_active`, `must_change_password`, `password_changed_at`, `last_login_at`, `created_at`, `updated_at`

- **security_logs**: 安全/帳號操作審計紀錄
  - `id`, `actor_username`, `action`, `target_username`, `detail`, `created_at`

- **app_settings**: 系統設定鍵值（安全設定、備份設定、封面設定等）
  - `key`, `value`, `updated_at`

- **backup_logs**: 備份執行紀錄（本機 / 雲端結果摘要）
  - `id`, `created_at`, `trigger_mode`, `status`, `backup_file`, `file_size_bytes`, `error_message`

#### 信眾管理
- **people**: 信眾單表（含戶籍角色/停用狀態）
  - `id`, `household_id`, `role_in_household`, `status`, `name`, `gender`, `birthday_ad`, `birthday_lunar`, `lunar_is_leap`, `birth_time`, `age`, `age_offset`, `zodiac`, `phone_home`, `phone_mobile`, `address`, `zip_code`, `note`, `joined_at`

#### 財務管理
- **income_items**: 收入項目設定
  - `id`, `name`, `amount`

- **expense_items**: 支出項目設定
  - `id`, `name`, `amount`

- **transactions**: 收支明細（收入/支出共用）
  - `id`, `date`, `type`, `category_id`, `category_name`, `amount`, `payer_person_id`, `payer_name`, `handler`, `receipt_number`, `note`, `is_deleted`, `created_at`

#### 身份管理
- **member_identity**: 信眾身份類別
  - `id`, `name`

#### 活動管理
- **activities**: 活動資料
  - `id`, `name`, `activity_start_date`, `activity_end_date`, `note`, `status`, `created_at`, `updated_at`

- **activity_plans**: 活動方案
  - `id`, `activity_id`, `name`, `items`, `price_type`, `fixed_price`, `suggested_price`, `min_price`, `allow_qty`, `sort_order`, `is_active`, `created_at`, `updated_at`

- **activity_signups**: 活動報名人員
  - `id`, `activity_id`, `person_id`, `signup_time`, `note`, `total_amount`, `created_at`, `updated_at`, `is_paid`, `paid_at`, `payment_txn_id`, `payment_receipt_number`

- **activity_signup_plans**: 報名方案明細
  - `id`, `signup_id`, `plan_id`, `qty`, `unit_price_snapshot`, `amount_override`, `line_total`, `note`

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
│   ├── backup_runner.py
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
│   │   ├── setup_db.py
│   │   └── temple.db
│   ├── dialogs/
│   │   ├── __init__.py
│   │   ├── account_management_dialog.py
│   │   ├── activity_edit_dialog.py
│   │   ├── activity_household_signup_dialog.py
│   │   ├── activity_signup_edit_dialog.py
│   │   ├── backup_settings_dialog.py
│   │   ├── base_person_dialog.py
│   │   ├── cover_settings_dialog.py
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
│   ├── mailer/
│   │   ├── __init__.py
│   │   ├── mail_config.yaml
│   │   ├── outbox_db.py
│   │   ├── smtp_client.py
│   │   └── worker.py
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
│       ├── search_bar.py
│       └── spin_with_arrows.py
├── reports/
│   └── finance_report.csv
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_account_security.py
│   ├── test_activity_controller.py
│   ├── test_activity_manage_page.py
│   ├── test_activity_payment_mapping.py
│   ├── test_activity_signup_page.py
│   ├── test_activity_wenshu_dialog.py
│   ├── test_app_controller.py
│   ├── test_backup_controller.py
│   ├── test_backup_settings_dialog.py
│   ├── test_database.py
│   ├── test_date_utils.py
│   ├── test_expense_dialog.py
│   ├── test_finance_report_controller.py
│   ├── test_household_people_controller.py
│   ├── test_income_dialog.py
│   ├── test_income_expense_dialog.py
│   ├── test_login_dialog.py
│   ├── test_main_page_records_split.py
│   ├── test_main_window.py
│   ├── test_member_identity_dialog.py
│   ├── test_print_helper.py
│   ├── test_reactivate_person.py
│   └── test_receipt_logic.py
├── requirements.txt
├── README.md
├── test.ipynb
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
#### 使用者權限管理
- 四種角色：管理員、會計、委員、工作人員
- 安全密碼加密儲存
- 角色權限控制

#### 資料備份與維護
- 備份設定與執行（本機 / Google Drive）
- 備份紀錄查詢與失敗訊息檢視
- 備份排程（內建）

##### 資料備份
- 備份目的地：可同時備份到本機 + Google Drive（OAuth）
- 保留規則：本機與 Drive 都依「保留最新備份數」清理舊檔

##### 實際執行邏輯（避免混淆）：
1. `啟用自動備份`
   - 代表「允許排程判斷」生效。
2. `程式內建排程`
   - 主程式開啟時，依 UI 設定（每日/每週/每月、時間、週幾/幾號）判斷是否執行。
3. `改用 CLI/作業系統排程（已隱藏）`
   - 屬相容模式，UI 目前不顯示此選項。
   - 啟用時：由 OS 排程器呼叫 CLI（適合主程式未開啟）。
   - CLI 模式下，UI 頻率仍然有效：OS 只負責「呼叫」，真正是否執行仍依 UI 設定（每日/每週/每月、時間、週幾/幾號）。
   - 因此不會打架，是「OS 觸發 + UI 條件判斷」雙層機制。
4. `立即備份`
   - 按下就執行，不看排程時間。
   - 會依當下勾選目的地備份（本機 / Drive / 雙寫）。
5. Google Drive 採 OAuth：首次需人工授權一次，後續使用 token 自動續期。

##### 建議配置：
- 目前建議：使用「程式內建排程」（UI 可設定頻率/時間，操作較簡單）。
- 主程式持續開啟時（即使登出回登入頁），仍可由程式內排程持續執行。

##### 建議設定流程（上線順序）：
- 步驟 1：先準備 Google OAuth `credentials.json`（初始不需要 `token.json`）
- 步驟 2：先完成系統內備份設定與立即備份驗證
- 步驟 3：最後到系統內「資料備份」填入目的地、JSON 路徑、資料夾 ID 與保留數量
- 步驟 4：用「立即備份」驗證一次

##### Google Drive（OAuth）設定（詳細）：
1. 第一步：建立 OAuth 憑證
   - Google Cloud Console → 「API 和服務」→ 「憑證」
   - 點擊「+ 建立憑證」→ 「OAuth 用戶端 ID」
   - 應用程式類型選擇「桌面應用程式 (Desktop App)」
   - 名稱可自訂（例如 `MyPCBackup`），建立後下載 JSON
   - 將下載檔案重新命名為 `credentials.json`
   - 建議放在專案外路徑
   - 進入「OAuth 同意畫面」，確認 `User Type` 為「外部」
   - 在「測試使用者 (Test users)」加入你的 Gmail（未加入可能出現 `403 Access Blocked`）
2. 第二步：首次授權前的系統設定
   - 在「系統管理 -> 資料備份」先設定 `OAuth 憑證 JSON` 路徑（`credentials.json`）
   - `OAuth Token 檔案` 建議先指定儲存位置（建議專案外；首次授權後會建立/更新）
   - 按「Google 授權（首次）」完成人工授權
   - 授權後系統才會建立/更新 `token.json`，後續可自動 refresh
3. 第三步：設定目標資料夾
   - 建立（或選擇）備份資料夾，例如「自動化備份區」
   - 取得資料夾 ID（網址 `.../folders/<folder_id>`）
4. 第四步：確認 API 已啟用
   - Google Cloud Console → API 和服務 → 啟用 API 和服務
   - 確認 Google Drive API 為「已啟用」
5. 系統內設定
   - 在「系統管理 -> 資料備份」勾選 `Google Drive（OAuth）`
   - 填入 `OAuth 憑證 JSON`、`OAuth Token 檔案` 與 `Drive 資料夾 ID`
   - 可同時勾選本機備份，形成雙寫

##### CLI / OS 排程（相容模式，UI 目前隱藏）
- 目前 UI 策略：
  - 備份功能以「程式內建排程」為主（降低操作複雜度）
  - `CLI/OS 排程` 模式已先從 UI 隱藏
  - `schema` 與 `controller` 仍保留相容欄位/設定鍵，後續可恢復進階模式
- 使用時機：
  - 主程式未開啟也要自動備份時
- 注意：
  - OS 排程器只負責呼叫 CLI，是否真的執行仍依 UI 內儲存的頻率/時間設定判斷

##### Windows（工作排程器）：
1. 開啟「工作排程器」-> 建立工作
2. 觸發條件設每日/每週/每月
3. 動作填入：`python -m app.backup_runner --run-once`
4. 起始於（Start in）設為專案根目錄（含 `app/` 的資料夾）

##### macOS（launchd）：
1. 建立 plist 呼叫 `python -m app.backup_runner --run-once`
2. WorkingDirectory 指向專案根目錄
3. 以 `launchctl load` 啟用排程

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
pip install --upgrade pip
pip install --only-binary=:all: -r requirements.txt

# 執行測試
pytest

# 程式碼格式檢查（可選）
# flake8 app/
# black app/
```

說明：此專案統一使用 wheel 安裝（`--only-binary=:all:`），可避免本機從原始碼編譯 PyQt5 等 GUI 相依套件時，因缺少 `qmake`/編譯環境而失敗，安裝結果也更一致。

## 常見問題

### Q: 如何重置資料庫？
A: 刪除 `app/database/temple.db`，再執行 `python -m app.database.setup_db`

### Q: 忘記管理員密碼怎麼辦？
A: 可由其他管理員在「系統管理 -> 帳號管理」執行重設密碼；若系統中已無可登入管理員，請先備份資料庫後重建並重新建立管理員帳號。

### Q: 如何備份資料？
A: 請參考上方「系統管理功能 -> 資料備份」章節。

### Q: 系統支援哪些作業系統？
A: 支援 Windows、macOS、Linux 等所有支援 Python 和 PyQt5 的作業系統

## 授權與支援

本專案為寺廟管理系統，專為提升傳統廟宇數位化管理效率而設計。

如有技術問題或功能建議，歡迎透過 Issue 回報。
